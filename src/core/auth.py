import json
import hashlib
import os
import logging

logger = logging.getLogger(__name__)

class AuthManager:
    def __init__(self, users_file_path):
        self.users_file = users_file_path
        self.users = {}
        self.load_users()

    def load_users(self):
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.users = data.get("users", {})
            except Exception:
                logger.exception("Error loading users from %s", self.users_file)
                self.users = {}
        
        # Ensure Default Admin
        if "admin" not in self.users:
            self.users["admin"] = {
                "password": self.hash_password("admin123"),
                "role": "admin",
                "full_name_ar": "المدير العام",
                "full_name_en": "General Manager",
                "permissions": ["all"]
            }
            self.save_users()

    def save_users(self):
        """Persists users to disk. Returns True on success, False on failure."""
        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump({"users": self.users}, f, ensure_ascii=False, indent=4)
            return True
        except Exception:
            logger.exception("Error saving users to %s", self.users_file)
            return False

    def hash_password(self, password):
        return hashlib.sha256(str(password).encode()).hexdigest()

    def authenticate(self, username, password):
        username = username.lower().strip()
        if username in self.users:
            stored_hash = self.users[username].get("password")
            if stored_hash == self.hash_password(password):
                return self.users[username]
        return None

    def add_user(self, username, password, role="viewer", name_ar="", name_en=""):
        username = username.lower().strip()
        if username in self.users:
            return False, "User already exists"
        
        self.users[username] = {
            "password": self.hash_password(password),
            "role": role,
            "full_name_ar": name_ar,
            "full_name_en": name_en,
            "permissions": ["read"] if role == "viewer" else ["all"]
        }
        if not self.save_users():
            # Roll back the in-memory change so state matches disk.
            del self.users[username]
            return False, "Failed to save user to disk"
        return True, "User added successfully"

    def update_password(self, username, new_password):
        username = username.lower().strip()
        if username in self.users:
            previous = self.users[username].get("password")
            self.users[username]["password"] = self.hash_password(new_password)
            if not self.save_users():
                self.users[username]["password"] = previous
                return False
            return True
        return False

    def delete_user(self, username):
        username = username.lower().strip()
        if username in self.users and username != "admin":
            removed = self.users.pop(username)
            if not self.save_users():
                self.users[username] = removed
                return False
            return True
        return False

    def update_role(self, username, new_role):
        username = username.lower().strip()
        if username in self.users and username != "admin":
            previous = {
                "role": self.users[username].get("role"),
                "permissions": self.users[username].get("permissions"),
            }
            self.users[username]["role"] = new_role
            self.users[username]["permissions"] = ["read"] if new_role == "viewer" else ["all"]
            if not self.save_users():
                self.users[username]["role"] = previous["role"]
                self.users[username]["permissions"] = previous["permissions"]
                return False
            return True
        return False
