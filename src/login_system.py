import tkinter as tk
from tkinter import messagebox, ttk

from src.face_recognition.face_database import FaceDatabase
from src.face_recognition.face_detector import FaceDetector
from src.face_recognition.face_recorder import FaceRecorder
from src.user_manage import UserManager

# ===== 登录界面 =====
class LoginWindow(tk.Frame):
    def __init__(self, master, switch_to_menu, switch_to_success):
        super().__init__(master)
        self.switch_to_menu = switch_to_menu
        self.switch_to_success = switch_to_success
        self.user_manager = UserManager()
        self.show_login_window()

    def show_login_window(self):
        tk.Label(self, text="Login Page", font=("Arial", 18)).pack(pady=20)
        tk.Label(self, text="Username:").pack()
        self.username_entry = tk.Entry(self)
        self.username_entry.pack()

        tk.Label(self, text="Password:").pack()
        self.password_entry = tk.Entry(self, show="*")
        self.password_entry.pack()

        tk.Button(self, text="Login", width=15, command=self.login).pack(pady=10)
        tk.Button(self, text="Back to Menu", width=15, command=self.switch_to_menu).pack()

    def show_success(self, username):
        self.clear_frame()
        frame = RegisterWindow(self.root, switch_to_menu=self.switch_to_menu)
        frame.pack(fill="both", expand=True)
        self.current_frame = frame


    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        if not username or not password:
            messagebox.showerror("Warning", "Please enter username and password")
            return

        if not self.user_manager.verify_user(username, password):
            messagebox.showerror("Error", "Invalid username or password")
            return

        messagebox.showinfo("Info", "Password verified.\nProceed to face verification.")
        self.verify_face(username)

    def verify_face(self, username):
        try:
            face_detector = FaceDetector()
            face_result = face_detector.run(username)

            if not face_result:
                messagebox.showerror("Error", "Face verification failed.")
                return

            messagebox.showinfo("Info", "Face verified.\nProceed to fingerprint verification.")
            self.verify_fingerprint(username)

        except Exception as e:
            messagebox.showerror("Error", f"Face verification error:\n{e}")

    # 指纹验证
    def verify_fingerprint(self, username):
        "TODO"
        messagebox.showinfo("Info", "Finger verification.")
        self.switch_to_success(username)
        return True

class SuccessWindow(tk.Frame):
    def __init__(self, master, username, switch_to_menu):
        super().__init__(master)
        self.username = username  # 接收登录成功的用户名
        self.switch_to_menu = switch_to_menu  # 返回菜单的回调函数
        self.show_success_window()  # 渲染界面

    def show_success_window(self):
        # 欢迎语（大字体突出）
        tk.Label(self, text=f"Welcome, {self.username}!", font=("Arial", 20, "bold")).pack(pady=50)

        # 登录成功提示
        tk.Label(self, text="Login Successful!", font=("Arial", 14)).pack(pady=10)

        # 可选：返回菜单按钮（按原有界面逻辑补充，方便操作）
        tk.Button(self, text="Back to Menu", width=15, command=self.switch_to_menu).pack(pady=30)

class RegisterWindow(tk.Frame):
    def __init__(self, master, switch_to_menu):
        super().__init__(master)
        self.switch_to_menu = switch_to_menu
        self.user_manager = UserManager()

        self.new_user = None
        self.new_pass = None
        self.username_entry = None
        self.password_entry = None
        self.face_registered = tk.BooleanVar(value=False)
        self.fingerprint_registered = tk.BooleanVar(value=False)
        self.current_widgets = []

        self.show_register_frame1()

    # 通用函数：清空当前界面
    def clear_frame(self):
        for widget in self.current_widgets:
            widget.destroy()
        self.current_widgets.clear()

    # 用户名和密码注册界面
    def show_register_frame1(self):
        self.clear_frame()

        label1 = tk.Label(self, text="Register Page", font=("Arial", 18))
        label1.pack(pady=20)
        label2 = tk.Label(self, text="Username:")
        label2.pack()
        entry1 = tk.Entry(self)
        entry1.pack()
        self.username_entry = entry1

        label3 = tk.Label(self, text="Password:")
        label3.pack()
        entry2 = tk.Entry(self, show="*")
        entry2.pack()
        self.password_entry = entry2

        button1 = tk.Button(self, text="Register", width=15, command=self.register)
        button1.pack(pady=10)
        button2 = tk.Button(self, text="Back to Menu", width=15, command=self.switch_to_menu)
        button2.pack()

        self.current_widgets += [label1, label2, label3, entry1, entry2, button1, button2,]

    def show_register_frame2(self):
        self.clear_frame()
        self.face_registered.set(False)
        self.fingerprint_registered.set(False)

        label1 = tk.Label(self, text=f"Welcome, {self.new_user}", font=("Microsoft YaHei", 13, "bold"))
        label1.pack(pady=10)
        label2 = tk.Label(self, text="Please complete face registration to finish sign-up.", font=("Microsoft YaHei", 10))
        label2.pack(pady=5)

        button1 = tk.Button(self, text="Register Face", width=18, command=self.register_face)
        button1.pack(pady=15)
        button2 = tk.Button(self, text="Register Fingerprint", width=18, command=self.register_fingerprint)
        button2.pack(pady=15)
        button3 = tk.Button(self, text="Complete Registration", width=18, command=self.complete_registration)
        button3.pack(pady=15)
        button4 = tk.Button(self, text="Cancel", width=18, command=self.show_register_frame1)
        button4.pack(pady=10)

        self.current_widgets += [label1, label2, button1, button2, button3, button4]

    # 用户名密码注册，并进行跳转
    def register(self):
        self.new_user = self.username_entry.get()
        self.new_pass = self.password_entry.get()

        if not self.new_user or not self.new_pass:
            messagebox.showwarning("Warning", "Username and password cannot be empty.")
            return

        if self.new_user in self.user_manager.user_data:
            messagebox.showerror("Error", "This username already exists.")
            return

        self.show_register_frame2()

    def register_face(self):
        try:
            recorder = FaceRecorder()
            result = recorder.run(self.new_user)  # 启动录制流程

            if not result:
                messagebox.showerror("Error", "Face registration failed. Please try again.")

            messagebox.showinfo("Info", "Face registration successful.")
            self.face_registered.set(True)

        except Exception as e:
            messagebox.showerror("Error", f"Face verification error:\n{e}")

    def register_fingerprint(self):
        "TODO"
        self.fingerprint_registered.set(True)
        messagebox.showinfo("Info", "Finger verification successful.")
        return True

    def complete_registration(self):
        if not self.face_registered.get():
            messagebox.showwarning("Warning", "Please complete face registration.")
        elif not self.fingerprint_registered.get():
            messagebox.showwarning("Warning", "Please complete fingerprint registration.")
        else:
            self.user_manager.add_user(self.new_user, self.new_pass)
            messagebox.showinfo("Success", f"Registration completed for user: {self.new_user}")

        self.switch_to_menu()

