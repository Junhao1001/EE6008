# -*- coding: utf-8 -*-
"""
EE6008 Multimodal Login System
- Username/Password + Face + Fingerprint
- Face:
    Register -> face_recorder.FaceRecorder.run(username)
    Verify   -> face_detector.FaceDetector.run(username)
  (自动尝试在 src/ 或 src/face_recognition/ 下导入)
- Fingerprint:
    capture_core.capture_fingerprint_bmp + matcher_core.verify_fingerprint
"""

import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

# ---------------- Paths ----------------
BASE_DIR = Path(__file__).resolve().parent          # .../src
PROJECT_ROOT = BASE_DIR.parent                      # repo root

for p in (str(BASE_DIR), str(PROJECT_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

# ---------------- Required (project) ----------------
from user_manage import UserManager
from config.paths import FINGERPRINT_DIR

# ---------------- Fingerprint SDK ----------------
from capture_core import capture_fingerprint_bmp
import matcher_core

# ---------------- Face modules (固定绑定到你同学实现) ----------------
FaceRecorderClass = None   # 注册用
FaceDetectorClass = None   # 登录验证用

# FaceRecorder：优先 src/face_recognition/face_recorder.py，其次 src/face_recorder.py
try:
    from face_recognition.face_recorder import FaceRecorder as _FR
    FaceRecorderClass = _FR
except Exception:
    try:
        from face_recorder import FaceRecorder as _FR
        FaceRecorderClass = _FR
    except Exception:
        FaceRecorderClass = None

# FaceDetector：优先 src/face_recognition/face_detector.py，其次 src/face_detector.py
try:
    from face_recognition.face_detector import FaceDetector as _FD
    FaceDetectorClass = _FD
except Exception:
    try:
        from face_detector import FaceDetector as _FD
        FaceDetectorClass = _FD
    except Exception:
        FaceDetectorClass = None


# ---------------- Helpers: 调用你同学的注册/验证 ----------------
def _face_enroll(username: str):
    """
    使用 FaceRecorder.run(name) 执行人脸注册。
    返回 (ok, msg)
    """
    if FaceRecorderClass is None:
        raise ImportError("FaceRecorder not found (face_recognition/face_recorder.py).")
    rec = FaceRecorderClass()
    ok = bool(rec.run(username))    # True=注册成功（会写入人脸库）
    return ok, "FaceRecorder.run"


def _face_verify(username: str):
    """
    使用 FaceDetector.run(username) 执行人脸验证。
    返回 (ok, msg)
    """
    if FaceDetectorClass is None:
        raise ImportError("FaceDetector not found (face_recognition/face_detector.py).")
    det = FaceDetectorClass()
    ok = bool(det.run(username))    # True=识别到的身份等于 username
    return ok, "FaceDetector.run"


# ---------------- Fingerprint Service ----------------
class FingerprintService:
    """
    - enroll(username): 采一张并保存到 data/fingerprints/<username>.bmp
    - verify(enrolled_path): 现场采一张并与样本比对
    """
    def __init__(self):
        FINGERPRINT_DIR.mkdir(parents=True, exist_ok=True)

    def _capture_once(self) -> Path:
        res = capture_fingerprint_bmp(
            on_event=None,
            max_tries=40,
            try_interval=0.7,
            pre_settle_time=1.2
        )
        if res and res.get("ok") and res.get("path") and os.path.exists(res["path"]):
            return Path(res["path"])

        # 兜底：部分驱动先保存再返回非零，尝试取 src/fptemp 最新一张
        fptemp = BASE_DIR / "fptemp"
        if fptemp.exists():
            cand = sorted(fptemp.glob("*.bmp"), key=os.path.getmtime, reverse=True)
            if cand:
                return cand[0]

        reason = (res or {}).get("reason", "unknown")
        raise RuntimeError(f"fingerprint capture failed: {reason}")

    def enroll(self, username: str) -> Path:
        tmp = self._capture_once()
        dst = FINGERPRINT_DIR / f"{username}.bmp"
        try:
            if dst.exists():
                dst.unlink()
        except Exception:
            pass
        tmp.replace(dst)
        return dst

    def verify(self, enrolled_path: Path, threshold: int = 15, ratio: float = 0.8):
        live = self._capture_once()
        ok, msg = matcher_core.verify_fingerprint(
            str(live), str(enrolled_path),
            threshold=threshold, ratio=ratio
        )
        return ok, msg


# ---------------- UI: Register / Login / Manage ----------------
class RegisterWindow(tk.Toplevel):
    def __init__(self, master, user_manager: UserManager):
        super().__init__(master)
        self.title("Register")
        self.geometry("520x380")
        self.resizable(False, False)

        self.user_manager = user_manager
        self.new_user = tk.StringVar()
        self.new_pwd = tk.StringVar()
        self.face_registered = tk.BooleanVar(value=False)
        self.fingerprint_registered = tk.BooleanVar(value=False)

        frm = ttk.LabelFrame(self, text="Create Account", padding=10)
        frm.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(frm, text="Username:").grid(row=0, column=0, sticky="e", padx=6, pady=6)
        ttk.Entry(frm, textvariable=self.new_user, width=28).grid(row=0, column=1, sticky="w", padx=6, pady=6)

        ttk.Label(frm, text="Password:").grid(row=1, column=0, sticky="e", padx=6, pady=6)
        ttk.Entry(frm, textvariable=self.new_pwd, show="*", width=28).grid(row=1, column=1, sticky="w", padx=6, pady=6)

        face_box = ttk.LabelFrame(frm, text="Face Enrollment", padding=8)
        face_box.grid(row=2, column=0, columnspan=2, sticky="ew", padx=4, pady=6)
        ttk.Button(face_box, text="Enroll Face", command=self.register_face).grid(row=0, column=0, padx=6, pady=4)
        ttk.Label(face_box, textvariable=self.face_registered).grid(row=0, column=1, padx=6, pady=4, sticky="w")

        fp_box = ttk.LabelFrame(frm, text="Fingerprint Enrollment", padding=8)
        fp_box.grid(row=3, column=0, columnspan=2, sticky="ew", padx=4, pady=6)
        ttk.Button(fp_box, text="Enroll Fingerprint", command=self.register_fingerprint).grid(row=0, column=0, padx=6, pady=4)
        ttk.Label(fp_box, textvariable=self.fingerprint_registered).grid(row=0, column=1, padx=6, pady=4, sticky="w")

        ttk.Button(frm, text="Complete Registration", command=self.complete_registration)\
            .grid(row=4, column=0, columnspan=2, pady=10)

    def register_face(self):
        user = (self.new_user.get() or "").strip()
        pwd  = (self.new_pwd.get() or "").strip()
        if not user or not pwd:
            messagebox.showwarning("Notice", "Please input username and password first.")
            return

        # 确保用户存在
        if not self.user_manager.user_exists(user):
            if not self.user_manager.add_user(user, pwd):
                messagebox.showerror("Error", "Username already exists.")
                return

        try:
            ok, msg = _face_enroll(user)
            if ok:
                self.user_manager.set_face_registered(user, True)
                self.face_registered.set(True)
                messagebox.showinfo("Info", f"Face enrolled. {msg}")
            else:
                messagebox.showerror("Error", f"Face enrollment failed. {msg}")
        except Exception as e:
            messagebox.showerror("Error", f"Face enrollment error:\n{e}")

    def register_fingerprint(self):
        user = (self.new_user.get() or "").strip()
        pwd  = (self.new_pwd.get() or "").strip()
        if not user or not pwd:
            messagebox.showwarning("Notice", "Please input username and password first.")
            return

        if not self.user_manager.user_exists(user):
            if not self.user_manager.add_user(user, pwd):
                messagebox.showerror("Error", "Username already exists.")
                return

        try:
            svc = FingerprintService()
            dst = svc.enroll(user)  # data/fingerprints/<username>.bmp
            self.user_manager.set_fingerprint(user, str(dst))
            self.fingerprint_registered.set(True)
            messagebox.showinfo("Info", f"Fingerprint enrolled: {dst.name}")
        except Exception as e:
            messagebox.showerror("Error", f"Fingerprint enrollment failed:\n{e}")

    def complete_registration(self):
        user = (self.new_user.get() or "").strip()
        if not user:
            messagebox.showwarning("Notice", "Please input username first.")
            return
        if not self.user_manager.is_face_registered(user):
            messagebox.showwarning("Notice", "Face not enrolled yet.")
            return
        if not self.user_manager.is_fingerprint_registered(user):
            messagebox.showwarning("Notice", "Fingerprint not enrolled yet.")
            return
        messagebox.showinfo("Success", "Registration completed.")
        self.destroy()


class LoginWindow(tk.Toplevel):
    def __init__(self, master, user_manager: UserManager):
        super().__init__(master)
        self.title("Login")
        self.geometry("520x260")
        self.resizable(False, False)

        self.user_manager = user_manager
        self.username = tk.StringVar()
        self.password = tk.StringVar()

        frm = ttk.LabelFrame(self, text="Sign In", padding=10)
        frm.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(frm, text="Username:").grid(row=0, column=0, sticky="e", padx=6, pady=6)
        ttk.Entry(frm, textvariable=self.username, width=28).grid(row=0, column=1, sticky="w", padx=6, pady=6)

        ttk.Label(frm, text="Password:").grid(row=1, column=0, sticky="e", padx=6, pady=6)
        ttk.Entry(frm, textvariable=self.password, show="*", width=28).grid(row=1, column=1, sticky="w", padx=6, pady=6)

        ttk.Button(frm, text="Login", command=self.try_login).grid(row=2, column=0, padx=6, pady=10)
        ttk.Button(frm, text="Register", command=self.open_register).grid(row=2, column=1, padx=6, pady=10, sticky="w")

    def open_register(self):
        RegisterWindow(self, self.user_manager)

    def try_login(self):
        username = (self.username.get() or "").strip()
        password = (self.password.get() or "").strip()
        if not self.user_manager.verify_user(username, password):
            messagebox.showerror("Failed", "Invalid username or password.")
            return

        # 1) 人脸验证
        if not self.verify_face(username):
            return

        # 2) 指纹验证
        if not self.verify_fingerprint(username):
            return

        self.switch_to_success(username)

    def verify_face(self, username: str) -> bool:
        try:
            ok, msg = _face_verify(username)
            if ok:
                return True
            messagebox.showerror("Failed", f"Face verification failed. {msg}")
            return False
        except Exception as e:
            messagebox.showerror("Error", f"Face verification error:\n{e}")
            return False

    def verify_fingerprint(self, username: str) -> bool:
        try:
            enrolled = self.user_manager.get_fingerprint_path(username)
            if not enrolled or not os.path.exists(enrolled):
                messagebox.showerror("Error", "No enrolled fingerprint for this user. Please register first.")
                return False

            svc = FingerprintService()
            ok, msg = svc.verify(Path(enrolled), threshold=15, ratio=0.8)  # 可按需调阈值
            if ok:
                messagebox.showinfo("Success", f"Fingerprint verified.\n{msg}")
                return True
            else:
                messagebox.showerror("Failed", f"Fingerprint not matched.\n{msg}")
                return False
        except Exception as e:
            messagebox.showerror("Error", f"Fingerprint verification error:\n{e}")
            return False

    def switch_to_success(self, username: str):
        messagebox.showinfo("Success", f"Login success. Welcome, {username}!")
        self.destroy()


class ManageWindow(tk.Toplevel):
    def __init__(self, master, user_manager: UserManager):
        super().__init__(master)
        self.title("User Management")
        self.geometry("520x360")
        self.resizable(False, False)

        self.user_manager = user_manager
        self.users_list = tk.Listbox(self)
        self.users_list.pack(fill="both", expand=True, padx=10, pady=10)

        btn_bar = ttk.Frame(self)
        btn_bar.pack(fill="x", padx=10, pady=6)
        ttk.Button(btn_bar, text="Refresh", command=self.refresh).pack(side="left", padx=4)
        ttk.Button(btn_bar, text="Delete", command=self.on_delete).pack(side="left", padx=4)

        self.refresh()

    def refresh(self):
        self.users_list.delete(0, tk.END)
        for u in self.user_manager.get_all_users():
            flags = []
            if self.user_manager.is_face_registered(u):
                flags.append("face")
            if self.user_manager.is_fingerprint_registered(u):
                flags.append("fp")
            suffix = f" [{','.join(flags)}]" if flags else ""
            self.users_list.insert(tk.END, u + suffix)

    def on_delete(self):
        sel = self.users_list.curselection()
        if not sel:
            messagebox.showwarning("Notice", "Please select a user.")
            return
        username = self.users_list.get(sel[0]).split(" [")[0]
        if not messagebox.askyesno("Confirm", f"Delete user '{username}' ?"):
            return

        if self.delete_user(username):
            messagebox.showinfo("Success", "User deleted.")
            self.refresh()
        else:
            messagebox.showerror("Failed", "Delete failed.")

    def delete_user(self, username: str) -> bool:
        # 1) 指纹样本路径
        fp_path = self.user_manager.get_fingerprint_path(username)

        # 2) 删用户记录
        if not self.user_manager.delete_user(username):
            return False

        # 3) 删指纹样本文件
        try:
            if fp_path and os.path.exists(fp_path):
                os.remove(fp_path)
        except Exception:
            pass

        # 若你们有人脸库删除接口，可在此追加（例如 FaceDatabase.delete_faces(username)）
        # 你同学的人脸库清理逻辑如果在别处，这里可留空或按需扩展。

        return True


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("EE6008 Multimodal Login")
        self.geometry("400x240")
        self.resizable(False, False)

        self.user_manager = UserManager()

        frm = ttk.LabelFrame(self, text="Actions", padding=12)
        frm.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Button(frm, text="Login", command=self.open_login)\
            .grid(row=0, column=0, padx=8, pady=8, sticky="ew")
        ttk.Button(frm, text="Register", command=self.open_register)\
            .grid(row=0, column=1, padx=8, pady=8, sticky="ew")
        ttk.Button(frm, text="Manage Users", command=self.open_manage)\
            .grid(row=1, column=0, columnspan=2, padx=8, pady=8, sticky="ew")

    def open_login(self):
        LoginWindow(self, self.user_manager)

    def open_register(self):
        RegisterWindow(self, self.user_manager)

    def open_manage(self):
        ManageWindow(self, self.user_manager)


if __name__ == "__main__":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = App()
    app.mainloop()
