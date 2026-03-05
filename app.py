import streamlit as st
import pandas as pd
import os
import sys
import json
import hashlib
import time
from datetime import datetime, timedelta
import base64
import re

# 1. Ensure project root is in path (Robust Injection)
import os
import sys

# Get the absolute path of the directory containing app.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Add src to path as well to allow both 'import src.core' and 'import core'
SRC_DIR = os.path.join(BASE_DIR, 'src')
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

try:
    from src.core.contracts import ContractManager
    from src.data.bengali_manager import BengaliDataManager
    from src.utils.phone_utils import create_pasha_whatsapp_excel, format_phone_number, save_to_local_desktop, render_pasha_export_button
    from src.core.matcher import CandidateMatcher, format_match_result
except ImportError:
    # Fallback for different environment path configurations
    from core.contracts import ContractManager
    from data.bengali_manager import BengaliDataManager
    from utils.phone_utils import create_pasha_whatsapp_excel, format_phone_number, save_to_local_desktop, render_pasha_export_button
    from core.matcher import CandidateMatcher, format_match_result

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

def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

def get_css():
    return """
    <style>
        /* Modern 2026 Luxury Executive Design System */
        @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700&family=Inter:wght@300;400;500;600;700&family=Cinzel:wght@500;700&family=Alex+Brush&family=Cairo:wght@400;600;700&family=My+Soul&display=swap');
        
        :root {
            --luxury-gold: #D4AF37;
            --deep-gold: #B8860B;
            --glass-bg: rgba(26, 26, 26, 0.7);
            --solid-dark: #0A0A0A;
            --accent-green: #00FF41;
            --text-main: #F4F4F4;
            --border-glow: rgba(212, 175, 55, 0.3);
        }

        /* 1) Global Aesthetics & Scrollbar */
        .stApp {
            background: radial-gradient(circle at top right, #001F3F, #000000) !important;
            color: var(--text-main);
            font-family: 'Inter', 'Cairo', 'Tajawal', sans-serif;
            direction: rtl; /* Force RTL */
        }

        /* Fix Checkbox Spacing for RTL - Icon on Right, Text on Left */
        div[data-testid="stCheckbox"] label {
            display: flex !important;
            flex-direction: row !important; /* Standard Row + RTL direction = Icon on Right */
            align-items: center !important;
            gap: 15px !important;
            width: 100% !important;
            justify-content: flex-start !important;
        }

        /* Ensure the checkbox square is always the first element (right side in RTL) */
        div[data-testid="stCheckbox"] label div:first-child {
            order: 1 !important;
        }
        
        div[data-testid="stCheckbox"] label div[data-testid="stMarkdownContainer"] {
            order: 2 !important;
            flex-grow: 1 !important;
            text-align: right !important;
        }

        div[data-testid="stCheckbox"] label div[data-testid="stMarkdownContainer"] p {
            margin: 0 !important;
            font-family: 'Cairo', sans-serif !important;
            font-size: 0.95rem !important;
        }

        /* Custom Premium Scrollbar */
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: #000; }
        ::-webkit-scrollbar-thumb { 
            background: linear-gradient(180deg, #111, #D4AF37); 
            border-radius: 10px; 
        }

        /* 2) Layout & Spacing - CRITICAL FIX FOR TOP SPACE */
        .main .block-container {
            padding-top: 0rem !important;
            padding-bottom: 2rem !important;
            max-width: 1200px !important;
        }

        header[data-testid="stHeader"] {
            background: transparent !important;
            height: 0 !important;
        }

        /* 3) Luxury Typography & Large Title */
        .luxury-main-title {
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
        }

        .flag-icon {
            font-size: 20px;
            vertical-align: middle;
            margin: 0 5px;
        }

        /* 4) Premium Form & Vertical Alignment */
        div[data-testid="stForm"] {
            background: rgba(10, 10, 10, 0.5) !important;
            backdrop-filter: blur(15px) !important;
            border: 1px solid rgba(212, 175, 55, 0.2) !important;
            border-radius: 20px !important;
            padding: 1.5rem !important;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.8) !important;
        }

        /* Profile Image Alignment Wrapper */
        .profile-row-container {
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 15px;
            width: 100%;
            margin-bottom: 10px;
        }

        .profile-img-circular {
            width: 70px;
            height: 70px;
            border-radius: 50%;
            border: 2px solid var(--luxury-gold);
            box-shadow: 0 0 15px rgba(212, 175, 55, 0.3);
            object-fit: cover;
        }

        /* Generic Inputs Styling */
        .stTextInput input, .stTextArea textarea, div[data-baseweb="select"] {
            background-color: rgba(40, 40, 40, 0.6) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 12px !important;
            color: #FFFFFF !important;
            padding: 8px 12px !important; /* Reduced padding for smaller fields */
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.06) !important;
        }

        .stTextInput input:focus, div[data-baseweb="select"]:focus-within {
            border-color: var(--luxury-gold) !important;
            box-shadow: 0 0 0 3px rgba(212, 175, 55, 0.2) !important;
            background-color: rgba(50, 50, 50, 0.8) !important;
        }

        /* Slider Styling */
        div[data-testid="stSlider"] [data-testid="stThumb"] {
            background-color: var(--luxury-gold) !important;
            border: 2px solid #FFFFFF !important;
        }
        div[data-testid="stSlider"] [data-testid="stTrack"] > div {
            background: linear-gradient(90deg, #333, #D4AF37) !important;
        }

        /* 5) Universal Luxury Button Style */
        .stButton button, div[data-testid="stFormSubmitButton"] button {
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
        }

        /* Mobile specific button refinements */
        @media screen and (max-width: 768px) {
            .stButton button, div[data-testid="stFormSubmitButton"] button {
                padding: 0.6rem 1.2rem !important;
                font-size: 0.85rem !important;
                letter-spacing: 1px !important;
            }
        }

        .stButton button:hover, div[data-testid="stFormSubmitButton"] button:hover {
            background: var(--luxury-gold) !important;
            color: #000 !important;
            border-color: var(--luxury-gold) !important;
            box-shadow: 0 0 25px rgba(212, 175, 55, 0.5) !important;
            transform: translateY(-3px) scale(1.02) !important;
        }

        /* Primary Search Variation */
        button[kind="primary"] {
            background: linear-gradient(135deg, #111, #222) !important;
            border: 1px solid var(--luxury-gold) !important;
        }

        /* 6) Table & Data Presentation - WHITE NEON STYLE (For DataFrames) */
        [data-testid="stDataFrame"], [data-testid="stTable"], .neon-white-table {
            background: rgba(255, 255, 255, 1) !important;
            border: 2px solid #FFFFFF !important;
            border-radius: 12px !important;
            box-shadow: 0 0 30px rgba(255, 255, 255, 0.8), 
                        inset 0 0 15px rgba(255, 255, 255, 0.5) !important;
            margin: 20px 0 !important;
            color: #000000 !important;
        }
        
        [data-testid="stDataFrame"] *, [data-testid="stTable"] *, .neon-white-table * {
            color: #000000; /* Removed !important to allow selective overrides */
            font-weight: 500 !important;
        }

        /* FIX: White Icons for Data Table Toolbars (Fullscreen, Search, Download) */
        [data-testid="stElementToolbar"] button, 
        [data-testid="stDataFrame"] [data-testid="stElementToolbar"] svg,
        [data-testid="stTable"] [data-testid="stElementToolbar"] svg {
            color: #FFFFFF !important;
            fill: #FFFFFF !important;
            filter: drop-shadow(0 0 5px rgba(255, 255, 255, 0.5)) !important;
        }
        
        [data-testid="stElementToolbar"] button:hover {
            background-color: rgba(255, 255, 255, 0.1) !important;
            border-radius: 50% !important;
        }
        
        /* Header specific for dataframes to handle high brightness */
        [data-testid="stDataFrame"] div[role="columnheader"] {
            background-color: rgba(240, 240, 240, 0.9) !important;
            color: #000000 !important;
            font-weight: 700 !important;
        }

        /* Status Column Glows - Enhanced for 2026 High-Tech Look */
        .glow-green { color: #00FF66 !important; text-shadow: 0 0 10px rgba(0, 255, 102, 0.4) !important; font-weight: 800 !important; }
        .glow-red { color: #FF3333 !important; text-shadow: 0 0 10px rgba(255, 51, 51, 0.4) !important; font-weight: 800 !important; }
        .glow-orange { color: #FF9900 !important; text-shadow: 0 0 10px rgba(255, 153, 0, 0.4) !important; font-weight: 800 !important; }

        /* 7) Sidebar Professionalism */
        section[data-testid="stSidebar"] {
            background-color: #080808 !important;
            border-right: 1px solid rgba(212, 175, 55, 0.15) !important;
        }

        .programmer-credit {
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
        }
        
        /* English version specific font */
        .programmer-credit.en {
            font-family: 'Cinzel', serif !important;
            font-size: 1.1rem;
            letter-spacing: 1px;
        }

        /* 8) Expander Luxury - UNIVERSAL WHITE NEON FRAME STYLE */
        .stExpander {
            background-color: rgba(10, 14, 26, 0.6) !important;
            border: 2px solid rgba(255, 255, 255, 0.5) !important;
            border-radius: 20px !important;
            margin-bottom: 25px !important;
            animation: neonWhitePulse 3s ease-in-out infinite alternate !important;
            box-shadow: 0 0 15px rgba(255, 255, 255, 0.2) !important;
            transition: all 0.4s ease !important;
            overflow: hidden !important;
        }
        
        .stExpander:hover {
            border-color: rgba(255, 255, 255, 0.9) !important;
            box-shadow: 0 0 30px rgba(255, 255, 255, 0.6) !important;
            transform: translateY(-2px);
        }

        /* Target the Header/Summary Area */
        .stExpander > details > summary {
            background-color: rgba(255, 255, 255, 0.05) !important;
            color: #FFFFFF !important;
            padding: 1.2rem 1.5rem !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
        }
        
        .stExpander > details > summary:hover {
            background-color: rgba(255, 255, 255, 0.1) !important;
        }

        /* Target the internal icons and labels */
        .stExpander summary span, .stExpander summary svg {
            color: #FFFFFF !important;
            fill: #FFFFFF !important;
        }

        /* Ensure internal content is appropriately styled */
        .stExpander > details > div[role="region"] {
            border: none !important;
            background: transparent !important;
            padding: 20px !important;
        }

        /* Re-refine filter labels for maximum white neon impact */
        .premium-filter-label {
            color: #FFFFFF !important;
            font-weight: 800 !important;
            text-shadow: 0 0 15px rgba(255, 255, 255, 0.8) !important;
            margin: 15px 0 10px 0 !important;
            font-size: 1.15rem !important;
            border-right: 5px solid #FFFFFF !important;
            padding-right: 12px !important;
            letter-spacing: 1px;
            display: inline-block;
        }

        /* Signature Neon (Standardized White-Gold) */
        .programmer-signature-neon, .red-neon-signature {
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
        }

        /* Signature Under Image */
        .signature-under-img {
            font-family: 'Alex Brush', cursive !important;
            color: #EEE !important; /* Slightly brighter for better visibility */
            font-size: 0.9rem !important;
            margin-top: 5px;
            text-align: center;
            letter-spacing: 1px;
            white-space: nowrap !important;
        }

        /* Login Screen Special Centering */
        .login-screen-wrapper {
            margin-top: 0vh !important;
            text-align: center;
        }
        
        /* Metric Styling with White Neon Glow */
        @keyframes neonWhitePulse {
            0% { 
                box-shadow: 0 0 10px rgba(255, 255, 255, 0.4), 0 0 20px rgba(255, 255, 255, 0.15), inset 0 0 10px rgba(255, 255, 255, 0.05);
                border-color: rgba(255, 255, 255, 0.5);
            }
            100% { 
                box-shadow: 0 0 20px rgba(255, 255, 255, 0.7), 0 0 40px rgba(255, 255, 255, 0.35), inset 0 0 20px rgba(255, 255, 255, 0.1);
                border-color: rgba(255, 255, 255, 0.8);
            }
        }

        .metric-container {
            background: rgba(10, 14, 26, 0.7) !important;
            border-radius: 20px !important;
            border: 1.5px solid rgba(255, 255, 255, 0.4) !important;
            padding: 1.8rem 1.5rem !important;
            transition: all 0.3s ease !important;
            animation: neonWhitePulse 3s ease-in-out infinite alternate;
            text-align: center;
        }
        .metric-container:hover { 
            transform: scale(1.05) translateY(-5px);
            border-color: #FFFFFF !important;
            box-shadow: 0 0 30px rgba(255, 255, 255, 0.9), 0 0 60px rgba(255, 255, 255, 0.4) !important;
        }

        .metric-label {
            font-size: 0.95rem;
            color: rgba(255, 255, 255, 0.6);
            margin-bottom: 8px;
            font-weight: 500;
        }
        .metric-value {
            font-size: 2.2rem;
            font-weight: 800;
            line-height: 1;
        }

        /* 9) Modern 2026 Premium Loader */
        .loader-wrapper {
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
        }

        @keyframes loader-entrance {
            from { opacity: 0; transform: scale(0.9) translateY(20px); }
            to { opacity: 1; transform: scale(1) translateY(0); }
        }

        .modern-hourglass-svg {
            width: 100px;
            height: 100px;
            filter: drop-shadow(0 0 15px rgba(212, 175, 55, 0.6));
            animation: hourglass-rotate 2.5s linear infinite;
        }

        @keyframes hourglass-rotate {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }

        .modern-hourglass-svg .glass {
            fill: none;
            stroke: var(--luxury-gold);
            stroke-width: 2.5;
            stroke-linejoin: round;
        }

        .modern-hourglass-svg .sand {
            fill: var(--luxury-gold);
            opacity: 0.9;
        }

        .modern-hourglass-svg .sand-top {
            animation: sand-sink 2.5s linear infinite;
        }

        .modern-hourglass-svg .sand-bottom {
            animation: sand-fill 2.5s linear infinite;
        }

        .modern-hourglass-svg .sand-drip {
            fill: var(--luxury-gold);
            animation: sand-drip 2.5s linear infinite;
        }

        @keyframes hourglass-flip {
            0%, 85% { transform: rotate(0deg); }
            95%, 100% { transform: rotate(180deg); }
        }

        @keyframes sand-sink {
            0% { clip-path: polygon(0 0, 100% 0, 100% 100%, 0 100%); }
            85%, 100% { clip-path: polygon(0 100%, 100% 100%, 100% 100%, 0 100%); }
        }

        @keyframes sand-fill {
            0% { clip-path: polygon(0 100%, 100% 100%, 100% 100%, 0 100%); }
            85%, 100% { clip-path: polygon(0 0, 100% 0, 100% 100%, 0 100%); }
        }

        @keyframes sand-drip {
            0%, 5% { opacity: 0; height: 0; }
            10%, 80% { opacity: 1; height: 30px; }
            85%, 100% { opacity: 0; height: 0; }
        }

        .loading-text-glow {
            margin-top: 30px;
            font-family: 'Cinzel', serif !important;
            color: var(--luxury-gold) !important;
            font-size: 1.2rem !important;
            letter-spacing: 5px !important;
            text-transform: uppercase !important;
            text-align: center;
            animation: text-pulse-glow 2s ease-in-out infinite alternate;
        }

        @keyframes text-pulse-glow {
            from { opacity: 0.6; text-shadow: 0 0 10px rgba(212, 175, 55, 0.2); }
            to { opacity: 1; text-shadow: 0 0 25px rgba(212, 175, 55, 0.8), 0 0 15px rgba(212, 175, 55, 0.4); }
        }

        /* 10) Persistent Top Banner */
        .persistent-top-banner {
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
        }

        .notif-bell-container {
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
        }

        /* Target the specific Streamlit button inside our bell container */
        div[data-testid="column"]:nth-of-type(3) button[key*="bell_trigger"] {
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
        }

        .notif-badge {
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
        }

        @keyframes pulse-red {
            0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 49, 49, 0.7); }
            70% { transform: scale(1.1); box-shadow: 0 0 0 8px rgba(255, 49, 49, 0); }
            100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 49, 49, 0); }
        }

        @keyframes banner-slide-down {
            from { transform: translateY(-100%); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }

        .banner-user-info {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 5px;
        }

        .banner-avatar {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            border: 2px solid #D4AF37;
            object-fit: cover;
            box-shadow: 0 0 15px rgba(212, 175, 55, 0.4);
            transition: transform 0.3s ease;
        }

        .banner-avatar:hover {
            transform: scale(1.1) rotate(5deg);
        }

        .banner-welcome-msg {
            font-family: 'Cairo', 'Tajawal', sans-serif;
            color: #FFFFFF;
            font-size: 1.1rem;
            font-weight: 600;
            text-shadow: 0 2px 4px rgba(0,0,0,0.5);
            margin: 0;
        }

        .banner-subtext {
            font-size: 0.8rem;
            color: rgba(212, 175, 55, 0.8);
            margin-top: -5px;
        }

        /* 11) Mobile Responsive Overrides */
        @media (max-width: 768px) {
            .main .block-container {
                padding: 1rem !important;
                padding-top: 5rem !important; /* Space for the floating banner on mobile */
            }

            .persistent-top-banner {
                margin: 0 !important;
                padding: 0.8rem 1rem !important;
                position: fixed !important; /* Fixed at top for mobile */
                width: 100%;
                left: 0;
            }

            .banner-welcome-msg { font-size: 0.95rem; }
            .banner-subtext { font-size: 0.7rem; }
            .banner-avatar { width: 45px; height: 45px; }

            /* Fix Sidebar Appearance on Mobile - Clean edge when closed */
            section[data-testid="stSidebar"] {
                background-color: #080808 !important;
                background-image: none !important;
                z-index: 10 !important;
                box-shadow: none !important;
            }

            /* FORCE HIDE sidebar when closed on mobile to prevent layout competition */
            section[data-testid="stSidebar"][aria-expanded="false"] {
                display: none !important;
                visibility: hidden !important;
                width: 0 !important;
            }

            /* Streamlit Mobile Sidebar User Content Fix */
            div[data-testid="stSidebarUserContent"] {
                background-color: #080808 !important;
            }

            /* 12) GLOBAL UI CLEANUP: Hide standard header junk */
            .stAppDeployButton, #MainMenu, header[data-testid="stHeader"] a {
                display: none !important;
            }

            /* 13) STYLED NEON WHITE SIDEBAR TOGGLE */
            /* This target works for BOTH "Open" and "Close" states */
            button[data-testid="stSidebarCollapse"],
            button[aria-label*="sidebar"],
            .st-emotion-cache-not-found button[kind="headerNoPadding"] {
                display: flex !important;
                visibility: visible !important;
                position: fixed !important;
                top: 10px !important;
                left: 15px !important;
                z-index: 9999999 !important;
                background-color: #FFFFFF !important; /* Neon White */
                border: 2px solid #D4AF37 !important;
                border-radius: 50% !important;
                box-shadow: 0 0 15px #FFFFFF, 0 0 30px rgba(212, 175, 55, 0.6) !important;
                width: 44px !important;
                height: 44px !important;
                opacity: 1 !important;
            }

            /* Ensure the icon inside is Gold/Black and clearly visible */
            button[aria-label*="sidebar"] svg,
            button[data-testid="stSidebarCollapse"] svg {
                fill: #1A1A1A !important;
                color: #1A1A1A !important;
                width: 26px !important;
                height: 26px !important;
                stroke: #D4AF37 !important;
                stroke-width: 0.5px;
            }

            /* Pulse animation for Neon effect */
            button[data-testid="stSidebarCollapse"] {
                animation: neon-white-pulse 2s infinite alternate;
            }

            @keyframes neon-white-pulse {
                0% { box-shadow: 0 0 10px #FFF, 0 0 20px rgba(212, 175, 55, 0.4); }
                100% { box-shadow: 0 0 20px #FFF, 0 0 40px rgba(212, 175, 55, 0.8); }
            }

            /* 14) Log Message Cards */
            .log-card {
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
            }
            .log-card:hover {
                background: rgba(212, 175, 55, 0.05) !important;
                border-color: rgba(212, 175, 55, 0.3) !important;
                transform: translateX(-5px) !important;
            }
            .log-info {
                display: flex !important;
                flex-direction: column !important;
                gap: 2px !important;
                text-align: right !important;
            }
            .log-name {
                font-weight: 700 !important;
                color: #FFF !important;
                font-size: 0.95rem !important;
            }
            .log-phone {
                font-size: 0.8rem !important;
                color: rgba(212, 175, 55, 0.8) !important;
            }
            .log-status-group {
                display: flex !important;
                flex-direction: column !important;
                align-items: flex-start !important;
                gap: 4px !important;
            }
            .log-status {
                display: flex !important;
                align-items: center !important;
                gap: 8px !important;
                font-size: 0.85rem !important;
            }
            .log-time {
                font-size: 0.75rem !important;
                color: #888 !important;
                font-family: 'Inter', sans-serif !important;
            }
            .status-badge {
                padding: 2px 8px !important;
                border-radius: 6px !important;
                font-size: 0.75rem !important;
                font-weight: 600 !important;
            }
            .status-success { background: rgba(0, 255, 65, 0.1) !important; color: #00FF41 !important; border: 1px solid rgba(0, 255, 65, 0.2) !important; }
            .status-error { background: rgba(255, 49, 49, 0.1) !important; color: #FF3131 !important; border: 1px solid rgba(255, 49, 49, 0.2) !important; }
        }
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

def style_df(df):
    """
    Applies custom styling to DataFrames.
    - Injects Flag URLs for nationality
    - Colors rows/cells dynamically (Gender: Blue/Pink, Default: Green)
    """
    if not isinstance(df, pd.DataFrame):
        return df

    styled_df = df.copy()
    
    # 1. Flag Image Injection
    nat_cols = [c for c in styled_df.columns if any(kw in str(c).lower() for kw in ["nationality", "الجنسية"])]
    for col in nat_cols:
        # Avoid double flags if re-running
        flag_col = f"🚩_{col}"
        if flag_col not in styled_df.columns:
            def get_flag_url(val):
                if not val: return None
                s_val = str(val).strip().lower()
                # Sort keys by length (longest first) to match "sri lankan" before "sri"
                sorted_keys = sorted(FLAG_MAP.keys(), key=len, reverse=True)
                for key in sorted_keys:
                    code = FLAG_MAP[key]
                    # Use boundaries for short keys to avoid false positives (e.g. 'in' in 'Fatima')
                    if len(key) <= 3:
                        pattern = r'(?:^|[\s,:;.\-/])' + re.escape(key) + r'(?:[\s,:;.\-/]|$)'
                        if re.search(pattern, s_val):
                            return f"https://flagcdn.com/w20/{code}.png"
                    else:
                        if key in s_val:
                            return f"https://flagcdn.com/w20/{code}.png"
                return None
            
            # Position flag before nationality
            idx = list(styled_df.columns).index(col)
            styled_df.insert(idx, flag_col, styled_df[col].apply(get_flag_url))

    # 2. Gender Icon Injection
    gen_cols = [c for c in styled_df.columns if any(kw in str(c).lower() for kw in ["gender", "الجنس"]) and str(c).lower() != "الجنسية"]
    for col in gen_cols:
        def add_gender_icon(val):
            if not val: return val
            s_val = str(val).strip().lower()
            for key, icon in GENDER_MAP.items():
                if key == s_val:
                    return f"{icon} {val}"
            return val
        styled_df[col] = styled_df[col].apply(add_gender_icon)

    # 3. Apply Dynamic Styling (Colors)
    def apply_colors(val):
        s_val = str(val).lower()
        if any(k in s_val for k in ["🚹", "ذكر", "male"]):
            return "color: #3498db; font-weight: bold;" 
        if any(k in s_val for k in ["🚺", "أنثى", "female"]):
            return "color: #e91e63; font-weight: bold;"
        return "color: #4CAF50;"

    return styled_df.style.map(
        apply_colors, 
        subset=[c for c in styled_df.columns if not str(c).startswith("🚩_")]
    )

def clean_date_display(df):
    """
    Finds date-like columns, parses them, and formats them to DATE ONLY (no time).
    Ensures they are sorted if a primary date column is found.
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        return df
        
    import re
    from dateutil import parser as dateutil_parser
    
    def _parse_to_date_str(val):
        if val is None or str(val).strip() == '': return ""
        try:
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

    date_keywords = ["date", "time", "تاريخ", "طابع", "التسجيل", "expiry", "end", "متى"]
    for col in df.columns:
        col_lower = str(col).lower()
        if any(kw in col_lower for kw in date_keywords):
            df[col] = df[col].apply(_parse_to_date_str)
            
    return df