class ManageWindow(tk.Frame):
    def __init__(self, master, switch_to_menu):
        super().__init__(master)
        self.switch_to_menu = switch_to_menu
        self.user_manager = UserManager()
        self.face_data = FaceDatabase()

        self.show_manage_window()

    def show_manage_window(self):
        tk.Label(self, text="User List", font=("Microsoft YaHei", 13, "bold")).pack(pady=10)

        # 使用 Treeview 展示用户列表
        self.tree = ttk.Treeview(self, columns=("username",), show="headings", height=8)
        self.tree.heading("username", text="username")
        self.tree.column("username", anchor="center", width=200)
        self.tree.pack(pady=10)

        self.load_users()

        tk.Button(self, text="Delete Selected User", width=20, command=self.delete_selected_user).pack(pady=5)
        tk.Button(self, text="Back to Menu", width=20, command=self.switch_to_menu).pack(pady=5)

    def load_users(self):
        self.tree.delete(*self.tree.get_children())

        for user in self.user_manager.user_data:
            self.tree.insert("", tk.END, values=(user,))

    def delete_user(self, username):
        if not self.user_manager.delete_user(username):
            return False
        if not self.face_data.delete_faces(username):
            return False
        "补充删除指纹数据接口"
        return True

    def delete_selected_user(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a user.！")
            return
        username = self.tree.item(selected_item[0], "values")[0]
        if messagebox.askyesno("Delete Confirm", f"Are you sure to delete {username}?"):
            if self.delete_user(username):
                messagebox.showinfo("Success", f"Delete User：{username} successfully.")
                self.load_users()
            else:
                messagebox.showerror("Error", "Delete failed. Please try again.！")

class LoginSystem:
    def __init__(self, root):
        self.root = root
        self.user_manager = UserManager()
        self.face_data = FaceDatabase()

        self.root.title("Multi-modal Login System")
        self.root.geometry("400x300")
        self.current_frame = None
        # self.root.resizable(False, False)

        self.show_main_menu()

    def clear_frame(self):
        """销毁当前frame"""
        if self.current_frame is not None:
            self.current_frame.destroy()

    def show_main_menu(self):
        self.clear_frame()
        frame = tk.Frame(self.root)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="Welcome Multi-modal Login System", font=("Arial", 18)).pack(pady=40)
        tk.Button(frame, text="Login", width=15, command=self.show_login).pack(pady=10)
        tk.Button(frame, text="Register", width=15, command=self.show_register).pack(pady=10)
        tk.Button(frame, text="ManageUser", width=15, command=self.show_manage).pack(pady=10)

        self.current_frame = frame

    def show_login(self):
        self.clear_frame()
        frame = LoginWindow(self.root, switch_to_menu=self.show_main_menu, switch_to_success=self.show_success)
        frame.pack(fill="both", expand=True)
        self.current_frame = frame

    def show_register(self):
        self.clear_frame()
        frame = RegisterWindow(self.root, switch_to_menu=self.show_main_menu)
        frame.pack(fill="both", expand=True)
        self.current_frame = frame

    def show_manage(self):
        self.root.geometry("400x350")
        self.clear_frame()
        frame = ManageWindow(self.root, switch_to_menu=self.show_main_menu)
        frame.pack(fill="both", expand=True)
        self.current_frame = frame

    def show_success(self, username):
        self.clear_frame()
        frame = SuccessWindow(self.root, username, switch_to_menu=self.show_main_menu)
        frame.pack(fill="both", expand=True)
        self.current_frame = frame

if __name__ == "__main__":
    # ========== 主界面 ==========
    root = tk.Tk()
    app = LoginSystem(root)
    root.mainloop()