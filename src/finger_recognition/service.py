# src/finger_recognition/service.py
# -*- coding: utf-8 -*-
"""
FingerprintService: Unified encapsulation of "capture one image → enroll sample → login verification"
Directly calls capture_core.py / matcher_core.py at the bottom layer
"""

from pathlib import Path
import os
import shutil
import time

from config.paths import FINGERPRINT_DIR
from capture_core import capture_fingerprint_bmp
import matcher_core  # Provides verify_fingerprint(live, enrolled, threshold, ratio)

class FingerprintService:
    def __init__(self):
        FINGERPRINT_DIR.mkdir(parents=True, exist_ok=True)

    # Capture once and return the "temporary captured file path"
    def capture_once(self) -> Path:
        """
        Call the available SDK capture function. Returns the path of the temporary BMP file.
        """
        res = capture_fingerprint_bmp(
            on_event=None,
            max_tries=40,
            try_interval=0.7,
            pre_settle_time=1.2
        )
        # Normal success case
        if res and res.get("ok") and res.get("path") and os.path.exists(res["path"]):
            return Path(res["path"])
        # Fallback: Some devices save first then return non-0; try to get the "latest image" from fptemp
        fptemp = Path(__file__).resolve().parent.parent / "fptemp"
        if fptemp.exists():
            latest = sorted(fptemp.glob("*.bmp"), key=os.path.getmtime, reverse=True)
            if latest:
                return latest[0]

        reason = (res or {}).get("reason", "unknown")
        raise RuntimeError(f"fingerprint capture failed: {reason}")

    # Enroll: Move/overwrite the captured temporary image to data/fingerprints/<username>.bmp
    def enroll(self, username: str) -> Path:
        tmp = self.capture_once()
        dst = FINGERPRINT_DIR / f"{username}.bmp"
        # Overwrite if the target file already exists
        if dst.exists():
            try:
                dst.unlink()
            except Exception:
                pass
        shutil.move(str(tmp), str(dst))
        return dst

    # Login verification: Capture one live image + match with enrolled sample (parameters consistent with your previous settings)
    def verify(self, enrolled_path: Path, threshold: int = 15, ratio: float = 0.8):
        """
        Returns (ok: bool, msg: str)
        """
        live = self.capture_once()
        ok, msg = matcher_core.verify_fingerprint(
            str(live), str(enrolled_path),
            threshold=threshold, ratio=ratio
        )
        return ok, msg