# 2.4 Global Premium Popup Helper
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
                pointer-events: all;
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

# 5. Apply Styles
st.markdown(get_css(), unsafe_allow_html=True)

# 6. Initialize Core (With Force Re-init for Updates)
if 'auth' not in st.session_state or not hasattr(st.session_state.auth, 'v10_marker'):
    # Show a brief initial loader for a premium feel
    loading = show_loading_hourglass()
    time.sleep(0.4)
    st.session_state.auth = AuthManager(USERS_FILE)
    st.session_state.auth.v10_marker = True # Marker with get_avatar/update_avatar support
    st.session_state.db = DBClient() # Force DB re-init as well
    loading.empty()

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
    if scroll_key not in st.session_state or st.session_state[scroll_key] != selected_idx:
        st.session_state[scroll_key] = selected_idx
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
            \U0001F464 {worker_name}
        </h2>
    </div>
    """, unsafe_allow_html=True)
    
    col_a, col_b = st.columns([1, 1])
    with col_a:
        if st.button(f"✨ {t('translate_cv_btn', lang)}", use_container_width=True, type="primary", key=f"btn_trans_{key_prefix}_{selected_idx}"):
            if cv_url and str(cv_url).startswith("http"):
                from src.core.file_translator import FileTranslator
                
                trans_loader = show_loading_hourglass(t("extracting", lang))
                try:
                    import requests
                    file_id = None
                    if "drive.google.com" in cv_url:
                        if "id=" in cv_url: file_id = cv_url.split("id=")[1].split("&")[0]
                        elif "/d/" in cv_url: file_id = cv_url.split("/d/")[1].split("/")[0]

                    # 1. Download full content
                    session = requests.Session()
                    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"})
                    
                    if file_id:
                        dl_url = f"https://docs.google.com/uc?export=download&id={file_id}"
                        resp = session.get(dl_url, stream=True, timeout=15)
                        
                        # Handle Drive Virus Warning
                        token = None
                        for k, v in resp.cookies.items():
                            if k.startswith('download_warning'): token = v; break
                        if token:
                            dl_url = f"https://docs.google.com/uc?export=download&confirm={token}&id={file_id}"
                            resp = session.get(dl_url, stream=True, timeout=15)
                        
                        if resp.status_code >= 500:
                            resp = requests.get(cv_url, timeout=15)
                    else:
                        resp = requests.get(cv_url, timeout=15)
                    
                    if resp.status_code == 200:
                        content = resp.content
                        
                        # 2. Determine file type from content or header
                        # Try to get extension from 'Content-Disposition' or original text
                        content_type = resp.headers.get('Content-Type', '').lower()
                        filename_from_header = ""
                        cd = resp.headers.get('Content-Disposition', '')
                        if 'filename=' in cd:
                            filename_from_header = cd.split('filename=')[1].strip('"')
                        
                        # Fallback extension detection
                        ext = ".pdf" # Default
                        if "word" in content_type or filename_from_header.endswith(".docx"): ext = ".docx"
                        elif "image" in content_type: 
                            if "png" in content_type: ext = ".png"
                            else: ext = ".jpg"
                        elif filename_from_header.endswith(".bdf"): ext = ".bdf"
                        elif content.startswith(b"%PDF"): ext = ".pdf"
                        elif content.startswith(b"PK\x03\x04"): ext = ".docx" # Zip/Docx signature
                        
                        # 3. Translate using the new Engine
                        ft = FileTranslator(source_lang="auto", target_lang="ar")
                        
                        # Mock a filename if not found
                        virtual_filename = filename_from_header if filename_from_header else f"file{ext}"
                        
                        result = ft.translate(content, virtual_filename)
                        
                        if result.get("success"):
                            st.session_state[f"trans_{key_prefix}_{selected_idx}"] = {
                                "orig": result.get("original_text", ""), 
                                "trans": result.get("translated_text", ""),
                                "output": result.get("output_bytes"),
                                "out_filename": result.get("output_filename")
                            }
                            st.rerun()
                        else:
                            st.error(f"❌ {result.get('error', 'Unknown Error')}")
                    else:
                        st.error(f"خطأ في الوصول للملف: (HTTP {resp.status_code}). جرب فتح الرابط يدوياً.")
                except Exception as e: 
                    st.error(f"Error Processing File: {str(e)}")
                finally:
                    trans_loader.empty()
            else: 
                st.warning("رابط السيرة الذاتية غير موجود أو غير صالح.")

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
                         use_container_width=True, key=f"hide_worker_{key_prefix}_{selected_idx}"):
                st.session_state.op_hidden_workers.add(worker_uid)
                st.rerun()
        else:
            st.info("⚠️ الحذف غير متاح في هذا النموذج.")
    else:
        # Original Deletion Logic for Search/Contract Board
        if sheet_row:
            with st.popover(f"🗑️ {t('delete_btn', lang)}", use_container_width=True):
                st.warning(t("confirm_delete_msg", lang))
                if st.button(t("confirm_btn", lang), type="primary", use_container_width=True, key=f"del_confirm_{key_prefix}_{selected_idx}"):
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
                if st.button(t("fix_ids", lang), key=f"fix_id_{key_prefix}_{selected_idx}", use_container_width=True):
                    st.session_state.db.fetch_data(force=True); st.rerun()
            with c2:
                if st.button(t("deep_reset", lang), key=f"reset_all_{key_prefix}_{selected_idx}", use_container_width=True):
                    # Clear all tab data and cache
                    for k in list(st.session_state.keys()):
                        if k.startswith("dash_table_") or k.startswith("last_scroll_"): del st.session_state[k]
                    st.session_state.db.fetch_data(force=True); st.rerun()

    trans_key = f"trans_{key_prefix}_{selected_idx}"
    if trans_key in st.session_state:
        t_data = st.session_state[trans_key]
        c1, c2 = st.columns(2)
        with c1:
            st.caption("English (Original)")
            st.text_area("Orig", t_data["orig"], height=300, key=f"orig_area_{key_prefix}_{selected_idx}")
        with c2:
            st.caption("العربية (المترجمة)")
            st.text_area("Trans", t_data["trans"], height=300, key=f"trans_area_{key_prefix}_{selected_idx}")
        
        # Download Button for the Translated File itself
        if t_data.get("output"):
            st.download_button(
                f"⬇️ {t('download_trans', lang)}",
                data=t_data["output"],
                file_name=t_data.get("out_filename", "translated_file"),
                mime="application/octet-stream",
                use_container_width=True,
                key=f"dl_trans_file_{key_prefix}_{selected_idx}"
            )
    
    st.markdown(f"#### 🔎 {t('preview_cv', lang)}")
    if cv_url and str(cv_url).startswith("http"):
        preview_url = cv_url
        if "drive.google.com" in cv_url:
            f_id = None
            if "id=" in cv_url: f_id = cv_url.split("id=")[1].split("&")[0]
            elif "/d/" in cv_url: f_id = cv_url.split("/d/")[1].split("/")[0]
            if f_id: preview_url = f"https://drive.google.com/file/d/{f_id}/preview"
        st.components.v1.iframe(preview_url, height=600, scrolling=True)
    else: st.info("لا يتوفر رابط معاينة لهذا العامل.")

# 11. Logic Functions
def login_screen():
    lang = st.session_state.lang
    
    # 2026 Luxury Flag Icons (Ensures consistent rendering on Windows)
    sa_icon = '<img src="https://flagcdn.com/w40/sa.png" style="width:24px; vertical-align:middle; border-radius:3px; margin:0 4px; box-shadow:0 0 8px rgba(0,0,0,0.4);">'
    ph_icon = '<img src="https://flagcdn.com/w40/ph.png" style="width:24px; vertical-align:middle; border-radius:3px; margin:0 4px; box-shadow:0 0 8px rgba(0,0,0,0.4);">'
    
    # Define Bilingual Titles with Flag Icons
    if lang == "ar":
        title_text = f'برنامج توريد العمالة الفلبينية {ph_icon} {sa_icon}'
    else:
        title_text = f'Philippines Recruitment Program {ph_icon} {sa_icon}'
    
    col1, col2, col3 = st.columns([1.5, 2.2, 1.5]) 
    with col2:
        # 1. Giant Luxury Title at Absolute Top
        st.markdown(f'<div class="luxury-main-title">{title_text}</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="login-screen-wrapper" style="margin-top: -20px !important;">', unsafe_allow_html=True)
        
        with st.form("login"):
            # 2. Horizontal Profile + Welcome Message Row
            ic1, ic2 = st.columns([1.2, 3]) # Adjust alignment for better proportion
            
            with ic1: # The Branding Column (Image -> EN/AR Name)
                if os.path.exists(IMG_PATH):
                    b64 = get_base64_image(IMG_PATH)
                    st.markdown(f'<img src="data:image/jpeg;base64,{b64}" class="profile-img-circular">', unsafe_allow_html=True)
                
                st.markdown('<div style="margin-top: 10px;"></div>', unsafe_allow_html=True)
                if lang == "ar":
                    st.markdown('<div class="signature-under-img">Alsaeed Alwazzan</div>', unsafe_allow_html=True)
                    st.markdown('<div class="signature-under-img" style="font-family:\'Cairo\', sans-serif; font-size: 0.8rem; margin-top: 2px;">برمجة السعيد الوزان</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="signature-under-img">Alsaeed Alwazzan</div>', unsafe_allow_html=True)
                    st.markdown('<div class="signature-under-img" style="font-size: 0.75rem; color:#888;">Lead Programmer</div>', unsafe_allow_html=True)

            with ic2: # The Welcome text & Username Field
                welcome_text = t('welcome_back', lang)
                st.markdown(f"<h3 style='margin:5px 0 10px 0; font-family:\"Cairo\", sans-serif; font-size: 1.1rem; text-align:right; color:#D4AF37;'>{welcome_text}</h3>", unsafe_allow_html=True)
                u = st.text_input(t("username", lang), label_visibility="collapsed", placeholder=t("username", lang))

            # 3. Password Field
            p = st.text_input(t("password", lang), type="password", label_visibility="collapsed", placeholder=t("password", lang))
            
            # 4. Buttons (Login and Language)
            submit = st.form_submit_button(t("login_btn", lang), use_container_width=True)
            lang_toggle = st.form_submit_button("En" if lang == "ar" else "عربي", use_container_width=True)

            if submit:
                login_loader = show_loading_hourglass()
                p_norm = p.strip()
                user = st.session_state.auth.authenticate(u, p_norm)
                login_loader.empty()
                if user:
                    # Save the CANONICAL lowercase username to session state
                    # This prevents case-sensitivity bugs on mobile avatar sync
                    user['username'] = u.lower().strip()
                    st.session_state.user = user
                    st.session_state.show_welcome = True
                    st.rerun()
                else:
                    st.error(t("invalid_creds", lang))

            if lang_toggle:
                toggle_lang()
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

def check_notifications():
    """Checks for new worker entries or customer requests and synchronizes UI data."""
    if 'db' not in st.session_state or not st.session_state.user:
        return

    # initialize session state
    if 'notifications' not in st.session_state: st.session_state.notifications = []
    if 'notif_last_worker_count' not in st.session_state: st.session_state.notif_last_worker_count = None
    if 'notif_last_cust_count' not in st.session_state: st.session_state.notif_last_cust_count = None
    if 'notif_triggered' not in st.session_state: st.session_state.notif_triggered = False
    
    st.session_state.last_sync_time = datetime.now().strftime("%H:%M:%S")

    def find_col(df, keywords):
        """Smart column finder - handles Arabic normalization (ة vs ه)."""
        cols = list(df.columns)
        import re
        for kw in keywords:
            # Normalize keyword: replace ة with ه pattern for matching
            kw_norm = kw.replace('ة', '[ةه]').replace('ه', '[ةه]')
            pattern = re.compile(kw_norm, re.IGNORECASE)
            for c in cols:
                if pattern.search(str(c)): return c
        return None

    def safe_val(row, col_name):
        if col_name is None: return '---'
        val = str(row.get(col_name, '---')).strip()
        if val in ['nan', 'None', '', 'NaN']: return '---'
        return val

    try:
        # 1. Check Workers (Filling in employee data)
        df_workers = st.session_state.db.fetch_data(is_notif_check=True)
        current_worker_count = len(df_workers)
        
        if st.session_state.notif_last_worker_count is not None and current_worker_count > st.session_state.notif_last_worker_count:
            new_rows = df_workers.tail(current_worker_count - st.session_state.notif_last_worker_count)
            c_name = find_col(df_workers, ['Full Name', 'الاسم'])
            c_nat = find_col(df_workers, ['Nationality', 'الجنسية'])
            c_phone = find_col(df_workers, ['Phone Number', 'رقم الهاتف', 'هاتف'])
            c_job = find_col(df_workers, ['Which job are you looking for', 'الوظيفة'])
            c_gender = find_col(df_workers, ['Gender', 'الجنس'])

            for _, row in new_rows.iterrows():
                name = safe_val(row, c_name)
                st.session_state.notifications.append({
                    'title': "🆕 تسجيل عامل جديد",
                    'msg': f"👤 {name} | 🌍 {safe_val(row, c_nat)}\n📱 {safe_val(row, c_phone)}\n💼 {safe_val(row, c_job)} | ⚧ {safe_val(row, c_gender)}",
                    'time': datetime.now().strftime("%H:%M")
                })
                st.toast(f"🆕 عامل جديد: {name}", icon="🔔")
                st.session_state.notif_triggered = True
            st.session_state.db.fetch_data(force=True) # Refresh main worker cache

        st.session_state.notif_last_worker_count = current_worker_count

        # 2. Check Customer Requests (استقطاب موظفين)
        df_cust = st.session_state.db.fetch_customer_requests(is_notif_check=True)
        current_cust_count = len(df_cust)
        
        if st.session_state.notif_last_cust_count is not None and current_cust_count > st.session_state.notif_last_cust_count:
            new_rows = df_cust.tail(current_cust_count - st.session_state.notif_last_cust_count)
            
            c_comp = find_col(df_cust, ['اسم الشركه', 'المؤسسة', 'الشركة', 'Company'])
            c_phone = find_col(df_cust, ['الموبيل', 'جوال', 'هاتف', 'Mobile'])
            c_role = find_col(df_cust, ['الفئة المطلوبة', 'نوع العمل'])
            c_nat = find_col(df_cust, ['الجنسية المطلوبة'])
            c_loc = find_col(df_cust, ['موقع العمل', 'المدينة'])
            
            for _, row in new_rows.iterrows():
                comp = safe_val(row, c_comp)
                st.session_state.notifications.append({
                    'title': "🔔 طلب عميل جديد",
                    'msg': f"🏢 {comp} | 📱 {safe_val(row, c_phone)}\n💪 {safe_val(row, c_role)} | 🌍 {safe_val(row, c_nat)}\n📍 {safe_val(row, c_loc)}",
                    'time': datetime.now().strftime("%H:%M")
                })
                st.toast(f"🔔 طلب جديد: {comp}", icon="☕")
                st.session_state.notif_triggered = True 
            st.session_state.db.fetch_customer_requests(force=True) # Refresh main customer cache
        
        st.session_state.notif_last_cust_count = current_cust_count

    except Exception as e:
        print(f"[ERROR] Notification check failed: {e}")

def render_top_banner():
    """renders a persistent top banner with user image and welcome message."""
    user = st.session_state.user
    lang = st.session_state.lang
    notifs = st.session_state.get('notifications', [])
    notif_count = len(notifs)

    # 1. Global Audio Alert - High Reliability Implementation
    if st.session_state.get('notif_triggered'):
        st.components.v1.html("""
