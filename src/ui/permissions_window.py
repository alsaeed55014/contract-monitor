import tkinter as tk
from tkinter import messagebox
from src.config import COLORS, FONTS
from src.ui.components import SmartTable, LuxuryButton, ModernEntry
from src.core.auth import AuthManager

class PermissionsWindow(tk.Toplevel):
    def __init__(self, parent, auth_manager):
        super().__init__(parent)
        self.title("Permissions Management")
        self.geometry("1000x800")
        self.config(bg=COLORS["bg_main"])
        self.auth = auth_manager
        
        self.create_header()
        self.create_content()

    def create_header(self):
        header = tk.Frame(self, bg=COLORS["bg_secondary"], height=100)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text="🔑 User Permissions", font=FONTS["h1"], 
                 bg=COLORS["bg_secondary"], fg=COLORS["white"]).pack(side=tk.LEFT, padx=30, pady=20)
        
        LuxuryButton(header, text="Close", command=self.destroy, bg=COLORS["danger"], width=10).pack(side=tk.RIGHT, padx=30)

    def create_content(self):
        container = tk.Frame(self, bg=COLORS["bg_main"])
        container.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Split: Left (Add User), Right (List Users)
        left_frame = tk.Frame(container, bg=COLORS["bg_secondary"], width=400, padx=20, pady=20)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        left_frame.pack_propagate(False)
        
        # Add User Form
        tk.Label(left_frame, text="Add New User", font=FONTS["h2"], bg=COLORS["bg_secondary"], fg=COLORS["accent"]).pack(pady=(0, 20))
        
        tk.Label(left_frame, text="Username", bg=COLORS["bg_secondary"], fg=COLORS["white"]).pack(anchor="w")
        self.entry_user = ModernEntry(left_frame)
        self.entry_user.pack(fill=tk.X, pady=(5, 15))

        tk.Label(left_frame, text="Password", bg=COLORS["bg_secondary"], fg=COLORS["white"]).pack(anchor="w")
        self.entry_pass = ModernEntry(left_frame, show="•")
        self.entry_pass.pack(fill=tk.X, pady=(5, 15))

        self.role_var = tk.StringVar(value="viewer")
        tk.Label(left_frame, text="Role", bg=COLORS["bg_secondary"], fg=COLORS["white"]).pack(anchor="w")
        role_frame = tk.Frame(left_frame, bg=COLORS["bg_secondary"])
        role_frame.pack(fill=tk.X, pady=(5, 15))
        
        tk.Radiobutton(role_frame, text="Admin", variable=self.role_var, value="admin", bg=COLORS["bg_secondary"], fg=COLORS["white"], selectcolor=COLORS["bg_main"]).pack(side=tk.LEFT)
        tk.Radiobutton(role_frame, text="Viewer", variable=self.role_var, value="viewer", bg=COLORS["bg_secondary"], fg=COLORS["white"], selectcolor=COLORS["bg_main"]).pack(side=tk.LEFT)

        LuxuryButton(left_frame, text="Add User", command=self.add_user, width=20).pack(pady=20)

        # Users List
        self.right_frame = tk.Frame(container, bg=COLORS["bg_main"])
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        tk.Label(self.right_frame, text="Existing Users", font=FONTS["h2"], bg=COLORS["bg_main"], fg=COLORS["white"]).pack(anchor="w", pady=(0, 10))
        
        self.refresh_users()

    def refresh_users(self):
        # Clear existing
        for w in self.right_frame.winfo_children():
            if isinstance(w, SmartTable):
                w.destroy()

        users = self.auth.users
        rows = []
        for u_key, u_data in users.items():
            rows.append([u_key, u_data.get('role', 'viewer'), u_data.get('full_name_en', '-')])
            
        t = SmartTable(self.right_frame, ["Username", "Role", "Name"])
        t.pack(fill=tk.BOTH, expand=True)
        t.populate(rows)

    def add_user(self):
        u = self.entry_user.get()
        p = self.entry_pass.get()
        r = self.role_var.get()
        
        if not u or not p:
            messagebox.showwarning("Warning", "Fields required")
            return
            
        success, msg = self.auth.add_user(u, p, role=r)
        if success:
            messagebox.showinfo("Success", msg)
            self.refresh_users()
        else:
            messagebox.showerror("Error", msg)
