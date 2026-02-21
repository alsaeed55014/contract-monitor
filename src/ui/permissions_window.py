import tkinter as tk
from tkinter import messagebox
from src.config import COLORS, FONTS
from src.ui.components import SmartTable, LuxuryButton, ModernEntry
from src.core.auth import AuthManager
from src.core.i18n import t

class PermissionsWindow(tk.Toplevel):
    def __init__(self, parent, auth_manager):
        super().__init__(parent)
        self.lang = getattr(parent, 'lang', 'ar')
        self.title(t("permissions_title", self.lang))
        self.geometry("1100x850")
        self.config(bg=COLORS["bg_main"])
        self.auth = auth_manager
        self.selected_username = None
        
        self.create_header()
        self.create_content()

    def create_header(self):
        header = tk.Frame(self, bg=COLORS["bg_secondary"], height=100)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text=f" {t('permissions_title', self.lang)}", font=FONTS["h1"], 
                 bg=COLORS["bg_secondary"], fg=COLORS["white"]).pack(side=tk.LEFT, padx=30, pady=20)
        
        LuxuryButton(header, text=t("close", self.lang), command=self.destroy, bg=COLORS["danger"], width=10).pack(side=tk.RIGHT, padx=30)

    def create_content(self):
        container = tk.Frame(self, bg=COLORS["bg_main"])
        container.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Split: Left (User Form), Right (List Users)
        left_frame = tk.Frame(container, bg=COLORS["bg_secondary"], width=450, padx=25, pady=25)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        left_frame.pack_propagate(False)
        
        # Form Title
        self.form_title = tk.Label(left_frame, text=t("add_user", self.lang), font=FONTS["h2"], bg=COLORS["bg_secondary"], fg=COLORS["accent"])
        self.form_title.pack(pady=(0, 20))
        
        # Username (Disabled when editing)
        tk.Label(left_frame, text=t("username", self.lang), bg=COLORS["bg_secondary"], fg=COLORS["white"]).pack(anchor="w")
        self.entry_user = ModernEntry(left_frame)
        self.entry_user.pack(fill=tk.X, pady=(5, 15))

        # Password (Optional when editing)
        self.pass_label = tk.Label(left_frame, text=t("password", self.lang), bg=COLORS["bg_secondary"], fg=COLORS["white"])
        self.pass_label.pack(anchor="w")
        self.entry_pass = ModernEntry(left_frame, show="•")
        self.entry_pass.pack(fill=tk.X, pady=(5, 15))

        # Role
        tk.Label(left_frame, text=t("role", self.lang), bg=COLORS["bg_secondary"], fg=COLORS["white"]).pack(anchor="w")
        self.role_var = tk.StringVar(value="viewer")
        role_frame = tk.Frame(left_frame, bg=COLORS["bg_secondary"])
        role_frame.pack(fill=tk.X, pady=(5, 15))
        
        tk.Radiobutton(role_frame, text=t("role_admin", self.lang), variable=self.role_var, value="admin", 
                       bg=COLORS["bg_secondary"], fg=COLORS["white"], selectcolor=COLORS["bg_main"],
                       font=FONTS["small"]).pack(side=tk.LEFT, padx=(0, 20))
        tk.Radiobutton(role_frame, text=t("role_viewer", self.lang), variable=self.role_var, value="viewer", 
                       bg=COLORS["bg_secondary"], fg=COLORS["white"], selectcolor=COLORS["bg_main"],
                       font=FONTS["small"]).pack(side=tk.LEFT)

        # Action Buttons
        btn_container = tk.Frame(left_frame, bg=COLORS["bg_secondary"])
        btn_container.pack(fill=tk.X, pady=20)

        self.btn_submit = LuxuryButton(btn_container, text=t("add_btn", self.lang), command=self.save_user_action)
        self.btn_submit.pack(fill=tk.X, pady=5)

        self.btn_delete = LuxuryButton(btn_container, text=t("delete_user_btn", self.lang), command=self.delete_user_action, bg=COLORS["danger"])
        self.btn_delete.pack(fill=tk.X, pady=5)
        
        self.btn_clear = LuxuryButton(btn_container, text=t("cancel_btn", self.lang), command=self.clear_form, bg=COLORS["text_dim"])
        self.btn_clear.pack(fill=tk.X, pady=5)

        # Users List
        self.right_frame = tk.Frame(container, bg=COLORS["bg_main"])
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        tk.Label(self.right_frame, text=t("users_list", self.lang), font=FONTS["h2"], bg=COLORS["bg_main"], fg=COLORS["white"]).pack(anchor="w", pady=(0, 10))
        
        self.refresh_users()

    def refresh_users(self):
        for w in self.right_frame.winfo_children():
            if isinstance(w, SmartTable):
                w.destroy()

        users = self.auth.users
        rows = []
        for u_key, u_data in users.items():
            role_label = t(f"role_{u_data.get('role', 'viewer')}", self.lang)
            name = u_data.get('full_name_ar' if self.lang == 'ar' else 'full_name_en', '-')
            if not name or name == '-':
                # Try fallback names from app.py style
                name = u_data.get('first_name_ar' if self.lang == 'ar' else 'first_name_en', '-')
            rows.append([u_key, role_label, name])
            
        self.table = SmartTable(self.right_frame, [t("username", self.lang), t("role", self.lang), "Name"])
        self.table.pack(fill=tk.BOTH, expand=True)
        self.table.populate(rows)
        # Bind selection
        self.table.tree.bind("<<TreeviewSelect>>", self.on_user_select)

    def on_user_select(self, event):
        selected = self.table.get_selected()
        if not selected: return
        
        username = selected[0]
        user_data = self.auth.users.get(username)
        if not user_data: return

        self.selected_username = username
        self.entry_user.delete(0, tk.END)
        self.entry_user.insert(0, username)
        self.entry_user.config(state="disabled")
        
        self.entry_pass.delete(0, tk.END)
        self.pass_label.config(text=t("new_password", self.lang))
        
        self.role_var.set(user_data.get("role", "viewer"))
        
        self.form_title.config(text=t("edit_user", self.lang))
        self.btn_submit.config(text=t("update_btn", self.lang))

    def clear_form(self):
        self.selected_username = None
        self.entry_user.config(state="normal")
        self.entry_user.delete(0, tk.END)
        self.entry_pass.delete(0, tk.END)
        self.pass_label.config(text=t("password", self.lang))
        self.role_var.set("viewer")
        self.form_title.config(text=t("add_user", self.lang))
        self.btn_submit.config(text=t("add_btn", self.lang))

    def save_user_action(self):
        u = self.entry_user.get()
        p = self.entry_pass.get()
        r = self.role_var.get()
        
        if self.selected_username:
            # Update mode
            if p: # Only update password if provided
                self.auth.update_password(self.selected_username, p)
            
            if self.selected_username != "admin":
                self.auth.update_role(self.selected_username, r)
            
            messagebox.showinfo(t("success", self.lang), t("update_success", self.lang))
            self.clear_form()
            self.refresh_users()
        else:
            # Add mode
            if not u or not p:
                messagebox.showwarning(t("error", self.lang), "Fields required")
                return
            
            success, msg = self.auth.add_user(u, p, role=r)
            if success:
                messagebox.showinfo(t("success", self.lang), t("user_added", self.lang))
                self.clear_form()
                self.refresh_users()
            else:
                messagebox.showerror(t("error", self.lang), msg)

    def delete_user_action(self):
        if not self.selected_username:
            messagebox.showwarning(t("error", self.lang), t("select_user_edit", self.lang))
            return
            
        if self.selected_username == "admin":
            messagebox.showerror(t("error", self.lang), t("cannot_delete_admin", self.lang))
            return
            
        confirm = messagebox.askyesno(t("confirm_delete_title", self.lang), t("confirm_delete_user", self.lang))
        if confirm:
            if self.auth.delete_user(self.selected_username):
                # Front message as requested
                messagebox.showinfo(t("success", self.lang), t("user_deleted", self.lang))
                self.clear_form()
                self.refresh_users()
            else:
                messagebox.showerror(t("error", self.lang), "Could not delete user")

