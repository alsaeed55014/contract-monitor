import streamlit as st
import pandas as pd
import os
import sys
import json
import hashlib
import time
from datetime import datetime, timedelta
import pytz
import base64
import re

# Saudi Arabia timezone for consistent time display
SAUDI_TZ = pytz.timezone('Asia/Riyadh')

def get_saudi_time():
    """Get current time in Saudi Arabia timezone."""
    return datetime.now(SAUDI_TZ)

# 1. Ensure project root is in path (Robust Injection)
# Get the absolute path of the directory containing app.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = BASE_DIR
PERSIST_FILE = os.path.join(BASE_DIR, 'src', '.persist_login.json')
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Add src to path as well to allow both 'import src.core' and 'import core'
SRC_DIR = os.path.join(BASE_DIR, 'src')
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

try:
    from src.core.contracts import ContractManager
    from src.data.bengali_manager import BengaliDataManager
    from src.utils.phone_utils import create_pasha_whatsapp_excel, format_phone_number, save_to_local_desktop, render_pasha_export_button, is_local_windows_pc
    from src.core.matcher import CandidateMatcher, format_match_result, _find_city_region, _fuzzy_match, REGION_PROXIMITY, REGION_MAP
except ImportError:
    # Fallback for different environment path configurations
    from core.contracts import ContractManager
    from data.bengali_manager import BengaliDataManager
    from utils.phone_utils import create_pasha_whatsapp_excel, format_phone_number, save_to_local_desktop, render_pasha_export_button, is_local_windows_pc
    from core.matcher import CandidateMatcher, format_match_result, _find_city_region, _fuzzy_match, REGION_PROXIMITY, REGION_MAP

# 2. Local Auth Class to prevent Import/Sync Errors
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

