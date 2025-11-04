# capture_core.py
# -*- coding: utf-8 -*-
"""
ZK 指纹仪采图接口（保存 BMP；标准库实现）
- 运行即开始尝试采集（无需按 Enter）
- 通过回调/事件传递 UI 文本（ready/attempt/busy/retry/saved/error）
- 保存位置：<脚本目录>/fptemp/
- 文件名：YYYYMMDDHHMM.bmp（同分钟自动加 _1, _2 防重）
"""

import os, sys, struct, time, ctypes as C
from typing import Callable, Dict, Generator, Optional, Tuple

# ========== 路径固定到脚本目录 ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
FP_TEMP_DIR = os.path.join(BASE_DIR, "fptemp")
os.makedirs(FP_TEMP_DIR, exist_ok=True)

# ========== DLL 载入 ==========
CANDIDATE_DLLS = ["libzkfp.dll", "zkfp.dll", "libzkfp_x64.dll", "zkfp_x64.dll"]

def _load_dll():
    last = None
    for name in CANDIDATE_DLLS:
        try:
            return C.WinDLL(name)
        except Exception as e:
            last = e
    raise OSError(f"无法加载指纹 DLL，请确认 DLL 文件名/路径及位数匹配。最后错误: {last}")

zk = _load_dll()

# ========== C 类型 & 函数原型 ==========
HANDLE = C.c_void_p
UINT   = C.c_uint
INT    = C.c_int
U8P    = C.POINTER(C.c_ubyte)

zk.ZKFPM_Init.restype = INT
zk.ZKFPM_Terminate.restype = INT
zk.ZKFPM_GetDeviceCount.restype = INT

zk.ZKFPM_OpenDevice.argtypes = [INT]
zk.ZKFPM_OpenDevice.restype  = HANDLE
zk.ZKFPM_CloseDevice.argtypes = [HANDLE]
zk.ZKFPM_CloseDevice.restype  = INT

zk.ZKFPM_GetParameters.argtypes = [HANDLE, INT, U8P, C.POINTER(UINT)]
zk.ZKFPM_GetParameters.restype  = INT

zk.ZKFPM_AcquireFingerprintImage.argtypes = [HANDLE, U8P, UINT]
zk.ZKFPM_AcquireFingerprintImage.restype  = INT

# ========== 参数代码 ==========
PARAM_IMG_W     = 1
PARAM_IMG_H     = 2
PARAM_IMG_BYTES = 106

# ========== 辅助 ==========
def _get_param_int(hdev: HANDLE, code: int, nbytes: int = 4) -> int:
    buf = (C.c_ubyte * nbytes)()
    size = UINT(nbytes)
    ret = zk.ZKFPM_GetParameters(hdev, code, buf, C.byref(size))
    if ret != 0:
        raise RuntimeError(f"GetParameters({code}) 失败, ret={ret}")
    return int.from_bytes(bytes(buf[:size.value]), "little", signed=False)

def _save_gray8_to_bmp(raw_bytes: bytes, w: int, h: int, out_path: str) -> None:
    if len(raw_bytes) < w * h:
        raise ValueError(f"原始数据不足：{len(raw_bytes)} < {w*h}")
    row_stride = (w + 3) & ~3
    padding = row_stride - w
    pixel_array_size = row_stride * h

    bfOffBits = 14 + 40 + 256 * 4
    bfSize = bfOffBits + pixel_array_size
    file_header = struct.pack("<2sIHHI", b"BM", bfSize, 0, 0, bfOffBits)
    info_header = struct.pack("<IIIHHIIIIII",
                              40, w, h, 1, 8, 0, pixel_array_size,
                              2835, 2835, 256, 0)

    palette = bytearray()
    for i in range(256):
        palette += bytes([i, i, i, 0])  # BGRA

    dst = bytearray()
    for y in range(h - 1, -1, -1):
        s = y * w
        dst.extend(raw_bytes[s:s + w])
        if padding:
            dst.extend(b"\x00" * padding)

    with open(out_path, "wb") as f:
        f.write(file_header)
        f.write(info_header)
        f.write(palette)
        f.write(dst)

def _make_timestamp_bmp_path() -> str:
    ts = time.strftime("%Y%m%d%H%M")
    base = os.path.join(FP_TEMP_DIR, ts)
    path = base + ".bmp"
    i = 1
    while os.path.exists(path):
        path = f"{base}_{i}.bmp"
        i += 1
    return path

