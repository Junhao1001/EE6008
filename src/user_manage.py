# src/user_manage.py
import json
import os
from typing import Optional, List, Dict, Any

from config.paths import USER_DATA_FILE


class UserManager:
    """
    User data manager
    - Stores users in a local JSON file (config.paths.USER_DATA_FILE)
    - Each user record:
        {
            "password": "<plain text or hashed string>",
            "face_registered": bool,
            "fingerprint_registered": bool,
            "fingerprint_path": "<abs or project-relative path to enrolled fingerprint image> | None"
        }
    """

    def __init__(self):
        self.data_file = USER_DATA_FILE
        self.user_data: Dict[str, Dict[str, Any]] = {}
        self.load_users()

    # ---------------- I/O ----------------
    def load_users(self) -> None:
        """Load user data from JSON file (create an empty one if missing)."""
        if not os.path.exists(self.data_file):
            # create empty json file
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
            self.user_data = {}
            return

        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self.user_data = data
            else:
                # fallback: unexpected format -> reset
                self.user_data = {}
        except Exception:
            # corrupted file -> reset
            self.user_data = {}
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)

    def save(self) -> None:
        """Persist user_data to JSON file."""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.user_data, f, ensure_ascii=False, indent=2)

    # ---------------- CRUD ----------------
    def add_user(self, username: str, password: str) -> bool:
        """
        Add a new user with initial flags set to False.
        Returns False if the username already exists.
        """
        if username in self.user_data:
            return False

        self.user_data[username] = {
            "password": password,
            "face_registered": False,
            "fingerprint_registered": False,
            "fingerprint_path": None,
        }
        self.save()
        return True

    def delete_user(self, username: str) -> bool:
        """Delete a user. Returns True on success."""
        if username in self.user_data:
            del self.user_data[username]
            self.save()
            return True
        return False

    def get_all_users(self) -> List[str]:
        """Return a list of all usernames."""
        return list(self.user_data.keys())

    def user_exists(self, username: str) -> bool:
        return username in self.user_data

    # ---------------- Password ----------------
    def verify_user(self, username: str, password: str) -> bool:
        """Return True iff the user exists and the password matches."""
        return (
            username in self.user_data
            and self.user_data[username].get("password") == password
        )

    # ---------------- Face flags ----------------
    def set_face_registered(self, username: str, ok: bool = True) -> bool:
        """Mark whether the user has completed face enrollment."""
        if username not in self.user_data:
            return False
        self.user_data[username]["face_registered"] = bool(ok)
        self.save()
        return True

    def is_face_registered(self, username: str) -> bool:
        if username not in self.user_data:
            return False
        return bool(self.user_data[username].get("face_registered"))

    # ---------------- Fingerprint fields ----------------
    def set_fingerprint(self, username: str, fingerprint_path: str) -> bool:
        """
        Set (or update) the user's enrolled fingerprint image path,
        and mark fingerprint_registered=True.
        """
        if username not in self.user_data:
            return False
        self.user_data[username]["fingerprint_path"] = fingerprint_path
        self.user_data[username]["fingerprint_registered"] = True
        self.save()
        return True

    def clear_fingerprint(self, username: str) -> bool:
        """
        Clear fingerprint info for a user (used when re-enrolling or deleting).
        """
        if username not in self.user_data:
            return False
        self.user_data[username]["fingerprint_path"] = None
        self.user_data[username]["fingerprint_registered"] = False
        self.save()
        return True

    def get_fingerprint_path(self, username: str) -> Optional[str]:
        """Return the enrolled fingerprint image path for the user (or None)."""
        if username not in self.user_data:
            return None
        return self.user_data[username].get("fingerprint_path")

    def is_fingerprint_registered(self, username: str) -> bool:
        if username not in self.user_data:
            return False
        return bool(self.user_data[username].get("fingerprint_registered"))
