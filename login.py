import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageDraw
import os
from src.config import COLORS, ASSETS_DIR, PROGRAMMER_NAME_EN
from src.ui.components import LuxuryButton, ModernEntry

class LoginScreen:
    def __init__(self, root, auth_manager, on_login_success):
        self.root = root
        self.auth = auth_manager
        self.on_success = on_login_success
        self.root.title("تسجيل الدخول")
        self.root.geometry("450x600")
        self.root.config(bg=COLORS["bg_main"])
        
        self.center_window()

        # Main Container (Centered Card)
        self.card = tk.Frame(self.root, bg=COLORS["bg_secondary"], width=380, padx=18, pady=18)
        self.card.place(relx=0.5, rely=0.5, anchor="center")
        self.card.pack_propagate(False)

        # 1. Avatar Image (Circular 70px)
        self.setup_avatar()

        # 2. Programmer Name (Small, Gold)
        tk.Label(self.card, text=PROGRAMMER_NAME_EN.upper(), 
                 font=("Segoe UI", 8, "bold"), 
                 bg=COLORS["bg_secondary"], fg=COLORS["accent"]).pack(pady=(6, 0))

        # 3. Title (Welcome)
        tk.Label(self.card, text="أهلاً بك", 
                 font=("Segoe UI", 18, "bold"), 
                 bg=COLORS["bg_secondary"], fg=COLORS["white"]).pack(pady=(4, 0))
        
        tk.Label(self.card, text="نظام مراقبة العقود", 
                 font=("Segoe UI", 9), 
                 bg=COLORS["bg_secondary"], fg=COLORS["text_dim"]).pack(pady=(0, 15))

        # 4. Input Fields
        field_container = tk.Frame(self.card, bg=COLORS["bg_secondary"])
        field_container.pack(fill=tk.X, expand=True)

        self.user_entry = ModernEntry(field_container, justify='center')
        self.user_entry.insert(0, "اسم المستخدم")
        self.user_entry.bind("<FocusIn>", lambda e: self.on_entry_click(self.user_entry, "اسم المستخدم"))
        self.user_entry.bind("<FocusOut>", lambda e: self.on_focusout(self.user_entry, "اسم المستخدم"))
        self.user_entry.pack(fill=tk.X, pady=4, ipady=6) # ~38px height with ipady

        self.pass_entry = ModernEntry(field_container, show="", justify='center')
        self.pass_entry.insert(0, "كلمة المرور")
        self.pass_entry.bind("<FocusIn>", lambda e: self.on_entry_click(self.pass_entry, "كلمة المرور", True))
        self.pass_entry.bind("<FocusOut>", lambda e: self.on_focusout(self.pass_entry, "كلمة المرور", True))
        self.pass_entry.pack(fill=tk.X, pady=4, ipady=6)
        self.pass_entry.bind('<Return>', self.do_login)

        # 5. Login Button
        self.login_btn = LuxuryButton(self.card, text="دخول", command=self.do_login)
        self.login_btn.config(font=("Segoe UI", 11, "bold"), pady=8) # Height ~40px
        self.login_btn.pack(fill=tk.X, pady=(15, 0))

        # 6. Language Switcher (Optional, as seen in image)
        lang_btn = tk.Button(self.card, text="عربي / English", font=("Segoe UI", 9),
                            bg=COLORS["bg_main"], fg=COLORS["white"], relief="flat", bd=1)
        lang_btn.pack(pady=(20, 0))

    def setup_avatar(self):
        img_name = "alsaeed.jpg"
        img_path = os.path.join(ASSETS_DIR, img_name)
        
        if not os.path.exists(img_path):
             potential_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), img_name)
             if os.path.exists(potential_path):
                 img_path = potential_path

        try:
            size = (70, 70)
            mask = Image.new('L', size, 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0) + size, fill=255)

            pil_image = Image.open(img_path)
            pil_image = pil_image.resize(size, Image.Resampling.LANCZOS)
            
            output = Image.new('RGBA', size, (0, 0, 0, 0))
            output.paste(pil_image, (0, 0), mask=mask)
            
            self.photo = ImageTk.PhotoImage(output)
            lbl_img = tk.Label(self.card, image=self.photo, bg=COLORS["bg_secondary"])
            lbl_img.pack(pady=(0, 0))
        except Exception as e:
            print(f"Image load error: {e}")

    def on_entry_click(self, entry, placeholder, is_pass=False):
        if entry.get() == placeholder:
            entry.delete(0, tk.END)
            if is_pass: entry.config(show="•")

    def on_focusout(self, entry, placeholder, is_pass=False):
        if entry.get() == '':
            entry.insert(0, placeholder)
            if is_pass: entry.config(show="")

    def center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"+{x}+{y}")

    def do_login(self, event=None):
        u = self.user_entry.get()
        p = self.pass_entry.get()
        
        # Don't login if placeholders
        if u == "اسم المستخدم" or p == "كلمة المرور":
            messagebox.showerror("خطأ", "يرجى إدخال اسم المستخدم وكلمة المرور")
            return

        user_data = self.auth.authenticate(u, p)
        if user_data:
            self.on_success(user_data)
        else:
            messagebox.showerror("Login Failed", "Invalid Username or Password")