# ========== 事件生成器 ==========
def capture_fingerprint_bmp_iter(
    max_tries: int = 30,
    try_interval: float = 0.6,
    pre_settle_time: float = 1.2
) -> Generator[Tuple[str, Dict], None, Dict]:
    r = zk.ZKFPM_Init()
    if r not in (0, 1):
        result = {"ok": False, "path": None, "reason": f"ZKFPM_Init ret={r}"}
        yield ("error", {"message": result["reason"]})
        return result
    try:
        n = zk.ZKFPM_GetDeviceCount()
        if n <= 0:
            result = {"ok": False, "path": None, "reason": f"no device (count={n})"}
            yield ("error", {"message": result["reason"]})
            return result

        hdev = zk.ZKFPM_OpenDevice(0)
        if not hdev:
            result = {"ok": False, "path": None, "reason": "OpenDevice(0) failed"}
            yield ("error", {"message": result["reason"]})
            return result
        try:
            try:
                img_bytes = _get_param_int(hdev, PARAM_IMG_BYTES)
                w = _get_param_int(hdev, PARAM_IMG_W)
                h = _get_param_int(hdev, PARAM_IMG_H)
            except Exception as e:
                result = {"ok": False, "path": None, "reason": f"GetParameters error: {e}"}
                yield ("error", {"message": result["reason"]})
                return result

            buf = (C.c_ubyte * img_bytes)()
            yield ("ready", {"message": f"device ready: {w}x{h}, bytes={img_bytes}"})
            if pre_settle_time > 0:
                time.sleep(pre_settle_time)

            last_ret = None
            for i in range(1, max_tries + 1):
                yield ("attempt", {"index": i, "max": max_tries})
                ret = zk.ZKFPM_AcquireFingerprintImage(hdev, buf, C.c_uint(img_bytes))
                last_ret = ret

                if ret == 0:
                    raw = bytes(buf)
                    if len(raw) < w * h:
                        result = {"ok": False, "path": None, "reason": f"payload too small {len(raw)}/{w*h}"}
                        yield ("error", {"message": result["reason"]})
                        return result
                    raw = raw[:w * h]
                    out_path = _make_timestamp_bmp_path()
                    try:
                        _save_gray8_to_bmp(raw, w, h, out_path)
                    except Exception as e:
                        result = {"ok": False, "path": None, "reason": f"save bmp error: {e}"}
                        yield ("error", {"message": result["reason"]})
                        return result
                    yield ("saved", {"path": out_path, "width": w, "height": h, "tries": i})
                    return {"ok": True, "path": out_path, "width": w, "height": h, "tries": i}

                elif ret == -12:
                    yield ("busy", {"ret": ret})
                elif ret == -8:
                    yield ("retry", {"ret": ret})
                else:
                    result = {"ok": False, "path": None, "reason": f"AcquireFingerprintImage ret={ret}"}
                    yield ("error", {"message": result["reason"]})
                    return result

                time.sleep(try_interval)

            result = {"ok": False, "path": None, "reason": "max tries exceeded", "last_ret": last_ret}
            yield ("error", {"message": result["reason"], "last_ret": last_ret})
            return result

        finally:
            zk.ZKFPM_CloseDevice(hdev)
    finally:
        zk.ZKFPM_Terminate()

# ========== 回调式包装（修复：保证拿到 StopIteration.value） ==========
def capture_fingerprint_bmp(
    on_event: Optional[Callable[[str, Dict], None]] = None,
    max_tries: int = 30,
    try_interval: float = 0.6,
    pre_settle_time: float = 1.2
) -> Dict:
    """
    回调式包装：手动 next() 迭代生成器，确保拿到 StopIteration.value。
    """
    gen = capture_fingerprint_bmp_iter(max_tries, try_interval, pre_settle_time)
    final_result = None
    try:
        while True:
            try:
                ev, data = next(gen)
            except StopIteration as stop:
                final_result = stop.value
                break
            except Exception as e:
                # 生成器本身抛出异常
                return {"ok": False, "path": None, "reason": f"generator exception: {e}"}

            if on_event:
                try:
                    on_event(ev, data)
                except Exception:
                    # 回调异常不影响流程
                    pass

    except Exception as e:
        return {"ok": False, "path": None, "reason": f"exception: {e}"}

    if not final_result:
        return {"ok": False, "path": None, "reason": "generator finished without result"}
    return final_result
