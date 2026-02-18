import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import os
from src.config import COLORS, FONTS, ASSETS_DIR, PROGRAMMER_NAME_EN
from src.ui.components import LuxuryButton, ModernEntry

class LoginScreen:
    def __init__(self, root, auth_manager, on_login_success):
        self.root = root
        self.auth = auth_manager
        self.on_success = on_login_success
        self.root.title("السعيد الوزان - تسجيل الدخول")
        self.root.geometry("900x600")
        self.root.config(bg=COLORS["bg_main"])
        
        # Center Window
        self.center_window()

        # Main Layout: Split 50/50
        # Left: Image & Programmer Name
        # Right: Login Form
        
        container = tk.Frame(self.root, bg=COLORS["bg_main"])
        container.pack(fill=tk.BOTH, expand=True)
        
        # --- LEFT SIDE ---
        left_frame = tk.Frame(container, bg=COLORS["bg_secondary"], width=450)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_frame.pack_propagate(False)
        
        # Image Logic
        img_name = "alsaeed.jpg"
        img_path = os.path.join(ASSETS_DIR, img_name)
        # Fallback search if not in assets
        if not os.path.exists(img_path):
             # Try root folder as per user context
             potential_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), img_name)
             if os.path.exists(potential_path):
                 img_path = potential_path
        
        try:
            pil_image = Image.open(img_path)
            pil_image = pil_image.resize((300, 300), Image.Resampling.LANCZOS)
            self.photo = ImageTk.PhotoImage(pil_image)
            
            lbl_img = tk.Label(left_frame, image=self.photo, bg=COLORS["bg_secondary"])
            lbl_img.pack(expand=True)
        except Exception as e:
            tk.Label(left_frame, text="[Image Not Found]", bg=COLORS["bg_secondary"], fg="red").pack(expand=True)
            print(f"Image load error: {e}")

        # Programmer Name
        tk.Label(left_frame, text=PROGRAMMER_NAME_EN, 
                 font=("Segoe UI", 12, "italic"), 
                 bg=COLORS["bg_secondary"], fg=COLORS["accent"]).pack(side=tk.BOTTOM, pady=40)

        # --- RIGHT SIDE ---
        right_frame = tk.Frame(container, bg=COLORS["bg_main"])
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        form_frame = tk.Frame(right_frame, bg=COLORS["bg_main"])
        form_frame.pack(expand=True)
        
        # Title
        tk.Label(form_frame, text="WELCOME BACK", font=("Orbitron", 24, "bold"), 
                 bg=COLORS["bg_main"], fg=COLORS["white"]).pack(pady=(0, 10))
        tk.Label(form_frame, text="Contract Monitor System", font=("Segoe UI", 12), 
                 bg=COLORS["bg_main"], fg=COLORS["text_dim"]).pack(pady=(0, 40))
        
        # Inputs
        tk.Label(form_frame, text="Username", bg=COLORS["bg_main"], fg=COLORS["text_dim"], font=FONTS["small"]).pack(anchor="w", padx=20)
        self.user_entry = ModernEntry(form_frame)
        self.user_entry.pack(fill=tk.X, padx=20, pady=(5, 20), ipady=5)
        
        tk.Label(form_frame, text="Password", bg=COLORS["bg_main"], fg=COLORS["text_dim"], font=FONTS["small"]).pack(anchor="w", padx=20)
        self.pass_entry = ModernEntry(form_frame, show="•")
        self.pass_entry.pack(fill=tk.X, padx=20, pady=(5, 30), ipady=5)
        self.pass_entry.bind('<Return>', self.do_login)

        # Login Button
        LuxuryButton(form_frame, text="LOGIN", command=self.do_login, width=20).pack(pady=10)

        # Footer
        tk.Label(form_frame, text="v2.0 - 2026", bg=COLORS["bg_main"], fg=COLORS["text_dim"], font=("Segoe UI", 8)).pack(pady=40)

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
        
        user_data = self.auth.authenticate(u, p)
        if user_data:
            self.on_success(user_data)
        else:
            messagebox.showerror("Login Failed", "Invalid Username or Password")
