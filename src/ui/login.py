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
        self.root.geometry("500x350") # عرض أكبر وارتفاع أقل
        self.root.config(bg=COLORS["bg_main"])
        
        self.center_window()

        # 1. Header Frame (Image + Welcome Text) - في المنتصف
        header_frame = tk.Frame(self.root, bg=COLORS["bg_main"])
        header_frame.pack(pady=(20, 5))

        # Avatar (Small 35px)
        self.setup_avatar_small(header_frame)

        # Welcome Text
        tk.Label(header_frame, text="أهلاً بك", 
                 font=("Segoe UI", 18, "bold"), 
                 bg=COLORS["bg_main"], fg=COLORS["accent"]).pack(side=tk.RIGHT, padx=10)
        
        # Subtitle
        tk.Label(self.root, text="نظام مراقبة العقود", 
                 font=("Segoe UI", 9), 
                 bg=COLORS["bg_main"], fg=COLORS["text_dim"]).pack(pady=(0, 15))

        # 2. Main Card Container
        self.card = tk.Frame(self.root, bg=COLORS["bg_secondary"], 
                            highlightbackground="#333", highlightthickness=1,
                            width=400, padx=20, pady=20)
        self.card.pack(pady=0)
        self.card.pack_propagate(False)

        # 3. Input Fields (Tight layout)
        self.user_entry = ModernEntry(self.card, justify='right')
        self.user_entry.insert(0, "اسم المستخدم")
        self.user_entry.bind("<FocusIn>", lambda e: self.on_entry_click(self.user_entry, "اسم المستخدم"))
        self.user_entry.bind("<FocusOut>", lambda e: self.on_focusout(self.user_entry, "اسم المستخدم"))
        self.user_entry.pack(fill=tk.X, pady=5, ipady=4) 

        self.pass_entry = ModernEntry(self.card, show="", justify='right')
        self.pass_entry.insert(0, "كلمة المرور")
        self.pass_entry.bind("<FocusIn>", lambda e: self.on_entry_click(self.pass_entry, "كلمة المرور", True))
        self.pass_entry.bind("<FocusOut>", lambda e: self.on_focusout(self.pass_entry, "كلمة المرور", True))
        self.pass_entry.pack(fill=tk.X, pady=5, ipady=4)
        self.pass_entry.bind('<Return>', self.do_login)

        # 4. Login Button (Small, Right aligned as in image)
        btn_frame = tk.Frame(self.card, bg=COLORS["bg_secondary"])
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.login_btn = LuxuryButton(btn_frame, text="دخول", command=self.do_login)
        self.login_btn.config(font=("Segoe UI", 9, "bold"), width=8, pady=3) 
        self.login_btn.pack(side=tk.RIGHT)

        # 5. Language Switcher (Floating style)
        lang_btn = tk.Button(self.root, text="En", font=("Segoe UI", 8, "bold"),
                            bg=COLORS["bg_secondary"], fg=COLORS["white"], 
                            relief="flat", bd=1, width=3)
        lang_btn.place(x=50, y=280) # وضع الزر في الأسفل كما في الصورة

    def setup_avatar_small(self, parent):
        img_name = "alsaeed.jpg"
        img_path = os.path.join(ASSETS_DIR, img_name)
        if not os.path.exists(img_path):
             potential_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), img_name)
             if os.path.exists(potential_path): img_path = potential_path

        try:
            size = (35, 35) # حجم صغير جداً بجانب النص
            mask = Image.new('L', size, 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0) + size, fill=255)
            pil_image = Image.open(img_path).resize(size, Image.Resampling.LANCZOS)
            output = Image.new('RGBA', size, (0, 0, 0, 0))
            output.paste(pil_image, (0, 0), mask=mask)
            self.photo_small = ImageTk.PhotoImage(output)
            tk.Label(parent, image=self.photo_small, bg=COLORS["bg_main"]).pack(side=tk.RIGHT)
        except: pass

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