<script>
(async function(){
    try {
        var AudioContext = window.AudioContext || window.webkitAudioContext;
        var ctx = new AudioContext();
        if (ctx.state === 'suspended') await ctx.resume();
        
        function playBell(freq, startTime, dur) {
            var osc = ctx.createOscillator(); var gain = ctx.createGain();
            osc.connect(gain); gain.connect(ctx.destination);
            osc.type = 'sine'; osc.frequency.setValueAtTime(freq, ctx.currentTime + startTime);
            gain.gain.setValueAtTime(0.5, ctx.currentTime + startTime);
            gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + startTime + dur);
            osc.start(ctx.currentTime + startTime); osc.stop(ctx.currentTime + startTime + dur);
        }
        playBell(830, 0.0, 0.6); playBell(1050, 0.3, 0.6); playBell(1320, 0.6, 0.8);
    } catch(e) { console.error('Audio fail:', e); }
})();
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

    # 1.5 Live Monitor (Silent Auto-Refresh every 30 seconds)
    st.components.v1.html("""
<script>
    if (!window.liveMonitorSet) {
        window.liveMonitorSet = true;
        console.log("[LiveMonitor] Background Service Started.");
        
        setInterval(function() {
            if (window.parent.document.visibilityState !== 'visible') return;
            var activeEl = window.parent.document.activeElement;
            var isTyping = activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA' || activeEl.isContentEditable);
            
            if (!isTyping) {
                var buttons = window.parent.document.querySelectorAll('button');
                for (var i = 0; i < buttons.length; i++) {
                    if (buttons[i].innerText === 'Heartbeat') {
                        console.log("[LiveMonitor] Syncing Data...");
                        buttons[i].click();
                        break;
                    }
                }
            }
        }, 10000); 
    }
</script>
""", height=0, width=0)

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
        # Force horizontal bar layout using Columns
        c1, c2, c3, c4 = st.columns([2.5, 4, 1, 2])
        
        with c1: # Profile
            st.markdown(f'<div style="display:flex; align-items:center; gap:15px; margin-top:5px;">{avatar_html}<div><p style="margin:0; font-weight:700; color:white;">{welcome_prefix} {full_name}</p><p style="margin:0; font-size:0.75rem; color:#D4AF37;">{program_name}</p></div></div>', unsafe_allow_html=True)
        
        with c2: st.write("") # Spacer
            
        with c3: # Bell & Badge
            badge_html = f'<span class="notif-badge">{notif_count}</span>' if notif_count > 0 else ''
            st.markdown(f'<div class="notif-bell-container" style="margin-top:5px; position:relative;">{badge_html}', unsafe_allow_html=True)
            if st.button("🔔", key="bell_trig_v2", help="View Notifications"):
                st.session_state.notif_panel_open = not st.session_state.get('notif_panel_open', False)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with c4: # Date/Log
            st.markdown(f'<div style="text-align:right; border-left:1px solid rgba(212,175,55,0.2); padding-left:15px; margin-top:5px;"><p style="color:rgba(255,255,255,0.6); font-size:0.75rem; margin:0;">{datetime.now().strftime("%Y-%m-%d")}</p><p style="color:#D4AF37; font-size:0.85rem; font-weight:bold; margin:0;">{t("contract_dashboard", lang)}</p></div>', unsafe_allow_html=True)

    # 4. Floating List Overlay
    if st.session_state.get('notif_panel_open') and notifs:
        st.markdown(f"""
<div style="background:rgba(10,14,26,0.98); backdrop-filter:blur(30px); border:1px solid #D4AF37; 
            border-radius:18px; padding:20px; box-shadow:0 30px 100px rgba(0,0,0,0.95); margin: 0 5%; z-index:99999; direction:rtl; max-height:500px; overflow-y:auto;">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px; border-bottom:1px solid rgba(212,175,55,0.2); padding-bottom:10px;">
        <h4 style="color:#D4AF37; margin:0;">🔔 الإشعارات الواردة</h4>
        <div style="background:#D4AF37; color:black; border-radius:10px; padding:2px 10px; font-weight:bold;">{notif_count}</div>
    </div>
""", unsafe_allow_html=True)
        
        for n in reversed(notifs[-10:]):
            msg_html = n['msg'].replace('\n', '<br>')
            st.markdown(f"""
<div style="background:rgba(255,255,255,0.04); padding:12px 15px; border-radius:12px; margin-bottom:10px; border-right:3px solid #D4AF37; direction:rtl;">
    <p style="margin:0 0 5px 0; font-weight:700; color:#D4AF37; font-size:0.95rem;">{n['title']}</p>
    <p style="margin:0 0 5px 0; color:#EEE; font-size:0.85rem; line-height:1.8;">{msg_html}</p>
    <p style="margin:0; text-align:left; font-size:0.7rem; color:rgba(255,255,255,0.3);">⏰ {n['time']}</p>
</div>
""", unsafe_allow_html=True)
            
        if st.button("🗑️ مسح الكل", use_container_width=True, key="clear_all_notifs"):
            st.session_state.notifications = []
            st.session_state.notif_panel_open = False
            st.rerun()
            
        # Audio Diagnostic Button
        if st.checkbox("⚙️ تجربة صوت التنبيه", key="cb_test_sound"):
            st.session_state.test_sound = True
            st.rerun()
            
        st.markdown("</div>", unsafe_allow_html=True)

    # Hide the old CSS-based banner to avoid double rendering
    st.markdown('<style>.persistent-top-banner { display:none !important; }</style>', unsafe_allow_html=True)

    # Optional: Display notifications if there are any
    if st.session_state.notifications:
        with st.sidebar.expander("🔔 الإشعارات الجديدة", expanded=False):
            for n in reversed(st.session_state.notifications[-10:]):
                sidebar_msg = n['msg'].replace('\n', '<br>')
                st.markdown(f"""
<div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 10px; margin-bottom: 5px; border-right: 3px solid #D4AF37; direction:rtl;">
    <p style="margin:0; font-weight:bold; color:#D4AF37; font-size:0.9rem;">{n['title']}</p>
    <p style="margin:0; font-size:0.8rem; color:#FFF; line-height:1.7;">{sidebar_msg}</p>
    <p style="margin:0; font-size:0.7rem; color:rgba(255,255,255,0.4); text-align:left;">⏰ {n['time']}</p>
</div>
""", unsafe_allow_html=True)
            if st.button("🗑️ مسح الإشعارات", use_container_width=True):
                st.session_state.notifications = []
                st.rerun()

