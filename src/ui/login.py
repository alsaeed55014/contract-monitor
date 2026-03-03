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
        self.root.geometry("400x420") # Reduced width, adjusted height for better layout
        self.root.config(bg=COLORS["bg_main"])
        self.root.resizable(False, False)
        
        self.center_window()

        # 1. Header Frame (Logo/Avatar + Title)
        header_frame = tk.Frame(self.root, bg=COLORS["bg_main"])
        header_frame.pack(pady=(30, 20))

        # Avatar
        self.setup_avatar_small(header_frame)

        # Welcome Text with subtle glow
        tk.Label(header_frame, text="تسجيل الدخول", 
                 font=("Segoe UI", 20, "bold"), 
                 bg=COLORS["bg_main"], fg="#FFD700").pack(pady=5) # Glowing Yellow/Gold
        
        tk.Label(self.root, text="نظام مراقبة العقود الذكي", 
                 font=("Segoe UI", 10), 
                 bg=COLORS["bg_main"], fg=COLORS["text_dim"]).pack()

        # 2. Main Card Container
        self.card = tk.Frame(self.root, bg=COLORS["bg_secondary"], 
                            highlightbackground="#333", highlightthickness=1,
                            padx=30, pady=30)
        self.card.pack(pady=30, padx=40, fill=tk.BOTH, expand=True)

        # 3. Input Fields
        self.user_entry = ModernEntry(self.card, justify='center', placeholder="اسم المستخدم")
        self.user_entry.pack(fill=tk.X, pady=(0, 15), ipady=8) 

        self.pass_entry = ModernEntry(self.card, show="•", justify='center', placeholder="كلمة المرور")
        self.pass_entry.pack(fill=tk.X, pady=(0, 20), ipady=8)
        self.pass_entry.bind('<Return>', self.do_login)

        # 4. Login Button (Full width for "Professional" look)
        self.login_btn = LuxuryButton(self.card, text="دخول الي النظام", command=self.do_login, 
                                     bg=COLORS["accent"], fg=COLORS["black"])
        self.login_btn.config(font=("Segoe UI", 11, "bold")) 
        self.login_btn.pack(fill=tk.X, ipady=5)

        # 5. Language Switcher (Floating / Bottom Right)
        lang_btn = tk.Button(self.root, text="English Mode", font=("Segoe UI", 8),
                            bg=COLORS["bg_main"], fg=COLORS["text_dim"], 
                            activebackground=COLORS["bg_main"], activeforeground=COLORS["white"],
                            relief="flat", bd=0, cursor="hand2")
        lang_btn.place(relx=0.5, rely=0.95, anchor="center")

    def setup_avatar_small(self, parent):
        img_name = "alsaeed.jpg"
        img_path = os.path.join(ASSETS_DIR, img_name)
        if not os.path.exists(img_path):
             potential_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), img_name)
             if os.path.exists(potential_path): img_path = potential_path

        try:
            size = (50, 50) # Slightly larger for better branding
            mask = Image.new('L', size, 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0) + size, fill=255)
            pil_image = Image.open(img_path).resize(size, Image.Resampling.LANCZOS)
            output = Image.new('RGBA', size, (0, 0, 0, 0))
            output.paste(pil_image, (0, 0), mask=mask)
            self.photo_small = ImageTk.PhotoImage(output)
            tk.Label(parent, image=self.photo_small, bg=COLORS["bg_main"]).pack(pady=5)
        except: pass

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
