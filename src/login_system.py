import tkinter as tk
from tkinter import messagebox, ttk
import json
import os

from config.paths import USER_DATA_FILE
from src.face_recognition.face_database import FaceDatabase

class UserManager:
    def __init__(self):
        self.data_file = USER_DATA_FILE
        self.user_data = {}

        self.load_users()

    def load_users(self):
        # load user data from local json file
        if not os.path.exists(self.data_file):
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=4)
        else:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                self.user_data = json.load(f)

    def save(self):
        """保存用户信息到JSON"""
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.user_data, f, indent=4)

    def add_user(self, username, password):
        """添加新用户"""
        if username in self.user_data:
            return False
        self.user_data[username] = password
        self.save()
        return True

    def verify_user(self, username, password):
        """验证用户是否存在且密码正确"""
        return username in self.user_data and self.user_data[username].get("password") == password

    def delete_user(self, username):
        """删除指定用户"""
        if username in self.user_data:
            del self.user_data[username]
            self.save()
            return True
        return False

    def get_all_users(self):
        """获取所有用户名"""
        return list(self.user_data.keys())

class LoginSystem:
    def __init__(self, root):
        self.root = root
        self.user_manager = UserManager()
        self.face_data = FaceDatabase()

        self.root.title("简易登录系统")
        self.root.geometry("400x340")
        self.root.resizable(False, False)

        self.login_window()

    def login_window(self):
        def face_detection(username):
            from src.face_recognition.face_detector import FaceDetector

            try:
                detector = FaceDetector()
                detect_name = detector.run()
                if detect_name & detect_name == username:
                    result = True
                else:
                    result = False
            except Exception as e:
                print("Face Detector Error", e)
                result = False

            return result

        # ======= 登录逻辑 =======
        def login():
            username = entry_username.get().strip()
            password = entry_password.get().strip()

            if self.user_manager.verify_user(username, password):
                messagebox.showinfo("Login Success!", f"Welcome Back，{username}！")
            else:
                messagebox.showerror("Login Fail", "用户名或密码错误。")

        # 顶部系统名称
        tk.Label(self.root, text="简易用户登录系统", font=("Microsoft YaHei", 16, "bold"), fg="#333").pack(pady=20)

        # 用户名和密码输入区
        tk.Label(self.root, text="用户名：", font=("Microsoft YaHei", 11)).pack(pady=5)
        entry_username = tk.Entry(self.root, font=("Microsoft YaHei", 11))
        entry_username.pack()

        tk.Label(self.root, text="密码：", font=("Microsoft YaHei", 11)).pack(pady=5)
        entry_password = tk.Entry(self.root, show="*", font=("Microsoft YaHei", 11))
        entry_password.pack()

        # 操作按钮
        tk.Button(self.root, text="登录", width=12, font=("Microsoft YaHei", 10), command=login).pack(pady=12)
        tk.Button(self.root, text="注册新用户", width=12, font=("Microsoft YaHei", 10), command=self.open_register_window).pack()
        tk.Button(self.root, text="管理用户", width=12, font=("Microsoft YaHei", 10), command=self.open_manage_window).pack(
            pady=10)

    def open_register_window(self):
        reg_step1_window = tk.Toplevel(self.root)
        reg_step1_window.title("Register - Step 1")
        reg_step1_window.geometry("350x260")
        reg_step1_window.resizable(False, False)

        tk.Label(reg_step1_window, text="Register New Account", font=("Microsoft YaHei", 14, "bold")).pack(pady=10)
        tk.Label(reg_step1_window, text="Username:", font=("Microsoft YaHei", 10)).pack(pady=5)
        entry_new_user = tk.Entry(reg_step1_window, font=("Microsoft YaHei", 10))
        entry_new_user.pack()

        tk.Label(reg_step1_window, text="Password:", font=("Microsoft YaHei", 10)).pack(pady=5)
        entry_new_pass = tk.Entry(reg_step1_window, show="*", font=("Microsoft YaHei", 10))
        entry_new_pass.pack()

        def go_next_step():
            new_user = entry_new_user.get().strip()
            new_pass = entry_new_pass.get().strip()

            if not new_user or not new_pass:
                messagebox.showwarning("Warning", "Username and password cannot be empty.")
                return

            if new_user in self.user_manager.user_data:
                messagebox.showerror("Error", "This username already exists.")
                return

            # 临时保存用户名和密码，进入下一步
            reg_step1_window.destroy()
            self.open_register_step2(new_user, new_pass)

        tk.Button(reg_step1_window, text="Next", width=12, command=go_next_step).pack(pady=10)
        tk.Button(reg_step1_window, text="Cancel", width=12, command=reg_step1_window.destroy).pack()

    # ======= 注册窗口 Step 2（人脸录入） =======
    def open_register_step2(self, username, password):
        def data_alignment():
            # face data alignment
            for name in list(self.face_data.face_data.keys()):
                if name not in self.user_manager.user_data.keys():
                    self.face_data.delete_faces(name)
        def back_to_step1():
            data_alignment()
            reg_step2_window.destroy()
            self.open_register_window()

        # 模拟调用你的人脸注册接口
        def register_face():
            from src.face_recognition.face_recorder import FaceRecorder

            try:
                recorder = FaceRecorder()
                result = recorder.run(username)  # 启动录制流程
            except Exception as e:
                print("Face Recorder Error", e)
                result = False

            # 假设录入成功
            if result:
                face_registered.set(True)
                messagebox.showinfo("Success", "Face registration completed successfully!")
            else:
                messagebox.showerror("Error", "Face registration failed. Please try again.")

        # 注册完成逻辑
        def complete_registration():
            if not username or not password:
                messagebox.showerror("Error", "Invalid username or password data.")
                return
            if not face_registered.get():
                messagebox.showwarning("Warning", "Please complete face registration first.")
                return

            # 保存用户数据（含人脸注册状态）
            self.user_manager.user_data[username] = {
                "password": password,
                "face_registered": True
            }
            self.user_manager.save()
            messagebox.showinfo("Success", f"Registration completed for user: {username}")
            reg_step2_window.destroy()

        reg_step2_window = tk.Toplevel(self.root)
        reg_step2_window.protocol("WM_DELETE_WINDOW", back_to_step1)
        reg_step2_window.title("Register - Step 2 (Face Registration)")
        reg_step2_window.geometry("380x250")
        reg_step2_window.resizable(False, False)

        tk.Label(reg_step2_window, text=f"Welcome, {username}", font=("Microsoft YaHei", 13, "bold")).pack(pady=10)
        tk.Label(reg_step2_window, text="Please complete face registration to finish sign-up.",
                 font=("Microsoft YaHei", 10)).pack(pady=5)

        # 标记人脸是否录入
        face_registered = tk.BooleanVar(value=False)

        tk.Button(reg_step2_window, text="Register Face", width=15, command=register_face).pack(pady=15)
        tk.Button(reg_step2_window, text="Complete Registration", width=18, command=complete_registration).pack(pady=5)
        tk.Button(reg_step2_window, text="Cancel", width=12, command=back_to_step1).pack(pady=10)

    # ======= 管理用户窗口 =======
    def open_manage_window(self):
        manage_window = tk.Toplevel(self.root)
        manage_window.title("用户管理")
        manage_window.geometry("360x300")
        manage_window.resizable(False, False)

        tk.Label(manage_window, text="用户列表", font=("Microsoft YaHei", 13, "bold")).pack(pady=10)

        # 使用 Treeview 展示用户列表
        tree = ttk.Treeview(manage_window, columns=("username",), show="headings", height=8)
        tree.heading("username", text="用户名")
        tree.column("username", anchor="center", width=200)
        tree.pack(pady=10)

        # 加载数据
        def load_users():
            tree.delete(*tree.get_children())
            for user in self.user_manager.get_all_users():
                tree.insert("", tk.END, values=(user,))

        load_users()

        # 删除选中用户
        def delete_selected_user():
            selected_item = tree.selection()
            if not selected_item:
                messagebox.showwarning("警告", "请先选择一个用户！")
                return
            username = tree.item(selected_item[0], "values")[0]
            if messagebox.askyesno("确认删除", f"确定要删除用户 {username} 吗？"):
                if self.user_manager.delete_user(username):
                    messagebox.showinfo("成功", f"已删除用户：{username}")
                    load_users()
                else:
                    messagebox.showerror("错误", "删除用户失败！")

        tk.Button(manage_window, text="删除选中用户", width=15, command=delete_selected_user).pack(pady=5)
        tk.Button(manage_window, text="关闭", width=15, command=manage_window.destroy).pack(pady=5)

if __name__ == "__main__":
    # ========== 主界面 ==========
    root = tk.Tk()
    app = LoginSystem(root)
    root.mainloop()