def dashboard():
    user = st.session_state.user
    lang = st.session_state.lang
    
    # Welcome Message - Premium Luxury Overlay (2026 Style, JS auto-remove)
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
            12%  {{ opacity:1; }}
            78%  {{ opacity:1; }}
            100% {{ opacity:0; pointer-events:none; }}
        }}
        @keyframes wSlideUp {{
            0%   {{ transform:translateY(40px) scale(0.95); opacity:0; }}
            12%  {{ transform:translateY(0)    scale(1);    opacity:1; }}
            78%  {{ transform:translateY(0)    scale(1);    opacity:1; }}
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
            background:rgba(4,7,16,0.87);
            backdrop-filter:blur(16px);
            -webkit-backdrop-filter:blur(16px);
            display:flex; align-items:center; justify-content:center;
            animation: wFadeIn 3.2s cubic-bezier(.4,0,.2,1) forwards;
            pointer-events:all;
        }}
        #lux-welcome-card {{
            background:linear-gradient(160deg,#0d1220,#090e1d,#0e1428);
            border:1px solid rgba(212,175,55,0.22);
            border-radius:28px;
            padding:52px 68px;
            max-width:520px; width:90%; min-width: 290px;
            text-align:center;
            position:relative; overflow:hidden;
            animation:wSlideUp 3.2s cubic-bezier(.4,0,.2,1) forwards;
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
                el.style.transition = 'opacity 0.6s ease';
                setTimeout(function() {{ if (el.parentNode) el.parentNode.removeChild(el); }}, 600);
            }}
        }}, 3000);
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
        
        # Determine Bengali Supply Visibility
        user_perms = user.get("permissions", [])
        if "all" in user_perms or "bengali_supply" in user_perms:
            if st.button("🇧🇩 " + t("bengali_supply_title", lang), key="btn_bengali_supply_main", use_container_width=True):
                st.session_state.page = "bengali_supply"
                st.rerun()
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
        
        st.markdown('<div id="live-monitor-trigger" style="display:none;">', unsafe_allow_html=True)
        if st.button("Heartbeat", key="background_heartbeat_btn"):
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # --- Monitor Status Indicator ---
        sync_time = st.session_state.get('last_sync_time', '--:--:--')
        st.markdown(f"""
        <div style="background:rgba(212,175,55,0.05); border:1px solid rgba(212,175,55,0.1); border-radius:10px; padding:10px; margin-top:20px;">
            <div style="display:flex; align-items:center; gap:8px; font-size:0.75rem; color:rgba(255,255,255,0.6);">
                <div style="width:8px; height:8px; background:#4CAF50; border-radius:50%; box-shadow:0 0 10px #4CAF50; animation: pulse 2s infinite;"></div>
                <span>المراقب المباشر يعمل: {sync_time}</span>
            </div>
        </div>
        <style>
            @keyframes pulse {{
                0% {{ transform:scale(0.95); box-shadow:0 0 0 0 rgba(76,175,80,0.7); }}
                70% {{ transform:scale(1); box-shadow:0 0 0 10px rgba(76,175,80,0); }}
                100% {{ transform:scale(0.95); box-shadow:0 0 0 0 rgba(76,175,80,0); }}
            }}
        </style>
        """, unsafe_allow_html=True)
        
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

    # --- Check Notifications first ---
    check_notifications()

    # --- Render Global Top Banner (Persistent) ---
    render_top_banner()

    # Admin Debug
    if user.get("role") == "admin":
        with st.sidebar.expander(t("debug", lang)):
            if st.button(t("test_db", lang)):
                try:
                    st.session_state.db.connect()
                    d = st.session_state.db.fetch_data(force=True)
                    st.write(f"Rows: {len(d)}")
                    if not d.empty: st.write(d.columns.tolist())
                except Exception as e:
                    st.error(f"Err: {e}")

    page = st.session_state.get('page', 'dashboard')
    
    if page == "dashboard": render_dashboard_content()
    elif page == "search": render_search_content()
    elif page == "translator": render_translator_content()
    elif page == "customer_requests":
        if user.get("role") == "viewer":
            st.error("🔒 لا تملك صلاحية الوصول لهذه الصفحة" if lang == 'ar' else "🔒 Access Denied")
            st.session_state.page = "dashboard"
            st.rerun()
        render_customer_requests_content()
    elif page == "order_processing": render_order_processing_content()
    elif page == "permissions": render_permissions_content()
    elif page == "bengali_supply": render_bengali_supply_content()
    elif page == "whatsapp_marketing": render_whatsapp_page()

