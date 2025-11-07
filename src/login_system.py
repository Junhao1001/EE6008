# -*- coding: utf-8 -*-
"""
EE6008 Multimodal Login System - Single Window, View Switching (no top nav)
- Views: Login / Register / Manage Users / Welcome
- Default shows Login view; buttons在页面内跳转
- Face: FaceRecorder.run (enroll), FaceDetector.run (verify)
- Fingerprint: finger_recognition.capture_core + finger_recognition.matcher_core
- Delete user: 同时删除指纹样本与人脸数据
- UI: ttkbootstrap (自动降级到 Tk)
- Register: 指纹采集按钮提示 + 10s 超时
- Login: 分步提示 -> 账号密码通过后提示“进行人脸验证”；人脸通过后提示“进行指纹验证”
"""

import os
import sys
import json
import shutil
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

# ---------------- Paths ----------------
BASE_DIR = Path(__file__).resolve().parent        # .../src
PROJECT_ROOT = BASE_DIR.parent
for p in (str(BASE_DIR), str(PROJECT_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

# ---------------- Project imports ----------------
from user_manage import UserManager
from config.paths import FINGERPRINT_DIR
try:
    from config.paths import FACE_DATA_FILE, FACE_SAMPLE_DIR
except Exception:
    FACE_DATA_FILE = PROJECT_ROOT / "data" / "face_data.json"
    FACE_SAMPLE_DIR = PROJECT_ROOT / "data" / "face_samples"

# 指纹核心
from finger_recognition.capture_core import capture_fingerprint_bmp
from finger_recognition import matcher_core

# 主题助手
from ui_theme import build_root

# ---------------- Face modules ----------------
FaceRecorderClass = None
FaceDetectorClass = None
FaceDBClass = None

try:
    from face_recognition.face_recorder import FaceRecorder as _FR
    FaceRecorderClass = _FR
except Exception:
    try:
        from face_recorder import FaceRecorder as _FR
        FaceRecorderClass = _FR
    except Exception:
        FaceRecorderClass = None

try:
    from face_recognition.face_detector import FaceDetector as _FD
    FaceDetectorClass = _FD
except Exception:
    try:
        from face_detector import FaceDetector as _FD
        FaceDetectorClass = _FD
    except Exception:
        FaceDetectorClass = None

try:
    from face_recognition.face_database import FaceDatabase as _FDB
    FaceDBClass = _FDB
except Exception:
    try:
        from face_database import FaceDatabase as _FDB
        FaceDBClass = _FDB
    except Exception:
        FaceDBClass = None


# ---------------- Face wrappers ----------------
def face_enroll(username: str):
    if FaceRecorderClass is None:
        raise ImportError("FaceRecorder not found.")
    return bool(FaceRecorderClass().run(username)), "FaceRecorder.run"

def face_verify(username: str):
    if FaceDetectorClass is None:
        raise ImportError("FaceDetector not found.")
    return bool(FaceDetectorClass().run(username)), "FaceDetector.run"

# 删除人脸记录（优先 FaceDatabase，失败走文件兜底）
_FACE_DELETE_CANDIDATES = ["delete_faces", "remove_user", "delete_user", "remove_faces"]

def _delete_face_via_db(username: str) -> bool:
    if FaceDBClass is None:
        return False
    try:
        db = FaceDBClass()
        for name in _FACE_DELETE_CANDIDATES:
            fn = getattr(db, name, None)
            if callable(fn):
                try:
                    fn(username)
                    return True
                except Exception:
                    continue
        return False
    except Exception:
        return False

def _delete_face_via_files(username: str) -> bool:
    changed = False
    # 删样本目录
    try:
        user_dir = FACE_SAMPLE_DIR / username
        if user_dir.exists():
            shutil.rmtree(user_dir, ignore_errors=True)
            changed = True
    except Exception:
        pass
    # 清理 face_data.json
    try:
        if FACE_DATA_FILE.exists():
            with open(FACE_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            def filter_list(lst):
                nonlocal changed
                kept = []
                for item in lst:
                    name = None
                    if isinstance(item, dict):
                        name = item.get("name") or item.get("username") or item.get("user")
                    if isinstance(name, str) and name == username:
                        changed = True
                        for v in item.values():
                            if isinstance(v, str) and v.lower().endswith((".jpg",".jpeg",".png",".bmp")):
                                try:
                                    Path(v).unlink(missing_ok=True)
                                except Exception:
                                    pass
                    else:
                        kept.append(item)
                return kept

            updated = False
            if isinstance(data, list):
                data = filter_list(data); updated = True
            elif isinstance(data, dict):
                if username in data:
                    rec = data.pop(username); changed = True; updated = True
                    if isinstance(rec, dict):
                        for v in rec.values():
                            if isinstance(v, str) and v.lower().endswith((".jpg",".jpeg",".png",".bmp")):
                                try: Path(v).unlink(missing_ok=True)
                                except Exception: pass
                for k, v in list(data.items()):
                    if isinstance(v, list):
                        data[k] = filter_list(v); updated = True
            if updated and changed:
                with open(FACE_DATA_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return changed

def delete_face_records(username: str) -> bool:
    if _delete_face_via_db(username):
        return True
    return _delete_face_via_files(username)


# ---------------- Fingerprint service ----------------
class FingerprintService:
    def __init__(self):
        FINGERPRINT_DIR.mkdir(parents=True, exist_ok=True)

    def _capture_once(self) -> Path:
        res = capture_fingerprint_bmp(on_event=None, max_tries=40, try_interval=0.7, pre_settle_time=1.2)
        if res and res.get("ok") and res.get("path") and os.path.exists(res["path"]):
            return Path(res["path"])
        fptemp = BASE_DIR / "fptemp"
        if fptemp.exists():
            cand = sorted(fptemp.glob("*.bmp"), key=os.path.getmtime, reverse=True)
            if cand: return cand[0]
        raise RuntimeError(f"fingerprint capture failed: {(res or {}).get('reason','unknown')}")

    def enroll(self, username: str) -> Path:
        tmp = self._capture_once()
        dst = FINGERPRINT_DIR / f"{username}.bmp"
        try:
            if dst.exists(): dst.unlink()
        except Exception: pass
        tmp.replace(dst)
        return dst

    def verify(self, enrolled_path: Path, threshold=15, ratio=0.8):
        live = self._capture_once()
        ok, msg = matcher_core.verify_fingerprint(str(live), str(enrolled_path),
                                                  threshold=threshold, ratio=0.8 if ratio is None else ratio)
        return ok, msg


# ---------------- Views (Frames) ----------------
class LoginView(ttk.Frame):
    def __init__(self, master, app, user_manager: UserManager):
        super().__init__(master)
        self.app = app
        self.user_manager = user_manager
        self.svc = FingerprintService()

        self.username = tk.StringVar()
        self.password = tk.StringVar()
        self.step_msg = tk.StringVar(value="")   # NEW: 登录流程提示

        top = ttk.Frame(self, padding=(10, 8))
        top.pack(fill="x")
        ttk.Label(
            top,
            text="Welcome to the Multimodal \n Recognition System",
            font=("Segoe UI", 16, "bold")
        ).pack(anchor="center", pady=(0, 8))

        frm = ttk.LabelFrame(self, text="Sign In", padding=10, style="Card.TLabelframe")
        frm.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(frm, text="Username:").grid(row=0, column=0, sticky="e", padx=6, pady=6)
        ttk.Entry(frm, textvariable=self.username, width=28).grid(row=0, column=1, sticky="w", padx=6, pady=6)

        ttk.Label(frm, text="Password:").grid(row=1, column=0, sticky="e", padx=6, pady=6)
        ttk.Entry(frm, textvariable=self.password, show="*", width=28).grid(row=1, column=1, sticky="w", padx=6, pady=6)

        btn_row = ttk.Frame(frm)
        btn_row.grid(row=2, column=0, columnspan=2, pady=10, sticky="w")
        self.btn_login = ttk.Button(btn_row, text="Login", command=self.try_login, bootstyle="primary")
        self.btn_login.pack(side="left", padx=6)
        ttk.Button(btn_row, text="Clear", command=self.clear_fields,
                   bootstyle="secondary").pack(side="left", padx=6)
        ttk.Button(btn_row, text="Register", command=self.app.show_register,
                   bootstyle="info").pack(side="left", padx=20)
        ttk.Button(btn_row, text="Manage Users", command=self.app.show_manage,
                   bootstyle="secondary").pack(side="left", padx=6)

        # NEW: 流程提示
        ttk.Label(frm, textvariable=self.step_msg, foreground="gray").grid(
            row=3, column=0, columnspan=2, sticky="w", padx=6, pady=(4,0)
        )

    def clear_fields(self):
        self.username.set("")
        self.password.set("")
        self.step_msg.set("")

    def try_login(self):
        user = self.username.get().strip()
        pwd  = self.password.get().strip()

        # 1) 账号密码校验
        if not self.user_manager.verify_user(user, pwd):
            self.step_msg.set("")
            messagebox.showerror("Failed", "Invalid username or password.")
            return

        # 账号密码 OK → 提示进行人脸验证
        self.btn_login.configure(state="disabled")
        self.step_msg.set("Credentials verified. Next: face verification ...")
        self.update_idletasks()
        messagebox.showinfo("Next step", "Credentials verified.\nPlease look at the camera for face verification.")

        # 2) 人脸验证
        try:
            ok, msg = face_verify(user)
            if not ok:
                self.step_msg.set("Face verification failed.")
                self.btn_login.configure(state="normal")
                messagebox.showerror("Failed", f"Face verification failed. {msg}")
                return
        except Exception as e:
            self.step_msg.set("Face verification error.")
            self.btn_login.configure(state="normal")
            messagebox.showerror("Error", f"Face verification error:\n{e}")
            return

        # 人脸 OK → 提示进行指纹验证
        self.step_msg.set("Face verified. Next: fingerprint verification ...")
        self.update_idletasks()
        messagebox.showinfo("Next step", "Face verified.\nPlease place your finger on the sensor.")

        # 3) 指纹验证
        try:
            from pathlib import Path as _P
            enrolled = self.user_manager.get_fingerprint_path(user)
            if not enrolled or not os.path.exists(enrolled):
                self.step_msg.set("No fingerprint enrolled for this user.")
                self.btn_login.configure(state="normal")
                messagebox.showerror("Error", "No enrolled fingerprint for this user.")
                return

            ok, msg = self.svc.verify(_P(enrolled), threshold=15, ratio=0.8)
            if ok:
                self.step_msg.set("Fingerprint verified. Logging in ...")
                self.app.show_welcome(user)  # 进入欢迎页
            else:
                self.step_msg.set("Fingerprint not matched.")
                messagebox.showerror("Failed", f"Fingerprint not matched.\n{msg}")
        except Exception as e:
            self.step_msg.set("Fingerprint verification error.")
            messagebox.showerror("Error", f"Fingerprint verification error:\n{e}")
        finally:
            self.btn_login.configure(state="normal")


class RegisterView(ttk.Frame):
    def __init__(self, master, app, user_manager: UserManager):
        super().__init__(master)
        self.app = app
        self.user_manager = user_manager
        self.svc = FingerprintService()

        self.new_user = tk.StringVar()
        self.new_pwd = tk.StringVar()
        self.face_registered = tk.BooleanVar(value=False)
        self.fp_registered = tk.BooleanVar(value=False)

        # 指纹提示 & 超时控制
        self.fp_hint = tk.StringVar(value="")
        self._fp_running = False
        self._fp_timed_out = False
        self._fp_timeout_job = None

        frm = ttk.LabelFrame(self, text="Create Account", padding=10, style="Card.TLabelframe")
        frm.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(frm, text="Username:").grid(row=0, column=0, sticky="e", padx=6, pady=6)
        ttk.Entry(frm, textvariable=self.new_user, width=28).grid(row=0, column=1, sticky="w", padx=6, pady=6)

        ttk.Label(frm, text="Password:").grid(row=1, column=0, sticky="e", padx=6, pady=6)
        ttk.Entry(frm, textvariable=self.new_pwd, show="*", width=28).grid(row=1, column=1, sticky="w", padx=6, pady=6)

        face_box = ttk.LabelFrame(frm, text="Face Enrollment", padding=8, style="Card.TLabelframe")
        face_box.grid(row=2, column=0, columnspan=2, sticky="ew", padx=4, pady=6)
        ttk.Button(face_box, text="Enroll Face", command=self.register_face, bootstyle="primary").grid(row=0, column=0, padx=6, pady=4)
        ttk.Label(face_box, textvariable=self.face_registered).grid(row=0, column=1, padx=6, pady=4, sticky="w")

        fp_box = ttk.LabelFrame(frm, text="Fingerprint Enrollment", padding=8, style="Card.TLabelframe")
        fp_box.grid(row=3, column=0, columnspan=2, sticky="ew", padx=4, pady=6)

        self.btn_enroll_fp = ttk.Button(fp_box, text="Enroll Fingerprint",
                                        command=self.register_fingerprint, bootstyle="info")
        self.btn_enroll_fp.grid(row=0, column=0, padx=6, pady=4)
        ttk.Label(fp_box, textvariable=self.fp_registered).grid(row=0, column=1, padx=6, pady=4, sticky="w")
        ttk.Label(fp_box, textvariable=self.fp_hint).grid(row=0, column=2, padx=12, pady=4, sticky="w")

        nav = ttk.Frame(frm)
        nav.grid(row=4, column=0, columnspan=2, pady=10, sticky="w")
        ttk.Button(nav, text="Complete Registration", command=self.complete_registration, bootstyle="success").pack(side="left", padx=6)
        ttk.Button(nav, text="Back to Login", command=self.app.show_login, bootstyle="secondary").pack(side="left", padx=12)

    def _ensure_user_exists(self, user, pwd) -> bool:
        if not self.user_manager.user_exists(user):
            if not self.user_manager.add_user(user, pwd):
                messagebox.showerror("Error", "Username already exists.")
                return False
        return True

    def register_face(self):
        user = self.new_user.get().strip()
        pwd = self.new_pwd.get().strip()
        if not user or not pwd:
            messagebox.showwarning("Notice", "Please input username and password first."); return
        if not self._ensure_user_exists(user, pwd): return
        try:
            ok, msg = face_enroll(user)
            if ok:
                self.user_manager.set_face_registered(user, True)
                self.face_registered.set(True)
                messagebox.showinfo("Info", f"Face enrolled. {msg}")
            else:
                messagebox.showerror("Error", f"Face enrollment failed. {msg}")
        except Exception as e:
            messagebox.showerror("Error", f"Face enrollment error:\n{e}")

    # ----- 指纹注册：提示 + 10 秒超时 -----
    def register_fingerprint(self):
        if self._fp_running:
            return
        user = self.new_user.get().strip()
        pwd = self.new_pwd.get().strip()
        if not user or not pwd:
            messagebox.showwarning("Notice", "Please input username and password first."); return
        if not self._ensure_user_exists(user, pwd): return

        self._fp_running = True
        self._fp_timed_out = False
        self.fp_hint.set("Please place your finger on the sensor...")
        self.btn_enroll_fp.configure(state="disabled")

        if self._fp_timeout_job:
            try: self.after_cancel(self._fp_timeout_job)
            except Exception: pass
        self._fp_timeout_job = self.after(10_000, self._on_fp_timeout)

        def worker():
            try:
                dst = FingerprintService().enroll(user)
                def on_done():
                    if self._fp_timed_out or not self._fp_running:
                        return
                    self.user_manager.set_fingerprint(user, str(dst))
                    self.fp_registered.set(True)
                    self.fp_hint.set("Captured.")
                    self._finish_fp_capture()
                    messagebox.showinfo("Info", f"Fingerprint enrolled: {dst.name}")
                self.after(0, on_done)
            except Exception as e:
                def on_fail():
                    if self._fp_timed_out:
                        self._finish_fp_capture()
                        return
                    self.fp_hint.set("")
                    self._finish_fp_capture()
                    messagebox.showerror("Error", f"Fingerprint enrollment failed:\n{e}")
                self.after(0, on_fail)
        threading.Thread(target=worker, daemon=True).start()

    def _on_fp_timeout(self):
        self._fp_timed_out = True
        self._fp_running = False
        self.btn_enroll_fp.configure(state="normal")
        self.fp_hint.set("Timeout. Click the button to retry.")
        messagebox.showwarning("Timeout", "Fingerprint capture timeout. Please click the button to retry.")

    def _finish_fp_capture(self):
        self._fp_running = False
        self.btn_enroll_fp.configure(state="normal")
        if self._fp_timeout_job:
            try: self.after_cancel(self._fp_timeout_job)
            except Exception: pass
            self._fp_timeout_job = None

    def complete_registration(self):
        user = self.new_user.get().strip()
        if not user:
            messagebox.showwarning("Notice", "Please input username first."); return
        if not self.user_manager.is_face_registered(user):
            messagebox.showwarning("Notice", "Face not enrolled yet."); return
        if not self.user_manager.is_fingerprint_registered(user):
            messagebox.showwarning("Notice", "Fingerprint not enrolled yet."); return
        messagebox.showinfo("Success", "Registration completed.")
        self.app.show_login()


class ManageView(ttk.Frame):
    def __init__(self, master, app, user_manager: UserManager):
        super().__init__(master)
        self.app = app
        self.user_manager = user_manager

        self.users_list = tk.Listbox(self)
        self.users_list.pack(fill="both", expand=True, padx=10, pady=10)

        btn_bar = ttk.Frame(self)
        btn_bar.pack(fill="x", padx=10, pady=6)
        ttk.Button(btn_bar, text="Refresh", command=self.refresh, bootstyle="info").pack(side="left", padx=4)
        ttk.Button(btn_bar, text="Delete", command=self.on_delete, bootstyle="danger").pack(side="left", padx=4)
        ttk.Button(btn_bar, text="Back to Login", command=self.app.show_login, bootstyle="secondary").pack(side="right", padx=4)

        self.refresh()

    def refresh(self):
        self.users_list.delete(0, tk.END)
        for u in self.user_manager.get_all_users():
            flags = []
            if self.user_manager.is_face_registered(u): flags.append("face")
            if self.user_manager.is_fingerprint_registered(u): flags.append("fp")
            suffix = f" [{','.join(flags)}]" if flags else ""
            self.users_list.insert(tk.END, u + suffix)

    def on_delete(self):
        sel = self.users_list.curselection()
        if not sel:
            messagebox.showwarning("Notice", "Please select a user."); return
        username = self.users_list.get(sel[0]).split(" [")[0]
        if not messagebox.askyesno("Confirm", f"Delete user '{username}' ?"):
            return

        face_deleted = delete_face_records(username)

        fp_path = self.user_manager.get_fingerprint_path(username)
        ok = self.user_manager.delete_user(username)
        if ok:
            try:
                if fp_path and os.path.exists(fp_path): os.remove(fp_path)
            except Exception: pass
            msg = "User deleted."
            if face_deleted: msg += " (face data removed)"
            messagebox.showinfo("Success", msg)
            self.refresh()
        else:
            messagebox.showerror("Failed", "Delete failed.")


# ---------------- Welcome View ----------------
class WelcomeView(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.username_var = tk.StringVar(value="")

        box = ttk.LabelFrame(self, text="Welcome", padding=16, style="Card.TLabelframe")
        box.pack(fill="both", expand=True, padx=12, pady=12)

        self.lbl = ttk.Label(box, textvariable=self.username_var, font=("Segoe UI", 14, "bold"))
        self.lbl.pack(pady=10)

        ttk.Button(box, text="Logout", command=self.app.logout, bootstyle="danger").pack(pady=12)

    def set_user(self, username: str):
        self.username_var.set(f"Welcome, {username}!")


# ---------------- App ----------------
class App:
    def __init__(self):
        self.root, self.tb = build_root("EE6008 Multimodal Identity Recognition System", "680x520", themename="flatly")
        self.user_manager = UserManager()
        self.current_user = None

        self.container = ttk.Frame(self.root)
        self.container.pack(fill="both", expand=True, padx=12, pady=12)

        self.login_view    = LoginView(self.container, self, self.user_manager)
        self.register_view = RegisterView(self.container, self, self.user_manager)
        self.manage_view   = ManageView(self.container, self, self.user_manager)
        self.welcome_view  = WelcomeView(self.container, self)

        self.current_view = None
        self.show_login()

    def _show(self, view: ttk.Frame):
        if self.current_view is not None:
            self.current_view.pack_forget()
        self.current_view = view
        self.current_view.pack(fill="both", expand=True)

    def show_login(self):
        self._show(self.login_view)

    def show_register(self):
        self._show(self.register_view)

    def show_manage(self):
        self._show(self.manage_view)

    def show_welcome(self, username: str):
        self.current_user = username
        self.welcome_view.set_user(username)
        self._show(self.welcome_view)

    def logout(self):
        self.current_user = None
        self.login_view.clear_fields()
        self.show_login()


# ---------------- main ----------------
if __name__ == "__main__":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = App()
    app.root.mainloop()
