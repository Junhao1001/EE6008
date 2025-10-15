import json
import os

from config.paths import USER_DATA_FILE

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
        self.user_data[username] = {
            "password": password,
            "face_registered": True,
            "fingerprint_registered": True
        }
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