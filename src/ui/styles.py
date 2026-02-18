import tkinter as tk
from tkinter import ttk
from src.config import COLORS, FONTS

class StyleManager:
    @staticmethod
    def setup_styles(root):
        style = ttk.Style(root)
        style.theme_use('clam') # Best base for custom styling

        # General Frame
        style.configure("TFrame", background=COLORS["bg_main"])
        style.configure("Card.TFrame", background=COLORS["bg_secondary"], relief="flat")
        
        # Labels
        style.configure("TLabel", background=COLORS["bg_main"], foreground=COLORS["text_main"], font=FONTS["body"])
        style.configure("Header.TLabel", background=COLORS["bg_main"], foreground=COLORS["accent"], font=FONTS["h1"])
        style.configure("CardHeader.TLabel", background=COLORS["bg_secondary"], foreground=COLORS["accent"], font=FONTS["h2"])
        style.configure("CardBody.TLabel", background=COLORS["bg_secondary"], foreground=COLORS["text_main"], font=FONTS["body"])

        # Buttons (Luxury Style)
        # We generally use tk.Button for more control over bg colors in Windows, 
        # but ttk.Button with styles can work too. 
        # For this "Luxury" look, I'll stick to custom Tkinter Buttons in components.py wrapper
        # but define treeview styles here.

        # Treeview (The core table)
        style.configure("Treeview", 
            background=COLORS["white"],
            foreground=COLORS["black"],
            fieldbackground=COLORS["white"],
            font=FONTS["body"],
            rowheight=35
        )
        style.configure("Treeview.Heading", 
            background=COLORS["bg_secondary"],
            foreground=COLORS["white"],
            font=FONTS["body_bold"]
        )
        style.map("Treeview", 
            background=[('selected', COLORS["accent"])],
            foreground=[('selected', COLORS["black"])]
        )

        # Scrollbars
        style.configure("Vertical.TScrollbar", 
            background=COLORS["bg_secondary"],
            troughcolor=COLORS["bg_main"],
            bordercolor=COLORS["bg_secondary"],
            arrowcolor=COLORS["accent"]
        )
        
        return style