def render_dashboard_content():
    lang = st.session_state.lang
    st.markdown('<div class="programmer-signature-neon">By: Alsaeed Alwazzan (v2.1)</div>', unsafe_allow_html=True)
    st.title(f" {t('contract_dashboard', lang)}")
    
    # Show loader while fetching data
    loading_placeholder = show_loading_hourglass()
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
        visible_cols = [c for c in cols if not str(c).startswith('__')]
        st.error(f"?? Error: Could not find the 'Contract End' column. Please check your spreadsheet headers. Available columns: {visible_cols}")
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
    
    cv_col = next((c for c in cols if any(kw in clean_col(c) for kw in ["cv", "سيرة", "download"])), None)
    
    # Configuration for LinkColumn needs the TRANSLATED column name if we rename it!
    # But Streamlit LinkColumn config keys must match the dataframe columns.
    
    t1, t2, t3 = st.tabs([t("tabs_urgent", lang), t("tabs_expired", lang), t("tabs_active", lang)])
    
    def show(data, tab_id):
        if not data: st.info(t("no_data", lang)); return
        d = pd.DataFrame(data)
        
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
                final_cfg[f"🚩_{col}"] = st.column_config.ImageColumn(" ", width="small")

        # Apply Green Text Styling
        styled_final = style_df(d_final)
        
        event = st.dataframe(
            styled_final, 
            use_container_width=True, 
            column_config=final_cfg,
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
            xl_data = create_pasha_whatsapp_excel(pd.DataFrame(stats['urgent']))
            if xl_data:
                xl_buf, xl_df = xl_data
                render_pasha_export_button(xl_df, "📤 تصدير للواتساب", "Urgent_WhatsApp.xlsx", "المرشحين_العاجل", key="btn_exp_urgent")
        show(stats['urgent'], "urgent")
        
    with t2: 
        c_exp_1, c_exp_2 = st.columns([4, 1])
        with c_exp_2:
            xl_data = create_pasha_whatsapp_excel(pd.DataFrame(stats['expired']))
            if xl_data:
                xl_buf, xl_df = xl_data
                render_pasha_export_button(xl_df, "📤 تصدير للواتساب", "Expired_WhatsApp.xlsx", "المرشحين_المنتهية", key="btn_exp_expired")
        show(stats['expired'], "expired")
        
    with t3: 
        c_exp_1, c_exp_2 = st.columns([4, 1])
        with c_exp_2:
            xl_data = create_pasha_whatsapp_excel(pd.DataFrame(stats['active']))
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
                # Sort Results
                res = res.sort_values(by='__days_sort', ascending=True)
            else:
                # FALLBACK SORT BY TIMESTAMP (REGISTRATION DATE)
                ts_col = next((c for c in res_cols if any(kw in clean_col(c) for kw in ["timestamp", "طابع", "تاريخ التسجيل"])), None)
                if ts_col:
                    try:
                        # Temporary numeric sort
                        res['__ts_sort'] = pd.to_datetime(res[ts_col], errors='coerce')
                        res = res.sort_values(by='__ts_sort', ascending=False)
                        res = res.drop(columns=['__ts_sort'])
                    except:
                        pass
            
            # Show count in UI
            count_found = len(res)
            if count_found > 0:
                show_toast(f"{'تم العثور على' if lang == 'ar' else 'Found'} {count_found} {'نتائج من أصل' if lang == 'ar' else 'results out of'} {total_rows}", "success", container=search_notif)
            
            # Debug Panel (for diagnosing search issues)
            with st.expander("🔧 تشخيص البحث | Search Debug", expanded=False):
                debug = eng.last_debug
                st.json(debug)
            
            # Handle both DataFrame and list returns
            is_empty = (isinstance(res, list) and len(res) == 0) or (hasattr(res, 'empty') and res.empty)
            
            if is_empty:
                show_toast(t("no_results", lang), "warning", container=search_notif)
            elif query and count_found == total_rows:
                show_toast("تنبيه: البحث أرجع جميع النتائج. تحقق من تشخيص البحث أعلاه." if lang == 'ar' else "Warning: Search returned all results. Check debug panel above.", "warning", container=search_notif)
            
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
                    column_config[f"🚩_{col}"] = st.column_config.ImageColumn(" ", width="small")

            # --- EXPORT BUTTON FOR SEARCH ---
            c_s_1, c_s_2 = st.columns([4, 1])
            with c_s_2:
                xl_result_search = create_pasha_whatsapp_excel(res)
                if xl_result_search:
                    xl_buf_search, _ = xl_result_search
                    st.download_button("📤 تصدير للواتساب", xl_buf_search, f"Search_WhatsApp_{datetime.now().strftime('%M%S')}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            
            # Use on_select to capture row selection
            df_height = min((len(res_display) + 1) * 35 + 40, 600)
            event = st.dataframe(
                style_df(res_display), 
                use_container_width=True,
                on_select="rerun",
                selection_mode="single-row",
                hide_index=True,
                column_config=column_config,
                key="search_results_table",
                height=df_height
            )

            # Handle Selection with Safety Check
            if event.selection and event.selection.get("rows"):
                selected_idx = event.selection["rows"][0]
                if 0 <= selected_idx < len(res):
                    worker_row = res.iloc[selected_idx]
                    render_cv_detail_panel(worker_row, selected_idx, lang, key_prefix="search")
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
                mime = uploaded_photo.type
                avatar_bytes = uploaded_photo.read()
                avatar_b64 = base64.b64encode(avatar_bytes).decode()
                full_uri = f"data:{mime};base64,{avatar_b64}"
                if st.button("💾 " + ("حفظ الصورة" if lang == 'ar' else "Save Photo"), key="save_avatar_btn"):
                    st.session_state.auth.update_avatar(selected_user, full_uri)
                    show_toast("✅ " + ("تم حفظ الصورة بنجاح" if lang == 'ar' else "Photo saved successfully!"), "success")
                    st.rerun()

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
    st.dataframe(style_df(df_users), use_container_width=True)

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
    st.markdown('<div style="color: #D4AF37; font-weight: 600; margin-bottom: 5px; font-family: \'Cairo\', sans-serif;">(AI) البحث الذكي</div>', unsafe_allow_html=True)
    
    with st.expander("🔍 " + ("تصفية متقدمة" if lang == 'ar' else "Advanced Filtering"), expanded=False):
        # 1. Row: Scheduling & Dates
        st.markdown(f'<div style="color: #888; margin-bottom: 10px;">{"📅 جدولة وتواريخ" if lang == 'ar' else "📅 Scheduling & Dates"}</div>', unsafe_allow_html=True)
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
        st.markdown(f'<div style="color: #888; margin-top: 15px; margin-bottom: 10px;">{"⚙️ تصفية ذكية متقدمة" if lang == 'ar' else "⚙️ Advanced Smart Filtering"}</div>', unsafe_allow_html=True)
        sc1, sc2, sc3 = st.columns(3)
        with sc3:
            expired_only = st.checkbox("العقود المنتهية" if lang == 'ar' else "Expired Contracts", key="op_expired")
        with sc2:
            not_working_only = st.checkbox("No (هل يعمل حالياً؟)" if lang == 'ar' else "No (Working Now?)", key="op_not_working")
        with sc1:
            st.markdown(f'<div style="font-size: 0.8rem; color: #888;">{"عدد نقل الكفالة" if lang == 'ar' else "Transfer Count"}</div>', unsafe_allow_html=True)
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
    c_weekly_holiday = find_cust_col(["holiday"]) or find_cust_col(["اجازة"])
    c_notes = find_cust_col(["notes"]) or find_cust_col(["ملاحظات"])
    
    # --- Worker Column Names ---
    w_name_col = next((c for c in workers_df.columns if "full name" in c.lower()), None)
    w_nationality_col = next((c for c in workers_df.columns if c.strip().lower() == "nationality"), None)
    w_gender_col = next((c for c in workers_df.columns if c.strip().lower() == "gender"), None)
    w_job_col = next((c for c in workers_df.columns if "job" in c.lower() and "looking" in c.lower()), None)
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
        w_job = normalize(worker_job)
        if not c_job or not w_job: return True
        
        tm = st.session_state.get('tm')
        search_terms = {normalize(c_job)}
        if tm:
            bundles = tm.analyze_query(c_job)
            for b in bundles:
                for s in b:
                    search_terms.add(normalize(s))
                    
        for term in search_terms:
            if not term: continue
            if term in w_job or w_job in term:
                return True
            parts = re.split(r'[\s|,،\-–]+', term)
            for p in parts:
                p = p.strip()
                if len(p) > 1 and (p in w_job or w_job in p):
                    return True
        return False
    
    def match_city(customer_location, worker_city):
        c_loc = str(customer_location).strip()
        w_city_val = normalize(worker_city)
        if not c_loc or not w_city_val: return True
        
        tm = st.session_state.get('tm')
        search_terms = {normalize(c_loc)}
        if tm:
            bundles = tm.analyze_query(c_loc)
            for b in bundles:
                for s in b:
                    search_terms.add(normalize(s))
                    
        for term in search_terms:
            if not term: continue
            if term in w_city_val or w_city_val in term:
                return True
            parts = re.split(r'[\s|,،\-–]+', term)
            for p in parts:
                p = p.strip()
                if len(p) > 1 and (p in w_city_val or w_city_val in p):
                    return True
        return False
    
    def find_matching_workers(customer_row):
        """Find workers. Returns (all_matches, all_scores, city_count)."""
        city_matches, city_scores = [], []
        other_matches, other_scores = [], []
        
        for _, worker in workers_df.iterrows():
            score = 0
            total_criteria = 0
            city_matched = False
            
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
            
            if c_work_nature and w_job_col:
                cv = str(customer_row.get(c_work_nature, ""))
                wv = str(worker.get(w_job_col, ""))
                if cv.strip():
                    total_criteria += 1
                    if match_job(cv, wv): score += 1
            
            if c_location and w_city_col:
                cv = str(customer_row.get(c_location, ""))
                wv = str(worker.get(w_city_col, ""))
                if cv.strip():
                    total_criteria += 1
                    if match_city(cv, wv):
                        score += 1
                        city_matched = True
            
            if total_criteria > 0 and score >= 1:
                pct = int((score / total_criteria) * 100)
                if city_matched:
                    city_matches.append(worker)
                    city_scores.append(pct)
                else:
                    other_matches.append(worker)
                    other_scores.append(pct)
        
        # Sort each group by: 1. Score (desc), 2. Timestamp (desc)
        def get_sort_key(score, worker):
            ts_val = pd.NaT
            if w_timestamp_col:
                raw_ts = str(worker.get(w_timestamp_col, ""))
                clean_ts = raw_ts.replace('م', 'PM').replace('ص', 'AM')
                ts_val = pd.to_datetime(clean_ts, errors='coerce')
            return (-score, -ts_val.timestamp() if pd.notnull(ts_val) else 0)

        if city_matches:
            # zip(scores, workers) -> sort by get_sort_key
            items = sorted(zip(city_scores, city_matches), key=lambda x: get_sort_key(x[0], x[1]))
            city_scores = [it[0] for it in items]
            city_matches = [it[1] for it in items]
            
        if other_matches:
            items = sorted(zip(other_scores, other_matches), key=lambda x: get_sort_key(x[0], x[1]))
            other_scores = [it[0] for it in items]
            other_matches = [it[1] for it in items]
        
        return city_matches + other_matches, city_scores + other_scores, len(city_matches)

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

    def info_cell(icon, label_text, value, color="#F4F4F4", min_width="200px"):
        if not value or str(value).strip().lower() in ["nan", "none", ""]:
            return ""
        return f'<div style="background: rgba(255,255,255,0.04); padding: 12px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.06); margin: 5px; flex: 1 1 {min_width}; min-height: 80px; display: flex; flex-direction: column; justify-content: center;"><span style="color: #888; font-size: 0.8rem;">{label_text}</span><span style="color: {color}; font-size: 1.1rem; font-weight: 600; margin-top: 4px;">{icon} {value}</span></div>'

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
    
    # Loop over all customers
    for idx, customer_row in customers_df.iterrows():
        company_val = str(customer_row.get(c_company, "")) if c_company else ""
        responsible_val = str(customer_row.get(c_responsible, "")) if c_responsible else ""
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
            display_title = f"🏢 {company_val}" if user_role != "viewer" else "🏢 " + ("طلب عميل" if lang == 'ar' else f"Customer Request")
            
            # Start Neon Frame and Header
            st.markdown(f"""
<style>
@keyframes neonWhitePulseCard {{
    0% {{ box-shadow: 0 0 10px rgba(255, 255, 255, 0.3), 0 0 20px rgba(255, 255, 255, 0.1); }}
    100% {{ box-shadow: 0 0 20px rgba(255, 255, 255, 0.6), 0 0 40px rgba(255, 255, 255, 0.3); }}
}}
.neon-wrapper-card {{
    border: 1.5px solid rgba(255, 255, 255, 0.6);
    border-radius: 18px;
    padding: 15px;
    margin: 15px 0;
    background: rgba(10, 14, 26, 0.6);
    animation: neonWhitePulseCard 3s ease-in-out infinite alternate;
    direction: rtl;
}}
</style>
<div class="neon-wrapper-card">
    <div style="background: linear-gradient(90deg, rgba(255,255,255,0.1), transparent); 
                padding: 12px 20px; border-radius: 12px; border-right: 5px solid #FFFFFF; margin: 0 0 15px 0;
                box-shadow: 0 0 15px rgba(255,255,255,0.2);">
        <h3 style="color: #FFFFFF; margin: 0; font-family: 'Tajawal', sans-serif; text-shadow: 0 0 10px rgba(255,255,255,0.5);">
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
            
            info_html += info_cell("📍", t('work_location', lang), str(customer_row.get(c_location, "")))
            info_html += info_cell("💼", t('work_nature', lang), str(customer_row.get(c_work_nature, "")))
            info_html += info_cell("👤", t('responsible_name', lang), responsible_val)
            info_html += info_cell("👥", t('required_category', lang), str(customer_row.get(c_category, "")))
            info_html += info_cell("🔢", t('num_employees', lang), str(customer_row.get(c_num_emp, "")), "#D4AF37")
            
            if user_role != "viewer":
                info_html += info_cell("📱", t('mobile_number', lang), str(customer_row.get(c_mobile, "")))
            else:
                info_html += info_cell("🔒", t('mobile_number', lang), "********")
                
            info_html += info_cell("🌍", t('required_nationality', lang), str(customer_row.get(c_nationality, "")))
            info_html += info_cell("💰", t('expected_salary', lang), str(customer_row.get(c_salary, "")), "#00FF41")
            
            # --- New Requested Fields ---
            info_html += info_cell("🔄", t('transfer_days_after', lang), str(customer_row.get(c_transfer_days, "")))
            info_html += info_cell("⏳", t('working_hours', lang), str(customer_row.get(c_working_hours, "")))
            info_html += info_cell("🗓️", t('weekly_holiday', lang), str(customer_row.get(c_weekly_holiday, "")))
            
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
            matches, scores, city_count = find_matching_workers(customer_row)
            
            if not matches:
                st.warning("⚠️ " + t('no_matching_workers', lang))
            else:
                city_list = matches[:city_count]
                other_list = matches[city_count:]
                city_scores = scores[:city_count]
                other_scores = scores[city_count:]

                # Same City Table
                if city_list:
                    city_df, city_idx_map = build_worker_table(city_list, city_scores)
                    if not city_df.empty:
                        # --- EXPORT FOR ORDER PROCESSING ---
                        c_op_1, c_op_2 = st.columns([4, 1])
                        with c_op_2:
                            xl_data_op = create_pasha_whatsapp_excel(city_df)
                            if xl_data_op:
                                xl_buf_op, xl_df_op = xl_data_op
                                render_pasha_export_button(xl_df_op, "📤 تصدير للواتساب", f"Matched_Workers_City_{idx+1}.xlsx", 
                                                          f"Matched_Workers_City_{idx+1}", key=f"dl_op_city_{idx}")
                        
                        loc_val = str(customer_row.get(c_location, ""))
                        regional_keywords = [
                            "عسير", "الجنوب", "الشمال", "الشرقية", "منطقة", 
                            "الوسطى", "الغربية", "نجد", "الحجاز",
                            "region", "south", "north", "east", "asir", "central", "western"
                        ]
                        is_regional = any(kw in loc_val.lower() for kw in regional_keywords)
                        
                        if is_regional:
                            label = f"🗺️ عمال في منطقة {loc_val}" if lang == 'ar' else f"🗺️ Workers in {loc_val} Region"
                            color = "#D4AF37"
                            explainer = f"""<div style="font-size: 0.85rem; color: #888; margin-top: -8px; margin-bottom: 10px; margin-left: 10px; font-family: 'Cairo', sans-serif;">
                                {'هؤلاء العمال مناسبون لأن مدنهم تتبع لمنطقة ' if lang == 'ar' else 'These workers are matches because their cities belong to '} {loc_val}
                            </div>"""
                        else:
                            label = f"📍 عمال في نفس المدينة ({loc_val})" if lang == 'ar' else f"📍 Workers in the same city ({loc_val})"
                            color = "#D4AF37"
                            explainer = ""

                        st.markdown(f"""<div style="color: {color}; font-weight: 700; margin: 10px 5px;">{label} — {len(city_df)}</div>""", unsafe_allow_html=True)
                        if explainer: st.markdown(explainer, unsafe_allow_html=True)
                        
                        # Configure Image columns
                        col_cfg_city = {}
                        for col in city_df.columns:
                            if any(kw in str(col).lower() for kw in ["nationality", "الجنسية"]):
                                col_cfg_city[f"🚩_{col}"] = st.column_config.ImageColumn(" ", width="small")

                        # Use selection
                        df_city_height = min((len(city_df) + 1) * 35 + 40, 500)
                        event_city = st.dataframe(
                            style_df(city_df.drop(columns=["__uid"])),
                            use_container_width=True,
                            hide_index=True,
                            on_select="rerun",
                            selection_mode="single-row",
                            column_config=col_cfg_city,
                            key=f"op_city_table_{idx}",
                            height=df_city_height
                        )
                        
                        if event_city.selection and event_city.selection.get("rows"):
                            sel_row_idx = event_city.selection["rows"][0]
                            original_idx = city_idx_map[sel_row_idx]
                            worker_row = city_list[original_idx]
                            worker_uid = city_df.iloc[sel_row_idx]["__uid"]
                            
                            # Detail Panel
                            render_cv_detail_panel(worker_row, sel_row_idx, lang, key_prefix=f"op_city_{idx}", worker_uid=worker_uid)

                # Other Cities Table
                if other_list:
                    other_df, other_idx_map = build_worker_table(other_list, other_scores)
                    if not other_df.empty:
                        # --- EXPORT FOR OTHER WORKERS ---
                        c_op2_1, c_op2_2 = st.columns([4, 1])
                        with c_op2_2:
                            xl_data_other = create_pasha_whatsapp_excel(other_df)
                            if xl_data_other:
                                xl_buf_other, xl_df_other = xl_data_other
                                render_pasha_export_button(xl_df_other, "📤 تصدير للواتساب", f"Matched_Workers_Other_{idx+1}.xlsx", 
                                                          f"مرشحين_مطابقين_{idx+1}", key=f"dl_op_other_{idx}")
                        
                        label_other = "🌍 عمال في مدن أخرى مناسبين" if lang == 'ar' else f"🌍 Workers in other cities ({len(other_df)})"
                        st.markdown(f"""
                            <div style="background: rgba(255,255,255,0.02); padding: 5px 15px; border-radius: 8px; border-left: 3px solid #666; margin: 15px 0 5px 0;">
                                <h5 style="color: #F4F4F4; margin: 0; font-family: 'Cairo', sans-serif;">{label_other} — {len(other_df)}</h5>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        column_config_other = {}
                        
                        # Configure Image columns
                        col_cfg_other = {}
                        for col in other_df.columns:
                            if any(kw in str(col).lower() for kw in ["nationality", "الجنسية"]):
                                col_cfg_other[f"🚩_{col}"] = st.column_config.ImageColumn(" ", width="small")

                        df_other_height = min((len(other_df) + 1) * 35 + 40, 500)
                        event_other = st.dataframe(
                            style_df(other_df.drop(columns=["__uid"])),
                            use_container_width=True,
                            hide_index=True,
                            on_select="rerun",
                            selection_mode="single-row",
                            column_config=col_cfg_other,
                            key=f"op_other_table_{idx}",
                            height=df_other_height
                        )
                        
                        if event_other.selection and event_other.selection.get("rows"):
                            sel_row_idx = event_other.selection["rows"][0]
                            original_idx = other_idx_map[sel_row_idx]
                            worker_row = other_list[original_idx]
                            worker_uid = other_df.iloc[sel_row_idx]["__uid"]
                            
                            # Detail Panel
                            render_cv_detail_panel(worker_row, sel_row_idx, lang, key_prefix=f"op_other_{idx}", worker_uid=worker_uid)
                
                if (not city_list or build_worker_table(city_list, city_scores)[0].empty) and \
                   (not other_list or build_worker_table(other_list, other_scores)[0].empty):
                    st.info("تم إخفاء جميع العمال المطابقين لهذا الطلب.")

            # --- Hide Request Button ---
            col_h1, col_h2 = st.columns([1, 4])
            with col_h1:
                if st.button("🚫 " + ("إخفاء هذا الطلب" if lang == 'ar' else "Hide this request"), 
                             key=f"hide_client_btn_{idx}"):
                    st.session_state.op_hidden_clients.add(client_key)
                    st.rerun()

            st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
            st.divider()



def render_customer_requests_content():
    lang = st.session_state.lang
    st.markdown('<div class="programmer-signature-neon">By: Alsaeed Alwazzan</div>', unsafe_allow_html=True)
    st.title(f" {t('customer_requests_title', lang)}")
    
    loading_placeholder = show_loading_hourglass()
    try:
        # Fetch data using the specific method
        df = st.session_state.db.fetch_customer_requests()
        
        # Reverse the order so the newest requests are at the top
        if not df.empty:
            df = df[::-1].reset_index(drop=True)
    except Exception as e:
        loading_placeholder.empty()
        import traceback
        full_err = traceback.format_exc()
        err_msg = str(e)
        
        # Check if it looks like a permission or connection issue
        is_permission_error = any(kw in err_msg.lower() or kw in full_err.lower() 
                                for kw in ["403", "permission", "not found", "gspread", "api"])

        if not err_msg:
            err_msg = "Connection or Permission Error" if is_permission_error else "Technical Error (Details below)"
            
        st.error(f"{t('error', lang)}: {err_msg}")
        
        # Show setup instructions for ANY error in this module to be safe
        st.warning("⚠️ إعدادات الربط غير مكتملة أو الملف غير متاح")
        st.info("لحل هذه المشكلة، يرجى التأكد من **مشاركة (Share)** ملف الإكسل مع هذا البريد الإلكتروني كـ **Editor**:")
        st.code("sheet-bot@smooth-league-454322-p2.iam.gserviceaccount.com")
        
        with st.expander("Show Technical Details | تفاصيل الخطأ التقنية"):
            st.code(full_err)
            
        if "REPLACE_WITH_CUSTOMER_REQUESTS_SHEET_URL" in err_msg or "URL" in err_msg:
            st.info("⚠️ يرجى تزويد المبرمج برابط ملف جوجل شيت (Spreadsheet) الخاص بتبويب 'الردود' في النموذج لإتمام الربط.")
        
        st.markdown("""
        **خطوات التأكد من الربط:**
        1. افتح ملف جوجل شيت (الذي سجلت فيه ردود النموذج).
        2. اضغط على زر **Share** (مشاركة) في الزاوية العلوية.
        3. انسخ هذا الإيميل: `sheet-bot@smooth-league-454322-p2.iam.gserviceaccount.com`
        4. أضف الإيميل وتأكد من اختيار **Editor** (محرر).
        5. اضغط على زر **Send** (إرسال).
        6. عد هنا وقم بـ **تحديث الصفحة (Refresh)**.
        """)
        return

    loading_placeholder.empty()

    # ────── Advanced Filters for Matching ──────
    lbl_age = t("age", lang)
    lbl_contract = t("contract_end", lang)
    lbl_reg = t("registration_date", lang)
    lbl_enable = "تفعيل" if lang == "ar" else "Activate"
    
    with st.expander(t("advanced_filters", lang) if t("advanced_filters", lang) != "advanced_filters" else "تصفية متقدمة", expanded=False):
        
        # Row 1: Date & Range Filters
        st.markdown(f'<div class="premium-filter-label">📅 {t("filter_dates_group", lang)}</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        
        with c1:
            use_age = st.checkbox(f" {lbl_enable} {lbl_age}", key="cr_use_age_filter")
            if use_age:
                ac1, ac2 = st.columns(2)
                with ac1:
                    a_min = st.number_input("من سن" if lang == 'ar' else "From", 1, 100, 16, key="cr_age_min")
                with ac2:
                    a_max = st.number_input("إلى سن" if lang == 'ar' else "To", 1, 100, 35, key="cr_age_max")
                age_range = (a_min, a_max)
            else: 
                age_range = (16, 35)

        with c2:
            use_contract = st.checkbox(f" {lbl_enable} {lbl_contract}", key="cr_use_contract_filter")
            if use_contract:
                contract_range = st.date_input("Contract Range", (datetime.now().date(), datetime.now().date() + timedelta(days=30)), label_visibility="collapsed", key="cr_contract_range")
            else: contract_range = []

        with c3:
            use_reg = st.checkbox(f" {lbl_enable} {lbl_reg}", key="cr_use_reg_filter")
            if use_reg:
                reg_range = st.date_input("Registration Range", (datetime.now().date().replace(day=1), datetime.now().date()), label_visibility="collapsed", key="cr_reg_range")
            else: reg_range = []

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f'<div class="premium-filter-label">⚙️ {t("filter_advanced_group", lang)}</div>', unsafe_allow_html=True)
        
        # Row 2: Status & Dropdown Filters
        c2_1, c2_2, c2_3 = st.columns(3)
        
        with c2_1:
            use_expired = st.checkbox(t("expired", lang), key="cr_use_expired_filter")
            if use_expired:
                st.caption("⚠️ " + ("ترتيب من الأقدم" if lang == "ar" else "Sorting Oldest first"))
        
        with c2_2:
            use_not_working = st.checkbox("No (هل يعمل حالياً؟)" if lang == "ar" else "Not Working (No)", key="cr_use_not_working_filter")
            
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
                key="cr_transfer_count_dropdown"
            )
            selected_transfer_key = [k for k, v in transfer_options.items() if v == selected_transfer_label][0]
        
        # Row 3: Huroob & Outside City Filters
        st.markdown("<br>", unsafe_allow_html=True)
        c3_1, c3_2 = st.columns(2)
        with c3_1:
            use_no_huroob = st.checkbox(t("no_huroob", lang), key="cr_use_no_huroob_filter")
        with c3_2:
            use_work_outside = st.checkbox(t("work_outside_city", lang), key="cr_use_work_outside_filter")

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
    if use_expired: filters['expired_only'] = True
    if use_not_working: filters['not_working_only'] = True
    if use_no_huroob: filters['no_huroob'] = True
    if use_work_outside: filters['work_outside_city'] = True
    if selected_transfer_key: filters['transfer_count'] = selected_transfer_key

    if df.empty:
        st.warning(t("no_data", lang))
        return

    # Similar display logic to the search results
    res = df.copy()
    
    # Rename columns before showing
    new_names = {}
    used_names = set()
    for c in res.columns:
        new_name = t_col(c, lang)
        original_new_name = new_name
        counter = 1
        while new_name in used_names:
            counter += 1
            new_name = f"{original_new_name} ({counter})"
        used_names.add(new_name)
        new_names[c] = new_name
        
    res.rename(columns=new_names, inplace=True)
    res = clean_date_display(res)
    
    # Hide internal columns
    res_display = res.copy()
    for int_col in ["__sheet_row", "__sheet_row_backup"]:
        if int_col in res_display.columns:
            res_display = res_display.drop(columns=[int_col])
    # White Neon Glow Frame around Customer Requests Table
    st.dataframe(
        style_df(res_display), 
        use_container_width=True,
        hide_index=True,
        key="customer_requests_table"
    )

    # ═══════════════════════════════════════════════════════════
    # Candidate Matching Section
    # ═══════════════════════════════════════════════════════════
    st.divider()
    match_title = "🔎 مطابقة المرشحين مع طلب العميل" if lang == "ar" else "🔎 Match Candidates to Request"
    st.markdown(f"### {match_title}")

    # Row selector
    row_count = len(df)
    if row_count == 0:
        return

    select_label = "اختر رقم الطلب للمطابقة:" if lang == "ar" else "Select request row to match:"
    selected_idx = st.selectbox(
        select_label,
        options=list(range(row_count)),
        format_func=lambda i: f"{'طلب' if lang == 'ar' else 'Request'} #{row_count - i}",
        key="matcher_row_select"
    )

    # Show selected request details in an expander
    selected_row = df.iloc[selected_idx]
    with st.expander("📋 " + ("تفاصيل الطلب المحدد" if lang == "ar" else "Selected Request Details"), expanded=False):
        for col_name, val in selected_row.items():
            if str(col_name).startswith("__"):
                continue
            st.markdown(f"**{t_col(col_name, lang)}:** {val}")

    # Row management (Delete & Match)
    st.markdown("<br>", unsafe_allow_html=True)
    c_m1, c_m2 = st.columns([1, 1])
    
    with c_m1:
        # Match button
        match_btn_label = "🚀 بحث ومطابقة المرشحين" if lang == "ar" else "🚀 Search & Match Candidates"
        run_match = st.button(match_btn_label, key="run_matcher_btn", use_container_width=True, type="primary")

    with c_m2:
        # Modern Deletion UI using Popover
        with st.popover("🗑️ " + ("حذف هذا الطلب" if lang == "ar" else "Delete this Request"), use_container_width=True):
            st.warning("⚠️ " + ("هل أنت متأكد من حذف هذا الطلب نهائياً؟" if lang == "ar" else "Are you sure you want to delete this permanently?"))
            if st.button("نعم، حذف", key=f"btn_confirm_del_{selected_idx}", use_container_width=True, type="primary"):
                sheet_url = "https://docs.google.com/spreadsheets/d/1ZlLGXqbFSnKrr2J-PRnxRhxykwrNOgOE6Mb34Zei_FU/edit"
                row_to_del = selected_row.get("__sheet_row")
                if row_to_del:
                    with st.spinner("جارِ الحذف..." if lang == "ar" else "Deleting..."):
                        success = st.session_state.db.delete_row(row_to_del, url=sheet_url)
                        if success:
                            st.success("تم الحذف بنجاح" if lang == "ar" else "Deleted successfully")
                            # Force database refresh after deletion
                            st.session_state.db.fetch_customer_requests(force=True)
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("فشل في الحذف" if lang == "ar" else "Failed to delete")

    if run_match:
        with st.spinner("جارٍ البحث عن مرشحين مطابقين..." if lang == "ar" else "Searching for matching candidates..."):
            try:
                # Fetch candidates (main workers database)
                candidates_df = st.session_state.db.fetch_data()

                if candidates_df is None or candidates_df.empty:
                    st.error("❌ " + ("لا توجد بيانات مرشحين في قاعدة البيانات" if lang == "ar" else "No candidate data in the database"))
                else:
                    # Pre-filter using SmartSearchEngine if any filters are active
                    if filters:
                        eng = SmartSearchEngine(candidates_df)
                        filtered_df = eng.search("", filters=filters)
                        # Handle potential empty results from filters
                        if filtered_df.empty:
                            st.warning("⚠️ " + ("لا توجد مرشحين يطابقون التصفية المتقدمة. يرجى تخفيف الشروط." if lang == "ar" else "No candidates match the advanced filters. Please broaden your criteria."))
                            return
                        candidates_to_match = filtered_df
                    else:
                        candidates_to_match = candidates_df

                    # Run the matcher
                    matcher = CandidateMatcher(candidates_to_match)
                    result = matcher.match(selected_row)

                    # Format and display
                    summary_md, status_md, alt_table_md, result_df = format_match_result(result, lang)

                    st.markdown("---")
                    st.markdown(summary_md)
                    st.markdown(status_md)

                    if not result_df.empty:
                        # Clean result columns for display
                        display_df = result_df.copy()
                        for int_col in ["__sheet_row", "__sheet_row_backup"]:
                            if int_col in display_df.columns:
                                display_df = display_df.drop(columns=[int_col])

                        # Rename columns for display
                        disp_names = {}
                        disp_used = set()
                        for c in display_df.columns:
                            new_n = t_col(c, lang)
                            orig_n = new_n
                            cnt = 1
                            while new_n in disp_used:
                                cnt += 1
                                new_n = f"{orig_n} ({cnt})"
                            disp_used.add(new_n)
                            disp_names[c] = new_n
                        display_df.rename(columns=disp_names, inplace=True)

                        # Configure Image columns
                        col_cfg_match = {}
                        for col in display_df.columns:
                            if any(kw in str(col).lower() for kw in ["nationality", "الجنسية"]):
                                col_cfg_match[f"🚩_{col}"] = st.column_config.ImageColumn(" ", width="small")

                        st.dataframe(
                            style_df(display_df),
                            use_container_width=True,
                            hide_index=True,
                            column_config=col_cfg_match,
                            key="matcher_results_table"
                        )
                        
                    if alt_table_md:
                        st.markdown(alt_table_md)

                    # Debug info (collapsible)
                    with st.expander("🛠️ " + ("معلومات التشخيص" if lang == "ar" else "Debug Info")):
                        st.json(matcher.debug_info)

            except Exception as match_err:
                import traceback
                st.error(f"❌ {'خطأ في المطابقة' if lang == 'ar' else 'Matching Error'}: {match_err}")
                with st.expander("تفاصيل الخطأ"):
                    st.code(traceback.format_exc())


def render_bengali_supply_content():
    lang = st.session_state.lang
    bm = BengaliDataManager()
    
    def normalize_ar(text):
        if not text: return ""
        t = str(text).lower().strip()
        t = t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
        t = t.replace("ة", "ه").replace("ى", "ي")
        t = t.replace("ئ", "ي").replace("ؤ", "و").replace("ء", "")
        return t
    
    st.markdown(f'<div class="luxury-main-title">{t("bengali_supply_title", lang)}</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs([t("form_supplier_employer", lang), t("form_worker_details", lang), t("search_manage_title", lang)])
    
    with tab1:
        st.markdown(f'### 🏗️ {t("form_supplier_employer", lang)}')
        
        # We split the form into two columns, each with its own form
        col_sup, col_emp = st.columns(2)
        
        with col_sup:
            with st.container(border=True):
                st.markdown(f"#### 📦 إضافة مورد جديد")
                with st.form("supplier_only_form", clear_on_submit=True):
                    st.markdown(f"**👤 {t('supplier_name', lang)}**")
                    s_name = st.text_input(t("supplier_name", lang), label_visibility="collapsed")
                    st.markdown(f"**📞 {t('supplier_phone', lang)}**")
                    s_phone = st.text_input(t("supplier_phone", lang), label_visibility="collapsed")
                    
                    if st.form_submit_button(t("add_supplier_btn", lang) + " المورد", use_container_width=True):
                        if s_name:
                            bm.add_supplier({"name": s_name, "phone": s_phone})
                            st.session_state['_notif_supplier'] = ("success", f"تم إضافة المورد: {s_name} بنجاح" if lang == 'ar' else f"Supplier {s_name} added!")
                        else:
                            st.session_state['_notif_supplier'] = ("error", "يرجى إدخال اسم المورد على الأقل" if lang == 'ar' else "Please enter supplier name")
                
                # Show notification Contextually below the form
                sup_notif = st.empty()
                if st.session_state.get('_notif_supplier'):
                    typ, msg = st.session_state.pop('_notif_supplier')
                    show_toast(msg, typ, container=sup_notif)

        with col_emp:
            with st.container(border=True):
                st.markdown(f"#### 🏢 إضافة عميل (صاحب عمل) جديد")
                with st.form("employer_only_form", clear_on_submit=True):
                    st.markdown(f"**🏢 {t('employer_name', lang)}**")
                    e_name = st.text_input(t("employer_name", lang), label_visibility="collapsed")
                    st.markdown(f"**☕ {t('cafe_name', lang)}**")
                    e_cafe = st.text_input(t("cafe_name", lang), label_visibility="collapsed")
                    st.markdown(f"**📱 {t('employer_mobile', lang)}**")
                    e_mobile = st.text_input(t("employer_mobile", lang), label_visibility="collapsed")
                    st.markdown(f"**📍 {t('city', lang)}**")
                    e_city = st.text_input(t("city", lang), label_visibility="collapsed")
                    
                    if st.form_submit_button(t("add_supplier_btn", lang) + " صاحب العمل", use_container_width=True):
                        if e_name:
                            bm.add_employer({"name": e_name, "cafe": e_cafe, "mobile": e_mobile, "city": e_city})
                            st.session_state['_notif_employer'] = ("success", f"تم إضافة صاحب العمل: {e_name} بنجاح" if lang == 'ar' else f"Employer {e_name} added!")
                        else:
                            st.session_state['_notif_employer'] = ("error", "يرجى إدخال اسم صاحب العمل على الأقل" if lang == 'ar' else "Please enter employer name")
                
                # Show notification Contextually below the form
                emp_notif = st.empty()
                if st.session_state.get('_notif_employer'):
                    typ, msg = st.session_state.pop('_notif_employer')
                    show_toast(msg, typ, container=emp_notif)

    with tab2:
        st.markdown(f'### 👷 {t("form_worker_details", lang)}')
        suppliers = bm.get_suppliers()
        employers = bm.get_employers()
        
        # Robust option building with default empty states
        s_options = []
        for s in suppliers:
            if isinstance(s, dict):
                s_name = s.get("name", "N/A")
                s_phone = s.get("phone", "")
                s_options.append(f"{s_name} ({s_phone})")
                
        e_options = []
        for e in employers:
            if isinstance(e, dict):
                e_name = e.get("name", "N/A")
                e_cafe = e.get("cafe", "N/A")
                e_city = e.get("city", "")
                e_options.append(f"{e_name} - {e_cafe} ({e_city})")
        
        if not s_options or not e_options:
            st.warning("⚠️ يجب إضافة مورد واحد وعميل (صاحب عمل) واحد على الأقل في التبويب الأول قبل التمكن من إضافة عامل.")
            if st.button("انتقل لإضافة مورد أو عميل"):
                # Use a hack to switch tab? Or just tell them.
                st.info("الرجاء الضغط على تبويب 'إضافة مورد وصاحب عمل' في الأعلى")
        
        with st.form("worker_entry_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Name - الاسم**")
                w_name = st.text_input(t("worker_name", lang), label_visibility="collapsed", key="w_name_in")
                st.markdown(f"**Mobile - الجوال**")
                w_mobile = st.text_input(t("worker_phone", lang), label_visibility="collapsed", key="w_mob_in")
            with c2:
                st.markdown(f"**ID/Passport - الهوية أو الجواز**")
                w_id = st.text_input(t("worker_passport_iqama", lang), label_visibility="collapsed", key="w_id_in")
            
            st.markdown("---")
            cc1, cc2 = st.columns(2)
            with cc1:
                st.markdown(f"**📦 {t('supplier_name', lang)}**")
                selected_s = st.selectbox(t("select_supplier", lang), s_options, label_visibility="collapsed", key="sel_s")
            with cc2:
                st.markdown(f"**🏢 {t('employer_name', lang)}**")
                selected_e = st.selectbox(t("select_employer", lang), e_options, label_visibility="collapsed", key="sel_e")
            
            st.markdown(f"**Attachments - المرفقات**")
            uploaded_files = st.file_uploader(t("upload_multiple_imgs", lang), accept_multiple_files=True, type=['png', 'jpg', 'jpeg', 'pdf'], label_visibility="collapsed", key="w_files")
            
            st.markdown(f"**Files Notes - ملاحظات المرفقات**")
            f_notes = st.text_area(t("notes_files", lang), label_visibility="collapsed", key="w_f_notes")
            
            st.markdown(f"**General Notes - ملاحظات عامة**")
            g_notes = st.text_area(t("general_notes", lang), label_visibility="collapsed", key="w_g_notes")
            
            if st.form_submit_button(t("add_worker_btn", lang), use_container_width=True):
                if w_name and (sel_s if s_options else True) and (sel_e if e_options else True):
                    # Save files physically
                    saved_files = []
                    if uploaded_files:
                        import uuid
                        upload_dir = os.path.join(BASE_DIR, "uploads", "bengali")
                        os.makedirs(upload_dir, exist_ok=True)
                        # We don't have the worker UUID yet, so generate a folder name based on time + random
                        import tempfile
                        worker_folder = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:6]}"
                        target_dir = os.path.join(upload_dir, worker_folder)
                        os.makedirs(target_dir, exist_ok=True)
                        
                        for uf in uploaded_files:
                            file_path = os.path.join(target_dir, uf.name)
                            try:
                                with open(file_path, "wb") as f:
                                    f.write(uf.getvalue())
                                # Store relative path or just information for retrieval
                                saved_files.append({"name": uf.name, "path": file_path})
                            except Exception as e:
                                print(f"Error saving worker file: {e}")

                    worker_data = {
                        "name": w_name,
                        "mobile": w_mobile,
                        "id": w_id,
                        "supplier": sel_s if s_options else "",
                        "employer": sel_e if e_options else "",
                        "file_notes": f_notes,
                        "general_notes": g_notes,
                        "files": saved_files,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    bm.add_worker(worker_data)
                    st.session_state['_notif_worker'] = ("success", t("save_success", lang))
                    st.rerun()
                else:
                    st.session_state['_notif_worker'] = ("error", "يرجى إكمال بيانات العامل واختيار المورد وصاحب العمل")
            
            # Show worker save notification Contextually below the form
            worker_save_notif = st.empty()
            if st.session_state.get('_notif_worker'):
                typ, msg = st.session_state.pop('_notif_worker')
                show_toast(msg, typ, container=worker_save_notif)

    with tab3:
        st.markdown(f"### {t('search_manage_title', lang)}")
        
        m_tab1, m_tab2, m_tab3 = st.tabs(["👷 " + ("العمال" if lang=='ar' else "Workers"), "📦 " + ("الموردون" if lang=='ar' else "Suppliers"), "🏢 " + ("أصحاب العمل" if lang=='ar' else "Employers")])
        
        user_perms = st.session_state.user.get('permissions', [])
        can_delete = "can_delete" in user_perms or "all" in user_perms
        
        # --- TAB 1: WORKERS ---
        with m_tab1:
            st.markdown("#### 🔍 البحث الموحد في كل بيانات العمال")
            st.caption("⌨️ اكتب أي اسم (عامل، مورد، عميل) أو رقم واضغط Enter")
            g_search = st.text_input("البحث الشامل", label_visibility="collapsed", key="bengali_global_search")
            
            workers_all = bm.get_workers()
            
            if g_search:
                q = normalize_ar(g_search)
                all_s = bm.get_suppliers()
                all_e = bm.get_employers()
                s_lookup = {f"{s['name']} ({s['phone']})": s for s in all_s}
                e_lookup = {f"{e['name']} - {e['cafe']} ({e['city']})": e for e in all_e}

                results = [w for w in workers_all if 
                           q in normalize_ar(w.get("name", "")) or 
                           q in normalize_ar(w.get("supplier", "")) or 
                           q in normalize_ar(w.get("employer", "")) or 
                           q in normalize_ar(w.get("mobile", "")) or 
                           q in normalize_ar(w.get("id", ""))]
                
                if results:
                    st.success(f"تم العثور على {len(results)} نتائج")
                    df_g = []
                    for w in sorted(results, key=lambda x: x.get("timestamp", ""), reverse=True):
                        s_info = s_lookup.get(w.get("supplier"), {})
                        e_info = e_lookup.get(w.get("employer"), {})
                        df_g.append({
                            "اسم العامل": w.get("name", ""),
                            "جوال العامل": w.get("mobile", ""),
                            "الهوية": w.get("id", ""),
                            "المورد": s_info.get("name", w.get("supplier")),
                            "صاحب العمل": e_info.get("name", w.get("employer")),
                            "التاريخ": w.get("timestamp", "")
                        })
                    df_bengali_search = pd.DataFrame(df_g)
                    col_cfg_b = {}
                    for col in df_bengali_search.columns:
                        if any(kw in str(col).lower() for kw in ["nationality", "الجنسية"]):
                            col_cfg_b[f"🚩_{col}"] = st.column_config.ImageColumn(" ", width="small")
                    
                    st.dataframe(style_df(df_bengali_search), use_container_width=True, hide_index=True, column_config=col_cfg_b)
                    
                    st.markdown("---")
                    for w in sorted(results, key=lambda x: x.get("timestamp", ""), reverse=True):
                        with st.expander(f"👷 {w.get('name', 'N/A')} - {w.get('id', '')}"):
                            w_uuid = w.get('worker_uuid')
                            c1, c2, c3 = st.columns(3)
                            s_info = s_lookup.get(w.get("supplier"), {})
                            e_info = e_lookup.get(w.get("employer"), {})

                            with c1:
                                st.markdown("**👤 بيانات العامل**")
                                st.write(f"الاسم: {w.get('name')}")
                                st.write(f"الجوال: {w.get('mobile')}")
                                st.write(f"الهوية: {w.get('id')}")
                            with c2:
                                st.markdown("**🏢 صاحب العمل**")
                                st.write(f"الاسم: {e_info.get('name', 'N/A')}")
                                st.write(f"المقهى: {e_info.get('cafe', 'N/A')}")
                            with c3:
                                st.markdown("**📦 المورد**")
                                st.write(f"الاسم: {s_info.get('name', 'N/A')}")
                            
                            # Images
                            saved_files = w.get("files", [])
                            if saved_files:
                                st.markdown("#### 📎 المرفقات")
                                img_cols = st.columns(2)
                                for i, sf in enumerate(saved_files):
                                    ic = img_cols[i % 2]
                                    path = sf.get("path")
                                    if path and os.path.exists(path):
                                        if path.lower().split(".")[-1] in ["jpg", "jpeg", "png", "webp"]:
                                            ic.image(path, use_column_width=True)
                            
                            if can_delete:
                                ec1, ec2 = st.columns(2)
                                with ec1:
                                    if st.button("🗑️ حذف العامل", key=f"del_worker_{w_uuid}", use_container_width=True):
                                        if bm.delete_worker(w_uuid):
                                            st.session_state['_notif_m_worker'] = ("success", "تم حذف العامل بنجاح ✅")
                                            st.rerun()
                                with ec2:
                                    show_edit = st.toggle("📝 تعديل البيانات", key=f"tog_edit_{w_uuid}")
                                
                                if show_edit:
                                    with st.form(f"edit_worker_form_{w_uuid}"):
                                        st.markdown("### 📝 تعديل بيانات العامل")
                                        en = st.text_input("Name", w.get("name", ""))
                                        em = st.text_input("Mobile", w.get("mobile", ""))
                                        ei = st.text_input("ID/Passport", w.get("id", ""))
                                        
                                        # Recalculate options for selectboxes
                                        cur_s_opts = [f"{s['name']} ({s['phone']})" for s in all_s]
                                        cur_e_opts = [f"{e['name']} - {e['cafe']} ({e['city']})" for e in all_e]
                                        
                                        idx_s = cur_s_opts.index(w['supplier']) if w.get('supplier') in cur_s_opts else 0
                                        idx_e = cur_e_opts.index(w['employer']) if w.get('employer') in cur_e_opts else 0
                                        
                                        es = st.selectbox("Supplier", cur_s_opts, index=idx_s)
                                        ee = st.selectbox("Employer", cur_e_opts, index=idx_e)
                                        
                                        if st.form_submit_button("💾 حفظ التعديلات", use_container_width=True):
                                            updated_w = {
                                                "name": en,
                                                "mobile": em,
                                                "id": ei,
                                                "supplier": es,
                                                "employer": ee,
                                                "file_notes": w.get("file_notes", ""),
                                                "general_notes": w.get("general_notes", ""),
                                                "files": w.get("files", []),
                                                "timestamp": w.get("timestamp", "")
                                            }
                                            if bm.update_worker(w_uuid, updated_w):
                                                st.session_state['_notif_m_worker'] = ("success", "تم تحديث بيانات العامل بنجاح ✅")
                                                st.rerun()
                else:
                    st.warning("لم يتم العثور على نتائج")
            else:
                st.info("💡 ابحث عن عامل بالاسم أو الرقم")
                st.metric("👷 إجمالي العمال المسجلين", len(workers_all))
            
            w_m_notif = st.empty()
            if st.session_state.get('_notif_m_worker'):
                t_val, m_val = st.session_state.pop('_notif_m_worker')
                show_toast(m_val, t_val, container=w_m_notif)

        # --- TAB 2: SUPPLIERS ---
        with m_tab2:
            st.markdown("#### 📦 إدارة الموردين")
            all_suppliers = bm.get_suppliers()
            if not all_suppliers:
                st.info("لا يوجد موردين مسجلين حالياً.")
            else:
                for s in all_suppliers:
                    with st.expander(f"📦 {s['name']}"):
                        with st.form(f"edit_sup_{s['id']}"):
                            new_name = st.text_input("Name", s['name'])
                            new_phone = st.text_input("Phone", s['phone'])
                            c_edit, c_del = st.columns(2)
                            if c_edit.form_submit_button("💾 حفظ التعديلات", use_container_width=True):
                                bm.update_supplier(s['id'], {"name": new_name, "phone": new_phone})
                                st.session_state['_notif_m_sup'] = ("success", f"تم تحديث المورد {new_name}")
                                st.rerun()
                            if c_del.form_submit_button("🗑️ حذف المورد", use_container_width=True):
                                if can_delete:
                                    bm.delete_supplier(s['id'])
                                    st.session_state['_notif_m_sup'] = ("success", "تم حذف المورد بنجاح")
                                    st.rerun()
                                else:
                                    st.error("ليس لديك صلاحية الحذف")
                
                s_m_notif = st.empty()
                if st.session_state.get('_notif_m_sup'):
                    t_val, m_val = st.session_state.pop('_notif_m_sup')
                    show_toast(m_val, t_val, container=s_m_notif)

        # --- TAB 3: EMPLOYERS ---
        with m_tab3:
            st.markdown("#### 🏢 إدارة أصحاب العمل")
            all_employers = bm.get_employers()
            if not all_employers:
                st.info("لا يوجد أصحاب عمل مسجلين حالياً.")
            else:
                for e in all_employers:
                    with st.expander(f"🏢 {e['name']} - {e.get('cafe', '')}"):
                        with st.form(f"edit_emp_{e['id']}"):
                            en = st.text_input("Name", e['name'])
                            ec = st.text_input("Cafe", e.get('cafe', ''))
                            em = st.text_input("Mobile", e.get('mobile', ''))
                            ect = st.text_input("City", e.get('city', ''))
                            c_edit, c_del = st.columns(2)
                            if c_edit.form_submit_button("💾 حفظ التعديلات", use_container_width=True):
                                bm.update_employer(e['id'], {"name": en, "cafe": ec, "mobile": em, "city": ect})
                                st.session_state['_notif_m_emp'] = ("success", "تم تحديث البيانات")
                                st.rerun()
                            if c_del.form_submit_button("🗑️ حذف صاحب العمل", use_container_width=True):
                                if can_delete:
                                    bm.delete_employer(e['id'])
                                    st.session_state['_notif_m_emp'] = ("success", "تم الحذف")
                                    st.rerun()
                                else:
                                    st.error("ليس لديك صلاحية")
                
                e_m_notif = st.empty()
                if st.session_state.get('_notif_m_emp'):
                    t_val, m_val = st.session_state.pop('_notif_m_emp')
                    show_toast(m_val, t_val, container=e_m_notif)

# 11. Main Entry
if not st.session_state.user:
    login_screen()
else:
    dashboard()
