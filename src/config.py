import os

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "image")
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
USERS_FILE = os.path.join(BASE_DIR, "users.json")
IGNORED_FILE = os.path.join(BASE_DIR, "ignored_rows.json")
BENGALI_DATA_FILE = os.path.join(BASE_DIR, "bengali_data.json")

# Branding
PROGRAMMER_NAME_AR = "برمجة: السعيد الوزان"
PROGRAMMER_NAME_EN = "Programmed by Alsaeed Alwazzan"
APP_TITLE = "Contract Monitor System"

# Colors (Dark Luxury Theme)
COLORS = {
    "bg_main": "#121212",       # Very Dark Grey
    "bg_secondary": "#1E1E1E",  # Dark Grey (Cards/Sidebar)
    "accent": "#D4AF37",        # Gold
    "text_main": "#E0E0E0",     # Light Grey
    "text_dim": "#A0A0A0",      # Dim Grey
    "success": "#2E7D32",       # Green
    "danger": "#C62828",        # Red
    "warning": "#F9A825",       # Amber
    "white": "#FFFFFF",
    "black": "#000000"
}

# Fonts
FONTS = {
    "h1": ("Segoe UI", 24, "bold"),
    "h2": ("Segoe UI", 18, "bold"),
    "body": ("Segoe UI", 11),
    "body_bold": ("Segoe UI", 11, "bold"),
    "small": ("Segoe UI", 9)
}
