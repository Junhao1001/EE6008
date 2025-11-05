# matcher_core.py
import os, tempfile, shutil
from typing import Tuple

_USE_INTERNAL_IDENTIFY = False
try:
    from fingerprint_core import identify_in_db_v2
    _USE_INTERNAL_IDENTIFY = True
except Exception:
    _USE_INTERNAL_IDENTIFY = False

def verify_fingerprint(live_img_path: str, enrolled_img_path: str,
                       threshold:int=15, ratio:float=0.8) -> Tuple[bool, str]:
    """
    返回 (ok, message)
    ok=True 表示通过；False 表示失败
    """
    if not os.path.exists(live_img_path):
        return False, f"live image not found: {live_img_path}"
    if not os.path.exists(enrolled_img_path):
        return False, f"enrolled image not found: {enrolled_img_path}"

    if _USE_INTERNAL_IDENTIFY:
        # 把注册图当作一个“小数据库”
        tmpdir = tempfile.mkdtemp(prefix="fpdb_")
        try:
            dst = os.path.join(tmpdir, os.path.basename(enrolled_img_path))
            shutil.copyfile(enrolled_img_path, dst)
            res = identify_in_db_v2(
                live_img_path, tmpdir,
                ratio=ratio, not_found_threshold=threshold,
                save_vis=False, unify_to_280x360=True, use_clahe=True
            )
            return (bool(res.ok), res.message or ("OK" if res.ok else "NOT OK"))
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    else:
        # 退化：使用简易 SIFT 比对（依赖 opencv-contrib-python）
        try:
            import cv2, numpy as np
        except Exception:
            return False, "No fingerprint_core and OpenCV not available"
        img1 = cv2.imread(live_img_path, cv2.IMREAD_GRAYSCALE)
        img2 = cv2.imread(enrolled_img_path, cv2.IMREAD_GRAYSCALE)
        if img1 is None or img2 is None:
            return False, "failed to read images"
        sift = cv2.SIFT_create()
        kp1, des1 = sift.detectAndCompute(img1, None)
        kp2, des2 = sift.detectAndCompute(img2, None)
        if des1 is None or des2 is None:
            return False, "insufficient features"
        flann = cv2.FlannBasedMatcher(dict(algorithm=1, trees=5), dict(checks=64))
        knn = flann.knnMatch(des1, des2, k=2)
        good = 0
        for pair in knn:
            if len(pair) < 2: continue
            m, n = pair
            if m.distance < ratio * n.distance:
                good += 1
        ok = good >= threshold
        return ok, (f"good={good} >= {threshold}" if ok else f"good={good} < {threshold}")
