# capture_core.py
# -*- coding: utf-8 -*-
"""
ZK Fingerprint Device Image Capture Interface (Saves BMP; Standard Library Implementation)
- Starts capture attempt immediately after running (no need to press Enter)
- Passes UI text via callbacks/events (ready/attempt/busy/retry/saved/error)
- Save location: <script directory>/fptemp/
- File name: YYYYMMDDHHMM.bmp (automatically appends _1, _2 in the same minute to avoid duplication)
"""

import os, sys, struct, time, ctypes as C
from typing import Callable, Dict, Generator, Optional, Tuple

# ========== Fix path to script directory ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
FP_TEMP_DIR = os.path.join(BASE_DIR, "fptemp")
os.makedirs(FP_TEMP_DIR, exist_ok=True)

# ========== DLL Loading ==========
CANDIDATE_DLLS = ["libzkfp.dll", "zkfp.dll", "libzkfp_x64.dll", "zkfp_x64.dll"]

def _load_dll():
    last_error = None
    for name in CANDIDATE_DLLS:
        try:
            return C.WinDLL(name)
        except Exception as e:
            last_error = e
    raise OSError(f"Failed to load fingerprint DLL. Please confirm the DLL filename/path and bitness match. Last error: {last_error}")

zk = _load_dll()

# ========== C Types & Function Prototypes ==========
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

# ========== Parameter Codes ==========
PARAM_IMG_W     = 1
PARAM_IMG_H     = 2
PARAM_IMG_BYTES = 106

# ========== Helpers ==========
def _get_param_int(hdev: HANDLE, code: int, nbytes: int = 4) -> int:
    """Get parameter (integer type)"""
    buf = (C.c_ubyte * nbytes)()
    size = UINT(nbytes)
    ret = zk.ZKFPM_GetParameters(hdev, code, buf, C.byref(size))
    if ret != 0:
        raise RuntimeError(f"GetParameters({code}) failed, ret={ret}")
    return int.from_bytes(bytes(buf[:size.value]), "little", signed=False)

def _save_gray8_to_bmp(raw_bytes: bytes, w: int, h: int, out_path: str) -> None:
    """Save 8-bit grayscale image to BMP format"""
    if len(raw_bytes) < w * h:
        raise ValueError(f"Insufficient raw data: {len(raw_bytes)} < {w*h}")
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
        palette += bytes([i, i, i, 0])  # BGRA format

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
    """Generate timestamped BMP path (avoids duplication in the same minute)"""
    ts = time.strftime("%Y%m%d%H%M")
    base = os.path.join(FP_TEMP_DIR, ts)
    path = base + ".bmp"
    i = 1
    while os.path.exists(path):
        path = f"{base}_{i}.bmp"
        i += 1
    return path

# ========== Event Generator ==========
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
        device_count = zk.ZKFPM_GetDeviceCount()
        if device_count <= 0:
            result = {"ok": False, "path": None, "reason": f"no device (count={device_count})"}
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
                width = _get_param_int(hdev, PARAM_IMG_W)
                height = _get_param_int(hdev, PARAM_IMG_H)
            except Exception as e:
                result = {"ok": False, "path": None, "reason": f"GetParameters error: {e}"}
                yield ("error", {"message": result["reason"]})
                return result

            buf = (C.c_ubyte * img_bytes)()
            yield ("ready", {"message": f"device ready: {width}x{height}, bytes={img_bytes}"})
            if pre_settle_time > 0:
                time.sleep(pre_settle_time)

            last_return_code = None
            for attempt in range(1, max_tries + 1):
                yield ("attempt", {"index": attempt, "max": max_tries})
                return_code = zk.ZKFPM_AcquireFingerprintImage(hdev, buf, C.c_uint(img_bytes))
                last_return_code = return_code

                if return_code == 0:
                    raw_data = bytes(buf)
                    if len(raw_data) < width * height:
                        result = {"ok": False, "path": None, "reason": f"payload too small {len(raw_data)}/{width*height}"}
                        yield ("error", {"message": result["reason"]})
                        return result
                    raw_data = raw_data[:width * height]
                    output_path = _make_timestamp_bmp_path()
                    try:
                        _save_gray8_to_bmp(raw_data, width, height, output_path)
                    except Exception as e:
                        result = {"ok": False, "path": None, "reason": f"save bmp error: {e}"}
                        yield ("error", {"message": result["reason"]})
                        return result
                    yield ("saved", {"path": output_path, "width": width, "height": height, "tries": attempt})
                    return {"ok": True, "path": output_path, "width": width, "height": height, "tries": attempt}

                elif return_code == -12:
                    yield ("busy", {"ret": return_code})
                elif return_code == -8:
                    yield ("retry", {"ret": return_code})
                else:
                    result = {"ok": False, "path": None, "reason": f"AcquireFingerprintImage ret={return_code}"}
                    yield ("error", {"message": result["reason"]})
                    return result

                time.sleep(try_interval)

            result = {"ok": False, "path": None, "reason": "max tries exceeded", "last_ret": last_return_code}
            yield ("error", {"message": result["reason"], "last_ret": last_return_code})
            return result

        finally:
            zk.ZKFPM_CloseDevice(hdev)
    finally:
        zk.ZKFPM_Terminate()

# ========== Callback-based Wrapper (Fixed: Ensure getting StopIteration.value) ==========
def capture_fingerprint_bmp(
    on_event: Optional[Callable[[str, Dict], None]] = None,
    max_tries: int = 30,
    try_interval: float = 0.6,
    pre_settle_time: float = 1.2
) -> Dict:
    """
    Callback-based wrapper: Manually iterate the generator with next() to ensure getting StopIteration.value.
    """
    gen = capture_fingerprint_bmp_iter(max_tries, try_interval, pre_settle_time)
    final_result = None
    try:
        while True:
            try:
                event, data = next(gen)
            except StopIteration as stop:
                final_result = stop.value
                break
            except Exception as e:
                # Handle exceptions thrown by the generator itself
                return {"ok": False, "path": None, "reason": f"generator exception: {e}"}

            if on_event:
                try:
                    on_event(event, data)
                except Exception:
                    # Callback exceptions should not affect the main process
                    pass

    except Exception as e:
        return {"ok": False, "path": None, "reason": f"exception: {e}"}

    if not final_result:
        return {"ok": False, "path": None, "reason": "generator finished without result"}
    return final_result