def load_saved_credentials():
    if os.path.exists(PERSIST_FILE):
        try:
            with open(PERSIST_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
    return None

def save_credentials(u, p):
    try:
        os.makedirs(os.path.dirname(PERSIST_FILE), exist_ok=True)
        with open(PERSIST_FILE, 'w', encoding='utf-8') as f:
            json.dump({"u": u, "p": p}, f)
    except Exception as e:
        print(f"Error saving credentials: {e}")

def clear_credentials():
    if os.path.exists(PERSIST_FILE):
        try:
            os.remove(PERSIST_FILE)
        except:
            pass

@st.cache_data(ttl=3600, show_spinner=False)
def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

@st.cache_data(ttl=600, show_spinner=False)
def get_css(lang='ar'):
    direction = 'rtl' if lang == 'ar' else 'ltr'
    toggle_side = 'right' if lang == 'ar' else 'left'
    toggle_opposite = 'left' if lang == 'ar' else 'right'
    sidebar_border_side = 'left' if lang == 'ar' else 'right'
    sidebar_border_none = 'right' if lang == 'ar' else 'left'
    checkbox_text_align = 'right' if lang == 'ar' else 'left'
    bell_col_idx = 4 if lang == 'ar' else 1
    
    return f"""
    <style>
        /* Modern 2026 Luxury Executive Design System */
        @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700&family=Inter:wght@300;400;500;600;700&family=Cinzel:wght@500;700&family=Alex+Brush&family=Cairo:wght@400;600;700&family=My+Soul&display=swap');
        
        :root {{
            --luxury-gold: #D4AF37;
            --deep-gold: #B8860B;
            --glass-bg: rgba(26, 26, 26, 0.7);
            --solid-dark: #0A0A0A;
            --accent-green: #00FF41;
            --text-main: #F4F4F4;
            --border-glow: rgba(212, 175, 55, 0.3);
        }}



        /* 1) Global Aesthetics & Scrollbar */
        html, body, .stApp {{
            direction: {direction} !important;
        }}
        
        .stApp {{
            background: radial-gradient(circle at top right, #001F3F, #000000) !important;
            color: var(--text-main);
            font-family: 'Inter', 'Cairo', 'Tajawal', sans-serif;
        }}
        
        .main, [data-testid="stSidebarUserContent"], [data-testid="stSidebar"] {{
            direction: {direction} !important;
        }}

        /* Fix Checkbox Spacing - Icon at start, Text at end */
        div[data-testid="stCheckbox"] label {{
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important;
            gap: 15px !important;
            width: 100% !important;
            justify-content: flex-start !important;
        }}

        div[data-testid="stCheckbox"] label div:first-child {{
            order: 1 !important;
        }}
        
        div[data-testid="stCheckbox"] label div[data-testid="stMarkdownContainer"] {{
            order: 2 !important;
            flex-grow: 1 !important;
            text-align: {checkbox_text_align} !important;
        }}

        div[data-testid="stCheckbox"] label div[data-testid="stMarkdownContainer"] p {{
            margin: 0 !important;
            font-family: 'Cairo', sans-serif !important;
            font-size: 0.95rem !important;
        }}

        /* Custom Premium Scrollbar */
        ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
        ::-webkit-scrollbar-track {{ background: #000; }}
        ::-webkit-scrollbar-thumb {{ 
            background: linear-gradient(180deg, #111, #D4AF37); 
            border-radius: 10px; 
        }}

        /* 2) Layout & Spacing - CRITICAL FIX FOR TOP SPACE */
        .main .block-container {{
            padding-top: 0rem !important;
            padding-bottom: 2rem !important;
            max-width: 1200px !important;
        }}

        header[data-testid="stHeader"] {{
            background: transparent !important;
            height: 0 !important;
        }}

        /* 3) Luxury Typography & Large Title */
        .luxury-main-title {{
            font-family: 'Fv Free soul', 'My Soul', 'Cairo', sans-serif !important;
            font-size: 20px !important; /* Specific size requested by user */
            font-weight: 700 !important;
            text-align: center !important;
            background: linear-gradient(to bottom, #FFFFFF 20%, #D4AF37 100%) !important;
            -webkit-background-clip: text !important;
            -webkit-text-fill-color: transparent !important;
            text-shadow: 0 4px 15px rgba(212, 175, 55, 0.4) !important;
            margin: -10px 0 5px 0 !important; /* Raised even higher */
            padding: 0 !important; 
            letter-spacing: 1px !important;
        }}

        .flag-icon {{
            font-size: 20px;
            vertical-align: middle;
            margin: 0 5px;
        }}

        /* 4) Premium Form & Vertical Alignment */
        div[data-testid="stForm"] {{
            background: rgba(10, 10, 10, 0.5) !important;
            backdrop-filter: blur(15px) !important;
            border: 1px solid rgba(212, 175, 55, 0.2) !important;
            border-radius: 20px !important;
            padding: 1.5rem !important;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.8) !important;
        }}

        /* Profile Image Alignment Wrapper */
        .profile-row-container {{
            display: flex;
            align-items: center;
            justify-content: flex-start;
            gap: 15px;
            width: 100%;
            margin-bottom: 10px;
        }}

        .profile-img-circular {{
            width: 70px;
            height: 70px;
            border-radius: 50%;
            border: 2px solid var(--luxury-gold);
            box-shadow: 0 0 15px rgba(212, 175, 55, 0.3);
            object-fit: cover;
        }}

        /* Generic Inputs Styling */
        .stTextInput input, .stTextArea textarea, div[data-baseweb="select"] {{
            background-color: rgba(40, 40, 40, 0.6) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 12px !important;
            color: #FFFFFF !important;
            padding: 8px 12px !important; /* Reduced padding for smaller fields */
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.06) !important;
        }}

        .stTextInput input:focus, div[data-baseweb="select"]:focus-within {{
            border-color: var(--luxury-gold) !important;
            box-shadow: 0 0 0 3px rgba(212, 175, 55, 0.2) !important;
            background-color: rgba(50, 50, 50, 0.8) !important;
        }}

        /* Slider Styling */
        div[data-testid="stSlider"] [data-testid="stThumb"] {{
            background-color: var(--luxury-gold) !important;
            border: 2px solid #FFFFFF !important;
        }}
        div[data-testid="stSlider"] [data-testid="stTrack"] > div {{
            background: linear-gradient(90deg, #333, #D4AF37) !important;
        }}

        /* 5) Universal Luxury Button Style */
        .stButton button, div[data-testid="stFormSubmitButton"] button {{
            background: linear-gradient(135deg, #1A1A1A 0%, #262626 100%) !important;
            color: var(--luxury-gold) !important;
            border: 1px solid var(--border-glow) !important;
            border-radius: 12px !important;
            padding: 0.75rem 2rem !important;
            font-weight: 600 !important;
            letter-spacing: 1.5px !important;
            text-transform: uppercase !important;
            transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1) !important;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5) !important;
            width: 100% !important; /* Default to full width for better mobile behavior */
        }}

        /* Mobile specific button refinements */
        @media screen and (max-width: 768px) {{
            .stButton button, div[data-testid="stFormSubmitButton"] button {{
                padding: 0.6rem 1.2rem !important;
                font-size: 0.85rem !important;
                letter-spacing: 1px !important;
            }}
        }}

        .stButton button:hover, div[data-testid="stFormSubmitButton"] button:hover {{
            background: var(--luxury-gold) !important;
            color: #000 !important;
            border-color: var(--luxury-gold) !important;
            box-shadow: 0 0 25px rgba(212, 175, 55, 0.5) !important;
            transform: translateY(-3px) scale(1.02) !important;
        }}

        /* Primary Search Variation */
        button[kind="primary"] {{
            background: linear-gradient(135deg, #111, #222) !important;
            border: 1px solid var(--luxury-gold) !important;
        }}

        /* WhatsApp Export Button - Red Text */
        .whatsapp-export-btn .stButton button,
        .whatsapp-export-btn .stDownloadButton button {{
            color: #FF0000 !important;
        }}
        .whatsapp-export-btn .stButton button:hover,
        .whatsapp-export-btn .stDownloadButton button:hover {{
            color: #FF0000 !important;
        }}

        /* 6) Table & Data Presentation - WHITE NEON STYLE (For DataFrames) */
        [data-testid="stDataFrame"], [data-testid="stTable"], .neon-white-table {{
            background: rgba(255, 255, 255, 1) !important;
            border: 2px solid #FFFFFF !important;
            border-radius: 12px !important;
            box-shadow: 0 0 30px rgba(255, 255, 255, 0.8), 
                        inset 0 0 15px rgba(255, 255, 255, 0.5) !important;
            margin: 20px 0 !important;
            color: #000000 !important;
        }}
        
        [data-testid="stDataFrame"] *, [data-testid="stTable"] *, .neon-white-table * {{
            color: #000000; /* Removed !important to allow selective overrides */
            font-weight: 500 !important;
        }}

        /* FIX: White Icons for Data Table Toolbars (Fullscreen, Search, Download) */
        [data-testid="stElementToolbar"] button, 
        [data-testid="stDataFrame"] [data-testid="stElementToolbar"] svg,
        [data-testid="stTable"] [data-testid="stElementToolbar"] svg {{
            color: #FFFFFF !important;
            fill: #FFFFFF !important;
            filter: drop-shadow(0 0 5px rgba(255, 255, 255, 0.5)) !important;
        }}
        
        [data-testid="stElementToolbar"] button:hover {{
            background-color: rgba(255, 255, 255, 0.1) !important;
            border-radius: 50% !important;
        }}
        
        /* Header specific for dataframes to handle high brightness */
        [data-testid="stDataFrame"] div[role="columnheader"] {{
            background-color: rgba(240, 240, 240, 0.9) !important;
            color: #000000 !important;
            font-weight: 700 !important;
        }}

        /* Status Column Glows - Enhanced for 2026 High-Tech Look */
        .glow-green {{ color: #00FF66 !important; text-shadow: 0 0 10px rgba(0, 255, 102, 0.4) !important; font-weight: 800 !important; }}
        .glow-red {{ color: #FF3333 !important; text-shadow: 0 0 10px rgba(255, 51, 51, 0.4) !important; font-weight: 800 !important; }}
        .glow-orange {{ color: #FF9900 !important; text-shadow: 0 0 10px rgba(255, 153, 0, 0.4) !important; font-weight: 800 !important; }}

        /* 7) Sidebar Professionalism */
        section[data-testid="stSidebar"] {{
            background-color: #080808 !important;
            border-{sidebar_border_side}: 1px solid rgba(212, 175, 55, 0.15) !important;
            border-{sidebar_border_none}: none !important;
        }}
        
        /* Force HIDE sidebar when closed to prevent the "vertical line" artifact */
        section[data-testid="stSidebar"][aria-expanded="false"],
        section[data-testid="stSidebar"][data-collapsed="true"] {{
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
        }}

        .programmer-credit {{
            color: #FFFFFF !important;
            text-shadow: 0 0 10px rgba(255, 255, 255, 0.8), 
                         0 0 20px rgba(212, 175, 55, 0.4) !important;
            font-family: 'Tajawal', sans-serif;
            font-weight: 700;
            font-size: 1.3rem;
            text-align: center;
            margin-top: 10px;
            line-height: 1.2;
            white-space: nowrap !important;
        }}
        
        /* English version specific font */
        .programmer-credit.en {{
            font-family: 'Cinzel', serif !important;
            font-size: 1.1rem;
            letter-spacing: 1px;
        }}

        /* 8) Expander Luxury - UNIVERSAL WHITE NEON FRAME STYLE */
        .stExpander {{
            background-color: rgba(10, 14, 26, 0.6) !important;
            border: 2px solid rgba(255, 255, 255, 0.5) !important;
            border-radius: 20px !important;
            margin-bottom: 25px !important;
            animation: neonWhitePulse 3s ease-in-out infinite alternate !important;
            box-shadow: 0 0 15px rgba(255, 255, 255, 0.2) !important;
            transition: all 0.4s ease !important;
            overflow: hidden !important;
        }}
        
        .stExpander:hover {{
            border-color: rgba(255, 255, 255, 0.9) !important;
            box-shadow: 0 0 30px rgba(255, 255, 255, 0.6) !important;
            transform: translateY(-2px);
        }}

        /* Target the Header/Summary Area */
        .stExpander > details > summary {{
            background-color: rgba(255, 255, 255, 0.05) !important;
            color: #FFFFFF !important;
            padding: 1.2rem 1.5rem !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
        }}
        
        .stExpander > details > summary:hover {{
            background-color: rgba(255, 255, 255, 0.1) !important;
        }}

        /* Target the internal icons and labels */
        .stExpander summary span, .stExpander summary svg {{
            color: #FFFFFF !important;
            fill: #FFFFFF !important;
        }}

        /* Ensure internal content is appropriately styled */
        .stExpander > details > div[role="region"] {{
            border: none !important;
            background: transparent !important;
            padding: 20px !important;
        }}

        /* Re-refine filter labels for maximum white neon impact */
        .premium-filter-label {{
            color: #FFFFFF !important;
            font-weight: 800 !important;
            text-shadow: 0 0 15px rgba(255, 255, 255, 0.8) !important;
            margin: 15px 0 10px 0 !important;
            font-size: 1.15rem !important;
            border-right: 5px solid #FFFFFF !important;
            padding-right: 12px !important;
            letter-spacing: 1px;
            display: inline-block;
        }}

        /* Signature Neon (Standardized White-Gold) */
        .programmer-signature-neon, .red-neon-signature {{
            font-family: 'Alex Brush', cursive !important;
            color: #FFFFFF !important;
            text-shadow: 0 0 10px rgba(255, 255, 255, 0.8), 
                         0 0 20px rgba(212, 175, 55, 0.4) !important;
            font-size: 1.4rem !important; /* Smaller signature */
            text-align: center !important;
            display: block !important;
            width: 100% !important;
            margin: 0 auto 10px auto !important;
            letter-spacing: 1px !important;
            white-space: nowrap !important; /* Prevent vertical wrapping on mobile */
        }}

        /* Signature Under Image */
        .signature-under-img {{
            font-family: 'Alex Brush', cursive !important;
            color: #EEE !important; /* Slightly brighter for better visibility */
            font-size: 0.9rem !important;
            margin-top: 5px;
            text-align: center;
            letter-spacing: 1px;
            white-space: nowrap !important;
        }}

        /* Login Screen Special Centering - FIXED HANGING VERSION */
        .login-screen-wrapper {{
            margin-top: 20px !important;
            text-align: center;
        }}

        /* Target the Streamlit Form - REMOVED GOLD BORDER */
        div[data-testid="stForm"] {{
            background: rgba(10, 10, 10, 0.4) !important;
            backdrop-filter: blur(25px) !important;
            border: none !important; /* NO BORDER */
            border-radius: 25px !important;
            padding: 2rem !important;
            box-shadow: 0 15px 50px rgba(0, 0, 0, 0.8) !important;
            width: 100% !important;
            max-width: 500px !important;
            margin: 0 auto 40px auto !important;
        }}

        /* White Neon Text Effect */
        div[data-testid="stForm"] h3, 
        div[data-testid="stForm"] label,
        .neon-text {{
            color: #FFFFFF !important;
            text-shadow: 0 0 5px #FFF, 0 0 10px #FFF, 0 0 20px #FFF !important;
            text-align: center !important;
            font-weight: bold !important;
        }}

        /* Neon Glow Around Inputs - ENHANCED HALO EFFECT */
        div[data-testid="stForm"] div[data-baseweb="input"] {{
            background: rgba(255, 255, 255, 0.05) !important;
            border: 1px solid rgba(255, 255, 255, 0.4) !important;
            border-radius: 12px !important;
            /* Layered shadows for a 'halo' light effect */
            box-shadow: 0 0 15px rgba(255, 255, 255, 0.2), 
                        0 0 30px rgba(255, 255, 255, 0.1), 
                        inset 0 0 5px rgba(255, 255, 255, 0.1) !important;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
        }}

        div[data-testid="stForm"] div[data-baseweb="input"]:focus-within {{
            box-shadow: 0 0 25px rgba(255, 255, 255, 0.7), 
                        0 0 45px rgba(255, 255, 255, 0.3), 
                        inset 0 0 10px rgba(255, 255, 255, 0.1) !important;
            border-color: #FFFFFF !important;
            transform: scale(1.01) !important;
        }}

        div[data-testid="stForm"] .stTextInput input {{
            text-align: center !important;
            background: transparent !important;
            border: none !important;
            color: white !important;
            text-shadow: 0 0 2px rgba(255, 255, 255, 0.5) !important;
        }}

        /* Checkbox Neon Alignment */
        div[data-testid="stForm"] .stCheckbox label p {{
            color: #FFFFFF !important;
            text-shadow: 0 0 8px #FFF !important;
            font-size: 0.95rem !important;
        }}

        /* Buttons Neon Halo - LARGE WHITE GLOW */
        div[data-testid="stForm"] button {{
            background: rgba(255, 255, 255, 0.1) !important;
            border: 1.5px solid rgba(255, 255, 255, 0.4) !important;
            color: white !important;
            border-radius: 15px !important;
            /* Large Layered halo effect */
            box-shadow: 0 0 15px rgba(255, 255, 255, 0.2), 
                        0 0 35px rgba(255, 255, 255, 0.1), 
                        inset 0 0 10px rgba(255, 255, 255, 0.05) !important;
            transition: all 0.4s ease-out !important;
            font-weight: bold !important;
            text-shadow: 0 0 5px #FFF !important;
        }}

        div[data-testid="stForm"] button:hover {{
            background: rgba(255, 255, 255, 0.2) !important;
            box-shadow: 0 0 25px rgba(255, 255, 255, 0.8), 
                        0 0 60px rgba(255, 255, 255, 0.4), 
                        inset 0 0 15px rgba(255, 255, 255, 0.1) !important;
            border-color: #FFFFFF !important;
            transform: translateY(-2px) scale(1.02) !important;
        }}
        
        /* Metric Styling with White Neon Glow */
        @keyframes neonWhitePulse {{
            0% {{ 
                box-shadow: 0 0 10px rgba(255, 255, 255, 0.4), 0 0 20px rgba(255, 255, 255, 0.15), inset 0 0 10px rgba(255, 255, 255, 0.05);
                border-color: rgba(255, 255, 255, 0.5);
            }}
            100% {{ 
                box-shadow: 0 0 20px rgba(255, 255, 255, 0.7), 0 0 40px rgba(255, 255, 255, 0.35), inset 0 0 20px rgba(255, 255, 255, 0.1);
                border-color: rgba(255, 255, 255, 0.8);
            }}
        }}

        .metric-container {{
            background: rgba(10, 14, 26, 0.7) !important;
            border-radius: 20px !important;
            border: 1.5px solid rgba(255, 255, 255, 0.4) !important;
            padding: 1.8rem 1.5rem !important;
            transition: all 0.3s ease !important;
            animation: neonWhitePulse 3s ease-in-out infinite alternate;
            text-align: center;
        }}
        .metric-container:hover {{ 
            transform: scale(1.05) translateY(-5px);
            border-color: #FFFFFF !important;
            box-shadow: 0 0 30px rgba(255, 255, 255, 0.9), 0 0 60px rgba(255, 255, 255, 0.4) !important;
        }}

        .metric-label {{
            font-size: 0.95rem;
            color: rgba(255, 255, 255, 0.6);
            margin-bottom: 8px;
            font-weight: 500;
        }}
        .metric-value {{
            font-size: 2.2rem;
            font-weight: 800;
            line-height: 1;
        }}

        /* 9) Modern 2026 Premium Loader */
        .loader-wrapper {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 50px;
            background: rgba(10, 10, 10, 0.4);
            backdrop-filter: blur(15px);
            border-radius: 40px;
            border: 1px solid rgba(212, 175, 55, 0.15);
            box-shadow: 0 20px 40px rgba(0,0,0,0.6), inset 0 0 20px rgba(212, 175, 55, 0.05);
            margin: 40px auto;
            width: fit-content;
            animation: loader-entrance 0.8s ease-out;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 50px;
            background: rgba(10, 10, 10, 0.4);
            backdrop-filter: blur(15px);
            border-radius: 40px;
            border: 1px solid rgba(212, 175, 55, 0.15);
            box-shadow: 0 20px 40px rgba(0,0,0,0.6), inset 0 0 20px rgba(212, 175, 55, 0.05);
            margin: 40px auto;
            width: fit-content;
            animation: loader-entrance 0.8s ease-out;
        }}

        @keyframes loader-entrance {{
            from {{ opacity: 0; transform: scale(0.9) translateY(20px); }}
            to {{ opacity: 1; transform: scale(1) translateY(0); }}
        }}

        .modern-hourglass-svg {{
            width: 100px;
            height: 100px;
            filter: drop-shadow(0 0 15px rgba(212, 175, 55, 0.6));
            animation: hourglass-rotate 2.5s linear infinite;
        }}

        @keyframes hourglass-rotate {{
            from {{ transform: rotate(0deg); }}
            to {{ transform: rotate(360deg); }}
        }}

        .modern-hourglass-svg .glass {{
            fill: none;
            stroke: var(--luxury-gold);
            stroke-width: 2.5;
            stroke-linejoin: round;
        }}

        .modern-hourglass-svg .sand {{
            fill: var(--luxury-gold);
            opacity: 0.9;
        }}

        .modern-hourglass-svg .sand-top {{
            animation: sand-sink 2.5s linear infinite;
        }}

        .modern-hourglass-svg .sand-bottom {{
            animation: sand-fill 2.5s linear infinite;
        }}

        .modern-hourglass-svg .sand-drip {{
            fill: var(--luxury-gold);
            animation: sand-drip 2.5s linear infinite;
        }}

        @keyframes hourglass-flip {{
            0%, 85% {{ transform: rotate(0deg); }}
            95%, 100% {{ transform: rotate(180deg); }}
        }}

        @keyframes sand-sink {{
            0% {{ clip-path: polygon(0 0, 100% 0, 100% 100%, 0 100%); }}
            85%, 100% {{ clip-path: polygon(0 100%, 100% 100%, 100% 100%, 0 100%); }}
        }}

        @keyframes sand-fill {{
            0% {{ clip-path: polygon(0 100%, 100% 100%, 100% 100%, 0 100%); }}
            85%, 100% {{ clip-path: polygon(0 0, 100% 0, 100% 100%, 0 100%); }}
        }}

        @keyframes sand-drip {{
            0%, 5% {{ opacity: 0; height: 0; }}
            10%, 80% {{ opacity: 1; height: 30px; }}
            85%, 100% {{ opacity: 0; height: 0; }}
        }}

        .loading-text-glow {{
            margin-top: 30px;
            font-family: 'Cinzel', serif !important;
            color: var(--luxury-gold) !important;
            font-size: 1.2rem !important;
            letter-spacing: 5px !important;
            text-transform: uppercase !important;
            text-align: center;
            animation: text-pulse-glow 2s ease-in-out infinite alternate;
        }}

        @keyframes text-pulse-glow {{
            from {{ opacity: 0.6; text-shadow: 0 0 10px rgba(212, 175, 55, 0.2); }}
            to {{ opacity: 1; text-shadow: 0 0 25px rgba(212, 175, 55, 0.8), 0 0 15px rgba(212, 175, 55, 0.4); }}
        }}

        /* 10) Persistent Top Banner */
        .persistent-top-banner {{
            position: sticky;
            top: 0;
            z-index: 1000;
            background: rgba(10, 10, 10, 0.7);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-bottom: 2px solid rgba(212, 175, 55, 0.3);
            margin: -1rem -5rem 2rem -5rem !important;
            padding: 1rem 5rem !important;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            animation: banner-slide-down 0.8s cubic-bezier(0.4, 0, 0.2, 1);
        }}

        .notif-bell-container {{
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 45px;
            height: 45px;
            background: rgba(212, 175, 55, 0.1);
            border: 1px solid rgba(212, 175, 55, 0.3);
            border-radius: 50%;
            transition: all 0.3s ease;
            box-shadow: 0 0 15px rgba(212, 175, 55, 0.1);
        }}

        /* Target the specific Streamlit button inside our bell container (Dynamic Column Shift) */
        div[data-testid="column"]:nth-of-type({bell_col_idx}) button[key*="bell_trig"] {{
            background-color: transparent !important;
            border: none !important;
            padding: 0 !important;
            width: 45px !important;
            height: 45px !important;
            font-size: 24px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            box-shadow: none !important;
            transform: none !important;
        }}

        .notif-badge {{
            position: absolute;
            top: -2px;
            right: -2px;
            background: #FF3131;
            color: white;
            font-size: 11px;
            font-weight: bold;
            padding: 2px 6px;
            border-radius: 50%;
            border: 2px solid #0A0A0A;
            box-shadow: 0 0 10px rgba(255, 49, 49, 0.8);
            z-index: 10;
            animation: pulse-red 2s infinite;
        }}

        @keyframes pulse-red {{
            0% {{ transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 49, 49, 0.7); }}
            70% {{ transform: scale(1.1); box-shadow: 0 0 0 8px rgba(255, 49, 49, 0); }}
            100% {{ transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 49, 49, 0); }}
        }}

        @keyframes banner-slide-down {{
            from {{ transform: translateY(-100%); opacity: 0; }}
            to {{ transform: translateY(0); opacity: 1; }}
        }}

        .banner-user-info {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 5px;
        }}

        .banner-avatar {{
            width: 60px;
            height: 60px;
            border-radius: 50%;
            border: 2px solid #D4AF37;
            object-fit: cover;
            box-shadow: 0 0 15px rgba(212, 175, 55, 0.4);
            transition: transform 0.3s ease;
        }}

        .banner-avatar:hover {{
            transform: scale(1.1) rotate(5deg);
        }}

        .banner-welcome-msg {{
            font-family: 'Cairo', 'Tajawal', sans-serif;
            color: #FFFFFF;
            font-size: 1.1rem;
            font-weight: 600;
            text-shadow: 0 2px 4px rgba(0,0,0,0.5);
            margin: 0;
        }}

        .banner-subtext {{
            font-size: 0.8rem;
            color: rgba(212, 175, 55, 0.8);
            margin-top: -5px;
        }}

        /* 11) Mobile Responsive Overrides */
        @media (max-width: 768px) {{
            .main .block-container {{
                padding: 1rem !important;
                padding-top: 5rem !important; /* Space for the floating banner on mobile */
            }}

            .persistent-top-banner {{
                margin: 0 !important;
                padding: 0.8rem 1rem !important;
                position: fixed !important; /* Fixed at top for mobile */
                width: 100%;
                left: 0;
            }}

            .banner-welcome-msg {{ font-size: 0.95rem; }}
            .banner-subtext {{ font-size: 0.7rem; }}
            .banner-avatar {{ width: 45px; height: 45px; }}

            /* Fix Sidebar Appearance on Mobile - Clean edge when closed */
            section[data-testid="stSidebar"] {{
                background-color: #080808 !important;
                background-image: none !important;
                z-index: 10 !important;
                box-shadow: none !important;
            }}

            /* FORCE HIDE sidebar when closed on mobile to prevent layout competition */
            section[data-testid="stSidebar"][aria-expanded="false"] {{
                display: none !important;
                visibility: hidden !important;
                width: 0 !important;
            }}

            /* Streamlit Mobile Sidebar User Content Fix */
            div[data-testid="stSidebarUserContent"] {{
                background-color: #080808 !important;
            }}

            /* 12) GLOBAL UI CLEANUP: Hide standard header junk */
            .stAppDeployButton, #MainMenu, header[data-testid="stHeader"] a {{
                display: none !important;
            }}

            /* 13) STYLED NEON RED SIDEBAR TOGGLE (Updated to Red) */
            /* This target works for BOTH "Open" and "Close" states */
            button[data-testid="stSidebarCollapse"],
            button[aria-label*="sidebar"],
            .st-emotion-cache-not-found button[kind="headerNoPadding"] {{
                display: flex !important;
                visibility: visible !important;
                position: fixed !important;
                top: 10px !important;
                {toggle_side}: 15px !important;
                {toggle_opposite}: auto !important;
                z-index: 9999999 !important;
                background-color: #FF0000 !important; /* Neon Red */
                border: 2px solid #8B0000 !important;
                border-radius: 50% !important;
                box-shadow: 0 0 15px #FF0000, 0 0 30px rgba(255, 0, 0, 0.4) !important;
                width: 44px !important;
                height: 44px !important;
                opacity: 1 !important;
            }}

            /* Ensure the icon inside is White and clearly visible */
            button[aria-label*="sidebar"] svg,
            button[data-testid="stSidebarCollapse"] svg {{
                fill: #FFFFFF !important;
                color: #FFFFFF !important;
                width: 26px !important;
                height: 26px !important;
                stroke: #FFFFFF !important;
                stroke-width: 0.5px;
            }}

            /* Pulse animation for Neon White effect */
            button[aria-label*="sidebar"],
            button[data-testid="stSidebarCollapseButton"],
            button[data-testid="stSidebarCollapse"] {{
                animation: neon-white-pulse 2s infinite alternate !important;
                background: rgba(255, 255, 255, 0.1) !important;
                border: 1px solid #FFFFFF !important;
            }}

            @keyframes neon-white-pulse {{
                0% {{ box-shadow: 0 0 8px #FFFFFF, 0 0 15px rgba(255, 255, 255, 0.3); }}
                100% {{ box-shadow: 0 0 15px #FFFFFF, 0 0 30px rgba(255, 255, 255, 0.6); }}
            }}

            /* 14) Log Message Cards */
            .log-card {{
                background: rgba(255, 255, 255, 0.03) !important;
                border: 1px solid rgba(212, 175, 55, 0.1) !important;
                border-radius: 12px !important;
                padding: 12px 15px !important;
                margin-bottom: 8px !important;
                display: flex !important;
                align-items: center !important;
                justify-content: space-between !important;
                transition: all 0.3s ease !important;
                direction: rtl !important;
            }}
            .log-card:hover {{
                background: rgba(212, 175, 55, 0.05) !important;
                border-color: rgba(212, 175, 55, 0.3) !important;
                transform: translateX(-5px) !important;
            }}
            .log-info {{
                display: flex !important;
                flex-direction: column !important;
                gap: 2px !important;
                text-align: right !important;
            }}
            .log-name {{
                font-weight: 700 !important;
                color: #FFF !important;
                font-size: 0.95rem !important;
            }}
            .log-phone {{
                font-size: 0.8rem !important;
                color: rgba(212, 175, 55, 0.8) !important;
            }}
            .log-status-group {{
                display: flex !important;
                flex-direction: column !important;
                align-items: flex-start !important;
                gap: 4px !important;
            }}
            .log-status {{
                display: flex !important;
                align-items: center !important;
                gap: 8px !important;
                font-size: 0.85rem !important;
            }}
            .log-time {{
                font-size: 0.75rem !important;
                color: #888 !important;
                font-family: 'Inter', sans-serif !important;
            }}
            .status-badge {{
                padding: 2px 8px !important;
                border-radius: 6px !important;
                font-size: 0.75rem !important;
                font-weight: 600 !important;
            }}
            .status-success {{ background: rgba(0, 255, 65, 0.1) !important; color: #00FF41 !important; border: 1px solid rgba(0, 255, 65, 0.2) !important; }}
            .status-error {{ background: rgba(255, 49, 49, 0.1) !important; color: #FF3131 !important; border: 1px solid rgba(255, 49, 49, 0.2) !important; }}

            /* === MOBILE RED ICONS: Table toolbar icons (fullscreen, search, download) === */
            [data-testid="stElementToolbar"] button,
            [data-testid="stElementToolbar"] svg,
            [data-testid="stDataFrame"] [data-testid="stElementToolbar"] button,
            [data-testid="stDataFrame"] [data-testid="stElementToolbar"] svg {{
                color: #FF0000 !important;
                fill: #FF0000 !important;
                filter: drop-shadow(0 0 6px rgba(255, 0, 0, 0.6)) !important;
            }}

            /* === MOBILE RED: WhatsApp export button === */
            /* WhatsApp Export Button - Mobile (Unified Luxury Style) */
            .whatsapp-export-btn .stButton button,
            .whatsapp-export-btn .stDownloadButton button,
            .stDownloadButton button {{
                background: linear-gradient(135deg, #0a0e1a 0%, #06080f 100%) !important;
                color: #D4AF37 !important;
                border: 1.5px solid #D4AF37 !important;
                box-shadow: 0 0 10px rgba(212, 175, 55, 0.2) !important;
                text-shadow: 0 0 5px rgba(212, 175, 55, 0.3) !important;
            }}
            .whatsapp-export-btn .stButton button:hover,
            .whatsapp-export-btn .stDownloadButton button:hover,
            .stDownloadButton button:hover {{
                background: #D4AF37 !important;
                color: #000000 !important;
                border-color: #D4AF37 !important;
                box-shadow: 0 0 20px rgba(212, 175, 55, 0.5) !important;
            }}

            /* === MOBILE RED: Selectbox / Dropdown arrows === */
            div[data-baseweb="select"] svg,
            div[data-baseweb="select"] [data-testid="stSelectboxChevron"],
            .stSelectbox svg,
            .stSelectbox [role="combobox"] svg,
            div[data-baseweb="popover"] svg {{
                color: #FF0000 !important;
                fill: #FF0000 !important;
                filter: drop-shadow(0 0 4px rgba(255, 0, 0, 0.5)) !important;
            }}

            /* === MOBILE RED: Expander toggle arrows === */
            .stExpander summary svg,
            .status-error {{ background: rgba(255, 49, 49, 0.1) !important; color: #FF3131 !important; border: 1px solid rgba(255, 49, 49, 0.2) !important; }}

            /* Table Translator Button - Mobile (Red) */
            .table-translator-btn button {{
                background: linear-gradient(135deg, #FF0000 0%, #8B0000 100%) !important;
                color: #FFFFFF !important;
                border: 2px solid #FF3131 !important;
                box-shadow: 0 0 15px rgba(255, 0, 0, 0.4) !important;
            }}

            /* === MOBILE NEON WHITE TEXT === */
            /* Advanced Filtering Checkboxes */
            div[data-testid="stExpander"] div[data-testid="stCheckbox"] label p,
            .mobile-neon-text {{
                color: #FFFFFF !important;
                text-shadow: 0 0 8px #ffffff, 0 0 15px #ffffff, 0 0 25px #ffffff !important;
                font-weight: bold !important;
            }}

            /* Login Input Fields Mobile Overrides (Black text on Light background) */
            div[data-testid="stForm"] div[data-baseweb="input"] {{
                background: rgba(255, 255, 255, 0.95) !important;
                border-color: #FFFFFF !important;
                box-shadow: 0 0 15px rgba(255, 255, 255, 0.5) !important;
            }}
            div[data-testid="stForm"] .stTextInput input {{
                color: #000000 !important;
                text-shadow: none !important;
                font-weight: bold !important;
            }}
            div[data-testid="stForm"] label p {{
                color: #FFFFFF !important;
                text-shadow: 0 0 8px rgba(255, 255, 255, 0.8) !important;
            }}
        }}


        /* Table Translator Button - Desktop/Tablet (White) */
        .table-translator-btn button {{
            background: linear-gradient(135deg, #FFFFFF 0%, #E0E0E0 100%) !important;
            color: #000000 !important;
            border: 2px solid #FFFFFF !important;
            box-shadow: 0 0 15px rgba(255, 255, 255, 0.3) !important;
            font-weight: 700 !important;
        }}
        .table-translator-btn button:hover {{
            transform: scale(1.05) !important;
            box-shadow: 0 0 25px rgba(255, 255, 255, 0.6) !important;
        }}
    </style>
    """

# --- Icon Mappings ---
FLAG_MAP = {
    # Arabic
    "هندي": "in", "هندية": "in", "الهند": "in",
    "فلبيني": "ph", "فلبينية": "ph", "الفلبين": "ph",
    "نيبالي": "np", "نيبالية": "np", "نيبال": "np",
    "بنجلاديشي": "bd", "بنجالية": "bd", "بنجلاديش": "bd", "بنقالي": "bd",
    "باكستاني": "pk", "باكستانية": "pk", "باكستان": "pk",
    "مصري": "eg", "مصرية": "eg", "مصر": "eg",
    "سوداني": "sd", "سودانية": "sd", "السودان": "sd",
    "سيريلانكي": "lk", "سيريلانكية": "lk", "سيريلانكا": "lk",
    "كيني": "ke", "كينية": "ke", "كينيا": "ke",
    "اوغندي": "ug", "اوغندية": "ug", "اوغندا": "ug",
    "اثيوبي": "et", "اثيوبية": "et", "اثيوبيا": "et",
    "مغربي": "ma", "مغربية": "ma", "المغرب": "ma",
    "يمني": "ye", "يمنية": "ye", "اليمن": "ye",
    "اندونيسي": "id", "اندونيسية": "id", "اندونيسيا": "id", "اندونيسا": "id",
    "رواندي": "rw", "رواندية": "rw", "رواندا": "rw", "روندا": "rw", "روندي": "rw", "روندية": "rw",
    "افغاني": "af", "افغانية": "af", "افغانستان": "af", "افغان": "af",
    "نيجيري": "ng", "نيجيرية": "ng", "نيجيريا": "ng", "نيجريا": "ng", "نيجري": "ng", "نيجرية": "ng",
    # English
    "indian": "in", "filipino": "ph", "nepi": "np", "nepali": "np", "nepal": "np",
    "bangla": "bd", "bangladeshi": "bd", "pakistan": "pk", "pakistani": "pk",
    "egypt": "eg", "egyptian": "eg", "sudan": "sd", "sudanese": "sd",
    "sri lanka": "lk", "sri lankan": "lk", "kenya": "ke", "kenyan": "ke",
    "uganda": "ug", "ugandan": "ug", "ethiopia": "et", "ethiopian": "et",
    "indonesian": "id", "indonesia": "id", "rwandan": "rw", "rwanda": "rw",
    "afghan": "af", "afghanistan": "af", "nigerian": "ng", "nigeria": "ng"
}

GENDER_MAP = {
    "ذكر": "🚹", "male": "🚹",
    "أنثى": "🚺", "female": "🚺"
}

@st.cache_data(ttl=600, show_spinner=False)
def _get_flag_url_cached(val):
    if not val: return None
    s_val = str(val).strip().lower()
    # Pre-sort keys by length descending for best match (done once at module level)
    # For now, just use the global FLAG_MAP
    for key, code in FLAG_MAP_SORTED:
        if len(key) <= 3:
            pattern = rf'(?:^|[\s,:;.\-/]){re.escape(key)}(?:[\s,:;.\-/]|$)'
            if re.search(pattern, s_val):
                return f"https://flagsapi.com/{code.upper()}/flat/64.png"
        else:
            if key in s_val:
                return f"https://flagsapi.com/{code.upper()}/flat/64.png"
    return None

# Pre-sort FLAG_MAP keys once at startup
FLAG_MAP_SORTED = sorted(FLAG_MAP.items(), key=lambda x: len(x[0]), reverse=True)

def style_df(df):
    """
    Applies custom styling to DataFrames (Optimized for 2026 Speed).
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        return df

    styled_df = df.copy()
    lang = st.session_state.lang
    
    # 0. Selective Auto-Translation for English UI
    if lang == 'en':
        # Only translate columns likely to have Arabic content
        trans_keywords = ["job", "skill", "city", "location", "profession", "الوظيفة", "مهارات", "المدينة", "المهنة"]
        for col in styled_df.columns:
            col_lower = str(col).lower()
            if any(kw in col_lower for kw in trans_keywords):
                if styled_df[col].dtype == 'object':
                    styled_df[col] = styled_df[col].apply(lambda x: auto_translate(x, target_lang='en'))

    # 1. Flag Image Injection (Optimized) - Insert BEFORE nationality column
    nat_cols = [c for c in styled_df.columns if any(kw in str(c).lower() for kw in ["nationality", "الجنسية"])]
    for col in nat_cols:
        flag_col = f"🚩_{col}"
        if flag_col not in styled_df.columns:
            # Get current index of nationality column
            idx = list(styled_df.columns).index(col)
            # Insert flag column at the same position (shifts nationality to right)
            styled_df.insert(idx, flag_col, styled_df[col].apply(_get_flag_url_cached))
        else:
            # Ensure it's in the correct position if it already exists
            cols = list(styled_df.columns)
            flag_idx = cols.index(flag_col)
            nat_idx = cols.index(col)
            if flag_idx != nat_idx - 1:
                cols.remove(flag_col)
                # Re-calculate index after removal
                new_nat_idx = cols.index(col)
                cols.insert(new_nat_idx, flag_col)
                styled_df = styled_df[cols]
        

        # Fast cleanup - remove emoji flags from text (Safe conversion for Arrow)
        import re
        styled_df[col] = styled_df[col].astype(str).apply(lambda x: re.sub(r'[\U0001F1E6-\U0001F1FF]{2}\s*', '', x))


    # 2. Gender Icon Injection (Fast Vectorized replacement)
    gen_cols = [c for c in styled_df.columns if any(kw in str(c).lower() for kw in ["gender", "الجنس"]) and str(c).lower() != "الجنسية"]
    for col in gen_cols:
        for key, icon in GENDER_MAP.items():
            mask = styled_df[col].astype(str).str.strip().str.lower() == key
            styled_df.loc[mask, col] = icon + " " + styled_df.loc[mask, col].astype(str)

    # 3. Apply Dynamic Styling (Optimized Styler)
    def apply_colors(val):
        s_val = str(val).lower()
        if '🚹' in s_val or 'ذكر' in s_val or 'male' in s_val:
            return "color: #3498db; font-weight: bold;" 
        if '🚺' in s_val or 'أنثى' in s_val or 'female' in s_val:
            return "color: #e91e63; font-weight: bold;"
        return "color: #4CAF50;"

    return styled_df.style.map(
        apply_colors, 
        subset=[c for c in styled_df.columns if not str(c).startswith("🚩_")]
    )

@st.cache_data(ttl=3600, show_spinner=False)
def _parse_to_date_str_cached(val):
    if val is None or str(val).strip() == '': return ""
    try:
        from dateutil import parser as dateutil_parser
        val_str = str(val).strip()
        # Arabic to Western Numerals
        a_to_w = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
        val_str = val_str.translate(a_to_w)
        # Remove Arabic AM/PM
        clean_s = re.sub(r'[صم]', '', val_str).strip()
        dt = dateutil_parser.parse(clean_s, dayfirst=False)
        return dt.strftime('%Y-%m-%d')
    except:
        # Fallback to pandas
        try:
            dt = pd.to_datetime(val, errors='coerce')
            if pd.isna(dt): return str(val)
            return dt.strftime('%Y-%m-%d')
        except:
            return str(val)

def clean_date_display(df):
    """
    Finds date-like columns and formats them (Cached & Optimized).
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        return df
        
    date_keywords = ["date", "time", "تاريخ", "طابع", "التسجيل", "expiry", "end", "متى"]
    for col in df.columns:
        col_lower = str(col).lower()
        if any(kw in col_lower for kw in date_keywords):
            df[col] = df[col].apply(_parse_to_date_str_cached)
            
    return df

# 2.4 Global Premium Popup Helper

def render_table_translator(df, key_prefix="table"):
    """
    Renders side-by-side translation buttons (Arabic and Tagalog) above tables.
    Translates Requested Job, Other Skills, and Iqama Profession columns.
    """
    if df is None or df.empty:
        return df

    # Expanded Keywords to catch all relevant columns in any language
    target_keywords = [
        "وظيفة", "الوظيفة", "مهنة", "المهنة", "مهارة", "مهارات", "خبرة", "الخبرة",
        "جنسية", "الجنسية", "جنس", "الجنس", "حالة", "الحالة",
        "job", "profession", "skill", "experience", "occupation",
        "nationality", "gender", "status", "requested"
    ]
    cols_to_translate = [c for c in df.columns if any(kw.lower() in str(c).lower() for kw in target_keywords)]

    if not cols_to_translate:
        return df

    from src.core.translation import TranslationManager
    tm = TranslationManager()

    st.markdown('<div class="table-translator-container">', unsafe_allow_html=True)
    ct1, ct2 = st.columns(2)
    
    t_state_key = f"table_trans_{key_prefix}"
    
    with ct1:
        st.markdown('<div class="table-translator-btn">', unsafe_allow_html=True)
        if st.button("🇸🇦 الترجمة للعربية", key=f"btn_ar_{key_prefix}", use_container_width=True):
            st.session_state[t_state_key] = "ar"
        st.markdown('</div>', unsafe_allow_html=True)

    with ct2:
        st.markdown('<div class="table-translator-btn">', unsafe_allow_html=True)
        if st.button("🇵🇭 ISALIN SA TAGALOG", key=f"btn_tl_{key_prefix}", use_container_width=True):
            st.session_state[t_state_key] = "tl"
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    target_lang = st.session_state.get(t_state_key)
    if target_lang in ['ar', 'tl']:
        spinner_msg = "جارِ الترجمة..." if target_lang == 'ar' else "Isinasalin sa Tagalog..."
        with st.spinner(spinner_msg):
            for col in cols_to_translate:
                unique_vals = [v for v in df[col].unique() if v and isinstance(v, str) and len(str(v).strip()) > 0]
                if unique_vals:
                    translations = {val: tm.translate_full_text(val, target_lang=target_lang) for val in unique_vals}
                    df[col] = df[col].map(translations).fillna(df[col])
            
            # Show toast only upon completion to confirm it worked
            if 'last_trans_msg' not in st.session_state or st.session_state.last_trans_msg != f"{key_prefix}_{target_lang}":
                msg = "✅ تمت الترجمة!" if target_lang == 'ar' else "✅ Tapos na ang pagsasalin!"
                st.toast(msg)
                st.session_state.last_trans_msg = f"{key_prefix}_{target_lang}"
    
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def get_cached_translation(val, target_lang):
    try:
        if not val: return val
        from src.core.translation import TranslationManager
        tm = TranslationManager()
        return tm.translate_full_text(val, target_lang=target_lang)
    except:
        return val

def auto_translate(val, target_lang='en', force_stay_ar=False):
    """
    Automatically translates text bidirectional between Arabic and English (Optimized).
    """
    if not val or not isinstance(val, (str, object)):
        return val
    
    val_str = str(val).strip()
    if not val_str or len(val_str) < 2:
        return val
    
    try:
        # Get TM from session state
        tm = st.session_state.get('tm')
        if not tm:
            from src.core.translation import TranslationManager
            st.session_state.tm = TranslationManager()
            tm = st.session_state.tm
        
        # SPECIAL: If force_stay_ar is True and it's already Arabic, don't translate to EN
        is_ar = bool(re.search(r'[\u0600-\u06FF]', val_str))
        if force_stay_ar and is_ar:
            return val_str

        # Use our new bidirectional UI translator
        translated = tm.translate_ui_value(val_str, target_lang)
        if translated != val_str:
            return translated
            
        # Fallback to cached full text translation if allowed and needed
        if (is_ar and target_lang == 'en') or (not is_ar and target_lang == 'ar'):
             return get_cached_translation(val_str, target_lang)
             
        return val_str
    except:
        return val_str

def show_toast(message, typ="success", duration=5, container=None):
    """
    Renders a floating luxury notification (popup) centered on the screen.
    """
    is_contextual = container is not None
    # Dead Center Positioning (Fixed for Global, Absolute for Local)
    if is_contextual:
        pos_css = "position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 340px;"
    else:
        pos_css = "position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 90%; max-width: 440px;"
    
    # Determine Icon, Colors, and Backgrounds based on type for a Premium Feel
    if typ == "success":
        icon_path = '<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" fill="#D4AF37"/>'
        bg = "linear-gradient(135deg, #1A1A1A 0%, #000 100%)"
        accent = "#D4AF37"
    elif typ == "error":
        icon_path = '<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" fill="#FF4B4B"/>'
        bg = "linear-gradient(135deg, #2D0A0A 0%, #000 100%)"
        accent = "#FF4B4B"
    elif typ == "warning":
        icon_path = '<path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z" fill="#FFA500"/>'
        bg = "linear-gradient(135deg, #2D200A 0%, #000 100%)"
        accent = "#FFA500"
    else:
        icon_path = '<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z" fill="#00BFFF"/>'
        bg = "linear-gradient(135deg, #0A1A2D 0%, #000 100%)"
        accent = "#00BFFF"

    # Contextual wrapper if needed
    wrapper_start = '<div style="position: relative; width: 100%; height: 0; min-height: 0;">' if is_contextual else ''
    wrapper_end = '</div>' if is_contextual else ''

    # CSS for the Floating Luxury Popup with Entrance/Exit Animations
    toast_html = f"""
    {wrapper_start}
    <div style="{pos_css} z-index: 2147483647; pointer-events: none; direction: rtl;">
        <div style="
            background: {bg};
            border: 2px solid {accent};
            border-radius: 16px;
            box-shadow: 0 40px 100px rgba(0,0,0,0.95), 0 0 30px {accent}33;
            display: flex;
            align-items: center;
            padding: 18px 25px;
            gap: 18px;
            animation: luxuryToastCenter 5s cubic-bezier(0.1, 0.9, 0.2, 1) forwards;
            overflow: hidden;
            backdrop-filter: blur(10px);
        ">
            <style>
                @keyframes luxuryToastCenter {{
                    0%   {{ opacity: 0; transform: scale(0.6) translateY(20px); }}
                    10%  {{ opacity: 1; transform: scale(1.05) translateY(0); }}
                    15%  {{ transform: scale(1); }}
                    85%  {{ opacity: 1; transform: scale(1); }}
                    100% {{ opacity: 0; transform: scale(0.9) translateY(-20px); visibility: hidden; }}
                }}
            </style>
            <div style="width: 32px; height: 32px; flex-shrink: 0;">
                <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="{accent}22"/>{icon_path}</svg>
            </div>
            <div style="color: #FFF; font-size: 16px; font-weight: 700; flex-grow: 1; text-align: center; font-family: 'Cairo', sans-serif; line-height: 1.4;">
                {message}
            </div>
        </div>
    </div>
    {wrapper_end}
    """
    
    if container:
        container.markdown(toast_html, unsafe_allow_html=True)
    else:
        st.markdown(toast_html, unsafe_allow_html=True)


# 2.5 Hourglass Loader Helper
def show_loading_hourglass(text=None, container=None):
    if text is None:
        text = "جاري التحميل..." if st.session_state.get('lang') == 'ar' else "Loading..."
    
    target = container if container else st.empty()
    with target:
        # Full-Screen Overlay Hourglass - Transparent background, centered, above all content
        st.markdown(f"""
            <div id="hourglass-overlay" style="
                position: fixed;
                top: 0; left: 0;
                width: 100vw; height: 100vh;
                background: rgba(0, 0, 0, 0.45);
                backdrop-filter: blur(3px);
                -webkit-backdrop-filter: blur(3px);
                z-index: 999999;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                pointer-events: none;
            ">
                <svg class="modern-hourglass-svg" viewBox="0 0 100 100" style="
                    width: 100px; height: 100px;
                    filter: drop-shadow(0 0 18px rgba(212, 175, 55, 0.8));
                ">
                    <!-- Glass Structure -->
                    <path class="glass" d="M30,20 L70,20 L50,50 L70,80 L30,80 L50,50 Z" />
                    <!-- Sand Top -->
                    <path class="sand sand-top" d="M30,20 L70,20 L50,50 Z" />
                    <!-- Sand Bottom -->
                    <path class="sand sand-bottom" d="M50,50 L70,80 L30,80 Z" />
                    <!-- Sand Drip -->
                    <rect class="sand-drip" x="49.5" y="50" width="1" height="30" />
                </svg>
                <p style="
                    color: #D4AF37;
                    font-size: 16px;
                    margin-top: 20px;
                    font-family: 'Cairo', sans-serif;
                    letter-spacing: 2px;
                    text-shadow: 0 0 10px rgba(212, 175, 55, 0.5);
                ">{text}</p>
            </div>
        """, unsafe_allow_html=True)
    return target

# 3. Imports with Error Handling
try:
    from src.core.search import SmartSearchEngine
    from src.core.contracts import ContractManager
    from src.core.translation import TranslationManager
    from src.data.db_client import DBClient
    from src.config import USERS_FILE, ASSETS_DIR
    from src.core.i18n import t, t_col # Added t_col
    from src.ui.whatsapp_ui import render_whatsapp_page
except ImportError as e:
    # Diagnostic: Check if 'src' exists
    import os
    src_exists = os.path.isdir(os.path.join(ROOT_DIR, "src"))
    st.error(f"Critical Import Error: {e}")
    if not src_exists:
        st.warning(f"⚠️ 'src' directory not found in: {ROOT_DIR}. Please ensure you are running the app from the correct folder.")
    else:
        st.info(f"💡 'src' found at {ROOT_DIR}. Internal module error or configuration issue.")
    st.stop()

# 4. Page Config
st.set_page_config(
    page_title="السعيد الوزان | نظام مراقبة العقود",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 5. Global Initialization Logic moved below for dynamic CSS

# 6. Initialize Core (With Force Re-init for Updates)
if 'auth' not in st.session_state or not hasattr(st.session_state.auth, 'v10_marker'):
    st.session_state.auth = AuthManager(USERS_FILE)
    st.session_state.auth.v10_marker = True 
    st.session_state.db = DBClient() 

# Report DB Load Errors to User
if hasattr(st.session_state.auth, 'load_error'):
    st.error(f"⚠️ Error Loading User Database: {st.session_state.auth.load_error}")

if 'db' not in st.session_state or not hasattr(st.session_state.db, 'fetch_customer_requests'):
    st.session_state.db = DBClient()

# Initialize TranslationManager if not already in session state
if 'tm' not in st.session_state:
    try:
        from src.core.translation import TranslationManager
        st.session_state.tm = TranslationManager()
    except Exception as e:
        print(f"[ERROR] Failed to init TranslationManager: {e}")
        st.session_state.tm = None

# 7. Session State Defaults
if 'user' not in st.session_state:
    st.session_state.user = None
if 'lang' not in st.session_state:
    st.session_state.lang = 'ar'
if 'last_login_time' not in st.session_state:
    st.session_state.last_login_time = 0
if 'notifications' not in st.session_state:
    st.session_state.notifications = []

# 5. Apply Dynamic Styles Based on Language
st.markdown(get_css(st.session_state.lang), unsafe_allow_html=True)

# 8. Constants
IMG_PATH = os.path.join(ASSETS_DIR, "alsaeed.jpg")
if not os.path.exists(IMG_PATH):
    IMG_PATH = "alsaeed.jpg" # Fallback

# 9. Language Toggle Helper
def toggle_lang():
    if st.session_state.lang == 'ar': st.session_state.lang = 'en'
    else: st.session_state.lang = 'ar'


# 11. CV Detail Panel Helper
def render_cv_detail_panel(worker_row, selected_idx, lang, key_prefix="search", worker_uid=None):
    """
    Standalone helper to render the professional CV profile card, 
    preview (iframe), and translation logic.
    """
    # Robust name detection (Handles original and translated names)
    name_keys = ["Full Name:", "الاسم الكامل", "Name", "الاسم"]
    worker_name = "Worker"
    for nk in name_keys:
        if nk in worker_row.index:
            worker_name = worker_row[nk]
            break
            
    # NEW: Calculate a unique ID for this worker to isolate translation state
    worker_id = worker_uid
    if not worker_id:
        sheet_row = worker_row.get('__sheet_row', worker_row.get('__sheet_row_backup'))
        if sheet_row:
            worker_id = f"row_{sheet_row}"
        else:
            import hashlib
            w_name_fallback = str(worker_row.get("Full Name:", worker_row.get("الاسم الكامل", worker_name)))
            worker_id = hashlib.md5(w_name_fallback.encode()).hexdigest()[:10]

    # Dynamically find CV column
    cv_col = None
    for c in worker_row.index:
        c_clean = str(c).lower()
        if "cv" in c_clean or "سيرة" in c_clean or "download" in c_clean:
            cv_col = c
            break
    cv_url = worker_row.get(cv_col, "") if cv_col else ""
    
    # --- AUTO SCROLL LOGIC ---
    scroll_key = f"last_scroll_{key_prefix}"
    if scroll_key not in st.session_state or st.session_state[scroll_key] != worker_id:
        st.session_state[scroll_key] = worker_id
        st.components.v1.html(
            f"""
            <script>
                setTimeout(function() {{
                    var el = window.parent.document.getElementById('cv-anchor-{key_prefix}');
                    if (el) el.scrollIntoView({{behavior: 'smooth'}});
                }}, 300);
            </script>
            """,
            height=0
        )

    # --- PROFESSIONAL PROFILE CARD (2026 LUXURY) ---
    st.markdown(f"<div id='cv-anchor-{key_prefix}'></div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="background: rgba(20, 20, 20, 0.85); 
                backdrop-filter: blur(15px);
                padding: 30px; 
                border-radius: 20px; 
                border-left: 5px solid #D4AF37; 
                border-bottom: 1px solid rgba(212, 175, 55, 0.2);
                margin: 25px 0;
                box-shadow: 0 15px 35px rgba(0,0,0,0.4);">
        <h2 style="color: #D4AF37; 
                   margin: 0; 
                   font-family: 'Cinzel', serif; 
                   letter-spacing: 2px;
                   text-transform: uppercase;
                   font-size: 1.8rem;">
            👤 {worker_name}
        </h2>
    </div>
    """, unsafe_allow_html=True)
    
    col_a, col_b = st.columns([1, 1])
    
    # === Professional Summary Modal & Button === #
    @st.dialog("الملخص الاحترافي للعامل" if lang == "ar" else "Professional Worker Summary")
    def show_worker_summary_modal():
        import re as _re
        # -- 1. Data Extraction --
        def g(ar_col, en_col):
            val = worker_row.get(en_col, worker_row.get(ar_col, ""))
            return str(val).strip() if pd.notnull(val) else ""

        name = g("الاسم الكامل", "Full Name:")
        nat = g("الجنسية", "Nationality")
        gen = g("الجنس", "Gender")
        age = g("العمر", "your Age:")
        ar_lang_val = g("هل تتحدث العربية؟", "Do you speak Arabic")
        job = g("الوظيفة المطلوبة", "Which job are you looking for")
        exp = g("الخبرة في هذا المجال", "Experience in this field")
        skills = g("مهارات أخرى", "What other jobs can you do")
        exp_other = g("الخبرة (أخرى)", "Other experience")
        card = g("هل لديك كرت بلدية؟", "Do you have Card Baladiya")
        card_val = g("مدة صلاحية الكرت (أشهر)", "how many months Card Baladiya valid")
        iqama_prof = g("المهنة في الإقامة", "What is the occupation listed on your Iqama")
        iqama_rem = g("المدة المتبقية في الإقامة", "If the Iqama is valid, how many months are left?")
        transfers = g("عدد مرات نقل الكفالة", "How many times did you transfer your sponsorship")

        # -- 2. EN→AR Dictionary for strict Arabic localization --
        is_ar = (lang == "ar")
        _en_ar = {
            "male": "ذكر", "female": "أنثى",
            "indian": "هندي", "bangladeshi": "بنغلاديشي", "pakistani": "باكستاني",
            "filipino": "فلبيني", "filipina": "فلبينية", "indonesian": "إندونيسي",
            "nepali": "نيبالي", "nepalese": "نيبالي", "sri lankan": "سريلانكي",
            "ethiopian": "إثيوبي", "eritrean": "إريتري", "sudanese": "سوداني",
            "egyptian": "مصري", "yemeni": "يمني", "syrian": "سوري",
            "jordanian": "أردني", "lebanese": "لبناني", "moroccan": "مغربي",
            "tunisian": "تونسي", "algerian": "جزائري", "iraqi": "عراقي",
            "afghan": "أفغاني", "turkish": "تركي", "kenyan": "كيني",
            "nigerian": "نيجيري", "ghanaian": "غاني", "ugandan": "أوغندي",
            "somali": "صومالي", "burmese": "بورمي", "thai": "تايلندي",
            "vietnamese": "فيتنامي", "chinese": "صيني", "malaysian": "ماليزي",
            "barista": "باريستا", "coffee maker": "صانع قهوة", "driver": "سائق",
            "chef": "شيف (طباخ)", "cook": "طباخ", "cleaner": "عامل نظافة",
            "waiter": "نادل", "cashier": "كاشير", "security guard": "حارس أمن",
            "plumber": "سبّاك", "electrician": "كهربائي", "carpenter": "نجار",
            "painter": "دهّان", "welder": "لحّام", "mechanic": "ميكانيكي",
            "ac technician": "فني تكييف", "technician": "فني", "supervisor": "مشرف",
            "manager": "مدير", "management": "إدارة", "managerial": "إداري",
            "accountant": "محاسب", "salesman": "بائع", "sales": "مبيعات",
            "worker": "عامل", "laborer": "عامل", "farmer": "مزارع",
            "gardener": "بستاني", "tailor": "خياط", "barber": "حلّاق",
            "baker": "خبّاز", "butcher": "جزّار", "nurse": "ممرض",
            "hairdresser": "مصفف شعر", "hair dresser": "مصفف شعر", "dresser": "مصفف شعر",
            "makeup artist": "خبير تجميل", "beautician": "أخصائى تجميل",
            "massage": "مساج", "massage therapist": "أخصائي مساج",
            "manicure": "بدكير", "pedicure": "منكير",
            "moroccan bath": "حمام مغربي", "bath": "حمام",
            "spa": "سبا", "salon": "صالون",
            "secretary": "سكرتير", "secretarial": "سكرتاريا",
            "office boy": "عامل مكتب (أوفيس بوي)", "tea boy": "عامل تقديم شاي (تي بوي)",
            "receptionist": "موظف استقبال", "waitress": "نادلة",
            "housekeeper": "عامل منزلي", "housemaid": "عاملة منزلية",
            "babysitter": "مربية أطفال", "nanny": "مربية أطفال",
            "delivery driver": "سائق توصيل", "delivery": "توصيل",
            "purchasing/warehouse manager": "مدير مشتريات/مستودعات",
            "warehouse manager": "مدير مستودعات", "purchasing": "مشتريات",
            "store keeper": "أمين مستودع", "storekeeper": "أمين مستودع",
            "data entry": "إدخال بيانات", "helper": "مساعد",
            "general helper": "مساعد عام", "flower coordinator": "منسق زهور",
            "coordinator": "منسق", "sales": "مبيعات",
            "first time": "المرة الأولى", "second time": "المرة الثانية",
            "third time": "المرة الثالثة", "fourth time": "المرة الرابعة",
            "once": "مرة واحدة", "twice": "مرتان", "never": "لم يتم النقل",
            "1 time": "مرة واحدة", "2 times": "مرتان", "3 times": "3 مرات",
            "i speak arabic fluently": "يتحدث العربية بطلاقة",
            "i speak arabic in the middle": "يتحدث العربية بشكل متوسط",
            "i speak arabic a little": "يتحدث العربية قليلاً",
            "i don't speak arabic": "لا يتحدث العربية",
            "i do not speak arabic": "لا يتحدث العربية",
            "fluently": "بطلاقة", "fluent": "بطلاقة",
            "a little": "قليلاً", "good": "جيد", "very good": "جيد جداً",
            "excellent": "ممتاز", "basic": "أساسي", "intermediate": "متوسط",
            "advanced": "متقدم", "no": "لا", "yes": "نعم",
            "experience": "خبرة", "experiance": "خبرة",
            "years": "سنوات", "year": "سنة", "months": "أشهر", "month": "شهر",
            "riyadh": "الرياض", "jeddah": "جدة", "makkah": "مكة المكرمة",
            "madinah": "المدينة المنورة", "medina": "المدينة المنورة",
            "dammam": "الدمام", "khobar": "الخبر", "abha": "أبها",
            "taif": "الطائف", "tabuk": "تبوك", "hail": "حائل",
            "jazan": "جازان", "najran": "نجران", "yanbu": "ينبع",
            "jubail": "الجبيل", "khamis mushait": "خميس مشيط",
            "buraydah": "بريدة", "al kharj": "الخرج",
            "and": "و", "or": "أو", "available": "متاح",
            # Restaurant & food industry
            "restaurant": "مطعم", "captain": "كابتن", "all": "جميع",
            "in": "في", "the": "الـ", "of": "من", "for": "لـ",
            "hotel": "فندق", "kitchen": "مطبخ", "cafe": "مقهى",
            "typing": "طباعة", "filing": "أرشفة",
        }

        def to_arabic(val):
            """Smart EN to AR: translates ALL English text to Arabic using Google Translate."""
            if not val or not is_ar:
                return val
            text = str(val).strip()
            if not _re.search(r'[a-zA-Z]', text):
                return text
            low = text.lower()
            # 1. Arabic proficiency phrases
            prof_match = _re.search(r'speak\s*arabic|arabic.*speak', low)
            if prof_match or ('arabic' in low and 'speak' in low):
                if _re.search(r'fluent|very\s*well', low):
                    return "يتحدث العربية بطلاقة"
                elif _re.search(r'middle|moderate|so\s*so|average|intermed', low):
                    return "يتحدث العربية بشكل متوسط"
                elif _re.search(r'little|basic|simple|small', low):
                    return "يتحدث العربية قليلاً"
                elif _re.search(r"don't|do\s*not", low):
                    return "لا يتحدث العربية"
                elif _re.search(r'good', low):
                    return "يتحدث العربية بشكل جيد"
                else:
                    return "يتحدث العربية"
            # 2. Numeric experience pattern
            cleaned = text.strip().replace("'s", "").replace("'", "")
            m = _re.match(r'^(\d+)\s*x?\s*(years?|months?)?(\s*experience|\s*experiance)?$', cleaned, _re.IGNORECASE)
            if m:
                n = m.group(1)
                unit = m.group(2)
                if not unit and int(n) < 50:
                    return f"{n} سنوات"
                if not unit:
                    return n
                u = "سنوات" if "year" in unit.lower() else "أشهر"
                if n == "1":
                    u = "سنة" if "year" in unit.lower() else "شهر"
                return f"{n} {u}"
            # 3. Google Translate for everything else
            try:
                translated = get_cached_translation(text, 'ar')
                if translated and not translated.startswith("Translation Error") and not translated.startswith("Error:"):
                    return translated.strip()
            except Exception:
                pass
            return text

        # -- UI Strings --
        msg_warning = "⚠️ لا توجد بيانات كافية لإنشاء ملخص." if is_ar else "⚠️ Not enough professional data found for summary."
        msg_success = "📝 **الملخص جاهز!** يمكنك نسخه الآن." if is_ar else "📝 **Summary Ready!** You can copy it now."
        title = "🚀 **ملف كفاءة مهنية مرشحة للعمل** 🚀" if is_ar else "🚀 **Professional Candidate Profile** 🚀"
        sep = "━━━━━━━━━━━━━━━━━━━━━━━━"
        sec_overview = "✨ **نظرة عامة على الملف الشخصي:**" if is_ar else "✨ **Profile Overview:**"
        lbl_name = "👤 **الاسم الكامل:**" if is_ar else "👤 **Full Name:**"
        lbl_nat = "🌍 **الجنسية:**" if is_ar else "🌍 **Nationality:**"
        lbl_age = "🎂 **العمر:**" if is_ar else "🎂 **Age:**"
        lbl_gen = "🚻 **الجنس:**" if is_ar else "🚻 **Gender:**"
        sec_quals = "💼 **المؤهلات المهنية والخبرات:**" if is_ar else "💼 **Professional Qualifications:**"
        lbl_job = "🎯 **المسمى الوظيفي المستهدف:**" if is_ar else "🎯 **Targeted Job Title:**"
        lbl_exp = "⚖️ **الخبرة النوعية:**" if is_ar else "⚖️ **Field Experience:**"
        lbl_skills = "🛠️ **المهارات المتعددة:**" if is_ar else "🛠️ **Diverse Skills:**"
        lbl_exp_other = "📚 **الخبرة (أخرى):**" if is_ar else "📚 **Other Experience:**"
        lbl_iqama_p = "🆔 **المهنة الرسمية (الإقامة):**" if is_ar else "🆔 **Official Profession (Iqama):**"
        sec_ready = "⚡ **التواجد والقانونية (جاهزية النقل):**" if is_ar else "⚡ **Legal & Readiness (Transfer):**"
        lbl_trans = "🔄 **سجل نقل الكفالة:**" if is_ar else "🔄 **Transfer History:**"
        lbl_lang = "🗣️ **إتقان اللغة العربية:**" if is_ar else "🗣️ **Arabic Proficiency:**"
        lbl_rem = "⏳ **صلاحية الإقامة:**" if is_ar else "⏳ **Iqama Validity:**"
        lbl_card = "🪪 **كرت البلدية:**" if is_ar else "🪪 **Baladiya Card:**"
        val_months = "شهراً" if is_ar else "Months"
        val_years = "عاماً" if is_ar else "Years old"
        val_card_status = "متوفر وساري" if is_ar else "Available and Valid"
        footer = "💡 *تم مراجعة هذا الملف بدقة لضمان الجودة.*" if is_ar else "💡 *This profile has been verified for quality assurance.*"

        # -- Check for basic data --
        if not any([job, exp, nat]):
            d = 'rtl' if is_ar else 'ltr'
            a = 'right' if is_ar else 'left'
            st.markdown(f"<div style='direction:{d};text-align:{a};'>", unsafe_allow_html=True)
            st.warning(msg_warning)
            st.markdown("</div>", unsafe_allow_html=True)
            return

        # -- Build Summary --
        summary = f"{title}\n{sep}\n\n"
        summary += f"{sec_overview}\n"
        if name: summary += f"{lbl_name} {name}\n"
        if nat: summary += f"{lbl_nat} {to_arabic(nat)}\n"
        if age: summary += f"{lbl_age} {age} {val_years}\n"
        if gen: summary += f"{lbl_gen} {to_arabic(gen)}\n\n"
        summary += f"{sec_quals}\n"
        if job: summary += f"{lbl_job} {to_arabic(job)}\n"
        if exp: summary += f"{lbl_exp} {to_arabic(exp)}\n"
        if skills: summary += f"{lbl_skills} {to_arabic(skills)}\n"
        if exp_other: summary += f"{lbl_exp_other} {to_arabic(exp_other)}\n"
        if iqama_prof: summary += f"{lbl_iqama_p} {to_arabic(iqama_prof)}\n\n"
        summary += f"{sec_ready}\n"
        if transfers: summary += f"{lbl_trans} {to_arabic(transfers)}\n"
        if ar_lang_val: summary += f"{lbl_lang} {to_arabic(ar_lang_val)}\n"
        if iqama_rem: summary += f"{lbl_rem} {iqama_rem} {val_months}\n"
        if "yes" in card.lower() or "نعم" in card.lower() or "ساري" in card.lower():
            v_info = f" ({card_val} {val_months})" if card_val else ""
            summary += f"{lbl_card} {val_card_status}{v_info}\n"
        summary += f"\n{sep}\n{footer}"

        # -- UI Display --
        d = 'rtl' if is_ar else 'ltr'
        a = 'right' if is_ar else 'left'
        st.markdown(f"<div style='direction:{d};text-align:{a};'>", unsafe_allow_html=True)
        st.success(msg_success)
        st.code(summary, language="markdown")
        st.markdown("</div>", unsafe_allow_html=True)
        
    if st.button("✨ " + ("إنشاء ملخص العامل" if lang == 'ar' else "Create Worker Summary"), use_container_width=True, key=f"btn_summary_mk_{key_prefix}_{worker_id}"):
        show_worker_summary_modal()

    translate_configs = [
        {"lang_code": "ar", "label": t('translate_cv_btn', lang), "key_suffix": "ar", "target": "ar"},
        {"lang_code": "tl", "label": "✨ Isalin ang CV (Filipino)", "key_suffix": "tl", "target": "tl"}
    ]

    for idx, config in enumerate(translate_configs):
        with col_a if idx == 0 else col_b:
            if st.button(config["label"], use_container_width=True, type="primary" if idx == 0 else "secondary", key=f"btn_trans_{key_prefix}_{worker_id}_{config['key_suffix']}"):
                if cv_url and str(cv_url).startswith("http"):
                    from src.core.file_translator import FileTranslator
                    
                    trans_loader = show_loading_hourglass(t("extracting", lang))
                    try:
                        import requests
                        file_id = None
                        if "drive.google.com" in cv_url:
                            if "id=" in cv_url: file_id = cv_url.split("id=")[1].split("&")[0]
                            elif "/d/" in cv_url: file_id = cv_url.split("/d/")[1].split("/")[0]

                        session = requests.Session()
                        session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"})
                        
                        if file_id:
                            dl_url = f"https://docs.google.com/uc?export=download&id={file_id}"
                            resp = session.get(dl_url, stream=True, timeout=15)
                            token = next((v for k, v in resp.cookies.items() if k.startswith('download_warning')), None)
                            if token:
                                dl_url = f"https://docs.google.com/uc?export=download&confirm={token}&id={file_id}"
                                resp = session.get(dl_url, stream=True, timeout=15)
                            if resp.status_code >= 500: resp = requests.get(cv_url, timeout=15)
                        else:
                            resp = requests.get(cv_url, timeout=15)
                        
                        if resp.status_code == 200:
                            content = resp.content
                            content_type = resp.headers.get('Content-Type', '').lower()
                            filename_from_header = ""
                            cd = resp.headers.get('Content-Disposition', '')
                            if 'filename=' in cd: filename_from_header = cd.split('filename=')[1].strip('"')
                            
                            ext = ".pdf"
                            if "word" in content_type or filename_from_header.endswith(".docx"): ext = ".docx"
                            elif "image" in content_type: ext = ".png" if "png" in content_type else ".jpg"
                            elif filename_from_header.endswith(".bdf"): ext = ".bdf"
                            elif content.startswith(b"%PDF"): ext = ".pdf"
                            elif content.startswith(b"PK\x03\x04"): ext = ".docx"
                            
                            ft = FileTranslator(source_lang="auto", target_lang=config["target"])
                            virtual_filename = filename_from_header if filename_from_header else f"file{ext}"
                            result = ft.translate(content, virtual_filename)
                            
                            if result.get("success"):
                                # Store with language-specific key
                                st.session_state[f"trans_{key_prefix}_{worker_id}_{config['key_suffix']}"] = {
                                    "orig": result.get("original_text", ""), 
                                    "trans": result.get("translated_text", ""),
                                    "output": result.get("output_bytes"),
                                    "out_filename": result.get("output_filename"),
                                    "target_label": "Arabic" if config["target"] == "ar" else "Filipino"
                                }
                                st.rerun()
                            else:
                                st.error(f"❌ {result.get('error', 'Unknown Error')}")
                        else:
                            st.error(f"خطأ في الوصول للملف: (HTTP {resp.status_code})")
                    except Exception as e: st.error(f"Error: {str(e)}")
                    finally: trans_loader.empty()
                else: st.warning("رابط السيرة الذاتية غير موجود أو غير صالح.")

    # Permanent Deletion with Confirmation
    sheet_row = worker_row.get('__sheet_row')
    if not sheet_row: sheet_row = worker_row.get('__sheet_row_backup') # Try backup key
    
    # Fallback lookup if ID is missing (Sync issues)
    if not sheet_row:
        if hasattr(st.session_state.db, "find_row_by_data"):
            with st.spinner("⏳ محاولة البحث عن معرف السطر..."):
                sheet_row = st.session_state.db.find_row_by_data(worker_name)
        else:
            st.warning("⚠️ ميزة الحذف الذكي تتطلب تحديث ملف `src/data/db_client.py`. يرجى رفعه لتجنب الأخطاء.")

    is_op_mode = str(key_prefix).startswith("op_")
    
    if is_op_mode:
        # For Order Processing: Replace Delete with Hide
        if worker_uid:
            if st.button("🚫 " + ("إخفاء هذا العامل" if lang == 'ar' else "Hide this worker"), 
                         use_container_width=True, key=f"hide_worker_{key_prefix}_{worker_id}"):
                st.session_state.op_hidden_workers.add(worker_uid)
                st.rerun()
        else:
            st.info("⚠️ الحذف غير متاح في هذا النموذج.")
    else:
        # Original Deletion Logic for Search/Contract Board
        if sheet_row:
            with st.popover(f"🗑️ {t('delete_btn', lang)}", use_container_width=True):
                st.warning(t("confirm_delete_msg", lang))
                if st.button(t("confirm_btn", lang), type="primary", use_container_width=True, key=f"del_confirm_{key_prefix}_{worker_id}"):
                    with st.spinner("⏳ جارٍ الحذف النهائي..."):
                        success = st.session_state.db.delete_row(sheet_row)
                        if success == True:
                            st.success(t("delete_success", lang))
                            time.sleep(1)
                            if f"last_scroll_{key_prefix}" in st.session_state: del st.session_state[f"last_scroll_{key_prefix}"]
                            st.rerun()
                        else:
                            st.error(f"{t('delete_error', lang)}: {success}")
        else:
            # Final Error UI with reset options
            st.error(f"⚠️ {t('delete_error', lang)} (ID Missing)")
            c1, c2 = st.columns(2)
            with c1:
                if st.button(t("fix_ids", lang), key=f"fix_id_{key_prefix}_{worker_id}", use_container_width=True):
                    st.session_state.db.fetch_data(force=True); st.rerun()
            with c2:
                if st.button(t("deep_reset", lang), key=f"reset_all_{key_prefix}_{worker_id}", use_container_width=True):
                    # Clear all tab data and cache
                    for k in list(st.session_state.keys()):
                        if k.startswith("dash_table_") or k.startswith("last_scroll_"): del st.session_state[k]
                    st.session_state.db.fetch_data(force=True); st.rerun()

    display_langs = ["ar", "tl"]
    for d_lang in display_langs:
        trans_key = f"trans_{key_prefix}_{worker_id}_{d_lang}"
        if trans_key in st.session_state:
            t_data = st.session_state[trans_key]
            target_label = t_data.get("target_label", "Translated")
            
            with st.expander(f"✨ CV Translation ({target_label})", expanded=True):
                c1, c2 = st.columns(2)
                with c1:
                    st.caption("English (Original)")
                    st.text_area(f"Orig_{d_lang}", t_data["orig"], height=300, key=f"orig_area_{key_prefix}_{worker_id}_{d_lang}")
                with c2:
                    st.caption(f"{target_label} (المترجمة)")
                    st.text_area(f"Trans_{d_lang}", t_data["trans"], height=300, key=f"trans_area_{key_prefix}_{worker_id}_{d_lang}")
                
                if t_data.get("output"):
                    st.download_button(
                        f"⬇️ {t('download_trans', lang)} ({target_label})",
                        data=t_data["output"],
                        file_name=t_data.get("out_filename", f"translated_{d_lang}"),
                        mime="application/octet-stream",
                        use_container_width=True,
                        key=f"dl_trans_file_{key_prefix}_{worker_id}_{d_lang}"
                    )
    
    st.markdown(f"#### 🔎 {t('preview_cv', lang)}")
    
    if cv_url and str(cv_url).startswith("http"):
        # NEW: Defer iframe loading to improve selection speed
        preview_key = f"show_preview_{key_prefix}_{worker_id}"
        if st.checkbox("👁️ " + ("عرض المعاينة المباشرة" if lang == 'ar' else "Show Live Preview"), key=preview_key):
            preview_url = cv_url
            if "drive.google.com" in cv_url:
                f_id = None
                if "id=" in cv_url: f_id = cv_url.split("id=")[1].split("&")[0]
                elif "/d/" in cv_url: f_id = cv_url.split("/d/")[1].split("/")[0]
                if f_id: preview_url = f"https://drive.google.com/file/d/{f_id}/preview"
            
            with st.spinner("⏳ " + ("جاري تحميل المعاينة..." if lang == 'ar' else "Loading Preview...")):
                st.components.v1.iframe(preview_url, height=600, scrolling=True)
        else:
            st.info("💡 " + ("اضغط على المربع أعلاه لعرض السيرة الذاتية هنا." if lang == 'ar' else "Click the checkbox above to view the CV here."))
            if st.button("🔗 " + ("فتح في نافذة جديدة" if lang == 'ar' else "Open in New Tab"), key=f"open_new_{worker_id}"):
                st.markdown(f'<a href="{cv_url}" target="_blank">Click here to open</a>', unsafe_allow_html=True)
    else: st.info("لا يتوفر رابط معاينة لهذا العامل.")

def login_screen():
    # Request browser notification permission early
    st.components.v1.html("""
<script>
// Request notification permission on page load
if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission().then(function(permission) {
        console.log('Notification permission:', permission);
    });
}
</script>
""", height=0)

    lang = st.session_state.lang
    
    # 2026 Luxury Flag Icons
    sa_icon = '<img src="https://flagcdn.com/w40/sa.png" style="width:24px; vertical-align:middle; border-radius:3px; margin:0 4px; box-shadow:0 0 8px rgba(0,0,0,0.4);">'
    ph_icon = '<img src="https://flagcdn.com/w40/ph.png" style="width:24px; vertical-align:middle; border-radius:3px; margin:0 4px; box-shadow:0 0 8px rgba(0,0,0,0.4);">'
    
    if lang == "ar":
        title_text = f'برنامج توريد العمالة الفلبينية {ph_icon} {sa_icon}'
    else:
        title_text = f'Philippines Recruitment Program {ph_icon} {sa_icon}'
    
    # Absolute Top Main Title
    st.markdown(f'<div class="luxury-main-title">{title_text}</div>', unsafe_allow_html=True)
    
    def render_login_box(suffix):
        saved = load_saved_credentials()
        saved_u = saved.get("u", "") if saved else ""
        saved_p = saved.get("p", "") if saved else ""
        
        with st.form(f"login_form_{suffix}"):
            # Row 1: Profile Image next to Welcome Text
            head_col1, head_col2 = st.columns([1, 2])
            with head_col2:
                welcome_text = t('welcome_back', lang)
                st.markdown(f'<h3 style="margin-top: 25px;">{welcome_text}</h3>', unsafe_allow_html=True)
            with head_col1:
                if os.path.exists(IMG_PATH):
                    b64 = get_base64_image(IMG_PATH)
                    st.markdown(f'<div style="text-align:right;"><img src="data:image/jpeg;base64,{b64}" class="profile-img-circular" style="width:80px; height:80px; border:2px solid #FFF; box-shadow: 0 0 15px #FFF;"></div>', unsafe_allow_html=True)
            
            # Inputs - Pre-fill with saved data if available
            u = st.text_input(t("username", lang), value=saved_u, label_visibility="collapsed", placeholder=t("username", lang), key=f"user_{suffix}")
            p = st.text_input(t("password", lang), value=saved_p, type="password", label_visibility="collapsed", placeholder=t("password", lang), key=f"pass_{suffix}")
            
            # Persistent check - White Neon Label
            persist_txt = "هل تريد حفظ الدخول" if lang == 'ar' else "Do you want to stay logged in?"
            st.checkbox(persist_txt, value=(True if saved else False), key=f"persist_{suffix}")
            
            submit = st.form_submit_button(t("login_btn", lang), use_container_width=True)
            lang_toggle = st.form_submit_button("En" if lang == "ar" else "عربي", use_container_width=True)

            if submit:
                if not u or not p:
                    st.error(t("invalid_creds", lang))
                else:
                    login_loader = show_loading_hourglass()
                    user = st.session_state.auth.authenticate(u, p.strip())
                    login_loader.empty()
                    if user:
                        # Handle Persistence Logic
                        should_persist = st.session_state.get(f"persist_{suffix}", False)
                        if should_persist:
                            save_credentials(u, p.strip())
                        else:
                            clear_credentials()
                            
                        user['username'] = u.lower().strip()
                        st.session_state.user = user
                        st.session_state.last_login_time = time.time()
                        st.session_state.show_welcome = True
                        
                        st.rerun()
                    else:
                        st.error(t("invalid_creds", lang))

            if lang_toggle:
                toggle_lang()
                st.rerun()

    # Layout with columns to center the single form
    col1, col2, col3 = st.columns([0.5, 2, 0.5]) 
    with col2:
        render_login_box("main")
        

@st.fragment(run_every="20s")
def silent_notification_monitor():
    """
    MODERN BACKGROUND MONITOR:
    Runs every 20 seconds in a fragment context.
    Immediately checks for notifications on Streamlit Cloud.
    """
    if st.session_state.get('user'):
        check_notifications()

def check_notifications():
    """Checks for new worker entries or customer requests directly from Google Sheets."""
    if 'db' not in st.session_state or not st.session_state.user:
        return

    # Initialize session state
    if 'notifications' not in st.session_state: st.session_state.notifications = []
    if 'notif_triggered' not in st.session_state: st.session_state.notif_triggered = False

    # Persistent storage file for counts
    NOTIF_STATE_FILE = os.path.join(BASE_DIR, "notification_state.json")

    # Load saved counts from file (for persistence across sessions)
    saved_worker_count = None
    saved_cust_count = None
    try:
        if os.path.exists(NOTIF_STATE_FILE):
            with open(NOTIF_STATE_FILE, 'r') as f:
                saved_state = json.load(f)
                saved_worker_count = saved_state.get('worker_count')
                saved_cust_count = saved_state.get('cust_count')
    except:
        pass

    def get_flag(nat_name):
        """Converts nationality name to emoji flag."""
        nat_name = str(nat_name).lower().strip()
        flags = {
            'مصر': '🇪🇬', 'مصري': '🇪🇬', 'egypt': '🇪🇬',
            'السودان': '🇸🇩', 'سوداني': '🇸🇩', 'sudan': '🇸🇩',
            'باكستان': '🇵🇰', 'باكستاني': '🇵🇰', 'pakistan': '🇵🇰',
            'الهند': '🇮🇳', 'هندي': '🇮🇳', 'india': '🇮🇳',
            'اليمن': '🇾🇪', 'يمني': '🇾🇪', 'yemen': '🇾🇪',
            'بنجلاديش': '🇧🇩', 'بنجالي': '🇧🇩', 'bangladesh': '🇧🇩',
            'الفلبين': '🇵🇭', 'فلبيني': '🇵🇭', 'philippines': '🇵🇭',
            'كينيا': '🇰🇪', 'كيني': '🇰🇪', 'kenya': '🇰🇪',
            'أوغندا': '🇺🇬', 'أوغندي': '🇺🇬', 'uganda': '🇺🇬',
            'إثيوبيا': '🇪🇹', 'إثيوبي': '🇪🇹', 'ethiopia': '🇪🇹',
        }
        for k, v in flags.items():
            if k in nat_name: return v
        return '🏁'

    try:
        # Get current data counts directly from Google Sheets
        df_workers = st.session_state.db.fetch_data()
        df_customers = st.session_state.db.fetch_customer_requests()

        current_worker_count = len(df_workers) if not df_workers.empty else 0
        current_cust_count = len(df_customers) if not df_customers.empty else 0

        # Use saved counts if available, otherwise use current (first run)
        last_worker = saved_worker_count if saved_worker_count is not None else current_worker_count
        last_cust = saved_cust_count if saved_cust_count is not None else current_cust_count

        # Check for new workers
        if current_worker_count > last_worker:
            new_count = current_worker_count - last_worker
            # Get the newest entries (last rows)
            new_rows = df_workers.tail(new_count)

            for _, row in new_rows.iterrows():
                # Helper to find value by partial header match
                def get_val(keywords, default="---"):
                    for k, v in row.items():
                        k_clean = str(k).lower().strip()
                        if any(kw.lower() in k_clean for kw in keywords):
                            return v
                    return default

                name = str(get_val(["الاسم", "Name", "Full Name", "الاسم الكامل"], '---'))
                nat = str(get_val(["الجنسية", "Nationality"], '---'))
                job = str(get_val(["نوع العمل", "الوظيفة", "Job", "Job Type"], '---'))
                loc = str(get_val(["المدينة", "Location", "City"], '---'))
                phone = str(get_val(["رقم الجوال", "Phone", "Mobile", "الهاتف"], '---'))
                age = str(get_val(["العمر", "Age"], '---'))
                religion = str(get_val(["الديانة", "Religion"], '---'))

                flag = get_flag(nat)
                
                # Build detailed notification message
                preview = "🆕 تسجيل عامل جديد\n"
                preview += f"الاسم : {name} 👤\n"
                preview += f"الجنسية : {nat} {flag}\n"
                preview += f"الوظيفة : {job} 💼\n"
                preview += f"المدينة : {loc} 📍\n"
                if age and age != '---':
                    preview += f"العمر : {age} 🎂\n"
                if religion and religion != '---':
                    preview += f"الديانة : {religion} 🕌\n"
                if phone and phone != '---':
                    preview += f"الجوال : {phone} 📱"

                notif_id = f"worker_{name}_{get_saudi_time().strftime('%H%M%S')}"
                # Avoid duplicate notifications
                existing_ids = [n.get('id', '') for n in st.session_state.notifications]
                if notif_id not in existing_ids:
                    st.session_state.notifications.append({
                        'id': notif_id,
                        'title': '🆕 تسجيل عامل جديد',
                        'msg': preview,
                        'time': get_saudi_time().strftime('%H:%M'),
                        'type': 'worker'
                    })
                    st.session_state.notif_triggered = True

        # Check for new customer requests
        if current_cust_count > last_cust:
            new_count = current_cust_count - last_cust
            new_rows = df_customers.tail(new_count)

            for _, row in new_rows.iterrows():
                # Helper to find value by partial header match
                def get_val(keywords, default="---"):
                    for k, v in row.items():
                        k_clean = str(k).lower().strip()
                        if any(kw.lower() in k_clean for kw in keywords):
                            return v
                    return default

                # Find company name
                company = str(get_val(["اسم الشركه", "المؤسسة", "Company", "الشركة", "شركه"], '---'))
                # Find contact person
                pic = str(get_val(["المسئول", "Contact Person", "Person in charge", "المسؤول"], ''))
                # Find phone
                phone = str(get_val(["رقم الجوال", "Phone", "Mobile", "الهاتف", "الجوال"], ''))
                # Find gender
                gender_val = str(get_val(["الفئة المطلوبة", "الجنس", "Gender", "الفئة"], '---'))
                # Find nationality
                nat = str(get_val(["الجنسية المطلوبة", "الجنسية", "Nationality"], '---'))
                # Find location
                loc = str(get_val(["موقع العمل", "الموقع", "Location", "المدينة"], '---'))
                # Find salary
                salary = str(get_val(["الراتب", "Salary", "Expected salary"], '---'))
                # Find experience
                exp = str(get_val(["الخبرة", "Experience"], '---'))
                # Find contract type
                contract = str(get_val(["نوع العقد", "Contract Type"], '---'))

                flag = get_flag(nat)
                
                # Gender Icons
                g_clean = str(gender_val).lower()
                g_icon = "🚻"
                if any(x in g_clean for x in ["رجال", "ذكر", "male"]): g_icon = "🚹"
                elif any(x in g_clean for x in ["نساء", "أنثى", "female", "بنت"]): g_icon = "🚺"
                
                # Build detailed notification message
                preview = "🔔 طلب عميل جديد\n"
                preview += f"الشركة : {company} 🏢\n"
                if pic and pic != '---':
                    preview += f"المسؤول : {pic} 👤\n"
                if phone and phone != '---' and phone != '':
                    preview += f"الجوال : {phone} 📱\n"
                preview += f"الفئة : {gender_val} {g_icon}\n"
                preview += f"الجنسية : {nat} {flag}\n"
                if loc and loc != '---':
                    preview += f"الموقع : {loc} 📍\n"
                if salary and salary != '---':
                    preview += f"الراتب المتوقع : {salary} 💰\n"
                if exp and exp != '---':
                    preview += f"الخبرة : {exp} 📊\n"
                if contract and contract != '---':
                    preview += f"نوع العقد : {contract} 📝"

                notif_id = f"cust_{company}_{get_saudi_time().strftime('%H%M%S')}"
                # Avoid duplicate notifications
                existing_ids = [n.get('id', '') for n in st.session_state.notifications]
                if notif_id not in existing_ids:
                    st.session_state.notifications.append({
                        'id': notif_id,
                        'title': '🔔 طلب عميل جديد',
                        'msg': preview,
                        'time': get_saudi_time().strftime('%H:%M'),
                        'type': 'customer'
                    })
                    st.session_state.notif_triggered = True

        # Save current counts to file for persistence
        try:
            with open(NOTIF_STATE_FILE, 'w') as f:
                json.dump({
                    'worker_count': current_worker_count,
                    'cust_count': current_cust_count,
                    'last_check': get_saudi_time().isoformat()
                }, f)
        except Exception as e:
            print(f"[DEBUG] Failed to save notification state: {e}")

        # Store counts in session for comparison on next check
        st.session_state.last_seen_worker_count = current_worker_count
        st.session_state.last_seen_cust_count = current_cust_count

    except Exception as e:
        print(f"[ERROR] Notification check failed: {e}")

def render_top_banner():
    """renders a persistent top banner with user image and welcome message."""
    user = st.session_state.user
    lang = st.session_state.lang
    notifs = st.session_state.get('notifications', [])
    notif_count = len(notifs)

    # 1. Global Audio Alert + Browser Push Notification
    if st.session_state.get('notif_triggered'):
        notif_count = len([n for n in st.session_state.get('notifications', [])])
        st.components.v1.html(f"""
<script>
(async function(){{
    // 1. Audio Alert
    try {{
        var AudioContext = window.AudioContext || window.webkitAudioContext;
        var ctx = new AudioContext();
        if (ctx.state === 'suspended') await ctx.resume();
        
        function playTone(freq, type, startTime, dur, vol) {{
            var osc = ctx.createOscillator(); var gain = ctx.createGain();
            osc.connect(gain); gain.connect(ctx.destination);
            osc.type = type; osc.frequency.setValueAtTime(freq, ctx.currentTime + startTime);
            gain.gain.setValueAtTime(vol, ctx.currentTime + startTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + startTime + dur);
            osc.start(ctx.currentTime + startTime); osc.stop(ctx.currentTime + startTime + dur);
        }}
        playTone(523.25, 'sine', 0.0, 0.8, 0.6); 
        playTone(1046.50, 'triangle', 0.1, 0.5, 0.4); 
        playTone(1318.51, 'sine', 0.4, 0.3, 0.3);
        playTone(1567.98, 'sine', 0.5, 0.3, 0.3);
        playTone(2093.00, 'sine', 0.6, 0.4, 0.2);
    }} catch(e) {{ console.error('Audio fail:', e); }}
    
    // 2. Browser Push Notification (works even when tab is in background)
    if ('Notification' in window && Notification.permission === 'granted') {{
        new Notification('نظام السعيد - إشعار جديد', {{
            body: 'لديك {notif_count} إشعارات جديدة',
            icon: '🔔',
            badge: '🔔',
            tag: 'alsaeed-notif',
            requireInteraction: true
        }});
    }}
}})();
</script>
""", height=0, width=0)
        st.session_state.notif_triggered = False

    # 1.4 Sound Test Diagnostic (Triggered from settings)
    if st.session_state.get('test_sound'):
        st.components.v1.html("""
<script>
(function(){
    try {
        var ctx = new (window.AudioContext || window.webkitAudioContext)();
        function playBell(f, s, d) {
            var o = ctx.createOscillator(); var g = ctx.createGain();
            o.connect(g); g.connect(ctx.destination);
            o.type = 'sine'; o.frequency.setValueAtTime(f, ctx.currentTime + s);
            g.gain.setValueAtTime(0.5, ctx.currentTime + s);
            g.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + s + d);
            o.start(ctx.currentTime + s); o.stop(ctx.currentTime + s + d);
        }
        playBell(880, 0, 0.5); playBell(1100, 0.2, 0.5);
    } catch(e) {}
})();
</script>
""", height=0, width=0)
        st.session_state.test_sound = False

    # 2. Styling and Content
    if lang == 'ar':
        f_name = user.get('first_name_ar', ''); fa_name = user.get('father_name_ar', '')
        welcome_prefix = "مرحباً بك،"; program_name = "نظام السعيد المتكامل 💎"
    else:
        f_name = user.get('first_name_en', ''); fa_name = user.get('father_name_en', '')
        welcome_prefix = "Welcome,"; program_name = "Alsaeed Integrated System 💎"

    full_name = f"{f_name} {fa_name}".strip() or user.get('username', 'User')
    avatar_val = st.session_state.auth.get_avatar(user.get('username', ''))
    avatar_src = avatar_val if str(avatar_val).startswith('data:') else f'data:image/png;base64,{avatar_val}' if avatar_val else None
    
    avatar_html = f'<img src="{avatar_src}" class="banner-avatar" />' if avatar_src else '<div class="banner-avatar" style="background:linear-gradient(135deg,#D4AF37,#8B7520);display:flex;align-items:center;justify-content:center;font-size:24px;">👤</div>'

    # 3. Main Container
    with st.container():
        # Language-aware column ordering to keep Bell on the Far Left
        if lang == 'ar':
            # In RTL: Index 0 is Right, Index 3 is Left. 
            # We assign c4(Date) to 0, c3(Spacer) to 1, c2(Profile) to 2, c1(Bell) to 3.
            cols = st.columns([2, 4.7, 2.5, 0.8])
            c4, c3, c2, c1 = cols[0], cols[1], cols[2], cols[3]
        else:
            # In LTR: Index 0 is Left, Index 3 is Right.
            # We assign c1(Bell) to 0, c2(Profile) to 1, c3(Spacer) to 2, c4(Date) to 3.
            cols = st.columns([0.8, 2.5, 4.7, 2])
            c1, c2, c3, c4 = cols[0], cols[1], cols[2], cols[3]
        
        with c1: # Bell & Badge at absolute left
            badge_html = f'<span class="notif-badge">{notif_count}</span>' if notif_count > 0 else ''
            st.markdown(f'<div class="notif-bell-container" style="margin-top:5px; position:relative;">{badge_html}', unsafe_allow_html=True)
            if st.button("🔔", key="bell_trig_v2", help="View Notifications"):
                st.session_state.notif_panel_open = not st.session_state.get('notif_panel_open', False)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with c2: # Profile
            st.markdown(f'<div style="display:flex; align-items:center; gap:15px; margin-top:5px;">{avatar_html}<div><p style="margin:0; font-weight:700; color:white;">{welcome_prefix} {full_name}</p><p style="margin:0; font-size:0.75rem; color:#D4AF37;">{program_name}</p></div></div>', unsafe_allow_html=True)
        
        with c3: st.write("") # Spacer
            
        with c4: # Date/Log at absolute right
            now = get_saudi_time()
            date_str = now.strftime("%Y-%m-%d")
            day_name = now.strftime("%A") if lang == 'en' else {
                'Saturday': 'السبت', 'Sunday': 'الأحد', 'Monday': 'الاثنين',
                'Tuesday': 'الثلاثاء', 'Wednesday': 'الأربعاء', 'Thursday': 'الخميس', 'Friday': 'الجمعة'
            }.get(now.strftime("%A"), now.strftime("%A"))
            time_str = now.strftime("%I:%M %p") if lang == 'en' else now.strftime("%I:%M %p").replace('AM', 'ص').replace('PM', 'م')
            st.markdown(f'<div style="text-align:right; margin-top:5px;"><p style="color:#D4AF37; font-size:0.85rem; font-weight:bold; margin:0;">{t("contract_dashboard", lang)}</p><p style="color:rgba(255,255,255,0.6); font-size:0.75rem; margin:0;">{day_name} | {date_str} | {time_str}</p></div>', unsafe_allow_html=True)

    # 4. Floating List Overlay
    if st.session_state.get('notif_panel_open') and notifs:
        dir_style = "rtl" if lang == 'ar' else "ltr"
        align_style = "right" if lang == 'ar' else "left"
        border_side = "right" if lang == 'ar' else "left"
        notif_title = f"🔔 الإشعارات الواردة ({notif_count})" if lang == 'ar' else f"🔔 Incoming Notifications ({notif_count})"
        with st.expander(notif_title, expanded=True):
            for n in reversed(notifs[-20:]):
                msg_html = n['msg'].replace('\n', '<br>')
                st.markdown(f"""
<div style="background:rgba(255,255,255,0.04); padding:12px 15px; border-radius:12px; margin-bottom:10px; border-{border_side}:3px solid #D4AF37; direction:{dir_style};">
    <div style="display:flex; justify-content:space-between; align-items:start;">
        <p style="margin:0; font-weight:700; color:#D4AF37; font-size:0.95rem;">{n['title']}</p>
        <p style="margin:0; font-size:0.7rem; color:rgba(255,255,255,0.3);">⏰ {n['time']}</p>
    </div>
    <p style="margin:8px 0 0 0; color:#EEE; font-size:0.85rem; line-height:1.8;">{msg_html}</p>
</div>
""", unsafe_allow_html=True)
            
            btn_clear = "🗑️ مسح الكل" if lang == 'ar' else "🗑️ Clear All"
            if st.button(btn_clear, use_container_width=True, key="clear_all_notifs"):
                # Mark all current notifications as seen for THIS user
                user_id = st.session_state.user.get('username', 'guest')
                USER_SEEN_FILE = os.path.join(BASE_DIR, f"notif_seen_{user_id}.json")
                
                seen_ids = []
                if os.path.exists(USER_SEEN_FILE):
                    try:
                        with open(USER_SEEN_FILE, "r") as f:
                            seen_ids = json.load(f)
                    except: pass
                
                # Add current notification IDs to seen list
                for n in st.session_state.notifications:
                    n_id = n.get('id')
                    if n_id and n_id not in seen_ids:
                        seen_ids.append(n_id)
                
                # Save back to user-specific file
                with open(USER_SEEN_FILE, "w") as f:
                    json.dump(seen_ids, f)

                st.session_state.notifications = []
                st.session_state.notif_panel_open = False
                st.rerun()
            
            # Audio Diagnostic Button
            btn_test = "⚙️ تجربة صوت التنبيه" if lang == 'ar' else "⚙️ Test Notification Sound"
            if st.checkbox(btn_test, key="cb_test_sound"):
                st.session_state.test_sound = True
                st.rerun()

        st.markdown(f"""
    <div class="persistent-top-banner">
        <div style="display: flex; align-items: center; gap: 20px;">
             <div class="banner-user-info">
                {avatar_html}
            </div>
            <div>
                <p class="banner-welcome-msg">{welcome_prefix} {full_name}</p>
                <p class="banner-subtext">{program_name}</p>
            </div>
        </div>
        <div style="display: flex; align-items: center; gap: 15px;">
            <div style="text-align: right;">
                <p style="color: rgba(255,255,255,0.6); font-size: 0.75rem; margin: 0;">{datetime.now().strftime('%Y-%m-%d')}</p>
                <p style="color: #D4AF37; font-size: 0.85rem; font-weight: bold; margin: 0;">{t('contract_dashboard', lang)}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def dashboard():
    user = st.session_state.user
    lang = st.session_state.lang

    # --- 1. Silent Notification Check (First thing in Dashboard) ---
    check_notifications()
    
    # --- 2. Welcome Message ---
    if st.session_state.get('show_welcome'):
        if lang == 'ar':
            f_name = user.get('first_name_ar', '')
            fa_name = user.get('father_name_ar', '')
            sub_text = "مرحباً بك في برنامج توريد العمالة الفلبينية"
        else:
            f_name = user.get('first_name_en', '')
            fa_name = user.get('father_name_en', '')
            sub_text = "Welcome to the Contract Management System"

        full_name = f"{f_name} {fa_name}".strip()
        if not full_name: full_name = user.get('username', 'User')
        greeting = "أهلاً،" if lang == 'ar' else "Hello,"

        # Get user avatar if exists - Universal Format Detection
        username_key = user.get('username', '')
        avatar_val = st.session_state.auth.get_avatar(username_key)
        if avatar_val:
            if str(avatar_val).startswith('data:'):
                avatar_html = f'<img src="{avatar_val}" style="width:80px;height:80px;border-radius:50%;object-fit:cover;border:2px solid #D4AF37;" />'
            else:
                # Legacy fallback
                avatar_html = f'<img src="data:image/png;base64,{avatar_val}" style="width:80px;height:80px;border-radius:50%;object-fit:cover;border:2px solid #D4AF37;" />'
        else:
            avatar_html = '<div style="width:80px;height:80px;border-radius:50%;background:linear-gradient(135deg,#D4AF37,#8B7520);display:flex;align-items:center;justify-content:center;font-size:36px;">👤</div>'

        st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;700&family=Inter:wght@300;400;700&display=swap');

        @keyframes wFadeIn {{
            0%   {{ opacity:0; }}
            20%  {{ opacity:1; }}
            80%  {{ opacity:1; }}
            100% {{ opacity:0; pointer-events:none; }}
        }}
        @keyframes wSlideUp {{
            0%   {{ transform:translateY(40px) scale(0.95); opacity:0; }}
            20%  {{ transform:translateY(0)    scale(1);    opacity:1; }}
            80%  {{ transform:translateY(0)    scale(1);    opacity:1; }}
            100% {{ transform:translateY(-16px) scale(0.97); opacity:0; }}
        }}
        @keyframes wShimmer {{
            0%   {{ background-position:-400% center; }}
            100% {{ background-position: 400% center; }}
        }}
        @keyframes wRing {{
            0%   {{ box-shadow:0 0 0 0 rgba(212,175,55,0.55); }}
            70%  {{ box-shadow:0 0 0 22px rgba(212,175,55,0); }}
            100% {{ box-shadow:0 0 0 0 rgba(212,175,55,0); }}
        }}
        @keyframes wStar {{
            0%,100% {{ opacity:.3; transform:scale(.8); }}
            50%     {{ opacity:1;  transform:scale(1.2); }}
        }}
        @keyframes wLineScan {{
            0%   {{ left:-100%; }}
            100% {{ left: 100%; }}
        }}

        #lux-welcome {{
            position: fixed; inset:0;
            z-index:2147483647;
            background:rgba(4,7,16,0.8);
            backdrop-filter:blur(10px);
            -webkit-backdrop-filter:blur(10px);
            display:flex; align-items:center; justify-content:center;
            animation: wFadeIn 1.2s cubic-bezier(.4,0,.2,1) forwards;
            pointer-events:none;
        }}
        #lux-welcome-card {{
            background:linear-gradient(160deg,#0d1220,#090e1d,#0e1428);
            border:1px solid rgba(212,175,55,0.22);
            border-radius:28px;
            padding:52px 68px;
            max-width:520px; width:90%; min-width: 290px;
            text-align:center;
            position:relative; overflow:hidden;
            animation:wSlideUp 1.2s cubic-bezier(.4,0,.2,1) forwards;
            box-shadow:0 40px 120px rgba(0,0,0,0.75), 0 0 60px rgba(212,175,55,0.06);
        }}
        #lux-welcome-card::before {{
            content:'';
            position:absolute; top:0; left:-100%; height:1px; width:60%;
            background:linear-gradient(90deg,transparent,rgba(212,175,55,.7),transparent);
            animation:wLineScan 2.4s linear infinite;
        }}
        .wc-avatar {{ margin:0 auto 22px; animation:wRing 2s ease-in-out infinite; width:fit-content; }}
        .wc-greet {{
            font-family:'Cairo','Inter',sans-serif;
            font-size:13px; letter-spacing:4px; text-transform:uppercase;
            color:rgba(212,175,55,.65); margin-bottom:6px;
        }}
        .wc-name {{
            font-family:'Cairo','Inter',sans-serif;
            font-size:36px; font-weight:700;
            background:linear-gradient(135deg,#fff 0%,#D4AF37 50%,#fff 100%);
            background-size:200% auto;
            -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
            animation:wShimmer 3s linear infinite;
            line-height:1.25; margin-bottom:12px;
        }}
        .wc-div {{
            width:50px; height:2px; margin:18px auto;
            background:linear-gradient(90deg,transparent,#D4AF37,transparent); border-radius:2px;
        }}
        .wc-sub {{
            font-family:'Cairo','Inter',sans-serif;
            font-size:14px; color:rgba(255,255,255,.45);
            line-height:1.75; margin-bottom:24px;
            word-wrap: break-word; overflow-wrap: break-word;
        }}
        .wc-stars {{ display:flex; justify-content:center; gap:7px; }}
        .wc-star {{ color:#D4AF37; font-size:13px; }}
        .wc-star:nth-child(1){{animation:wStar 1.6s ease infinite .0s;}}
        .wc-star:nth-child(2){{animation:wStar 1.6s ease infinite .3s;}}
        .wc-star:nth-child(3){{animation:wStar 1.6s ease infinite .6s;}}
        .wc-star:nth-child(4){{animation:wStar 1.6s ease infinite .9s;}}
        .wc-star:nth-child(5){{animation:wStar 1.6s ease infinite 1.2s;}}
        </style>

        <div id="lux-welcome">
          <div id="lux-welcome-card">
            <div class="wc-avatar">{avatar_html}</div>
            <div class="wc-greet">{greeting}</div>
            <div class="wc-name">{full_name}</div>
            <div class="wc-div"></div>
            <div class="wc-sub">{sub_text}</div>
            <div class="wc-stars">
              <span class="wc-star">★</span><span class="wc-star">★</span>
              <span class="wc-star">★</span><span class="wc-star">★</span>
              <span class="wc-star">★</span>
            </div>
          </div>
        </div>

        <script>
        setTimeout(function() {{
            var el = document.getElementById('lux-welcome');
            if (el) {{
                el.style.opacity = '0';
                el.style.transition = 'opacity 0.4s ease';
                setTimeout(function() {{ if (el.parentNode) el.parentNode.removeChild(el); }}, 400);
            }}
        }}, 1000);
        </script>
        """, unsafe_allow_html=True)

        del st.session_state.show_welcome


    with st.sidebar:
        # Use columns to force horizontal centering for the image block
        sc1, sc2, sc3 = st.columns([1, 2, 1])
        with sc2:
            if os.path.exists(IMG_PATH):
                st.image(IMG_PATH, use_container_width=True)
        
        # Credit text - Split into two lines for clarity (with language-specific font class)
        credit_class = "programmer-credit en" if lang == "en" else "programmer-credit"
        line1 = "برمجة" if lang == "ar" else "By:"
        line2 = "السعيد الوزان" if lang == "ar" else "Alsaeed Alwazzan"
        st.markdown(f'<div class="{credit_class}">{line1}<br>{line2}</div>', unsafe_allow_html=True)
        
        # Spacing
        st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
        
        # Language Toggle (Using Wrapper for CSS targeting)
        st.markdown('<div class="lang-toggle-wrapper">', unsafe_allow_html=True)
        btn_label = "En" if lang == "ar" else "عربي"
        if st.button(btn_label, key="lang_btn_dashboard", use_container_width=True):
            toggle_lang()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)

        if st.button(t("dashboard", lang), use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()
        if st.button(t("smart_search", lang), use_container_width=True):
            # Reset the filter expander state to force open on entry
            for key in list(st.session_state.keys()):
                if key.startswith("filter_expander_"):
                    del st.session_state[key]
            st.session_state.page = "search"
            st.rerun()
        if st.button(t("cv_translator", lang), use_container_width=True):
            st.session_state.page = "translator"
            st.rerun()
        if user.get("role") != "viewer":
            if st.button(t("customer_requests", lang), use_container_width=True):
                st.session_state.page = "customer_requests"
                st.rerun()
        if st.button(t("order_processing", lang), use_container_width=True):
            st.session_state.page = "order_processing"
            st.rerun()
        
        # WhatsApp Marketing 2026 Button
        if st.button("📱 " + t("whatsapp_marketing", lang), use_container_width=True):
            st.session_state.page = "whatsapp_marketing"
            st.rerun()
        
        # Duplicate Remover Button
        if st.button("🗑️ " + t("duplicate_remover", lang), use_container_width=True):
            st.session_state.page = "duplicate_remover"
            st.rerun()
        
        # Determine Bengali Supply Visibility
        user_perms = user.get("permissions", [])
        if "all" in user_perms or "bengali_supply" in user_perms:
            # PURE CSS BANGLADESH FLAG (Zero Dependency/100% Reliable)
            st.sidebar.markdown("""
                <style>
                #bengali-btn-wrapper button p {
                    display: flex !important;
                    flex-direction: row-reverse !important;
                    align-items: center !important;
                    justify-content: center !important;
                    gap: 12px !important;
                }
                /* Pure CSS Bangladesh Flag */
                #bengali-btn-wrapper button p::before {
                    content: "" !important;
                    display: block !important;
                    width: 24px !important;
                    height: 16px !important;
                    background-color: #006a4e !important;
                    border-radius: 2px !important;
                    position: relative !important;
                    order: -1 !important;
                }
                #bengali-btn-wrapper button p::after {
                    content: "" !important;
                    position: absolute !important;
                    width: 9px !important;
                    height: 9px !important;
                    background-color: #f42a41 !important;
                    border-radius: 50% !important;
                    /* Move to the right side of the button text space where ::before is */
                    right: 21px; /* Precision position over the green box */
                    top: 50%;
                    transform: translateY(-50%);
                    z-index: 101 !important;
                }
                </style>
                <div id="bengali-btn-wrapper">
            """, unsafe_allow_html=True)
            
            if st.button(t("bengali_supply_title", lang), key="btn_bengali_supply_main", use_container_width=True):
                st.session_state.page = "bengali_supply"
                st.rerun()
            
            st.sidebar.markdown("</div>", unsafe_allow_html=True)

        if user.get("role") == "admin":
            if st.button(t("permissions", lang), use_container_width=True):
                st.session_state.page = "permissions"
                st.rerun()
            
            # Refresh Data button below Permissions for Admins
            refresh_notif = st.empty()
            if st.button(t("refresh_data_btn", lang), key="force_refresh_db", use_container_width=True):
                refresh_loader = show_loading_hourglass()
                st.session_state.db.fetch_data(force=True)
                st.session_state.db.fetch_customer_requests(force=True)
                refresh_loader.empty()
                st.session_state['_notif_refresh'] = ("success", "تم تحديث البيانات من Google Sheets بنجاح! ✅" if lang == 'ar' else "Data refreshed successfully! ✅")
                st.rerun()
            
            # Show refresh notification Contextually below the button
            if st.session_state.get('_notif_refresh'):
                typ, msg = st.session_state.pop('_notif_refresh')
                show_toast(msg, typ, container=refresh_notif)
        
        st.markdown("<div style='margin: 15px 0;'></div>", unsafe_allow_html=True)
        
        if st.button(t("logout", lang), type="primary", use_container_width=True):
            st.session_state.user = None
            st.rerun()
        
        # Global Deep Reset Opportunity
        st.sidebar.divider()
        with st.sidebar.expander(t("deep_reset", lang)):
            st.caption(t("deep_reset_desc", lang))
            if st.button(t("deep_reset", lang), key="sidebar_deep_reset", use_container_width=True):
                # Clear all navigation and table caches
                for k in list(st.session_state.keys()):
                    if any(k.startswith(prefix) for prefix in ["dash_table_", "last_scroll_", "trans_", "search_results"]):
                        del st.session_state[k]
                st.session_state.db.fetch_data(force=True)
                st.success("تم تنظيف الذاكرة وتحديث البيانات!")
                time.sleep(1)
                st.rerun()

    # --- Background Notifications (Handled by Fragment) ---
    silent_notification_monitor()

    # --- Render Global Top Banner (Persistent) ---
    render_top_banner()

    # Admin Tools
    # if user.get("role") == "admin":
    #     with st.sidebar.expander(t("permissions", lang)):
    #         if st.button(t("test_db", lang)):
    #             try:
    #                 st.session_state.db.connect()
    #                 d = st.session_state.db.fetch_data(force=True)
    #                 st.write(f"Rows: {len(d)}")
    #                 if not d.empty: st.write(d.columns.tolist())
    #             except Exception as e:
    #                 st.error(f"Err: {e}")

    page = st.session_state.get('page', 'dashboard')
    
    if page == "dashboard": render_dashboard_content()
    elif page == "search": render_search_content()
    elif page == "translator": render_translator_content()
    elif page == "customer_requests":
        if user.get("role") == "viewer":
            st.error("🔒 لا تملك صلاحية الوصول لهذه الصفحة" if lang == 'ar' else "🔒 Access Denied")
            st.session_state.page = "dashboard"
            st.rerun()
        render_order_processing_content()
    elif page == "order_processing": render_order_processing_content()
    elif page == "permissions": render_permissions_content()
    elif page == "bengali_supply": render_bengali_supply_content()
    elif page == "whatsapp_marketing": render_whatsapp_page()
    elif page == "duplicate_remover": render_duplicate_remover_content()



def __apply_pinned_columns(df_or_style, cfg=None):
    if cfg is None: cfg = {}
    import streamlit as st
    # Priority Keywords for Pinning
    pin_keywords = [
        "حالة العقد", "contract status", "status",
        "وقت", "طابع", "timestamp", "registration",
        "الاسم", "name", 
        "جنسية", "nationality", "🚩", "دولة", "country",
        "جنس", "gender"
    ]

    # Keywords for Width Control
    wide_keywords = ["job", "وظيفة", "skill", "مهارة", "note", "ملاحظات", "nature", "طبيعة", "details", "تفاصيل", "name", "الاسم"]
    small_keywords = ["nationality", "جنسية", "جنس", "gender", "status", "حالة", "🚩", "age", "عمر"]
    
    # Handle both DataFrame and Styler
    if hasattr(df_or_style, 'data'):
        cols = df_or_style.data.columns
    elif hasattr(df_or_style, 'columns'):
        cols = df_or_style.columns
    else:
        return cfg
        
    for col in cols:
        col_str = str(col).lower()
        
        # Determine Width
        is_wide = any(kw.lower() in col_str for kw in wide_keywords)
        is_small = any(kw.lower() in col_str for kw in small_keywords)
        target_width = "large" if is_wide else ("small" if is_small else "medium")
        
        # Determine Pinning
        should_pin = any(kw.lower() in col_str for kw in pin_keywords)
        
        if col not in cfg:
            # Create new column config with natural width fit
            cfg[col] = st.column_config.Column(pinned=should_pin, width=target_width)
        else:
            # For existing config, only try to pin if needed
            if isinstance(cfg[col], dict):
                cfg[col]["pinned"] = should_pin
                if "width" not in cfg[col]:
                    cfg[col]["width"] = target_width
    
    return cfg

def render_dashboard_content():
    lang = st.session_state.lang
    st.markdown('<div class="programmer-signature-neon">By: Alsaeed Alwazzan (v2.1)</div>', unsafe_allow_html=True)
    st.title(f" {t('contract_dashboard', lang)}")
    
    # Show loader while fetching data - Moved after title for immediate UI recognition
    loading_placeholder = st.empty()
    with loading_placeholder:
        show_loading_hourglass(container=loading_placeholder)
    
    start_time = time.time()
    
    try:
        df = st.session_state.db.fetch_data()
    except Exception as e:
        loading_placeholder.empty()
        st.error(f"{t('error', lang)}: {e}")
        return

    if df.empty:
        loading_placeholder.empty()
        st.warning(t("no_data", lang))
        return

    # Don't rename yet, logic needs English/Original headers
    cols = df.columns.tolist()
    
    # Robust column detection with space normalization
    def clean_col(c): return " ".join(str(c).lower().split())
    
    date_col = next((c for c in cols if any(kw in clean_col(c) for kw in ["contract end", "انتهاء العقد", "contract expiry"])), None)
    if not date_col:
        loading_placeholder.empty() # CLEAR LOADER BEFORE RETURN!
        visible_cols = [c for c in cols if not str(c).startswith('__')]
        st.error(f"⚠️ Error: Could not find the 'Contract End' column. Please check your spreadsheet headers. Available columns: {visible_cols}")
        return

    stats = {'urgent': [], 'expired': [], 'active': []}
    for _, row in df.iterrows():
        try:
            status = ContractManager.calculate_status(row[date_col])
            r = row.to_dict()
            global_status = status['status']
            days = status.get('days', 0)
            if days is None: days = 9999
            
            # Numeric Days for sorting
            r['__days_sort'] = days
            
            if lang == 'ar':
                if global_status == 'expired':
                    r['حالة العقد'] = f"❌ منتهي (منذ {abs(days)} يوم)"
                elif global_status in ['urgent', 'warning']:
                    r['حالة العقد'] = f"⚠️ عاجل (متبقى {days} يوم)"
                else: # active
                    r['حالة العقد'] = f"✅ ساري (متبقى {days} يوم)"
            else:
                r['Contract Status'] = f"{status['label_en']} ({abs(days)} Days)"

            if global_status == 'urgent' or global_status == 'warning': stats['urgent'].append(r)
            elif global_status == 'expired': stats['expired'].append(r)
            elif global_status == 'active': stats['active'].append(r)
        except Exception:
            continue

    # Clear loader once stats are ready
    # Ensure at least 0.5s of visibility for the premium feel
    elapsed = time.time() - start_time
    if elapsed < 0.5:
        time.sleep(0.5 - elapsed)
    loading_placeholder.empty()

    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown(f"""
            <div class="metric-container glow-orange">
                <div class="metric-label">{t("urgent_7_days", lang)}</div>
                <div class="metric-value">{len(stats['urgent'])}</div>
            </div>
            """, unsafe_allow_html=True)
            
    with c2:
        st.markdown(f"""
            <div class="metric-container glow-red">
                <div class="metric-label">{t("expired", lang)}</div>
                <div class="metric-value">{len(stats['expired'])}</div>
            </div>
            """, unsafe_allow_html=True)
            
    with c3:
        st.markdown(f"""
            <div class="metric-container glow-green">
                <div class="metric-label">{t("active", lang)}</div>
                <div class="metric-value">{len(stats['active'])}</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("---")
    
    # --- ADD SMART SEARCH UI TO DASHBOARD ---
    lbl_age = t("age", lang)
    lbl_contract = t("contract_end", lang)
    lbl_reg = t("registration_date", lang)
    lbl_enable = "تفعيل" if lang == "ar" else "Activate"

    with st.expander(t("advanced_filters", lang) if t("advanced_filters", lang) != "advanced_filters" else "تصفية متقدمة", expanded=False):
        st.markdown(f'<div class="premium-filter-label">📅 {t("filter_dates_group", lang)}</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            use_age = st.checkbox(f" {lbl_enable} {lbl_age}", key="dash_use_age_filter")
            if use_age:
                ac1, ac2 = st.columns(2)
                with ac1: a_min = st.number_input("من سن" if lang == 'ar' else "From", 1, 100, 16, key="dash_age_min")
                with ac2: a_max = st.number_input("إلى سن" if lang == 'ar' else "To", 1, 100, 35, key="dash_age_max")
                age_range = (a_min, a_max)
            else: age_range = (16, 35)
        with c2:
            use_contract = st.checkbox(f" {lbl_enable} {lbl_contract}", key="dash_use_contract_filter")
            if use_contract:
                contract_range = st.date_input("Contract Range", (datetime.now().date(), datetime.now().date() + timedelta(days=30)), label_visibility="collapsed", key="dash_contract_range")
            else: contract_range = []
        with c3:
            use_reg = st.checkbox(f" {lbl_enable} {lbl_reg}", key="dash_use_reg_filter")
            if use_reg:
                reg_range = st.date_input("Registration Range", (datetime.now().date().replace(day=1), datetime.now().date()), label_visibility="collapsed", key="dash_reg_range")
            else: reg_range = []

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f'<div class="premium-filter-label">⚙️ {t("filter_advanced_group", lang)}</div>', unsafe_allow_html=True)
        c2_1, c2_2, c2_3 = st.columns(3)
        with c2_1:
            use_not_working = st.checkbox("No (هل يعمل حالياً؟)" if lang == "ar" else "Not Working (No)", key="dash_use_not_working")
        with c2_2:
            transfer_options = {"": f"— {t('transfer_all', lang)} —", "First time": t("transfer_1", lang), "Second time": t("transfer_2", lang), "The third time": t("transfer_3", lang), "More than three": t("transfer_more", lang)}
            selected_transfer_label = st.selectbox(t("transfer_count_label", lang), options=list(transfer_options.values()), key="dash_transfer_dropdown")
            selected_transfer_key = [k for k, v in transfer_options.items() if v == selected_transfer_label][0]
        with c2_3:
            use_no_huroob = st.checkbox(t("no_huroob", lang), key="dash_use_no_huroob")
        
        st.markdown("<br>", unsafe_allow_html=True)
        c3_1, c3_2 = st.columns(2)
        with c3_1:
            use_work_outside = st.checkbox(t("work_outside_city", lang), key="dash_use_work_outside")

    dash_query = st.text_input(t("smart_search", lang), placeholder=t("search_placeholder", lang), key="dash_search_query")
    dash_search_clicked = st.button(t("search_btn", lang), key="dash_search_btn", use_container_width=True, type="primary")

    dash_filters = {}
    if use_age: dash_filters['age_enabled'] = True; dash_filters['age_min'] = age_range[0]; dash_filters['age_max'] = age_range[1]
    if use_contract and len(contract_range) == 2: dash_filters['contract_enabled'] = True; dash_filters['contract_end_start'] = contract_range[0]; dash_filters['contract_end_end'] = contract_range[1]
    if use_reg and len(reg_range) == 2: dash_filters['date_enabled'] = True; dash_filters['date_start'] = reg_range[0]; dash_filters['date_end'] = reg_range[1]
    if use_not_working: dash_filters['not_working_only'] = True
    if use_no_huroob: dash_filters['no_huroob'] = True
    if use_work_outside: dash_filters['work_outside_city'] = True
    if selected_transfer_key: dash_filters['transfer_count'] = selected_transfer_key

    st.markdown("---")
    # --- END SMART SEARCH UI ---

    cv_col = next((c for c in cols if any(kw in clean_col(c) for kw in ["cv", "سيرة", "download"])), None)
    
    # Configuration for LinkColumn needs the TRANSLATED column name if we rename it!
    # But Streamlit LinkColumn config keys must match the dataframe columns.
    
    t1, t2, t3 = st.tabs([t("tabs_urgent", lang), t("tabs_expired", lang), t("tabs_active", lang)])
    
    def show(data, tab_id):
        if not data: st.info(t("no_data", lang)); return
        d = pd.DataFrame(data)

        # Apply Smart Search if active
        if dash_query or dash_filters:
            eng = SmartSearchEngine(d)
            d = eng.search(dash_query, filters=dash_filters)
            if d.empty:
                st.info(t("no_results", lang) if t("no_results", lang) != "no_results" else "لا توجد نتائج تطابق بحثك في هذا التبويب")
                return

        # Sort Logic:
        # For Expired: sort by absolute days (smallest number of days ago first)
        # For others: sort by raw days (soonest to expire first)
        if tab_id == 'expired':
            d['__abs_days'] = d['__days_sort'].abs()
            d = d.sort_values(by='__abs_days', ascending=True)
            d = d.drop(columns=['__abs_days'])
        else:
            d = d.sort_values(by='__days_sort', ascending=True)
        
        # Select columns: 'حالة العقد' then the rest (EXCLUDING ANY __ COLS)
        status_key = 'حالة العقد' if lang == 'ar' else 'Contract Status'
        show_cols = [status_key] + [c for c in cols if c in d.columns and not str(c).startswith('__')]
        d_final = d[show_cols].copy()
        
        # Rename Columns Mechanism (Safe to prevent duplicates)
        new_names = {}
        used_names = set()
        for c in d_final.columns:
            new_name = t_col(c, lang)
            original_new_name = new_name
            counter = 1
            while new_name in used_names:
                counter += 1
                new_name = f"{original_new_name} ({counter})"
            used_names.add(new_name)
            new_names[c] = new_name
            
        d_final.rename(columns=new_names, inplace=True)
        
        # FINAL POLISH: Format all visible dates to be clean (No Time)
        d_final = clean_date_display(d_final)
        
        # Recalculate Column Config Key
        final_cfg = {}
        if cv_col and cv_col in new_names:
            trans_cv_col = new_names[cv_col]
            final_cfg[trans_cv_col] = st.column_config.LinkColumn(
                t("cv_download", lang), 
                display_text=t("download_pdf", lang)
            )
        
        # Suffix Configuration for Numeric Remaining Column
        rem_key_display = new_names.get('المتبقى', 'المتبقى') if lang == 'ar' else new_names.get('Remaining', 'Remaining')
        final_cfg[rem_key_display] = st.column_config.NumberColumn(
            rem_key_display,
            format="%d يوم" if lang == 'ar' else "%d Days"
        )
        
        # Flag Image Configuration
        for col in d_final.columns:
            if any(kw in str(col).lower() for kw in ["nationality", "الجنسية"]):
                final_cfg[f"🚩_{col}"] = st.column_config.ImageColumn(t("country_label", lang), width="small", pinned=True)
        
        
        # Smart Translator Button
        d_final = render_table_translator(d_final, key_prefix=f"dash_{tab_id}")

        # Apply Green Text Styling
        styled_final = style_df(d_final)
        
        event = st.dataframe(
            styled_final, 
            use_container_width=False, 
            column_config=__apply_pinned_columns(styled_final, final_cfg),
            on_select="rerun",
            selection_mode="single-row",
            hide_index=True,
            key=f"dash_table_{lang}_{tab_id}"
        )
        
        if event.selection and event.selection.get("rows"):
            sel_idx = event.selection["rows"][0]
            worker_row = d.iloc[sel_idx]
            render_cv_detail_panel(worker_row, sel_idx, lang, key_prefix=f"dash_{tab_id}")

    with t1: 
        c_exp_1, c_exp_2 = st.columns([4, 1])
        with c_exp_2:
            xl_data = create_pasha_whatsapp_excel(pd.DataFrame(stats['urgent']), lang=lang)
            if xl_data:
                xl_buf, xl_df = xl_data
                btn_text = "📤 " + ("تصدير للواتساب" if lang == 'ar' else "Export to WhatsApp")
                render_pasha_export_button(xl_df, btn_text, "Urgent_WhatsApp.xlsx", "المرشحين_العاجل", key="btn_exp_urgent")
        show(stats['urgent'], "urgent")
        
    with t2: 
        c_exp_1, c_exp_2 = st.columns([4, 1])
        with c_exp_2:
            xl_data = create_pasha_whatsapp_excel(pd.DataFrame(stats['expired']), lang=lang)
            if xl_data:
                xl_buf, xl_df = xl_data
                btn_text = "📤 " + ("تصدير للواتساب" if lang == 'ar' else "Export to WhatsApp")
                render_pasha_export_button(xl_df, btn_text, "Expired_WhatsApp.xlsx", "المرشحين_المنتهية", key="btn_exp_expired")
        show(stats['expired'], "expired")
        
    with t3: 
        c_exp_1, c_exp_2 = st.columns([4, 1])
        with c_exp_2:
            xl_data = create_pasha_whatsapp_excel(pd.DataFrame(stats['active']), lang=lang)
            if xl_data:
                xl_buf, xl_df = xl_data
                render_pasha_export_button(xl_df, "📤 تصدير للواتساب", "Active_WhatsApp.xlsx", "المرشحين_الفواعل", key="btn_exp_active")
        show(stats['active'], "active")

def render_search_content():
    lang = st.session_state.lang
    
    # Absolute Top Signature
    st.markdown('<div class="programmer-signature-neon">By: Alsaeed Alwazzan</div>', unsafe_allow_html=True)
    
    # 1. Glowing Title at the Absolute Top
    title_text = "Smart Search" if lang != 'ar' else "(AI) البحث الذكي"
    st.markdown(f'<div class="glowing-title">{title_text}</div>', unsafe_allow_html=True)
    
    # Rest of the content
    lbl_age = t("age", lang)
    lbl_contract = t("contract_end", lang)
    lbl_reg = t("registration_date", lang)
    lbl_enable = "تفعيل" if lang == "ar" else "Activate"
    
    # Advanced Filters UI
    # Advanced Filters UI
    filter_expander_key = f"filter_expander_{st.session_state.get('search_entry_count', 0)}"
    with st.expander(t("advanced_filters", lang) if t("advanced_filters", lang) != "advanced_filters" else "تصفية متقدمة", expanded=False):
        
        # Row 1: Date & Range Filters
        st.markdown(f'<div class="premium-filter-label">📅 {t("filter_dates_group", lang)}</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        
        with c1:
            use_age = st.checkbox(f" {lbl_enable} {lbl_age}", key="use_age_filter")
            if use_age:
                ac1, ac2 = st.columns(2)
                with ac1:
                    a_min = st.number_input("من سن" if lang == 'ar' else "From", 1, 100, 16, key="age_min_search")
                with ac2:
                    a_max = st.number_input("إلى سن" if lang == 'ar' else "To", 1, 100, 35, key="age_max_search")
                age_range = (a_min, a_max)
            else: 
                age_range = (16, 35)

        with c2:
            use_contract = st.checkbox(f" {lbl_enable} {lbl_contract}", key="use_contract_filter")
            if use_contract:
                contract_range = st.date_input("Contract Range", (datetime.now().date(), datetime.now().date() + timedelta(days=30)), label_visibility="collapsed", key="contract_range")
            else: contract_range = []

        with c3:
            use_reg = st.checkbox(f" {lbl_enable} {lbl_reg}", key="use_reg_filter")
            if use_reg:
                reg_range = st.date_input("Registration Range", (datetime.now().date().replace(day=1), datetime.now().date()), label_visibility="collapsed", key="reg_range")
            else: reg_range = []

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f'<div class="premium-filter-label">⚙️ {t("filter_advanced_group", lang)}</div>', unsafe_allow_html=True)
        
        # Row 2: Status & Dropdown Filters
        c2_1, c2_2, c2_3 = st.columns(3)
        
        with c2_1:
            use_expired = st.checkbox(t("expired", lang), key="use_expired_filter")
            if use_expired:
                st.caption("⚠️ " + ("ترتيب من الأقدم" if lang == "ar" else "Sorting Oldest first"))
        
        with c2_2:
            use_not_working = st.checkbox("No (هل يعمل حالياً؟)" if lang == "ar" else "Not Working (No)", key="use_not_working_filter")
            
        with c2_3:
            transfer_options = {
                "": f"— {t('transfer_all', lang)} —",
                "First time": t("transfer_1", lang),
                "Second time": t("transfer_2", lang),
                "The third time": t("transfer_3", lang),
                "More than three": t("transfer_more", lang)
            }
            selected_transfer_label = st.selectbox(
                t("transfer_count_label", lang),
                options=list(transfer_options.values()),
                key="transfer_count_dropdown"
            )
            # Find the key (English value) from the selected label
            selected_transfer_key = [k for k, v in transfer_options.items() if v == selected_transfer_label][0]
        
        # Row 3: Huroob & Outside City Filters
        st.markdown("<br>", unsafe_allow_html=True)
        c3_1, c3_2 = st.columns(2)
        with c3_1:
            use_no_huroob = st.checkbox(t("no_huroob", lang), key="use_no_huroob_filter")
        with c3_2:
            use_work_outside = st.checkbox(t("work_outside_city", lang), key="use_work_outside_filter")

    # 2. Search Input & Button
    st.markdown('<div class="search-container">', unsafe_allow_html=True)
    query = st.text_input(t("smart_search", lang), placeholder=t("search_placeholder", lang), key="search_query_input")
    
    # Search Button - Robust Full-width / Centered
    search_clicked = st.button(t("search_btn", lang), key="main_search_btn", use_container_width=True, type="primary")
    
    # NEW: Detect search trigger (Button OR Enter) and increment session ID to reset table selection
    current_search_hash = f"{query}_{str(st.session_state.get('use_age_filter'))}_{str(st.session_state.get('use_contract_filter'))}"
    if search_clicked or (query and st.session_state.get('last_search_hash') != current_search_hash):
        st.session_state.search_entry_count = st.session_state.get('search_entry_count', 0) + 1
        st.session_state.last_search_hash = current_search_hash

    # Notification placeholder right below the button
    search_notif = st.empty()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Gather Filters
    filters = {}
    
    if use_age:
        filters['age_enabled'] = True
        filters['age_min'] = age_range[0]
        filters['age_max'] = age_range[1]
    
    if use_contract and len(contract_range) == 2:
        filters['contract_enabled'] = True
        filters['contract_end_start'] = contract_range[0]
        filters['contract_end_end'] = contract_range[1]
        
    if use_reg and len(reg_range) == 2:
        filters['date_enabled'] = True
        filters['date_start'] = reg_range[0]
        filters['date_end'] = reg_range[1]

    if use_expired:
        filters['expired_only'] = True

    if use_not_working:
        filters['not_working_only'] = True

    if use_no_huroob:
        filters['no_huroob'] = True

    if use_work_outside:
        filters['work_outside_city'] = True
        
    if selected_transfer_key:
        filters['transfer_count'] = selected_transfer_key
    
    # Check if any filter is actually active
    has_active_filter = bool(filters)
    
    # Trigger on button click OR when query changes (Enter is pressed)
    if search_clicked or query or has_active_filter:
        search_loader = show_loading_hourglass() # Custom premium loader
        
        # Debug: Show what filters are being sent
        if filters:
            active_filter_names = []
            if filters.get('age_enabled'): active_filter_names.append(f"{lbl_age}")
            if filters.get('contract_enabled'): active_filter_names.append(f"{lbl_contract}")
            if filters.get('date_enabled'): active_filter_names.append(f"{lbl_reg}")
            if filters.get('expired_only'): active_filter_names.append("العقود المنتهية" if lang == 'ar' else "Expired Contracts")
            if filters.get('not_working_only'): active_filter_names.append("غير موظف" if lang == 'ar' else "Not Working")
            if filters.get('no_huroob'): active_filter_names.append(t("no_huroob", lang))
            if filters.get('work_outside_city'): active_filter_names.append(t("work_outside_city", lang))
            if filters.get('transfer_count'): active_filter_names.append("عدد مرات النقل" if lang == 'ar' else "Transfer Count")
            
            if active_filter_names:
                st.info(f"{'الفلاتر النشطة' if lang == 'ar' else 'Active filters'}: {', '.join(active_filter_names)}")

        # Fetch fresh data
        original_data = st.session_state.db.fetch_data()
        total_rows = len(original_data)
        
        if total_rows == 0:
            show_toast("لم يتم العثور على أي بيانات في قاعدة البيانات. تأكد من الربط مع Google Sheets.", "error", container=search_notif)
            return

        eng = SmartSearchEngine(original_data)
        try:
            res = eng.search(query, filters=filters)
            search_loader.empty() # Clear loader immediately after search results are ready
            
            # --- CUSTOM STATUS LOGIC FOR SEARCH RESULTS ---
            # Try to find date column in results
            res_cols = res.columns.tolist()
            def clean_col(c): return " ".join(str(c).lower().split())
            date_col_search = next((c for c in res_cols if any(kw in clean_col(c) for kw in ["contract end", "انتهاء العقد", "contract expiry"])), None)
            
            if date_col_search:
                status_list = []
                rem_list = []
                sort_list = []
                for _, row in res.iterrows():
                    s = ContractManager.calculate_status(row[date_col_search])
                    gs = s['status']
                    ds = s.get('days', 0)
                    if ds is None: ds = 9999
                    sort_list.append(ds)
                    if lang == 'ar':
                        if gs == 'expired':
                            status_list.append(f"❌ منتهي (منذ {abs(ds)} يوم)")
                        elif gs in ['urgent', 'warning']:
                            status_list.append(f"⚠️ عاجل (متبقى {ds} يوم)")
                        else:
                            status_list.append(f"✅ ساري (متبقى {ds} يوم)")
                    else:
                        status_list.append(f"{s['label_en']} ({abs(ds)} Days)")
                
                status_key = 'حالة العقد' if lang == 'ar' else 'Contract Status'
                res[status_key] = status_list
                res['__days_sort'] = sort_list
                
                # Sort Results: Primary = Geo Tier (Proximity), Secondary = Days Sort
                sort_cols = []
                if '__geo_tier' in res.columns: sort_cols.append('__geo_tier')
                sort_cols.append('__days_sort')
                res = res.sort_values(by=sort_cols, ascending=True)
            else:
                # FALLBACK SORT BY TIMESTAMP (REGISTRATION DATE)
                ts_col = next((c for c in res_cols if any(kw in clean_col(c) for kw in ["timestamp", "طابع", "تاريخ التسجيل"])), None)
                if ts_col:
                    try:
                        # Temporary numeric sort
                        res['__ts_sort'] = pd.to_datetime(res[ts_col], errors='coerce')
                        sort_cols = []
                        asc_list = []
                        if '__geo_tier' in res.columns:
                            sort_cols.append('__geo_tier')
                            asc_list.append(True)
                        sort_cols.append('__ts_sort')
                        asc_list.append(False) # Newest first for timestamp
                        
                        res = res.sort_values(by=sort_cols, ascending=asc_list)
                        res = res.drop(columns=['__ts_sort'])
                    except:
                        pass
            
            # Show count in UI
            count_found = len(res)
            if count_found > 0:
                show_toast(f"{'تم العثور على' if lang == 'ar' else 'Found'} {count_found} {'نتائج من أصل' if lang == 'ar' else 'results out of'} {total_rows}", "success", container=search_notif)
            
            # Debug Panel (for diagnosing search issues)
            # with st.expander("🔧 تشخيص البحث | Search Debug", expanded=False):
            #     debug = eng.last_debug
            #     st.json(debug)
            
            # Handle both DataFrame and list returns
            is_empty = (isinstance(res, list) and len(res) == 0) or (hasattr(res, 'empty') and res.empty)
            
            if is_empty:
                show_toast(t("no_results", lang), "warning", container=search_notif)
            elif query and count_found == total_rows:
                show_toast("تنبيه: البحث أرجع جميع النتائج." if lang == 'ar' else "Warning: Search returned all results.", "warning", container=search_notif)
            
            # Preserve internal diagnostic columns for logic (dropping them here was causing the ID Missing error)
            # internal_cols = [c for c in res.columns if str(c).startswith('__')]
            # res = res.drop(columns=internal_cols)
        except Exception as e:
            st.error(f"حدث خطأ أثناء البحث: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
            return
        else:
            # Rename columns before showing (Safe Rename)
            new_names = {}
            used_names = set()
            for c in res.columns:
                if str(c).startswith('__'): continue
                new_name = t_col(c, lang)
                original_new_name = new_name
                counter = 1
                while new_name in used_names:
                    counter += 1
                    new_name = f"{original_new_name} ({counter})"
                used_names.add(new_name)
                new_names[c] = new_name
                
            res.rename(columns=new_names, inplace=True)
            
            # FINAL POLISH: Format all visible dates to be clean (No Time)
            res = clean_date_display(res)
            
            # Recalculate Column Config Key
            
            # Reorder columns for Search Table (Status first)
            status_key = 'حالة العقد' if lang == 'ar' else 'Contract Status'
            if status_key in res.columns:
                other_cols = [c for c in res.columns if c != status_key]
                res = res[[status_key] + other_cols]

            # Hide internal sheet row from display but keep in original 'res' for logic
            res_display = res.copy()
            for int_col in ["__sheet_row", "__sheet_row_backup"]:
                if int_col in res_display.columns:
                    res_display = res_display.drop(columns=[int_col])
            
            # --- ROW SELECTION & PROFESSIONAL UI ---

            
            # Configure columns for better look
            column_config = {}
            cv_col_name = t_col("Download CV", lang)
            column_config[cv_col_name] = st.column_config.LinkColumn(
                cv_col_name,
                help="Click to open original file",
                validate="^http",
                display_text="فتح الملف 🔗"
            )
            
            # Numeric Suffix for Search
            rem_key_search = t_col('المتبقى' if lang == 'ar' else 'Remaining', lang)
            column_config[rem_key_search] = st.column_config.NumberColumn(
                rem_key_search,
                format="%d يوم" if lang == 'ar' else "%d Days"
            )

            # Flag Image Configuration
            for col in res_display.columns:
                if any(kw in str(col).lower() for kw in ["nationality", "الجنسية"]):
                    column_config[f"🚩_{col}"] = st.column_config.ImageColumn(t("country_label", lang), width="small", pinned=True)



            # --- EXPORT BUTTON FOR SEARCH ---
            c_s_1, c_s_2 = st.columns([4, 1])
            with c_s_2:
                xl_result_search = create_pasha_whatsapp_excel(res, lang=lang)
                if xl_result_search:
                    xl_buf_search, xl_df_search = xl_result_search
                    btn_text = "📤 " + ("تصدير للواتساب" if lang == 'ar' else "Export to WhatsApp")
                    render_pasha_export_button(xl_df_search, btn_text, f"Search_WhatsApp_{datetime.now().strftime('%M%S')}.xlsx", "البحث_الذكي_واتساب", key="btn_exp_search")
            
            # Smart Translator Button
            res_display = render_table_translator(res_display, key_prefix="search_res")
            
            # Use on_select to capture row selection
            df_height = min((len(res_display) + 1) * 35 + 40, 600)
            event = st.dataframe(
                style_df(res_display), 
                use_container_width=False,
                on_select="rerun",
                selection_mode="single-row",
                hide_index=True,
                column_config=__apply_pinned_columns(style_df(res_display), column_config),
                key=f"search_results_table_{st.session_state.get('search_entry_count', 0)}",
                height=df_height
            )

            # Handle Selection with Safety Check
            if event.selection and event.selection.get("rows"):
                selected_idx = event.selection["rows"][0]
                if 0 <= selected_idx < len(res):
                    worker_row = res.iloc[selected_idx]
                    
                    # Generate unique UID for search mode to pass to panel
                    # Use original column names if possible or translated ones
                    name_col = t_col("Full Name:", lang)
                    phone_col = t_col("Phone", lang)
                    w_name = str(worker_row.get(name_col, worker_row.get("Full Name:", worker_row.get("الاسم الكامل", "Worker"))))
                    w_phone = str(worker_row.get(phone_col, worker_row.get("Phone", "")))
                    worker_uid = hashlib.md5(f"{w_name}{w_phone}".encode()).hexdigest()
                    
                    render_cv_detail_panel(worker_row, selected_idx, lang, key_prefix="search", worker_uid=worker_uid)
                else:
                    st.toast("⚠️ Selection out of bounds. Please refresh search." if lang == 'en' else "⚠️ التحديد خارج النطاق. يرجى تحديث البحث.")


def render_translator_content():
    lang = st.session_state.lang
    from src.core.file_translator import FileTranslator, TranslationService

    # ──── Premium CSS for Translator Module ────
    st.markdown("""
    <style>
    .translator-hero {
        background: linear-gradient(135deg, rgba(13,18,32,0.95) 0%, rgba(9,14,29,0.95) 50%, rgba(14,20,40,0.95) 100%);
        border: 1px solid rgba(212,175,55,0.2);
        border-radius: 20px;
        padding: 35px 40px;
        margin-bottom: 25px;
        position: relative;
        overflow: hidden;
    }
    .translator-hero::before {
        content: '';
        position: absolute;
        top: 0; left: -100%;
        height: 1px; width: 60%;
        background: linear-gradient(90deg, transparent, rgba(212,175,55,0.6), transparent);
        animation: heroScan 3s linear infinite;
    }
    @keyframes heroScan {
        0% { left: -100%; }
        100% { left: 100%; }
    }
    .translator-title {
        font-family: 'Cairo', 'Inter', sans-serif;
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #fff 0%, #D4AF37 50%, #fff 100%);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: titleShimmer 3s linear infinite;
        margin-bottom: 8px;
    }
    @keyframes titleShimmer {
        0% { background-position: -200% center; }
        100% { background-position: 200% center; }
    }
    .translator-subtitle {
        color: rgba(255,255,255,0.55);
        font-size: 0.95rem;
        font-family: 'Cairo', sans-serif;
        margin-bottom: 0;
    }
    .format-badges {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        margin-top: 15px;
    }
    .format-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 14px;
        border-radius: 50px;
        font-size: 0.8rem;
        font-weight: 600;
        border: 1px solid rgba(212,175,55,0.25);
        background: rgba(212,175,55,0.08);
        color: #D4AF37;
        transition: all 0.3s ease;
    }
    .format-badge:hover {
        background: rgba(212,175,55,0.18);
        border-color: rgba(212,175,55,0.5);
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(212,175,55,0.15);
    }
    .log-entry {
        padding: 6px 12px;
        border-radius: 8px;
        margin: 4px 0;
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 0.82rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .log-info { background: rgba(59,130,246,0.08); color: #93c5fd; border-left: 3px solid #3b82f6; }
    .log-success { background: rgba(34,197,94,0.08); color: #86efac; border-left: 3px solid #22c55e; }
    .log-warning { background: rgba(234,179,8,0.08); color: #fde047; border-left: 3px solid #eab308; }
    .log-error { background: rgba(239,68,68,0.08); color: #fca5a5; border-left: 3px solid #ef4444; }
    .log-time { color: rgba(255,255,255,0.3); font-size: 0.75rem; min-width: 65px; }
    .result-card {
        background: linear-gradient(160deg, rgba(13,18,32,0.9), rgba(9,14,29,0.9));
        border: 1px solid rgba(212,175,55,0.15);
        border-radius: 16px;
        padding: 20px;
    }
    .stat-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 8px 16px;
        border-radius: 50px;
        font-size: 0.85rem;
        background: rgba(212,175,55,0.1);
        border: 1px solid rgba(212,175,55,0.2);
        color: #D4AF37;
        margin-right: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

    # ──── Hero Section ────
    formats_html = ""
    for ext, info in FileTranslator.FILE_TYPE_INFO.items():
        name = info.get(f"name_{lang}", info.get("name_en"))
        icon = info["icon"]
        formats_html += f'<span class="format-badge">{icon} {ext}</span>'

    subtitle = t("translator_desc_new", lang)
    st.markdown(f"""
    <div class="translator-hero">
        <div class="translator-title">{'🌐 ' + t('translator_title', lang)}</div>
        <div class="translator-subtitle">{subtitle}</div>
        <div class="format-badges">{formats_html}</div>
    </div>
    """, unsafe_allow_html=True)

    # ──── Language Selection ────
    lang_options = TranslationService.SUPPORTED_LANGUAGES
    lang_keys = list(lang_options.keys())
    lang_labels = list(lang_options.values())

    col_src, col_arrow, col_tgt = st.columns([2, 0.5, 2])
    with col_src:
        src_idx = 0  # "auto" is first option
        src_options = [t("auto_detect", lang)] + lang_labels
        src_keys = ["auto"] + lang_keys
        selected_src = st.selectbox(
            t("src_lang", lang),
            options=src_options,
            index=0,
            key="trans_src_lang"
        )
        src_lang_code = src_keys[src_options.index(selected_src)]

    with col_arrow:
        st.markdown("<div style='text-align:center; padding-top:32px; font-size:1.8rem; color:#D4AF37;'>→</div>", unsafe_allow_html=True)

    with col_tgt:
        # Default to Arabic
        default_tgt_idx = lang_keys.index("ar") if "ar" in lang_keys else 0
        selected_tgt = st.selectbox(
            t("tgt_lang", lang),
            options=lang_labels,
            index=default_tgt_idx,
            key="trans_tgt_lang"
        )
        tgt_lang_code = lang_keys[lang_labels.index(selected_tgt)]

    st.markdown("<div style='margin: 10px 0;'></div>", unsafe_allow_html=True)

    # ──── File Upload ────
    supported_types = ["docx", "bdf", "jpg", "jpeg", "png", "pdf"]
    uploaded = st.file_uploader(
        t("upload_file_label", lang),
        type=supported_types,
        key="translator_file_upload",
        help=f"{t('supported_formats', lang)}: .docx, .pdf, .jpg, .png, .jpeg, .bdf"
    )

    if uploaded:
        file_id = f"ft_{uploaded.name}_{uploaded.size}_{src_lang_code}_{tgt_lang_code}"
        file_bytes = uploaded.read()
        file_size = len(file_bytes)

        # File info display
        ft_temp = FileTranslator()
        ext = ft_temp.get_file_type(uploaded.name)
        file_info = FileTranslator.FILE_TYPE_INFO.get(ext, {})
        icon = file_info.get("icon", "📁")
        type_name = file_info.get(f"name_{lang}", file_info.get("name_en", ext))
        size_str = FileTranslator._format_size(file_size)

        st.markdown(f"""
        <div style="display:flex; gap:15px; flex-wrap:wrap; margin: 10px 0 20px 0;">
            <span class="stat-pill">📁 {uploaded.name}</span>
            <span class="stat-pill">{icon} {type_name}</span>
            <span class="stat-pill">📏 {size_str}</span>
        </div>
        """, unsafe_allow_html=True)

        # ──── Translation Trigger ────
        btn_col1, btn_col2, btn_col3 = st.columns([1.5, 2, 1.5])
        with btn_col2:
            translate_clicked = st.button(
                t("translate_now", lang),
                use_container_width=True,
                type="primary",
                key="btn_start_translation"
            )

        # Run translation
        if translate_clicked or st.session_state.get('last_trans_file') == file_id:
            if st.session_state.get('last_trans_file') != file_id:
                # New file — translate
                progress_bar = st.progress(0, text=t("translating_wait", lang))
                status_text = st.empty()

                def update_progress(pct, msg):
                    progress_bar.progress(min(pct, 1.0), text=msg)

                try:
                    translator = FileTranslator(
                        source_lang=src_lang_code,
                        target_lang=tgt_lang_code
                    )

                    result = translator.translate(file_bytes, uploaded.name, progress_callback=update_progress)
                    log_entries = translator.get_log()

                    progress_bar.progress(1.0, text=t("translation_complete", lang) if result.get("success") else t("translation_failed", lang))

                    # Cache results
                    st.session_state.last_trans_result = result
                    st.session_state.last_trans_file = file_id
                    st.session_state.last_trans_log = log_entries

                except Exception as e:
                    progress_bar.progress(1.0, text=t("translation_failed", lang))
                    st.error(f"{t('error', lang)}: {str(e)}")
                    st.session_state.last_trans_result = None
                    st.session_state.last_trans_file = file_id
                    st.session_state.last_trans_log = []

            # Display results
            result = st.session_state.get('last_trans_result')
            log_entries = st.session_state.get('last_trans_log', [])

            if result and result.get("success"):
                st.markdown(f"""
                <div style="background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.3); 
                     border-radius: 12px; padding: 15px 20px; margin: 15px 0;">
                    <span style="font-size: 1.1rem; color: #86efac; font-weight: 600;">
                        {t("translation_complete", lang)}
                    </span>
                </div>
                """, unsafe_allow_html=True)

                # Download buttons
                dl_col1, dl_col2 = st.columns(2)
                with dl_col1:
                    if result.get("output_bytes"):
                        st.download_button(
                            t("download_trans", lang),
                            data=result["output_bytes"],
                            file_name=result.get("output_filename", "translated_file"),
                            mime=result.get("output_mime", "application/octet-stream"),
                            use_container_width=True,
                            key="dl_translated_file"
                        )
                with dl_col2:
                    if result.get("translated_text"):
                        st.download_button(
                            t("download_trans_txt", lang),
                            data=result["translated_text"],
                            file_name=f"translated_{uploaded.name.rsplit('.', 1)[0]}.txt",
                            mime="text/plain",
                            use_container_width=True,
                            key="dl_translated_txt"
                        )

                # Side-by-side text comparison
                st.markdown("<div style='margin: 15px 0;'></div>", unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"""<div class="result-card">
                        <div style="color:#D4AF37; font-weight:600; margin-bottom:10px; font-family:'Cairo',sans-serif;">
                            📝 {t("original", lang)}
                        </div>
                    </div>""", unsafe_allow_html=True)
                    st.text_area("orig", result.get("original_text", ""), height=350,
                                 key="trans_orig_area", label_visibility="collapsed")
                with c2:
                    st.markdown(f"""<div class="result-card">
                        <div style="color:#D4AF37; font-weight:600; margin-bottom:10px; font-family:'Cairo',sans-serif;">
                            🌐 {t("translated", lang)}
                        </div>
                    </div>""", unsafe_allow_html=True)
                    st.text_area("trans", result.get("translated_text", ""), height=350,
                                 key="trans_result_area", label_visibility="collapsed")

            elif result and not result.get("success"):
                st.error(f"{t('translation_failed', lang)}: {result.get('error', '')}")

            # ──── Operation Log ────
            if log_entries:
                with st.expander(t("translation_log", lang), expanded=False):
                    log_html = ""
                    for entry in log_entries:
                        level = entry.get("level", "info")
                        log_html += f"""
                        <div class="log-entry log-{level}">
                            <span class="log-time">{entry['time']}</span>
                            <span>{entry['message']}</span>
                        </div>"""
                    st.markdown(log_html, unsafe_allow_html=True)

    else:
        # Clear cache if no file is uploaded
        if 'last_trans_file' in st.session_state:
            del st.session_state.last_trans_file
        if 'last_trans_result' in st.session_state:
            del st.session_state.last_trans_result
        if 'last_trans_log' in st.session_state:
            del st.session_state.last_trans_log

        # Empty state placeholder
        st.markdown(f"""
        <div style="text-align:center; padding: 60px 20px; color: rgba(255,255,255,0.3);">
            <div style="font-size: 4rem; margin-bottom: 15px;">📄</div>
            <div style="font-size: 1.1rem; font-family: 'Cairo', sans-serif;">
                {t("no_file_uploaded", lang)}
            </div>
            <div style="font-size: 0.85rem; margin-top: 8px; color: rgba(255,255,255,0.2);">
                {t("supported_formats", lang)}: .docx, .pdf, .jpg, .png, .bdf
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_permissions_content():
    lang = st.session_state.lang
    st.title(f" {t('permissions_title', lang)}")
    
    # Persistent Success Message after Rerun
    if st.session_state.get('permissions_success'):
        show_toast(st.session_state.permissions_success, "success")
        del st.session_state.permissions_success

    with st.expander(t("add_user", lang), expanded=False):
        with st.form("new_user"):
            u = st.text_input(t("username", lang))
            p = st.text_input(t("password", lang), type="password")
            
            # Bilingual Name Inputs
            c1, c2 = st.columns(2)
            with c1:
                fn_ar = st.text_input(t("first_name_ar", lang))
                ftn_ar = st.text_input(t("father_name_ar", lang))
            with c2:
                fn_en = st.text_input(t("first_name_en", lang))
                ftn_en = st.text_input(t("father_name_en", lang))
                
            r = st.selectbox(t("role", lang), ["viewer", "admin"])
            if st.form_submit_button(t("add_btn", lang)):
                s, m = st.session_state.auth.add_user(u, p, r, fn_ar, ftn_ar, fn_en, ftn_en)
                if s: 
                    st.session_state.permissions_success = t("user_added", lang)
                    st.rerun()
                else: show_toast(m, "error")

    st.subheader(t("users_list", lang))
    
    # Show loading when preparing user data
    perm_loader = show_loading_hourglass()
    users = st.session_state.auth.users
    user_list = list(users.keys())
    perm_loader.empty()
    
    selected_user = st.selectbox(t("select_user", lang), user_list)
    if selected_user:
        current_data = users[selected_user]
        with st.form("edit_user_form"):
            st.write(f"Editing: **{selected_user}**")
            current_role_idx = 0 if current_data.get("role") == "viewer" else 1
            new_role = st.selectbox(t("role", lang), ["viewer", "admin"], index=current_role_idx)
            
            # Bilingual Edits
            c1, c2 = st.columns(2)
            with c1:
                new_f_ar = st.text_input(t("first_name_ar", lang), value=current_data.get("first_name_ar", ""))
                new_fa_ar = st.text_input(t("father_name_ar", lang), value=current_data.get("father_name_ar", ""))
            with c2:
                new_f_en = st.text_input(t("first_name_en", lang), value=current_data.get("first_name_en", ""))
                new_fa_en = st.text_input(t("father_name_en", lang), value=current_data.get("father_name_en", ""))
                
            new_pass = st.text_input(t("new_password", lang), type="password")
            
            # Additional Permissions Toggle
            st.markdown(f"**⚙️ {t('permissions', lang)}**")
            current_perms = current_data.get("permissions", [])
            bengali_perm = st.toggle(t("perm_bengali_supply", lang), value="bengali_supply" in current_perms)
            delete_perm = st.toggle(t("perm_delete_global", lang), value="can_delete" in current_perms)
            
            if st.form_submit_button(t("update_btn", lang)):
                # Prepare permission list
                new_perms = []
                # Keep 'all' if they had it
                if "all" in current_perms: new_perms.append("all")
                if "read" in current_perms: new_perms.append("read")
                
                if bengali_perm:
                    if "bengali_supply" not in new_perms: new_perms.append("bengali_supply")
                if delete_perm:
                    if "can_delete" not in new_perms: new_perms.append("can_delete")
                
                st.session_state.auth.update_permissions(selected_user, new_perms)
                st.session_state.auth.update_role(selected_user, new_role)
                st.session_state.auth.update_profile(selected_user, new_f_ar, new_fa_ar, new_f_en, new_fa_en)
                if new_pass:
                    st.session_state.auth.update_password(selected_user, new_pass)
                
                st.session_state.permissions_success = t("update_success", lang)
                st.rerun()

        # Profile Photo Upload Section
        st.markdown("---")
        st.markdown(f"**🖼️ {'صورة الملف الشخصي' if lang == 'ar' else 'Profile Photo'}**")
        
        # Show current avatar
        current_avatar = st.session_state.auth.get_avatar(selected_user)
        av_col1, av_col2 = st.columns([1, 3])
        with av_col1:
            if current_avatar:
                img_src = current_avatar if str(current_avatar).startswith('data:') else f"data:image/png;base64,{current_avatar}"
                st.markdown(f'<img src="{img_src}" style="width:80px;height:80px;border-radius:50%;object-fit:cover;border:2px solid #D4AF37;" />', unsafe_allow_html=True)
            else:
                st.markdown('<div style="width:80px;height:80px;border-radius:50%;background:linear-gradient(135deg,#D4AF37,#8B7520);display:flex;align-items:center;justify-content:center;font-size:36px;">👤</div>', unsafe_allow_html=True)
        with av_col2:
            uploaded_photo = st.file_uploader(
                "رفع صورة (PNG/JPG)" if lang == 'ar' else "Upload Photo (PNG/JPG)", 
                type=["png","jpg","jpeg"],
                key=f"avatar_upload_{selected_user}",
                label_visibility="collapsed"
            )
            if uploaded_photo:
                try:
                    from PIL import Image
                    from streamlit_cropper import st_cropper
                    import io
                    
                    img = Image.open(uploaded_photo)
                    st.markdown("🎯 **حدد الجزء المراد قصه من الصورة داخل المربع**" if lang == 'ar' else "🎯 **Drag to adjust the circular crop**", unsafe_allow_html=True)
                    
                    # Display the interactive cropper
                    cropped_img = st_cropper(img, realtime_update=True, box_color='#D4AF37', aspect_ratio=(1, 1), key=f"cropper_{selected_user}")
                    
                    if st.button("💾 " + ("حفظ الصورة المحددة" if lang == 'ar' else "Save Cropped Photo"), key="save_avatar_btn", type="primary"):
                        buf = io.BytesIO()
                        cropped_img.save(buf, format="PNG")
                        avatar_bytes = buf.getvalue()
                        avatar_b64 = base64.b64encode(avatar_bytes).decode('utf-8')
                        full_uri = f"data:image/png;base64,{avatar_b64}"
                        
                        st.session_state.auth.update_avatar(selected_user, full_uri)
                        show_toast("✅ " + ("تم حفظ الصورة المحددة بنجاح" if lang == 'ar' else "Cropped photo saved successfully!"), "success")
                        st.rerun()
                except Exception as e:
                    st.error("عذراً، حدث خطأ أثناء معالجة الصورة. الرجاء التأكد من أن الملف سليم." if lang == 'ar' else "Error processing image. Please ensure valid file.")
                    print(f"Cropper error: {e}")

        if selected_user != "admin":
            st.markdown("""
                <style>
                /* Style only the delete button within the popover trigger */
                div[data-testid="stPopover"] > button {
                    background-color: #8B0000 !important;
                    color: #D4AF37 !important;
                    border: 1px solid #D4AF37 !important;
                    padding: 8px 25px !important;
                    font-size: 14px !important;
                    border-radius: 12px !important;
                    transition: 0.3s !important;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }
                div[data-testid="stPopover"] > button:hover {
                    background-color: #D4AF37 !important;
                    color: #000 !important;
                    box-shadow: 0 0 15px rgba(212, 175, 55, 0.4) !important;
                }
                </style>
            """, unsafe_allow_html=True)
            
            # Use columns to make the button "small" or centered
            c1, c2, c3 = st.columns([1, 1, 1])
            with c1:
                with st.popover("حذف المستخدم" if lang=='ar' else "Delete User"):
                    st.warning("هل أنت متأكد من حذف هذا المستخدم؟" if lang=='ar' else "Are you sure you want to delete this user?")
                    if st.button("نعم، احذف المستخدم" if lang=='ar' else "Yes, Delete User", type="primary", use_container_width=True):
                        res = st.session_state.auth.delete_user(selected_user)
                        
                        # Handle both old (bool) and new (tuple) return types safely
                        if isinstance(res, tuple):
                            success, message = res
                        else:
                            success, message = res, ("تم الحذف" if res else "فشل الحذف")
                            
                        if success:
                            st.session_state.permissions_success = "تم الحذف بنجاح"
                            st.rerun()
                        else:
                            show_toast(f"خطأ: {message}", "error")
    
    # Translate table keys for Users Table
    table_data = []
    for k, v in users.items():
        table_data.append({
            t_col("User", lang): k,
            t_col("Role", lang): v.get('role', 'viewer')
        })
    
    # Stylized DataFrame
    df_users = pd.DataFrame(table_data)
    st.dataframe(style_df(df_users), use_container_width=True, column_config=__apply_pinned_columns(style_df(df_users)))

def render_order_processing_content():
    """Order Processing: Matches Customer Requests with available Workers."""
    lang = st.session_state.lang
    st.markdown('<div class="programmer-signature-neon">By: Alsaeed Alwazzan</div>', unsafe_allow_html=True)
    st.title(f" {t('order_processing_title', lang)}")
    
    loading_placeholder = show_loading_hourglass()
    start_op_time = time.time()
    
    try:
        customers_df = st.session_state.db.fetch_customer_requests()
        workers_df = st.session_state.db.fetch_data()
    except Exception as e:
        loading_placeholder.empty()
        st.error(f"{t('error', lang)}: {e}")
        return
    
    # Ensure at least 0.6s of visibility for the premium rotating feel
    elapsed = time.time() - start_op_time
    if elapsed < 0.6:
        time.sleep(0.6 - elapsed)
        
    loading_placeholder.empty()
    
    if customers_df.empty:
        st.warning(t("no_data", lang))
        return
    
    if workers_df.empty:
        st.warning("لا توجد بيانات عمال" if lang == 'ar' else "No worker data available")
        return

    # --- NEW: Advanced Filtering Panel (Matching Image) ---
    ai_title = "(AI) البحث الذكي" if lang == 'ar' else "Smart Search (AI)"
    st.markdown(f'<div class="mobile-neon-text" style="color: #D4AF37; font-weight: 600; margin-bottom: 5px; font-family: \'Cairo\', sans-serif;">{ai_title}</div>', unsafe_allow_html=True)
    
    with st.expander("🔍 " + ("تصفية متقدمة" if lang == 'ar' else "Advanced Filtering"), expanded=False):
        # 1. Row: Scheduling & Dates
        st.markdown(f'<div class="mobile-neon-text" style="color: #888; margin-bottom: 10px;">{"📅 جدولة وتواريخ" if lang == "ar" else "📅 Scheduling & Dates"}</div>', unsafe_allow_html=True)
        rc1, rc2, rc3 = st.columns(3)
        with rc3: # Rightmost (Arabic)
            age_enabled = st.checkbox("تفعيل العمر" if lang == 'ar' else "Enable Age", key="op_age_en")
            if age_enabled:
                ac1, ac2 = st.columns(2)
                with ac1:
                    a_min = st.number_input("من سن" if lang == 'ar' else "From", 1, 100, 16, key="op_age_min")
                with ac2:
                    a_max = st.number_input("إلى سن" if lang == 'ar' else "To", 1, 100, 35, key="op_age_max")
                age_range = (a_min, a_max)
            else:
                age_range = (16, 35)
        with rc2:
            contract_enabled = st.checkbox("تفعيل تاريخ انتهاء العقد" if lang == 'ar' else "Enable Contract End Date", key="op_cont_en")
            if contract_enabled:
                c_start = st.date_input("من", value=datetime.today(), key="op_cont_start")
                c_end = st.date_input("إلى", value=datetime.today() + timedelta(days=365), key="op_cont_end")
        with rc1:
            date_enabled = st.checkbox("تفعيل تاريخ التسجيل" if lang == 'ar' else "Enable Reg. Date", key="op_date_en")
            if date_enabled:
                d_start = st.date_input("من", value=datetime.today() - timedelta(days=30), key="op_date_start")
                d_end = st.date_input("إلى", value=datetime.today(), key="op_date_end")

        # 2. Row: Advanced Smart Filtering
        st.markdown(f'<div class="mobile-neon-text" style="color: #888; margin-top: 15px; margin-bottom: 10px;">{"⚙️ تصفية ذكية متقدمة" if lang == "ar" else "⚙️ Advanced Smart Filtering"}</div>', unsafe_allow_html=True)
        sc1, sc2, sc3 = st.columns(3)
        with sc3:
            expired_only = st.checkbox("العقود المنتهية" if lang == 'ar' else "Expired Contracts", key="op_expired")
        with sc2:
            not_working_only = st.checkbox("No (هل يعمل حالياً؟)" if lang == 'ar' else "No (Working Now?)", key="op_not_working")
        with sc1:
            st.markdown(f'<div class="mobile-neon-text" style="font-size: 0.8rem; color: #888;">{"عدد نقل الكفالة" if lang == "ar" else "Transfer Count"}</div>', unsafe_allow_html=True)
            trans_count = st.selectbox("", ["— الكل —", "1", "2", "3", "4+"], key="op_transfer", label_visibility="collapsed")

        # 3. Row: Status Flags
        tc1, tc2, tc3 = st.columns(3)
        with tc3:
            no_huroob = st.checkbox("بدون بلاغ هروب (No)" if lang == 'ar' else "No Huroob (No)", key="op_no_huroob")
        with tc2:
            work_outside = st.checkbox("يقبل العمل خارج مدينته (Yes)" if lang == 'ar' else "Work Outside City (Yes)", key="op_outside")
        with tc1:
            pass # Reserved

        # Apply Filters using SmartSearchEngine
        filters = {
            'age_enabled': age_enabled,
            'age_min': age_range[0] if age_enabled else None,
            'age_max': age_range[1] if age_enabled else None,
            'contract_enabled': contract_enabled,
            'contract_end_start': c_start if contract_enabled else None,
            'contract_end_end': c_end if contract_enabled else None,
            'date_enabled': date_enabled,
            'date_start': d_start if date_enabled else None,
            'date_end': d_end if date_enabled else None,
            'expired_only': expired_only,
            'not_working_only': not_working_only,
            'no_huroob': no_huroob,
            'work_outside_city': work_outside,
            'transfer_count': trans_count if trans_count != "— الكل —" else None
        }
        
        # Execute global filter on worker dataset
        if any(filters.values()):
            engine = SmartSearchEngine(workers_df)
            workers_df = engine.search("", filters=filters)
            st.info(f"💡 {'تم تطبيق التصفية: متاح حالياً ' if lang == 'ar' else 'Filter applied: available '} {len(workers_df)} {' عامل' if lang == 'ar' else ' workers'}")

    # --- Resume Original Logic ---

    # --- Customer Column Names (name-based lookup to handle __sheet_row offset) ---
    def find_cust_col(keywords):
        for c in customers_df.columns:
            c_lower = str(c).lower()
            if all(kw in c_lower for kw in keywords): return c
        return None
    
    # --- GLOBAL SORT: Newest Requests First ---
    ts_sort_col = find_cust_col(["timestamp"]) or find_cust_col(["الطابع"]) or find_cust_col(["تاريخ"])
    if not ts_sort_col and len(customers_df.columns) > 0:
        if customers_df.columns[0] == "__sheet_row" and len(customers_df.columns) > 1:
            ts_sort_col = customers_df.columns[1]
        else:
            ts_sort_col = customers_df.columns[0]
            
    if ts_sort_col:
        try:
            # Robust parsing for Arabic AM/PM markers
            def robust_parse(v):
                if not v: return pd.NaT
                s = str(v).replace('م', 'PM').replace('ص', 'AM')
                return pd.to_datetime(s, errors='coerce')
                
            customers_df['__temp_sort'] = customers_df[ts_sort_col].apply(robust_parse)
            # Sort newest first
            customers_df = customers_df.sort_values(by='__temp_sort', ascending=False)
            customers_df = customers_df.drop(columns=['__temp_sort'])
        except:
            pass
    
    c_company = find_cust_col(["company"]) or find_cust_col(["شركه"]) or find_cust_col(["مؤسس"])
    c_responsible = find_cust_col(["responsible"]) or find_cust_col(["مسؤول"])
    c_mobile = find_cust_col(["mobile"]) or find_cust_col(["موبيل"])
    c_category = find_cust_col(["category"]) or find_cust_col(["فئ"])
    c_nationality = find_cust_col(["nationality"]) or find_cust_col(["جنسي"])
    c_location = find_cust_col(["location"]) or find_cust_col(["موقع"])
    c_num_emp = find_cust_col(["number of employees"]) or find_cust_col(["عدد"])
    c_work_nature = find_cust_col(["nature"]) or find_cust_col(["طبيعة"])
    c_salary = find_cust_col(["salary"]) or find_cust_col(["راتب"])
    c_transfer_days = find_cust_col(["transfer days"]) or find_cust_col(["نقل الكفالة"]) or find_cust_col(["نقل"])
    c_working_hours = find_cust_col(["working hours"]) or find_cust_col(["ساعات"])
    c_weekly_holiday = find_cust_col(["holiday"]) or find_cust_col(["day off"]) or find_cust_col(["أسبوعي"]) or find_cust_col(["اجازة"]) or find_cust_col(["إجازة"])
    c_notes = find_cust_col(["notes"]) or find_cust_col(["ملاحظات"])
    
    # --- Worker Column Names ---
    w_name_col = next((c for c in workers_df.columns if "full name" in c.lower()), None)
    w_nationality_col = next((c for c in workers_df.columns if c.strip().lower() == "nationality"), None)
    w_gender_col = next((c for c in workers_df.columns if c.strip().lower() == "gender"), None)
    w_job_col = next((c for c in workers_df.columns if "job" in c.lower() and "looking" in c.lower()), None)
    w_other_job_col = next((c for c in workers_df.columns if "other jobs" in c.lower()), None)
    w_city_col = next((c for c in workers_df.columns if "city" in c.lower() and "saudi" in c.lower()), None)
    w_phone_col = next((c for c in workers_df.columns if "phone" in c.lower()), None)
    w_age_col = next((c for c in workers_df.columns if "age" in c.lower()), None)
    w_timestamp_col = next((c for c in workers_df.columns if any(kw in str(c).lower() for kw in ["timestamp", "طابع", "تاريخ التسجيل"])), None)
    w_contract_end_col = next((c for c in workers_df.columns if any(kw in str(c).lower() for kw in ["contract end", "انتهاء العقد"])), None)

    import re
    
    def normalize(text):
        if not text: return ""
        s = str(text).strip().lower()
        s = re.sub(r'[^\w\s\-]', ' ', s, flags=re.UNICODE)
        return ' '.join(s.split()).strip()
    
    def match_gender(customer_category, worker_gender):
        cat = normalize(customer_category)
        gen = normalize(worker_gender)
        if not cat or not gen: return True
        is_male_request = ("رجال" in cat) or (re.search(r'\bmale\b', cat) and "female" not in cat)
        is_female_request = ("نساء" in cat) or ("female" in cat)
        if is_male_request:
            return re.search(r'\bmale\b', gen) is not None and "female" not in gen
        elif is_female_request:
            return "female" in gen
        return True
    
    def match_nationality(customer_nat, worker_nat):
        c_raw = str(customer_nat).strip()
        w_raw = str(worker_nat).strip()
        if not c_raw or not w_raw: return True

        # Helper to clean and split a string by common separators and remove emojis
        def get_clean_parts(text):
            # Remove emojis (common flags, etc.)
            clean = re.sub(r'[^\w\s\-–|/]', ' ', text)
            # Split by separators
            parts = [p.strip() for p in re.split(r'[\-–|/]', clean) if p.strip()]
            return parts

        # 1. Extract Master Search Terms from Customer Request
        c_parts = get_clean_parts(c_raw)
        master_search_terms = set()
        tm = st.session_state.get('tm')

        for cp in c_parts:
            # Add normalized part
            master_search_terms.add(normalize(cp))
            # Add translations if available
            if tm:
                bundles = tm.analyze_query(cp)
                for b in bundles:
                    for s in b:
                        master_search_terms.add(normalize(s))

        # 2. Extract Worker Nationality Parts
        w_parts = [normalize(wp) for wp in get_clean_parts(w_raw)]
        
        # 3. Precise Matching
        for term in master_search_terms:
            if not term: continue
            for wp in w_parts:
                if not wp: continue
                # Strict or high-confidence match
                if term == wp or (len(term) > 3 and (term in wp or wp in term)):
                    return True
        return False
    
    def match_job(customer_job, worker_job):
        c_job = str(customer_job).strip()
        w_job_raw = str(worker_job).strip()
        if not c_job or not w_job_raw: return True
        
        c_norm = normalize(c_job)
        w_norm = normalize(w_job_raw)
        if not c_norm or not w_norm: return True
        
        # 1. Direct full phrase match (normalized)
        if c_norm in w_norm or w_norm in c_norm:
            return True
        
        # 2. Bilingual full phrase match (uses Arabic↔English translation)
        if _fuzzy_match(w_job_raw, c_job):
            return True
        
        # 3. Word-level bilingual matching (skip generic title words)
        generic_words = {"coordinator", "supervisor", "worker", "employee", "manager",
                         "منسق", "عامل", "موظف", "بائع", "صانع", "مقدم", "مشرف",
                         "sales", "driver", "and", "the", "a", "an", "or", "in", "of"}
        
        c_words = re.split(r'[\s,،/\-–]+', c_job)
        for cw in c_words:
            cw = cw.strip()
            if not cw or len(cw) < 3 or cw.lower() in generic_words:
                continue
            # Bilingual match for this meaningful keyword
            if _fuzzy_match(w_job_raw, cw):
                return True
        
        # 4. Domain synonym groups (cross-language matching for common professions)
        synonym_groups = [
            {"flower", "flowers", "florist", "floral", "زهور", "ورد", "floriculture"},
            {"coffee", "barista", "باريستا", "قهوة", "مقهى", "كوفي", "cafe"},
            {"cook", "cooking", "chef", "طباخ", "طبخ", "شيف", "cuisine"},
            {"clean", "cleaner", "cleaning", "نظافة", "تنظيف", "نظافه"},
            {"hair", "hairdresser", "stylist", "حلاق", "كوافير", "مصفف", "شعر", "coiffeur"},
            {"nail", "manicure", "pedicure", "بدكير", "منكير", "اظافر"},
            {"massage", "مساج", "spa"},
            {"pastry", "dessert", "sweets", "حلا", "حلويات", "معجنات"},
            {"nurse", "nursing", "ممرض", "ممرضة", "تمريض"},
            {"driver", "driving", "سائق", "قيادة"},
            {"butcher", "جزار", "لحام", "لحوم", "meat", "مجزر"},
            {"waiter", "waitress", "نادل", "نادلة", "garson"},
            {"secretary", "سكرتيرة", "سكرتير", "admin", "اداري", "ادارية"},
            {"guard", "security", "حارس", "أمن", "امن", "حراسة"},
            {"carpenter", "نجار", "نجارة", "woodwork"},
            {"plumber", "سباك", "سباكة", "plumbing"},
            {"electrician", "كهربائي", "كهرباء", "electrical"},
            {"painter", "دهان", "طلاء", "painting"},
            {"tailor", "خياط", "خياطة", "sewing"},
            {"mechanic", "ميكانيكي", "صيانة", "maintenance"},
            {"welder", "لحام", "welding"},
            {"farmer", "مزارع", "فلاح", "farm", "زراعة", "agriculture"},
            {"baker", "خباز", "مخبز", "bakery"},
            {"cashier", "كاشير", "محاسب", "صراف"},
            {"salesman", "مندوب", "مبيعات", "sales representative"},
            {"teacher", "مدرس", "معلم", "تعليم", "teaching"},
            {"accountant", "محاسب", "حسابات", "accounting"},
            {"warehouse", "مستودع", "مخزن", "storekeeper"},
            {"delivery", "توصيل", "مندوب توصيل"},
            {"housemaid", "خادمة", "شغالة", "عاملة منزلية", "domestic"},
        ]
        
        c_lower = c_job.lower()
        w_lower = w_job_raw.lower()
        
        for group in synonym_groups:
            c_has = any(syn in c_lower for syn in group)
            w_has = any(syn in w_lower for syn in group)
            if c_has and w_has:
                return True

        return False
    
    def find_matching_workers(customer_row):
        """Find workers. Returns (all_matches, all_scores, city_count, region_count)."""
        city_matches, city_scores = [], []
        region_matches, region_scores = [], []
        other_matches, other_scores = [], []
        
        for _, worker in workers_df.iterrows():
            score = 0
            total_criteria = 0
            geo_tier = 99 # 0=City, 1=Region, 2+=Proximity Regions, 99=Other
            
            if c_category and w_gender_col:
                cv = str(customer_row.get(c_category, ""))
                wv = str(worker.get(w_gender_col, ""))
                if cv.strip():
                    if not match_gender(cv, wv):
                        continue # Hard Filter: Skip if gender mismatch
                    total_criteria += 1
                    score += 1
            
            if c_nationality and w_nationality_col:
                cv = str(customer_row.get(c_nationality, ""))
                wv = str(worker.get(w_nationality_col, ""))
                if cv.strip():
                    if not match_nationality(cv, wv):
                        continue # Hard Filter: Skip if nationality mismatch
                    total_criteria += 1
                    score += 1
            
            if c_work_nature and (w_job_col or w_other_job_col):
                cv = str(customer_row.get(c_work_nature, ""))
                
                job_val = str(worker.get(w_job_col, "")) if w_job_col else ""
                other_val = str(worker.get(w_other_job_col, "")) if w_other_job_col else ""
                
                if job_val and other_val:
                    wv = f"{job_val} / {other_val}"
                elif job_val:
                    wv = job_val
                elif other_val:
                    wv = other_val
                else:
                    wv = ""

                if cv.strip():
                    if not wv or not match_job(cv, wv):
                        continue # Hard Filter: Skip if job mismatch completely
                    total_criteria += 1
                    score += 1
            
            if c_location and w_city_col:
                cv = str(customer_row.get(c_location, ""))
                wv = str(worker.get(w_city_col, ""))
                if cv.strip():
                    total_criteria += 1
                    
                    # Hierarchical Geographic Matching
                    if _fuzzy_match(wv, cv):
                        geo_tier = 0
                    else:
                        target_reg = _find_city_region(cv)
                        worker_reg = _find_city_region(wv)
                        if target_reg and worker_reg and target_reg == worker_reg:
                            geo_tier = 1
                        elif target_reg and target_reg in REGION_PROXIMITY:
                            ordered = REGION_PROXIMITY[target_reg]
                            if worker_reg in ordered:
                                geo_tier = 2 + ordered.index(worker_reg)
                    
                    if geo_tier < 99:
                        score += 1
            
            if total_criteria > 0 and score >= 1:
                pct = int((score / total_criteria) * 100)
                if geo_tier == 0:
                    city_matches.append(worker)
                    city_scores.append(pct)
                elif geo_tier == 1:
                    region_matches.append(worker)
                    region_scores.append(pct)
                else:
                    # Store geo_tier temporarily for sorting
                    worker_copy = worker.copy()
                    worker_copy['__geo_tier'] = geo_tier
                    other_matches.append(worker_copy)
                    other_scores.append(pct)
        
        # Sort each group by: 1. Score (desc), 2. Geo Tier (for others), 3. Timestamp (desc)
        def get_sort_key(score, worker):
            ts_val = pd.NaT
            if w_timestamp_col:
                raw_ts = str(worker.get(w_timestamp_col, ""))
                clean_ts = raw_ts.replace('م', 'PM').replace('ص', 'AM')
                ts_val = pd.to_datetime(clean_ts, errors='coerce')
            
            gt = worker.get('__geo_tier', 0)
            return (-score, gt, -ts_val.timestamp() if pd.notnull(ts_val) else 0)

        sorted_results = []
        for matches, scores in [(city_matches, city_scores), (region_matches, region_scores), (other_matches, other_scores)]:
            if matches:
                 items = sorted(zip(scores, matches), key=lambda x: get_sort_key(x[0], x[1]))
                 sorted_results.append(([it[1] for it in items], [it[0] for it in items]))
            else:
                 sorted_results.append(([], []))
        
        f_city, f_city_scores = sorted_results[0]
        f_region, f_region_scores = sorted_results[1]
        f_other, f_other_scores = sorted_results[2]
        
        return f_city + f_region + f_other, f_city_scores + f_region_scores + f_other_scores, len(f_city), len(f_region)


    # --- Initialize session state ---
    if 'op_hidden_clients' not in st.session_state:
        st.session_state.op_hidden_clients = set()
    if 'op_hidden_workers' not in st.session_state:
        st.session_state.op_hidden_workers = set()

    # --- Global Unhide ---
    if st.session_state.op_hidden_workers:
        if st.sidebar.button("🔓 " + ("أظهر جميع العمال المخفيين" if lang == 'ar' else "Show all hidden workers")):
            st.session_state.op_hidden_workers.clear()
            st.rerun()

    # --- Helper: build worker table ---
    def build_worker_table(worker_list, score_list):
        rows = []
        filtered_indices = []
        for i, (worker, score) in enumerate(zip(worker_list, score_list)):
            # Unique ID for hiding (using name and phone)
            w_name = str(worker.get(w_name_col, "")) if w_name_col else ""
            w_phone = str(worker.get(w_phone_col, "")) if w_phone_col else ""
            worker_uid = hashlib.md5(f"{w_name}{w_phone}".encode()).hexdigest()
            
            if worker_uid in st.session_state.op_hidden_workers:
                continue
                
            row = {}
            if w_timestamp_col:
                raw_ts = str(worker.get(w_timestamp_col, ""))
                d_part, t_part = "", ""
                pts = raw_ts.split()
                for p in pts:
                    if '/' in p or '-' in p: d_part = p
                    elif ':' in p: t_part = p
                if 'م' in raw_ts: t_part += " م"
                elif 'ص' in raw_ts: t_part += " ص"
                if not d_part and not t_part: d_part = raw_ts
                
                date_key = 'تاريخ التسجيل' if lang == 'ar' else 'Reg. Date'
                time_key = 'وقت التسجيل' if lang == 'ar' else 'Reg. Time'
                row[date_key] = d_part
                row[time_key] = t_part
            
            # --- Replacement: Match Score -> Contract Status ---
            if w_contract_end_col:
                s = ContractManager.calculate_status(worker.get(w_contract_end_col))
                gs = s['status']
                ds = s.get('days', 0)
                if ds is None: ds = 9999
                
                status_text = ""
                if lang == 'ar':
                    if gs == 'expired':
                        status_text = f"❌ منتهي (منذ {abs(ds)} يوم)"
                    elif gs in ['urgent', 'warning']:
                        status_text = f"⚠️ عاجل (متبقى {ds} يوم)"
                    else:
                        status_text = f"✅ ساري (متبقى {ds} يوم)"
                else:
                    status_text = f"{s['label_en']} ({abs(ds)} Days)"
                
                status_key = 'حالة العقد' if lang == 'ar' else 'Contract Status'
                row[status_key] = status_text
            
            # --- Dynamic Fields (All others from the worker database) ---
            priority_cols = [w_timestamp_col, w_contract_end_col]
            for col in worker.index:
                # Skip internal columns and priority columns already handled
                if str(col).startswith('__') or col in priority_cols:
                    continue
                
                translated_header = t_col(col, lang)
                row[translated_header] = str(worker.get(col, ""))
            
            # Internal key for hiding
            row["__uid"] = worker_uid
            rows.append(row)
            filtered_indices.append(i)
            
        return pd.DataFrame(rows), filtered_indices


    def info_cell(icon, label_text, value, color="#F4F4F4", min_width="200px", force_ar=False):
        if not value or str(value).strip().lower() in ["nan", "none", ""]:
            return ""
        
        # Bidirectional translation based on current UI language
        disp_val = auto_translate(str(value), target_lang=lang, force_stay_ar=force_ar)
        
        # Detect if this is a phone/number field for LTR direction
        is_phone_field = any(kw in label_text.lower() for kw in ["phone", "mobile", "جوال", "هاتف", "موبايل"])
        val_direction = 'direction:ltr; unicode-bidi:embed;' if is_phone_field else ''
        
        # Flag Injection: Look for nationality fields
        if any(kw in label_text.lower() for kw in ["nationality", "جنسية"]):
            import re
            
            # Comprehensive name-to-code mapping (both Arabic and English)
            all_names = {
                # Arabic names
                "بنجلاديشي": "BD", "بنغالي": "BD", "بنجالي": "BD", "بنغلاديشي": "BD",
                "نيبالي": "NP", "نيبال": "NP",
                "فلبيني": "PH", "فلبينية": "PH", "الفلبين": "PH",
                "هندي": "IN", "هندية": "IN", "الهند": "IN",
                "مصري": "EG", "مصرية": "EG", "مصر": "EG",
                "باكستاني": "PK", "باكستانية": "PK", "باكستان": "PK",
                "سوداني": "SD", "سودانية": "SD", "السودان": "SD",
                "كيني": "KE", "كينية": "KE", "كينيا": "KE",
                "أوغندي": "UG", "أوغندية": "UG", "أوغندا": "UG",
                "إثيوبي": "ET", "إثيوبية": "ET", "إثيوبيا": "ET",
                "يمني": "YE", "يمنية": "YE", "اليمن": "YE",
                "إندونيسي": "ID", "اندونيسي": "ID", "إندونيسية": "ID", "اندونيسية": "ID", "إندونيسيا": "ID",
                "سريلانكي": "LK", "سريلانكية": "LK",
                # English names
                "bangladeshi": "BD", "bengali": "BD", 
                "nepali": "NP", "nepalese": "NP",
                "filipino": "PH", "filipina": "PH", "philippines": "PH",
                "indian": "IN",
                "egyptian": "EG",
                "pakistani": "PK",
                "sudanese": "SD",
                "kenyan": "KE",
                "ugandan": "UG",
                "ethiopian": "ET",
                "yemeni": "YE",
                "indonesian": "ID",
                "sri lankan": "LK",
            }
            
            # Split by comma only (each nationality = "عربي - English")
            segments = re.split(r'\s*,\s*', disp_val)
            new_segments = []
            
            for seg in segments:
                seg_stripped = seg.strip()
                if not seg_stripped:
                    continue
                
                # Find the FIRST matching nationality in this segment
                matched_code = None
                for name, code in all_names.items():
                    if name.lower() in seg_stripped.lower():
                        matched_code = code
                        break
                
                if matched_code:
                    flag_img = f'<img src="https://flagsapi.com/{matched_code}/flat/24.png" style="height:16px; vertical-align:middle; margin:0 4px 2px 4px;">'
                    new_segments.append(f"{seg_stripped} {flag_img}")
                else:
                    new_segments.append(seg_stripped)
            
            disp_val = " , ".join(new_segments)

        return f'<div style="background: rgba(255,255,255,0.04); padding: 12px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.06); margin: 5px; flex: 1 1 {min_width}; min-height: 80px; display: flex; flex-direction: column; justify-content: center;"><span style="color: #888; font-size: 0.8rem;">{label_text}</span><span style="color: {color}; font-size: 1.1rem; font-weight: 600; margin-top: 4px; {val_direction}">{icon} {disp_val}</span></div>'


    # --- Timestamp column lookup ---
    c_timestamp = find_cust_col(["timestamp"]) or find_cust_col(["الطابع"]) or find_cust_col(["تاريخ"])
    if not c_timestamp and len(customers_df.columns) > 0:
        # Avoid using __sheet_row as the timestamp
        if customers_df.columns[0] == "__sheet_row" and len(customers_df.columns) > 1:
            c_timestamp = customers_df.columns[1]
        else:
            c_timestamp = customers_df.columns[0]

    # --- Container for all requests ---
    st.markdown("### 📋 " + t('customer_requests', lang))
    
    # NEW SEARCH INPUT
    search_lbl = "🔍 بحث عن بطاقة طلب (رقم الجوال أو اسم المسؤول أو موقع العمل)" if lang == 'ar' else "🔍 Search Request (Mobile, Manager or Location)"
    cust_search_q = st.text_input(search_lbl, key="order_processing_cust_search").strip()
    
    # Smart phone normalizer (same logic as SmartSearchEngine)
    def _normalize_phone_op(text):
        arabic_to_western = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
        s = str(text).translate(arabic_to_western)
        digits = re.sub(r'\D', '', s)
        if not digits:
            return ""
        if digits.startswith('00'):
            digits = digits[2:]
        if digits.startswith('966'):
            digits = digits[3:]
        while digits.startswith('0'):
            digits = digits[1:]
        return digits

    def _is_phone_query_op(q):
        arabic_to_western = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
        clean = re.sub(r'[\s\+\-\(\)]', '', str(q)).translate(arabic_to_western)
        return clean.isdigit() and len(clean) >= 5

    # Loop over all customers
    for idx, customer_row in customers_df.iterrows():
        company_val = str(customer_row.get(c_company, "")) if c_company else ""
        responsible_val = str(customer_row.get(c_responsible, "")) if c_responsible else ""
        mobile_val = str(customer_row.get(c_mobile, "")) if c_mobile else ""
        location_val = str(customer_row.get(c_location, "")) if c_location else ""

        if cust_search_q:
            if _is_phone_query_op(cust_search_q):
                # Smart phone search: normalize both query and mobile value
                q_phone = _normalize_phone_op(cust_search_q)
                m_phone = _normalize_phone_op(mobile_val)
                if not (q_phone and q_phone in m_phone):
                    continue
            else:
                # Text search: name or location
                q_lower = cust_search_q.lower()
                match = False
                for val in [responsible_val, location_val, company_val]:
                    if q_lower in val.lower().strip():
                        match = True
                        break
                if not match:
                    continue

        client_key = f"client_{idx}"
        
        # Display name
        display_name = f"{company_val} - {responsible_val}".strip(" -")
        if not display_name: display_name = f"طلب #{idx+1}" if lang == 'ar' else f"Request #{idx+1}"
        
        if client_key in st.session_state.op_hidden_clients:
            continue
            
        # --- Single Customer Section ---
        with st.container():
            # Header with White Neon Glow Frame integrated
            user_role = st.session_state.user.get("role")
            display_title = f"🏢 {company_val}" if user_role != "viewer" else '<span class="mobile-neon-text">🏢 ' + ("طلبات العملاء" if lang == "ar" else "Customer Requests") + '</span>'
            
            # Start Neon Frame and Header (Static CSS to avoid mobile lag)
            st.markdown(f"""
<div style="border: 1.5px solid rgba(255, 255, 255, 0.4); border-radius: 18px; padding: 15px; margin: 15px 0; background: rgba(10, 14, 26, 0.6); box-shadow: 0 0 10px rgba(255, 255, 255, 0.2); direction: rtl;">
    <div style="background: linear-gradient(90deg, rgba(255,255,255,0.1), transparent); 
                padding: 12px 20px; border-radius: 12px; border-right: 5px solid #FFFFFF; margin: 0 0 15px 0;
                box-shadow: 0 0 12px rgba(255,255,255,0.2);">
        <h3 style="color: #FFFFFF; margin: 0; font-family: 'Tajawal', sans-serif; text-shadow: 0 0 8px rgba(255,255,255,0.5);">
            {display_title} <span style="font-size: 0.8rem; color: #888;">#{idx+1}</span>
        </h3>
    </div>
""", unsafe_allow_html=True)
            
            # Info Grid (Flexbox) - Removing all indentation from strings to avoid markdown code-block triggers
            info_html = '<div style="display: flex; flex-wrap: wrap; gap: 0; width: 100%;">'
            
            # --- Standard Fields ---
            if c_timestamp:
                raw_ts = str(customer_row.get(c_timestamp, ""))
                date_part = ""
                time_part = ""
                parts = raw_ts.split()
                for p in parts:
                    if '/' in p or '-' in p: date_part = p
                    elif ':' in p: time_part = p
                if 'م' in raw_ts: time_part += " م"
                elif 'ص' in raw_ts: time_part += " ص"
                if not date_part and not time_part: date_part = raw_ts

                if date_part:
                    info_html += info_cell("📅", "تاريخ الطلب" if lang == 'ar' else "Order Date", date_part)
                if time_part:
                    info_html += info_cell("⏰", "وقت الطلب" if lang == 'ar' else "Order Time", time_part)
            
            info_html += info_cell("📍", t('work_location', lang), str(customer_row.get(c_location, "")), force_ar=True)
            info_html += info_cell("💼", t('work_nature', lang), str(customer_row.get(c_work_nature, "")))
            info_html += info_cell("👤", t('responsible_name', lang), responsible_val)
            info_html += info_cell("👥", t('required_category', lang), str(customer_row.get(c_category, "")))
            info_html += info_cell("🔢", t('num_employees', lang), str(customer_row.get(c_num_emp, "")), "#D4AF37")
            
            if user_role != "viewer":
                info_html += info_cell("📱", t('mobile_number', lang), str(customer_row.get(c_mobile, "")))
            else:
                info_html += info_cell("🔒", t('mobile_number', lang), "********")
                
            info_html += info_cell("💰", t('expected_salary', lang), str(customer_row.get(c_salary, "")), "#00FF41")
            info_html += info_cell("⏳", t('working_hours', lang), str(customer_row.get(c_working_hours, "")))
            info_html += info_cell("🗓️", t('weekly_holiday', lang), str(customer_row.get(c_weekly_holiday, "")))
            info_html += info_cell("🔄", t('transfer_days_after', lang), str(customer_row.get(c_transfer_days, "")))
            
            # --- Additional Info ---
            info_html += info_cell("🌍", t('required_nationality', lang), str(customer_row.get(c_nationality, "")))
            
            # Special Notes field with larger min-width
            info_html += info_cell("📝", t('additional_notes', lang), str(customer_row.get(c_notes, "")), min_width="350px")
            
            info_html += "</div>"
            
            # Use two main columns for info and actions
            main_col, action_col = st.columns([9, 1])
            with main_col:
                st.markdown(info_html, unsafe_allow_html=True)
            
            with action_col:
                if user_role != "viewer":
                    st.markdown('<div style="margin-top: 5px;"></div>', unsafe_allow_html=True)
                    # Activate Toggle (Visual only for now or session state)
                    is_active = st.toggle("✅ تفعيل" if lang == 'ar' else "✅ Activate", key=f"active_{idx}", value=True)
                    
                    st.markdown('<div style="margin-top: 20px;"></div>', unsafe_allow_html=True)
                    
                    # Delete with confirmation (Permission check)
                    user_perms = st.session_state.user.get('permissions', [])
                    if "can_delete" in user_perms or "all" in user_perms:
                        with st.popover("🗑️ حذف" if lang == 'ar' else "🗑️ Delete"):
                            st.warning("⚠️ هل أنت متأكد من حذف هذا الطلب نهائياً؟" if lang == 'ar' else "⚠️ Delete this request permanently?")
                            if st.button("نعم، حذف" if lang == 'ar' else "Yes, Delete", key=f"del_cust_{idx}", type="primary", use_container_width=True):
                                # Get sheet row from hidden __sheet_row column
                                row_num = customer_row.get('__sheet_row')
                                if row_num:
                                    url = "https://docs.google.com/spreadsheets/d/1ZlLGXqbFSnKrr2J-PRnxRhxykwrNOgOE6Mb34Zei_FU/edit"
                                    success = st.session_state.db.delete_row(row_num, url=url)
                                    if success:
                                        show_toast("✅ تم حذف الطلب بنجاح" if lang == 'ar' else "✅ Request deleted successfully", "success")
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        st.error("فشل الحذف" if lang == 'ar' else "Delete failed")
                                else:
                                    st.error("تعذر تحديد رقم الصف" if lang == 'ar' else "Could not determine row number")
                    else:
                        st.caption("🔒 لا تملك صلاحية الحذف" if lang == 'ar' else "🔒 No delete permission")
                else:
                    st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)
                    st.caption("🔒 وضع المشاهد" if lang == 'ar' else "🔒 Viewer Mode")

            # Close the White Neon Glow Frame integrated
            st.markdown("</div>", unsafe_allow_html=True)

            # --- Workers ---
            matches, scores, city_count, region_count = find_matching_workers(customer_row)
            
            if not matches:
                st.warning("⚠️ " + t('no_matching_workers', lang))
            else:
                city_list = matches[:city_count]
                region_list = matches[city_count : city_count + region_count]
                other_list = matches[city_count + region_count :]
                
                city_scores = scores[:city_count]
                region_scores = scores[city_count : city_count + region_count]
                other_scores = scores[city_count + region_count :]

                # Segment Header Helper
                def render_segment_header(label, count, color="#D4AF37", explainer=None):
                    st.markdown(f"""<div style="color: {color}; font-weight: 700; margin: 15px 5px 5px 5px; font-family: 'Cairo', sans-serif;">{label} — {count}</div>""", unsafe_allow_html=True)
                    if explainer:
                        st.markdown(f"""<div style="font-size: 0.85rem; color: #888; margin-top: -5px; margin-bottom: 10px; margin-left: 10px; font-family: 'Cairo', sans-serif;">{explainer}</div>""", unsafe_allow_html=True)

                # Same City Table
                if city_list:
                    city_df, city_idx_map = build_worker_table(city_list, city_scores)
                    if not city_df.empty:
                        # Export
                        c_op_2 = st.columns([4, 1])[1]
                        with c_op_2:
                            xl_data_op = create_pasha_whatsapp_excel(city_df, lang=lang)
                            if xl_data_op:
                                _, xl_df_op = xl_data_op
                                btn_exp = "📤 " + ("تصدير للواتساب" if lang == 'ar' else "Export to WhatsApp")
                                render_pasha_export_button(xl_df_op, btn_exp, f"Matched_Workers_City_{idx+1}.xlsx", 
                                                          f"Matched_Workers_City_{idx+1}", key=f"dl_op_city_{idx}")
                        
                        loc_val = str(customer_row.get(c_location, ""))
                        label = f"📍 عمال في نفس المدينة ({loc_val})" if lang == 'ar' else f"📍 Workers in the same city ({loc_val})"
                        render_segment_header(label, len(city_df), color="#D4AF37")
                        
                        col_cfg_city = {}
                        nat_col_city = None
                        for col in city_df.columns:
                            if any(kw in str(col).lower() for kw in ["nationality", "الجنسية"]):
                                nat_col_city = col
                                col_cfg_city[f"🚩_{col}"] = st.column_config.ImageColumn(t("country_label", lang), width="small", pinned=True)

                        st.markdown("<br>", unsafe_allow_html=True)
                        city_df = render_table_translator(city_df, key_prefix=f"op_city_{idx}")
                        
                        city_styled = style_df(city_df.drop(columns=["__uid"]))
                        
                        df_city_height = min((len(city_df) + 1) * 35 + 40, 500)
                        event_city = st.dataframe(
                            city_styled,
                            use_container_width=False, hide_index=True, on_select="rerun",
                            selection_mode="single-row", column_config=__apply_pinned_columns(city_styled, col_cfg_city),
                            key=f"op_city_table_{idx}", height=df_city_height
                        )
                        
                        if event_city.selection and event_city.selection.get("rows"):
                            sel_idx = event_city.selection["rows"][0]
                            worker_row = city_list[city_idx_map[sel_idx]]
                            worker_uid = city_df.iloc[sel_idx]["__uid"]
                            render_cv_detail_panel(worker_row, sel_idx, lang, key_prefix=f"op_city_{idx}", worker_uid=worker_uid)

                if region_list:
                    reg_df, reg_idx_map = build_worker_table(region_list, region_scores)
                    if not reg_df.empty:
                        c_reg_2 = st.columns([4, 1])[1]
                        with c_reg_2:
                            xl_reg = create_pasha_whatsapp_excel(reg_df, lang=lang)
                            if xl_reg:
                                _, xl_df_reg = xl_reg
                                btn_exp = "📤 " + ("تصدير للواتساب" if lang == 'ar' else "Export to WhatsApp")
                                render_pasha_export_button(xl_df_reg, btn_exp, f"Region_Match_{idx+1}.xlsx", 
                                                          f"Region_Match_{idx+1}", key=f"dl_op_reg_{idx}")
                        
                        loc_val = str(customer_row.get(c_location, ""))
                        target_region_name = _find_city_region(loc_val) or loc_val
                        if lang != "ar":
                            target_region_name = {
                                "الشمالية": "Northern Region", "الغربية": "Western Region",
                                "الشرقية": "Eastern Province", "الوسطى": "Central Region",
                                "الجنوبية": "Southern Region"
                            }.get(target_region_name, target_region_name)
                        label = f"🏘️ عمال في المنطقة ({target_region_name})" if lang == 'ar' else f"🏘️ Workers in the Region ({target_region_name})"
                        explainer = f"{'هؤلاء العمال في مدن تتبع لنفس المنطقة ولاكن في مدن اخرى' if lang == 'ar' else 'These workers are in other cities within the same region'}"
                        render_segment_header(label, len(reg_df), color="#D4AF37", explainer=explainer)

                        st.markdown("<br>", unsafe_allow_html=True)
                        reg_df = render_table_translator(reg_df, key_prefix=f"op_reg_{idx}")
                        
                        col_cfg_reg = {}
                        nat_col_reg = None
                        for col in reg_df.columns:
                            if any(kw in str(col).lower() for kw in ["nationality", "الجنسية"]):
                                nat_col_reg = col
                                col_cfg_reg[f"🚩_{col}"] = st.column_config.ImageColumn(t("country_label", lang), width="small", pinned=True)

                        reg_styled = style_df(reg_df.drop(columns=["__uid"]))
                        
                        df_reg_h = min((len(reg_df) + 1) * 35 + 40, 400)
                        ev_reg = st.dataframe(
                            reg_styled,
                            use_container_width=True, hide_index=True, on_select="rerun",
                            selection_mode="single-row", column_config=__apply_pinned_columns(reg_styled, col_cfg_reg),
                            key=f"op_reg_table_{idx}", height=df_reg_h
                        )
                        if ev_reg.selection and ev_reg.selection.get("rows"):
                             sel_idx = ev_reg.selection["rows"][0]
                             w_row = region_list[reg_idx_map[sel_idx]]
                             w_uid = reg_df.iloc[sel_idx]["__uid"]
                             render_cv_detail_panel(w_row, sel_idx, lang, key_prefix=f"op_reg_{idx}", worker_uid=w_uid)


                # Other Cities Table
                if other_list:
                    other_df, other_idx_map = build_worker_table(other_list, other_scores)
                    if not other_df.empty:
                        # Export Section
                        exp_oth_col = st.columns([4, 1])[1]
                        with exp_oth_col:
                            xl_oth_data = create_pasha_whatsapp_excel(other_df, lang=lang)
                            if xl_oth_data:
                                _, xl_oth_df = xl_oth_data
                                btn_exp_lbl = "📤 " + ("تصدير للواتساب" if lang == 'ar' else "Export to WhatsApp")
                                render_pasha_export_button(xl_oth_df, btn_exp_lbl, f"Workers_Other_Cities_{idx+1}.xlsx", 
                                                          f"Other_Cities_Table_{idx+1}", key=f"btn_xl_oth_stable_{idx}")

                        label_other = "🌍 عمال في مدن أخرى (مرتبين حسب القرب)" if lang == 'ar' else f"🌍 Workers in other cities (sorted by proximity)"
                        render_segment_header(label_other, len(other_df), color="#FFFFFF")
                        
                        col_cfg_other = {}
                        for col in other_df.columns:
                            if any(kw in str(col).lower() for kw in ["nationality", "الجنسية"]):
                                col_cfg_other[f"🚩_{col}"] = st.column_config.ImageColumn(t("country_label", lang), width="small", pinned=True)

                        other_df = render_table_translator(other_df, key_prefix=f"op_other_{idx}")
                        other_styled = style_df(other_df.drop(columns=["__uid"]))
                        
                        df_oth_h = min((len(other_df) + 1) * 35 + 40, 400)
                        ev_oth = st.dataframe(
                            other_styled, 
                            use_container_width=True, hide_index=True, on_select="rerun",
                            selection_mode="single-row", column_config=__apply_pinned_columns(other_styled, col_cfg_other),
                            key=f"op_other_table_{idx}", height=df_oth_h
                        )
                        if ev_oth.selection and ev_oth.selection.get("rows"):
                             sel_idx = ev_oth.selection["rows"][0]
                             w_row = other_list[other_idx_map[sel_idx]]
                             w_uid = other_df.iloc[sel_idx]["__uid"]
                             render_cv_detail_panel(w_row, sel_idx, lang, key_prefix=f"op_other_{idx}", worker_uid=w_uid)


            # --- Hide Request Button (Admin Only) ---
            if st.session_state.user.get("role") == "admin":
                if st.button("🚫 " + ("إخفاء هذا الطلب" if lang == 'ar' else "Hide this request"), key=f"hide_req_{idx}"):
                    st.session_state.op_hidden_clients.add(client_key)
                    st.rerun()
            st.divider()

def render_duplicate_remover_content():
    lang = st.session_state.lang
    is_ar = lang == 'ar'
    st.title("🗑️ " + t('duplicate_remover', lang))
    
    st.markdown(f"""
    <div style="background: rgba(255,255,255,0.02); padding: 20px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.05); margin-bottom: 20px;">
        <h4 style="color: #D4AF37; margin-bottom: 15px;">{'تعليمات الأداة' if is_ar else 'Tool Instructions'}</h4>
        <ul style="color: #CCC; font-size: 0.95rem;">
            <li>{'ارفع ملف أو عدة ملفات إكسل بصيغة .xlsx' if is_ar else 'Upload one or more Excel files (.xlsx)'}</li>
            <li>{'سيقوم النظام بدمج الملفات وحذف الصفوف المكررة تماماً' if is_ar else 'The system will merge files and remove duplicate rows'}</li>
            <li>{'يمكنك اختيار عمود معين ليتم الحذف بناءً عليه (مثل رقم الجوال)' if is_ar else 'You can select a specific column to base the removal on (e.g. Mobile Number)'}</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader(t("upload_file_label", lang), type=["xlsx"], accept_multiple_files=True, key="dupe_rem_up")
    
    if uploaded_files:
        # Load all data
        combined_df = pd.DataFrame()
        with st.status("📁 " + ("جاري قراءة الملفات..." if is_ar else "Reading files...")) as status:
            for uploaded_file in uploaded_files:
                try:
                    df = pd.read_excel(uploaded_file)
                    combined_df = pd.concat([combined_df, df], ignore_index=True)
                    st.write(f"✅ {uploaded_file.name} ({len(df)} " + ("صف" if is_ar else "rows") + ")")
                except Exception as e:
                    st.error(f"❌ Error loading {uploaded_file.name}: {e}")
            
            if not combined_df.empty:
                status.update(label=("تم تحميل البيانات" if is_ar else "Data loaded"), state="complete")
        
        if not combined_df.empty:
            st.divider()
            
            # Options
            st.subheader("⚙️ " + ("إعدادات التصفية" if is_ar else "Filter Settings"))
            
            # Let user pick column or ALL
            all_cols_option = "كل الأعمدة (تطابق كامل)" if is_ar else "All Columns (Exact Match)"
            options = [all_cols_option] + list(combined_df.columns)
            
            col_to_check = st.selectbox(
                "اختر العمود الأساسي للبحث عن المكرر" if is_ar else "Select base column for duplicate search",
                options=options,
                index=0
            )

            # --- Professional Cleaning Rules Toggle ---
            st.markdown("---")
            st.markdown(f"#### 🧹 {'الفلترة والتدقيق الاحترافي' if is_ar else 'Professional Filtering & Validation'}")
            do_pro_clean = st.checkbox(
                "تطبيق قواعد التدقيق (رقم الإقامة 10 أرقام + الجوال 12 رقم)" if is_ar else "Apply Validation Rules (Iqama 10-digits + Phone 12-digits max)",
                value=True,
                help="سيتم حذف الأسطر الفارغة، الرموز، النصوص، والأرقام غير الصالحة تلقائياً." if is_ar else "Automatically removes empty rows, symbols, text, and invalid numbers."
            )
            
            smart_normalize = False
            if col_to_check != all_cols_option and not do_pro_clean:
                # If it's a phone column, offer smart normalization (only if pro clean is off)
                if any(kw in str(col_to_check).lower() for kw in ["phone", "mobile", "جوال", "هاتف", "واتساب"]):
                    smart_normalize = st.checkbox(
                        "استخدام تنظيف الأرقام الذكي (لدمج الأرقام بصيغ مختلفة)" if is_ar else "Use Smart Phone Normalization",
                        value=True
                    )
            
            if st.button("🚀 " + ("بدء المعالجة" if is_ar else "Start Processing"), type="primary", use_container_width=True):
                original_count = len(combined_df)
                import re
                
                with st.status("⏳ " + ("جاري معالجة وتدقيق البيانات..." if is_ar else "Processing & Validating...")) as status:
                    # Internal Working DF
                    data = combined_df.copy()
                    
                    # Pre-clean: Remove completely empty rows
                    data = data.dropna(how='all')
                    
                    if do_pro_clean:
                        # 1. Identify Key Columns with better matching
                        iqama_keywords = ["رقم الاقامة", "رقم الإقامة", "iqama", "رقم الهوية", "national id"]
                        phone_keywords = ["رقم الهاتف", "جوال", "mobile", "phone", "whatsapp", "واتساب", "رقم الجوال"]
                        
                        iqama_col = next((c for c in data.columns if any(k in str(c).lower().strip() for k in iqama_keywords)), None)
                        phone_col = next((c for c in data.columns if any(k in str(c).lower().strip() for k in phone_keywords)), None)
                        
                        def clean_iqama(val):
                            if pd.isna(val) or str(val).strip() == "": return None
                            # Keep only Western digits (0-9)
                            s_val = str(val)
                            # Convert Arabic digits to Western
                            arabic_to_western = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
                            digits = s_val.translate(arabic_to_western)
                            # Remove EVERYTHING that is not a digit (removes Arabic/English text, symbols)
                            digits = re.sub(r'[^\d]', '', digits)
                            # Rule: Min 10 digits
                            if len(digits) < 10: return None
                            return digits

                        def clean_phone_val(val):
                            from src.utils.phone_utils import format_phone_number
                            if pd.isna(val) or str(val).strip() == "": return None
                            formatted = format_phone_number(val)
                            if not formatted: return None
                            # Rule: Delete if digits after + exceeds 12
                            after_plus = formatted.replace("+", "")
                            if len(after_plus) > 12: return None
                            return formatted

                        # Apply Rules & Remove Invalid Rows
                        if iqama_col:
                            st.write(f"🔍 {'تنظيف عمود الإقامة' if is_ar else 'Cleaning Iqama column'}: `{iqama_col}`")
                            data[iqama_col] = data[iqama_col].apply(clean_iqama)
                            data = data.dropna(subset=[iqama_col])
                        
                        if phone_col:
                            st.write(f"📱 {'تنظيف عمود الجوال' if is_ar else 'Cleaning Phone column'}: `{phone_col}`")
                            data[phone_col] = data[phone_col].apply(clean_phone_val)
                            data = data.dropna(subset=[phone_col])
                        
                        # After cleaning, if col_to_check is the identified primary column, keep it. 
                        # Otherwise, if "All Columns" is selected but we have a strong ID column, use it for smarter deduplication.
                        dedup_subset = None
                        if col_to_check == all_cols_option:
                            if iqama_col: dedup_subset = [iqama_col]
                            elif phone_col: dedup_subset = [phone_col]
                        else:
                            dedup_subset = [col_to_check]
                        
                        if dedup_subset:
                            clean_df = data.drop_duplicates(subset=dedup_subset, keep='first')
                        else:
                            clean_df = data.drop_duplicates()
                    else:
                        # Standard handling without pro-cleaning
                        if col_to_check == all_cols_option:
                            clean_df = data.drop_duplicates()
                        else:
                            if smart_normalize:
                                from src.utils.phone_utils import format_phone_number
                                norm_col = "__norm_check"
                                data[norm_col] = data[col_to_check].apply(lambda x: format_phone_number(str(x)))
                                clean_df = data.drop_duplicates(subset=[norm_col], keep='first').drop(columns=[norm_col])
                            else:
                                clean_df = data.drop_duplicates(subset=[col_to_check], keep='first')
                    
                    status.update(label=("تم الانتهاء من المعالجة" if is_ar else "Processing complete"), state="complete")
                
                removed_count = original_count - len(clean_df)
                
                # Show Results
                if removed_count > 0:
                    st.success(f"🎊 {('تم الانتهاء! تم حذف' if is_ar else 'Done! Removed')} **{removed_count}** {('سجل مكرر.' if is_ar else 'duplicates.')}")
                else:
                    st.info("✅ " + ("لم يتم العثور على أي سجل مكرر." if is_ar else "No duplicates found."))
                
                # Stats
                c1, c2, c3 = st.columns(3)
                c1.metric("📊 " + ("الإجمالي الأصلي" if is_ar else "Original Total"), original_count)
                c2.metric("✂️ " + ("المكرر المحذوف" if is_ar else "Duplicates Removed"), removed_count)
                c3.metric("✨ " + ("الإجمالي النظيف" if is_ar else "Clean Total"), len(clean_df))
                
                # Download
                st.divider()
                st.markdown("### ⬇️ " + ("تحميل الملف المنظف" if is_ar else "Download Cleaned File"))
                
                from src.utils.phone_utils import render_pasha_export_button
                fn = f"Cleaned_Data_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
                render_pasha_export_button(clean_df, "📤 " + ("تحميل الملف الآن" if is_ar else "Download Now"), fn, "Cleaned_File", key="download_cleaned")

def render_bengali_supply_content():
    lang = st.session_state.lang
    bm = BengaliDataManager()
    # High-quality flag image for the title
    flag_url = "https://flagsapi.com/BD/flat/64.png"
    flag_html = f'<img src="{flag_url}" style="height:40px; vertical-align:middle; margin-bottom:10px; margin-left:10px;">'
    st.markdown(f'<div class="luxury-main-title">{flag_html} {t("bengali_supply_title", lang)}</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs([t("form_supplier_employer", lang), t("form_worker_details", lang), t("search_manage_title", lang)])
    
    with tab1:
        st.markdown(f'### 🏗️ {t("form_supplier_employer", lang)}')
        col1, col2 = st.columns(2)
        with col1:
            with st.container(border=True):
                st.markdown(f"#### 👤 {t('supplier_name', lang)}")
                with st.form("b_sup_f_final", clear_on_submit=True):
                    s_name = st.text_input(t("supplier_name", lang))
                    s_phone = st.text_input(t("supplier_phone", lang))
                    s_notes = st.text_area(t("general_notes", lang), key="s_notes_input")
                    if st.form_submit_button(t("add_supplier_btn", lang), use_container_width=True):
                        if s_name:
                            bm.add_supplier({"name": s_name, "phone": s_phone, "notes": s_notes})
                            st.success("✅ " + ("تم إضافة المورد بنجاح" if lang == 'ar' else "Supplier added"))
                            time.sleep(1)
                            st.rerun()
        with col2:
            with st.container(border=True):
                st.markdown(f"#### 🏢 {t('employer_name', lang)}")
                with st.form("b_emp_f_final", clear_on_submit=True):
                    e_name = st.text_input(t("employer_name", lang))
                    e_mobile = st.text_input(t("employer_mobile", lang))
                    e_cafe = st.text_input(t("cafe_name", lang))
                    e_city = st.text_input(t("city", lang))
                    e_notes = st.text_area(t("general_notes", lang), key="e_notes_input")
                    if st.form_submit_button(t("add_supplier_btn", lang), use_container_width=True):
                        if e_name:
                            bm.add_employer({"name": e_name, "cafe": e_cafe, "mobile": e_mobile, "city": e_city, "notes": e_notes})
                            st.success("✅ " + ("تم إضافة صاحب العمل بنجاح" if lang == 'ar' else "Employer added"))
                            time.sleep(1)
                            st.rerun()

    with tab2:
        st.markdown(f'### 👷 {t("form_worker_details", lang)}')
        all_s = bm.get_suppliers()
        all_e = bm.get_employers()
        s_opts = [f"{s['name']} ({s['phone']})" for s in all_s]
        e_opts = [f"{e['name']} - {e.get('cafe','')} ({e.get('city','')})" for e in all_e]
        
        if not s_opts or not e_opts:
            st.warning("⚠️ " + ("يرجى إضافة مورد وصاحب عمل أولاً في التبويب الأول" if lang == 'ar' else "Please add a supplier and employer first"))
        else:
            mode = st.radio(t("entry_method", lang), [t("by_details", lang), t("by_count", lang)], horizontal=True)
            with st.form("b_worker_f_final", clear_on_submit=True):
                if mode == t("by_details", lang):
                    w_name = st.text_input(t("worker_name", lang))
                    w_id = st.text_input(t("worker_passport_iqama", lang))
                    is_batch, w_count = False, 1
                else:
                    w_count = st.number_input(t("worker_count", lang), 1, 1000, 1)
                    w_name = f"{w_count} عمال (بدون أسماء)" if lang == 'ar' else f"{w_count} Workers (Batch)"
                    w_id, is_batch = "-", True
                
                sel_s = st.selectbox(t("select_supplier", lang), s_opts)
                sel_e = st.selectbox(t("select_employer", lang), e_opts)

                # Automatic Day and Date (Insertion Date)
                now = datetime.now(SAUDI_TZ)
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    day_name = now.strftime("%A")
                    days_ar = {"Monday": "الاثنين", "Tuesday": "الثلاثاء", "Wednesday": "الأربعاء", "Thursday": "الخميس", "Friday": "الجمعة", "Saturday": "السبت", "Sunday": "الأحد"}
                    display_day = days_ar.get(day_name, day_name) if lang == 'ar' else day_name
                    st.text_input(t("day_label", lang), value=display_day, disabled=True)
                with col_d2:
                    current_date_val = now.date()
                    # To allow override if needed, but the user asked for automatic.
                    # I'll keep it as a value that's saved.
                    st.text_input(t("insertion_date", lang), value=current_date_val.strftime("%Y-%m-%d"), disabled=True)

                notes = st.text_area(t("general_notes", lang))
                
                if st.form_submit_button(t("add_worker_btn", lang), use_container_width=True):
                    bm.add_worker({
                        "name": w_name, "id": w_id, "supplier": sel_s, "employer": sel_e,
                        "general_notes": notes, "is_headcount": is_batch, "headcount": w_count,
                        "timestamp": get_saudi_time().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    st.success("✅ " + ("تم إضافة بيانات العامل/العدد بنجاح!" if lang == 'ar' else "Saved successfully!"))
                    time.sleep(1)
                    st.rerun()




    with tab3:
        st.markdown(f"### 🔍 {t('search_manage_title', lang)}")
        
        all_workers = bm.get_workers()
        all_suppliers = bm.get_suppliers()
        all_employers = bm.get_employers()
        
        # 1. Global Search Box at the Top
        col_s1, col_s2 = st.columns([4, 1])
        with col_s1:
            g_search = st.text_input("🔍 " + t("search_placeholder_bengali", lang), key="master_search_bengali")
        with col_s2:
            st.write(""); st.write("")
            def clear_master_search():
                st.session_state.master_search_bengali = ""
            
            st.button("🔄", use_container_width=True, help="تفريغ البحث", on_click=clear_master_search)

        # 2. Filter All Data first for Counts
        if g_search:
            g_s = g_search.lower()
            matched_w = [w for w in all_workers if g_s in str(w).lower()]
            matched_s = [s for s in all_suppliers if g_s in str(s).lower()]
            matched_e = [e for e in all_employers if g_s in str(e).lower()]
            
            s_names = {s['name'].strip() for s in matched_s}
            e_names = {e['name'].strip() for e in matched_e}
            
            for w in matched_w:
                w_s = w.get('supplier', '')
                if '(' in w_s: s_names.add(w_s.split('(')[0].strip())
                else: s_names.add(w_s.strip())
                
                w_e = w.get('employer', '')
                if '-' in w_e: e_names.add(w_e.split('-')[0].strip())
                else: e_names.add(w_e.strip())

            filtered_w = []
            for w in all_workers:
                w_s = w.get('supplier', '')
                w_s_clean = w_s.split('(')[0].strip() if '(' in w_s else w_s.strip()
                w_e = w.get('employer', '')
                w_e_clean = w_e.split('-')[0].strip() if '-' in w_e else w_e.strip()
                if w in matched_w or w_s_clean in s_names or w_e_clean in e_names:
                    if w not in filtered_w: filtered_w.append(w)
                    
            filtered_s = []
            for s in all_suppliers:
                if s in matched_s or s['name'].strip() in s_names:
                    filtered_s.append(s)
            
            filtered_e = []
            for e in all_employers:
                if e in matched_e or e['name'].strip() in e_names:
                    filtered_e.append(e)
                    
            ar_msg = f"📊 نتائج البحث المترابطة: {len(filtered_w)} عمال، {len(filtered_s)} موارد، {len(filtered_e)} أصحاب عمل."
            en_msg = f"📊 Cross-Referenced Results: {len(filtered_w)} Workers, {len(filtered_s)} Suppliers, {len(filtered_e)} Employers."
            st.info(ar_msg if lang == 'ar' else en_msg)
        else:
            filtered_w, filtered_s, filtered_e = all_workers, all_suppliers, all_employers

        # 3. Tabs for Categories with Counts
        m_t1, m_t2, m_t3 = st.tabs([
            f"👷 {t('workers_tab', lang)} ({len(filtered_w)})", 
            f"📦 {t('suppliers_tab', lang)} ({len(filtered_s)})", 
            f"🏢 {t('employers_tab', lang)} ({len(filtered_e)})"
        ])
        
        can_edit_delete = True 
        
        with m_t1:
            st.markdown(f"#### 👷 {t('workers_tab', lang)}")
            
            if not filtered_w:
                st.info("⚠️ " + t("no_results", lang))
            else:
                for w in reversed(filtered_w):
                    w_uuid = w.get('worker_uuid')
                    with st.container(border=True):
                        # Modern Header
                        c1, c2, c3 = st.columns([2, 2, 1])
                        c1.markdown(f"**👤 {w.get('name')}**")
                        c2.markdown(f"**📦 {w.get('supplier')}**")
                        
                        # Calculation for Days Passed
                        try:
                            t_str = w.get('timestamp','')
                            if t_str and " " in t_str:
                                # Parse without timezone then attach SAUDI_TZ if original was naive (or just compare naively)
                                entry_dt = datetime.strptime(t_str, "%Y-%m-%d %H:%M:%S")
                                # Compare dates only
                                now_dt = get_saudi_time().replace(tzinfo=None)
                                days_diff = (now_dt.date() - entry_dt.date()).days
                                
                                if days_diff <= 0:
                                    days_text = f"🟢 {t('today_label', lang)}"
                                else:
                                    days_text = f"⏳ {days_diff} {t('days_passed_label', lang)}"
                            else:
                                days_text = "-"
                        except:
                            days_text = "-"
                            
                        c3.markdown(f"**{days_text}**")
                        # Detail Reveal
                        with st.expander(t("details_label", lang)):
                            sc1, sc2 = st.columns(2)
                            with sc1:
                                st.write(f"🆔 **ID:** {w.get('id')}")
                                if w.get('mobile'): st.write(f"📱 **Mobile:** {w.get('mobile')}")
                                
                                lbl = "الوقت المنقضي" if lang == 'ar' else "Time Passed"
                                st.write(f"⏱️ **{lbl}:** {days_text}")
                            
                            st.markdown("---")
                            det1, det2 = st.columns(2)
                            
                            s_match = next((s for s in all_suppliers if w.get('supplier', '').startswith(s.get('name', ''))), None)
                            e_match = next((e for e in all_employers if w.get('employer', '').startswith(e.get('name', ''))), None)
                            
                            with det1:
                                st.markdown("**(📦) " + ("بيانات المورد الكاملة" if lang == 'ar' else "Full Supplier Details") + "**")
                                if s_match:
                                    st.write(f"👤 {s_match.get('name', '-')}")
                                    st.write(f"📞 {s_match.get('phone', '')}")
                                    if s_match.get('notes'): st.markdown(f"> 📝 {s_match['notes']}")
                                else:
                                    st.write(w.get('supplier', '-'))
                                    
                            with det2:
                                st.markdown("**(🏢) " + ("بيانات صاحب العمل الكاملة" if lang == 'ar' else "Full Employer Details") + "**")
                                if e_match:
                                    st.write(f"👤 {e_match.get('name', '-')}")
                                    st.write(f"☕ {e_match.get('cafe', '')}")
                                    st.write(f"📍 {e_match.get('city', '')} | 📱 {e_match.get('mobile', '')}")
                                    if e_match.get('notes'): st.markdown(f"> 📝 {e_match['notes']}")
                                else:
                                    st.write(w.get('employer', '-'))
                            
                            if w.get('general_notes'):
                                st.info(f"📝 {w['general_notes']}")
                            

                            # Actions
                            ac1, ac2, ac3 = st.columns(3)
                            with ac1:
                                with st.popover("✏️ " + t("edit_btn", lang), use_container_width=True):
                                    with st.form(f"edit_w_{w_uuid}"):
                                        new_name = st.text_input("Name", w.get('name'))
                                        new_id = st.text_input("ID", w.get('id'))
                                        if st.form_submit_button("💾 "+ t("save_btn", lang)):
                                            w.update({"name": new_name, "id": new_id})
                                            bm.save_data()
                                            st.rerun()
                            with ac2:
                                # Return Logic (Decrements headcount or deletes)

                                if "headcount" in w:
                                    with st.popover("🔄 " + t("return_btn", lang), use_container_width=True):
                                        st.write(f"Current Count: {w['headcount']}")
                                        ret_amt = st.number_input("Return Amount", min_value=1, max_value=int(w['headcount']), value=1, key=f"ret_amt_{w_uuid}")
                                        if st.button("Confirm Return", key=f"conf_ret_{w_uuid}", use_container_width=True, type="primary"):
                                            bm.return_worker(w_uuid, ret_amt)
                                            st.success("✅ Success")
                                            st.rerun()
                                else:
                                    if st.button("🔄 " + t("return_btn", lang), key=f"ret_indiv_{w_uuid}", use_container_width=True):
                                        bm.return_worker(w_uuid)
                                        st.rerun()


                            with ac3:
                                if can_edit_delete:
                                    with st.popover("🗑️ " + t("delete_btn_sm", lang), use_container_width=True):
                                        st.write("هل أنت متأكد من الحذف؟" if lang == 'ar' else "Are you sure?")
                                        if st.button("تأكيد الحذف 🗑️" if lang == 'ar' else "Confirm Delete 🗑️", key=f"del_w_{w_uuid}", use_container_width=True, type="primary"):
                                            bm.delete_worker(w_uuid)
                                            st.rerun()


        with m_t2:
            st.markdown(f"#### 📦 {t('suppliers_tab', lang)}")
            
            if not filtered_s:
                st.info("⚠️ " + t("no_results", lang))
            
            for s in filtered_s:
                with st.container(border=True):
                    sc1, sc2, sc3 = st.columns([2, 2, 1])
                    sc1.markdown(f"**📦 {s.get('name')}**")
                    sc2.markdown(f"📞 {s.get('phone')}")
                    
                    s_w_count = sum(int(w.get('headcount', 1)) if 'headcount' in w else 1 for w in all_workers if w.get('supplier', '').startswith(s.get('name', '')))
                    lbl = "إجمالي العمال المرتبطين" if lang == 'ar' else "Total Workers Associated"
                    st.info(f"👥 **{lbl}: {s_w_count}**")
                    
                    if s.get('notes'):
                        st.write(f"📝 {s['notes']}")
                    
                    with sc3:
                        with st.popover("⚙️", use_container_width=True):
                            with st.form(f"ed_sup_{s['id']}"):
                                sn = st.text_input("Name", s['name'])
                                sp = st.text_input("Phone", s['phone'])
                                snt = st.text_area("Notes", s.get('notes', ''))
                                if st.form_submit_button("💾"):
                                    bm.update_supplier(s['id'], {"name": sn, "phone": sp, "notes": snt})
                                    st.rerun()
                            if can_edit_delete:
                                with st.popover("🗑️ " + ("حذف" if lang=='ar' else "Delete"), use_container_width=True):
                                    st.write("هل أنت متأكد؟" if lang=='ar' else "Are you sure?")
                                    if st.button("تأكيد 🗑️" if lang=='ar' else "Confirm 🗑️", key=f"del_s_b_{s['id']}", use_container_width=True, type="primary"):
                                        bm.delete_supplier(s['id'])
                                        st.rerun()

        with m_t3:
            st.markdown(f"#### 🏢 {t('employers_tab', lang)}")
            
            if not filtered_e:
                st.info("⚠️ " + t("no_results", lang))

            for e in filtered_e:
                with st.container(border=True):
                    ec1, ec2, ec3 = st.columns([2, 1, 1])
                    ec1.markdown(f"**🏢 {e.get('name')}**")
                    ec2.markdown(f"☕ {e.get('cafe','')}")
                    
                    e_w_count = sum(int(w.get('headcount', 1)) if 'headcount' in w else 1 for w in all_workers if w.get('employer', '').startswith(e.get('name', '')))
                    lbl = "إجمالي العمال المرتبطين" if lang == 'ar' else "Total Workers Associated"
                    st.info(f"👥 **{lbl}: {e_w_count}**")
                    
                    with ec3:
                        with st.expander("📍"):
                            st.write(f"City: {e.get('city','')}")
                            st.write(f"Mobile: {e.get('mobile','')}")
                            if e.get('notes'):
                                st.info(f"📝 {e['notes']}")
                            with st.popover("✏️", use_container_width=True):
                                with st.form(f"ed_emp_{e['id']}"):
                                    en = st.text_input("Name", e['name'])
                                    ec = st.text_input("Cafe", e.get('cafe',''))
                                    em = st.text_input("Mobile", e.get('mobile',''))
                                    ect = st.text_input("City", e.get('city',''))
                                    ent = st.text_area("Notes", e.get('notes', ''))
                                    if st.form_submit_button("💾"):
                                        bm.update_employer(e['id'], {"name": en, "cafe": ec, "mobile": em, "city": ect, "notes": ent})
                                        st.rerun()
                            if can_edit_delete:
                                with st.popover("🗑️ " + ("حذف" if lang=='ar' else "Delete"), use_container_width=True):
                                    st.write("هل أنت متأكد؟" if lang=='ar' else "Are you sure?")
                                    if st.button("تأكيد 🗑️" if lang=='ar' else "Confirm 🗑️", key=f"del_e_b_{e['id']}", use_container_width=True, type="primary"):
                                        bm.delete_employer(e['id'])
                                        st.rerun()




# 11. Main Entry
if not st.session_state.user:
    login_screen()
else:
    dashboard()
