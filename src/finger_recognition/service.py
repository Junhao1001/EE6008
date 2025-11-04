# src/finger_recognition/service.py
# -*- coding: utf-8 -*-
"""
FingerprintService：统一封装“采一次图 → 注册样本 → 登录比对”
底层直接调用你之前已稳定可用的 capture_core.py / matcher_core.py
"""

from pathlib import Path
import os
import shutil
import time

from config.paths import FINGERPRINT_DIR
from capture_core import capture_fingerprint_bmp
import matcher_core  # 提供 verify_fingerprint(live, enrolled, threshold, ratio)

class FingerprintService:
    def __init__(self):
        FINGERPRINT_DIR.mkdir(parents=True, exist_ok=True)

    # 采集一次，返回“临时采集文件路径”
    def capture_once(self) -> Path:
        """
        调用你已可用的 SDK 采集函数。返回 BMP 临时文件路径。
        """
        res = capture_fingerprint_bmp(
            on_event=None,
            max_tries=40,
            try_interval=0.7,
            pre_settle_time=1.2
        )
        # 正常 OK
        if res and res.get("ok") and res.get("path") and os.path.exists(res["path"]):
            return Path(res["path"])
        # 兜底：有些设备会先 saved 再返回非 0；这里尝试从 fptemp 中取“最新一张”
        fptemp = Path(__file__).resolve().parent.parent / "fptemp"
        if fptemp.exists():
            latest = sorted(fptemp.glob("*.bmp"), key=os.path.getmtime, reverse=True)
            if latest:
                return latest[0]

        reason = (res or {}).get("reason", "unknown")
        raise RuntimeError(f"fingerprint capture failed: {reason}")

    # 注册：把采集到的临时图移动/覆盖到 data/fingerprints/<username>.bmp
    def enroll(self, username: str) -> Path:
        tmp = self.capture_once()
        dst = FINGERPRINT_DIR / f"{username}.bmp"
        # 如果目标已存在就覆盖
        if dst.exists():
            try:
                dst.unlink()
            except Exception:
                pass
        shutil.move(str(tmp), str(dst))
        return dst

    # 登录比对：现场采一张 + 与注册样本比对（参数与你之前保持一致）
    def verify(self, enrolled_path: Path, threshold: int = 15, ratio: float = 0.8):
        """
        返回 (ok: bool, msg: str)
        """
        live = self.capture_once()
        ok, msg = matcher_core.verify_fingerprint(
            str(live), str(enrolled_path),
            threshold=threshold, ratio=ratio
        )
        return ok, msg
