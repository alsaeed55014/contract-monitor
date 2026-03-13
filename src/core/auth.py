import json
import hashlib
import os

class AuthManager:
    def __init__(self, users_file_path):
        self.users_file = users_file_path
        self.users = {}
        self.is_bilingual = True # Version marker for session refresh
        self.load_users()

    def load_users(self):
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.users = data.get("users", {})
            except Exception as e:
                # Store error for UI feedback
                self.load_error = str(e)
                self.users = {}
        
        # Ensure Default Admin
        if "admin" not in self.users:
            self.users["admin"] = {
                "password": self.hash_password("266519111"), # User's preferred password
                "role": "admin",
                "first_name_ar": "السعيد",
                "father_name_ar": "الوزان",
                "first_name_en": "Alsaeed",
                "father_name_en": "Alwazzan",
                "permissions": ["all"]
            }
            self.save_users()

    def save_users(self):
        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump({"users": self.users}, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving users: {e}")

    def hash_password(self, password):
        return hashlib.sha256(str(password).encode()).hexdigest()

    def authenticate(self, username, password):
        username = username.lower().strip()
        if username in self.users:
            stored_hash = self.users[username].get("password")
            if stored_hash == self.hash_password(password):
                return self.users[username]
        return None

    def add_user(self, username, password, role="viewer", f_ar="", fa_ar="", f_en="", fa_en=""):
        username = username.lower().strip()
        if username in self.users:
            return False, "User already exists"
        self.users[username] = {
            "password": self.hash_password(password),
            "role": role,
            "first_name_ar": f_ar, "father_name_ar": fa_ar,
            "first_name_en": f_en, "father_name_en": fa_en,
            "permissions": ["all"] if role == "admin" else []
        }
        self.save_users()
        return True, "User added successfully"

    def update_password(self, username, new_password):
        username = str(username).strip()
        target = None
        for u in self.users:
            if u.lower() == username.lower():
                target = u
                break
        
        if target:
            self.users[target]["password"] = self.hash_password(new_password)
            self.save_users()
            return True
        return False

    def delete_user(self, username):
        if not username:
            return False, "اسم المستخدم فارغ"
        
        target = str(username).strip().lower()
        if target == "admin":
            return False, "لا يمكن حذف المدير الرئيسي"
            
        # find original key
        user_to_del = None
        for u in self.users:
            if u.lower() == target:
                user_to_del = u
                break
        
        if user_to_del:
            try:
                del self.users[user_to_del]
                self.save_users()
                return True, "تم الحذف"
            except Exception as e:
                return False, f"خطأ أثناء الحذف: {str(e)}"
        
        return False, "المستخدم غير موجود في النظام"

    def update_role(self, username, new_role):
        username = str(username).strip()
        target = None
        for u in self.users:
            if u.lower() == username.lower():
                target = u
                break
        
        if target:
            self.users[target]["role"] = new_role
            self.users[target]["permissions"] = ["read"] if new_role == "viewer" else ["all"]
            self.save_users()
            return True
        return False

    def update_profile(self, username, f_ar=None, fa_ar=None, f_en=None, fa_en=None):
        target = str(username).lower().strip()
        if target in self.users:
            if f_ar is not None: self.users[target]["first_name_ar"] = f_ar
            if fa_ar is not None: self.users[target]["father_name_ar"] = fa_ar
            if f_en is not None: self.users[target]["first_name_en"] = f_en
            if fa_en is not None: self.users[target]["father_name_en"] = fa_en
            self.save_users()
            return True
        return False

    def update_permissions(self, username, perms_list):
        target = str(username).lower().strip()
        if target in self.users:
            self.users[target]["permissions"] = perms_list
            self.save_users()
            return True
        return False

    def update_avatar(self, username, avatar_b64):
        """Save a base64-encoded profile photo for the user."""
        target = str(username).lower().strip()
        if target in self.users:
            self.users[target]["avatar"] = avatar_b64
            self.save_users()
            return True
        return False

    def get_avatar(self, username):
        """Get the base64-encoded profile photo for the user, or None."""
        target = str(username).lower().strip()
        return self.users.get(target, {}).get("avatar", None)
