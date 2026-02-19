import streamlit as st
import pandas as pd
import os
import sys
import json
import hashlib
import time
from datetime import datetime, timedelta

# 1. Ensure project root is in path (Robust Injection)
import os
import sys
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

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
            "first_name_ar": f_ar,
            "father_name_ar": fa_ar,
            "first_name_en": f_en,
            "father_name_en": fa_en,
            "permissions": ["read"] if role == "viewer" else ["all"]
        }
        self.save_users()
        return True, "User added successfully"

    def update_password(self, username, new_password):
        username = username.lower().strip()
        if username in self.users:
            self.users[username]["password"] = self.hash_password(new_password)
            self.save_users()
            return True
        return False

    def delete_user(self, username):
        username = username.lower().strip()
        if username in self.users and username != "admin":
            del self.users[username]
            self.save_users()
            return True
        return False

    def update_role(self, username, new_role):
        username = username.lower().strip()
        if username in self.users and username != "admin":
            self.users[username]["role"] = new_role
            self.users[username]["permissions"] = ["read"] if new_role == "viewer" else ["all"]
            self.save_users()
            return True
        return False

    def update_profile(self, username, f_ar=None, fa_ar=None, f_en=None, fa_en=None):
        username = username.lower().strip()
        if username in self.users:
            if f_ar is not None: self.users[username]["first_name_ar"] = f_ar
            if fa_ar is not None: self.users[username]["father_name_ar"] = fa_ar
            if f_en is not None: self.users[username]["first_name_en"] = f_en
            if fa_en is not None: self.users[username]["father_name_en"] = fa_en
            self.save_users()
            return True
        return False

def get_css():
    return """
    <style>
        /* General Imports */
        @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;700&family=Cinzel:wght@600&family=Orbitron:wght@600&family=Alex+Brush&family=Aref+Ruqaa&display=swap');
        
        /* Main Container */
        .stApp {
            background-color: #0F0F0F;
            color: #F8F8F8;
            font-family: 'Tajawal', sans-serif;
        }

        /* Headers */
        h1, h2, h3 {
            color: #D4AF37 !important; /* Gold */
            font-family: 'Tajawal', sans-serif;
            text-align: center;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }

        /* Login Screen Image & Title Layout */
        .login-screen-wrapper {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            width: 100%;
        }
        
        /* Smaller Image as requested */
        .login-screen-wrapper img {
            border-radius: 50%;
            border: 3px solid #D4AF37;
            box-shadow: 0 0 15px rgba(212, 175, 55, 0.4);
            margin-bottom: 5px;
            width: 80px !important; /* Smaller size */
            height: 80px !important;
        }

        /* Container for Welcome Text + Signature side-by-side */
        .welcome-signature-container {
             display: flex;
             align-items: baseline; /* Align text baselines */
             justify-content: center;
             gap: 15px;
             margin-bottom: 20px;
             flex-wrap: wrap; 
        }

        /* Programmer Signature - Neon English Style */
        .programmer-signature-neon {
            font-family: 'Alex Brush', cursive;
            font-size: 1.8rem;
            color: #fff;
            text-shadow:
                0 0 5px #fff,
                0 0 10px #fff,
                0 0 20px #D4AF37,
                0 0 30px #D4AF37,
                0 0 40px #D4AF37;
            animation: neon-flicker 1.5s infinite alternate;       
        }

        /* Red Neon Signature - Requested for page tops */
        .red-neon-signature {
            font-family: 'Alex Brush', cursive;
            font-size: 2.5rem;
            color: #FF3131; /* Bright Neon Red */
            text-align: center;
            width: 100%;
            display: block;
            margin-bottom: 0px;
            padding-bottom: 5px;
            text-shadow:
                0 0 7px #FF3131,
                0 0 15px #FF3131,
                0 0 25px #FF3131,
                0 0 45px #FF0000;
            font-weight: 900 !important;
        }
        
        @keyframes neon-flicker {
            0%, 19%, 21%, 23%, 25%, 54%, 56%, 100% {
                text-shadow:
                    0 0 4px #fff,
                    0 0 10px #fff,
                    0 0 18px #D4AF37,
                    0 0 38px #D4AF37,
                    0 0 73px #D4AF37;
            }
            20%, 24%, 55% {        
                text-shadow: none;
            }
        }

        /* Essential Card Tweaks - Login Form Container */
        div[data-testid="stForm"] {
            background-color: #1A1A1A !important;
            border: 1px solid rgba(212, 175, 55, 0.3) !important;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5) !important;
            max-width: 420px !important;
            margin: 0 auto !important;
            padding: 30px !important;
            border-radius: 20px !important; /* Rounded corners */
        }
        
        /* Form Inner Spacing */
        div[data-testid="stForm"] > div {
             gap: 1.5rem !important; /* Space between inputs */
        }

        /* Programmer Credit - Neon Green Handwritten Style */
        .programmer-credit {
            color: #39FF14 !important; /* Sharp Neon Green */
            font-family: 'Aref Ruqaa', serif;
            margin: 5px auto !important;
            font-size: 1.5em !important; /* Adjusted for better fit */
            letter-spacing: 0.5px;
            text-align: center;
            font-weight: 700 !important; 
            text-shadow: 
                0 0 2px rgba(0, 0, 0, 1), 
                0 0 8px rgba(57, 255, 20, 0.6);
            white-space: nowrap !important; /* Force the name to stay together */
            width: auto !important;
            display: block;
            line-height: 1.2;
        }
        
        /* Premium Buttons (General styling) */
        .stButton > button {
            background: linear-gradient(135deg, #2E7D32 0%, #1B5E20 100%) !important;
            color: #FFFFFF !important;
            font-weight: 800 !important;
            letter-spacing: 1px !important;
            border: none !important;
            padding: 12px 0 !important;
            box-shadow: 0 4px 15px rgba(46, 125, 50, 0.4) !important;
            border-radius: 8px !important;
            transition: all 0.3s ease !important;
        }

        /* Full-width context for buttons that need it (Forms, Sidebar, etc.) */
        div[data-testid="stForm"] .stButton > button,
        section[data-testid="stSidebar"] .stButton > button,
        .full-width-btn .stButton > button {
            width: 100% !important;
            margin-top: 10px !important;
        }
        
        div.stButton > button:hover {
            background: linear-gradient(135deg, #388E3C 0%, #2E7D32 100%) !important;
            box-shadow: 0 0 25px rgba(76, 175, 80, 0.6) !important;
            transform: scale(1.02);
        }

        /* Sidebar Styling & Centering */
        section[data-testid="stSidebar"] {
            background-color: #161616 !important;
            border-left: 1px solid rgba(212, 175, 55, 0.1);
            padding-top: 2rem !important; /* Ensure image starts below header */
        }
        
        /* 
           AGGRESSIVE SIDEBAR CENTERING 
           Targeting the vertical block containers that Streamlit uses
        */
        section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div {
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            width: 100% !important;
            text-align: center !important;
        }

        section[data-testid="stSidebar"] .stImage {
             display: flex !important;
             justify-content: center !important;
             width: 100% !important;
             margin: 0 auto !important;
        }
        
        section[data-testid="stSidebar"] .stImage img {
            border-radius: 50%;
            border: 2px solid #D4AF37;
            padding: 3px;
            margin: 0 auto !important;
        }

        /* All Sidebar Buttons Uniform - Green */
        section[data-testid="stSidebar"] .stButton > button {
            background-color: #2E7D32 !important;
            color: #FFFFFF !important;
            font-weight: 700;
            border: none;
            border-radius: 8px;
            padding: 12px 0px;
            margin: 8px 0px !important;
            width: 100% !important;
            height: 45px !important;
            display: flex;
            justify-content: center;
            align-items: center;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            font-size: 0.95rem;
        }
        
        section[data-testid="stSidebar"] .stButton > button:hover {
            background-color: #388E3C !important;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(46, 125, 50, 0.5);
            color: #FFFFFF !important;
        }

        /* Data Tables - Modern Green Text */
        div[data-testid="stDataFrame"] td, 
        div[data-testid="stTable"] td,
        .styled-table td {
            color: #4CAF50 !important; /* Elegant Green */
            font-weight: 500;
        }
        


        /* Custom Inputs (Robust targeting) */
        .stTextInput > div > div > input {
            background-color: #222 !important;
            color: #fff !important;
            border: 1px solid #444 !important;
            border-radius: 8px !important;
            padding: 10px !important; /* Comfortable padding */
        }
        
        .stTextInput > div > div > input:focus {
            border-color: #D4AF37 !important;
            box-shadow: 0 0 5px rgba(212, 175, 55, 0.5) !important;
        }

        /* 
           LANGUAGE TOGGLE - ULTRA ROBUST TARGETING
           Using the "Marker + Sibling" pattern to target specific buttons
        */
        
        /* --- LOGIN BUTTONS ROBUST STYLING --- */
        
        /* 1. Hide the anchor containers themselves so they don't take up space in the form's GAP layout */
        div:has(> #login-btn-anchor), 
        div:has(> #login-lang-new-anchor) {
            display: none !important;
        }

        /* 2. Unify all buttons in the login card */
        .login-screen-wrapper .stButton button {
            width: 100% !important;
            margin: 0 !important; /* Let the form gap handle spacing */
            background: #1A1A1B !important; 
            border: 1px solid rgba(212, 175, 55, 0.4) !important;
            height: 48px !important;
            border-radius: 10px !important;
            transition: all 0.3s ease !important;
        }

        /* 3. SPECIFIC: Login Button (Yellow Glow) - Target EVERYTHING to ensure it changes */
        div:has(> #login-btn-anchor) + div .stButton button,
        div:has(> #login-btn-anchor) + div .stButton button p,
        div:has(> #login-btn-anchor) + div .stButton button span {
            color: #FFFF00 !important; 
            text-shadow: 0 0 10px #FFFF00, 0 0 20px #FFFF00 !important;
            font-weight: 900 !important;
        }

        /* 4. SPECIFIC: Language Button (Gold Theme) */
        div:has(> #login-lang-new-anchor) + div .stButton button,
        div:has(> #login-lang-new-anchor) + div .stButton button p,
        div:has(> #login-lang-new-anchor) + div .stButton button span {
            color: #D4AF37 !important;
            font-weight: 700 !important;
        }
        
        /* 5. Hover Effects */
        .login-screen-wrapper .stButton button:hover {
            border-color: #FFFF00 !important;
            box-shadow: 0 0 20px rgba(255, 255, 0, 0.4) !important;
            background: #252525 !important;
        }

        /* 2. Sidebar Toggle (Large Green Pill) */
        div:has(> #sidebar-lang-anchor) + div .stButton > button {
            width: 120px !important;
            height: 120px !important;
            min-width: 120px !important;
            max-width: 120px !important;
            border-radius: 25px !important;
            font-size: 2.2rem !important; 
            font-weight: 800 !important;
            background-color: #2E7D32 !important; 
            color: #FFFFFF !important; 
            border: 2px solid rgba(255, 255, 255, 0.4) !important;
            box-shadow: 0 8px 25px rgba(0,0,0,0.7) !important;
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            margin: 15px auto !important;
            padding: 0 !important;
            aspect-ratio: 1/1 !important;
            transition: all 0.3s ease !important;
        }

        /* Reset Hover Opacity for marker in sidebar */
        div:has(> #sidebar-lang-anchor) + div .stButton > button:hover {
            opacity: 0.9 !important;
            transform: scale(1.05) !important;
            border-color: #D4AF37 !important;
        }

        /* 
           GLOBAL TABLE STYLING 
           Headers: Gold Color (#D4AF37)
           We target multiple possible DOM structures for Streamlit DataFrames
        */
        
        /* 1. Standard DataFrame Headers (Glide/Modern) */
        [data-testid="stDataFrame"] thead th,
        [data-testid="stDataFrame"] [role="columnheader"],
        [data-testid="stDataFrame"] [role="columnheader"] *,
        [data-testid="stDataFrame"] [data-testid="stHeader"] *,
        [data-testid="stDataFrame"] .st-emotion-cache-12w0u95 *,
        [data-testid="stDataFrame"] div:has(> [role="columnheader"]) * {
            color: #D4AF37 !important;
            font-weight: bold !important;
            font-size: 1.05rem !important;
        }

        /* 2. Legacy Table Headers */
        table th, table th * {
            color: #D4AF37 !important;
            font-weight: bold !important;
        }

        /* Glowing Metric Cards */
        .metric-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            transition: transform 0.3s ease;
            width: 100%;
        }
        .metric-container:hover {
            transform: translateY(-5px);
            background: rgba(255, 255, 255, 0.05);
        }
        .metric-label {
            font-size: 1.4rem !important;
            font-weight: 700 !important;
            margin-bottom: 10px !important;
            letter-spacing: 1px;
            text-transform: uppercase;
        }
        .metric-value {
            font-size: 3.5rem !important;
            font-weight: 800 !important;
            margin: 0 !important;
            line-height: 1;
        }
        
        /* Specific Glow Colors */
        .glow-green .metric-label { color: #4CAF50 !important; }
        .glow-green .metric-value { 
            color: #4CAF50 !important; 
            text-shadow: 0 0 15px rgba(76, 175, 80, 0.8), 0 0 30px rgba(76, 175, 80, 0.4);
        }
        
        .glow-red .metric-label { color: #FF5252 !important; }
        .glow-red .metric-value { 
            color: #FF5252 !important; 
            text-shadow: 0 0 15px rgba(255, 82, 82, 0.8), 0 0 30px rgba(255, 82, 82, 0.4);
        }
        
        .glow-orange .metric-label { color: #FFAB40 !important; }
        .glow-orange .metric-value { 
            color: #FFAB40 !important; 
            text-shadow: 0 0 15px rgba(255, 171, 64, 0.8), 0 0 30px rgba(255, 171, 64, 0.4);
        }

        /* Glowing Page Title for Search */
        .glowing-title {
            color: #D4AF37 !important; /* Gold */
            font-size: 3rem !important;
            font-weight: 900 !important;
            text-align: center !important;
            text-shadow: 
                0 0 10px rgba(212, 175, 55, 0.9),
                0 0 20px rgba(212, 175, 55, 0.6),
                0 0 30px rgba(212, 175, 55, 0.3) !important;
            margin-bottom: 30px !important;
            padding-top: 10px !important;
            width: 100% !important;
            display: block !important;
            font-family: 'Tajawal', sans-serif;
        }

        /* Large Search Button Specifically targeting via anchor */
        div:has(#search-btn-anchor) ~ div .stButton button,
        div:has(#search-btn-anchor) ~ div .stButton button p,
        div:has(#search-btn-anchor) ~ div .stButton button span {
            height: 60px !important;
            width: 5cm !important; 
            min-width: 5cm !important; 
            max-width: 5cm !important;
            color: #D4AF37 !important; /* Gold text */
            font-size: 2.1rem !important; /* Size 21 scale */
            font-weight: 900 !important; /* Extra bold */
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            margin: 0 auto !important;
        }

        /* --- CUSTOM HOURGLASS LOADER --- */
        .loader-wrapper {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 40px;
            width: 100%;
        }
        .hourglass {
            display: inline-block;
            position: relative;
            width: 80px;
            height: 80px;
        }
        .hourglass:after {
            content: " ";
            display: block;
            border-radius: 50%;
            width: 0;
            height: 0;
            margin: 6px;
            box-sizing: border-box;
            border: 32px solid #D4AF37;
            border-color: #D4AF37 transparent #D4AF37 transparent;
            animation: hourglass 1.2s infinite;
        }
        @keyframes hourglass {
            0% { transform: rotate(0); animation-timing-function: cubic-bezier(0.55, 0.055, 0.675, 0.19); }
            50% { transform: rotate(900deg); animation-timing-function: cubic-bezier(0.215, 0.61, 0.355, 1); }
            100% { transform: rotate(1800deg); }
        }
        .loading-text {
            color: #D4AF37;
            font-family: 'Tajawal', sans-serif;
            font-size: 1.5rem;
            margin-top: 20px;
            font-weight: 700;
            text-shadow: 0 0 10px rgba(212, 175, 55, 0.5);
        }
    </style>
    """

def style_df(df):
    """
    Applies custom styling to DataFrames.
    - Text Color: Green (#4CAF50)
    - Background: Transparent/Dark
    """
    if isinstance(df, pd.DataFrame):
        return df.style.map(lambda _: "color: #4CAF50;")
    return df

# 2.5 Hourglass Loader Helper
def show_loading_hourglass(text=None, container=None):
    if text is None:
        text = "جاري التحميل..." if st.session_state.get('lang') == 'ar' else "Loading..."
    
    target = container if container else st.empty()
    with target:
        st.markdown(f"""
            <div class="loader-wrapper">
                <div class="hourglass"></div>
                <div class="loading-text">{text}</div>
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
if 'auth' not in st.session_state or not hasattr(st.session_state.auth, 'is_bilingual'):
    # Show a brief initial loader for a premium feel
    loading = show_loading_hourglass()
    time.sleep(0.4)
    st.session_state.auth = AuthManager(USERS_FILE)
    loading.empty()

# Report DB Load Errors to User
if hasattr(st.session_state.auth, 'load_error'):
    st.error(f"⚠️ Error Loading User Database: {st.session_state.auth.load_error}")

if 'db' not in st.session_state:
    st.session_state.db = DBClient()

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
def render_cv_detail_panel(worker_row, selected_idx, lang, key_prefix="search"):
    """
    Standalone helper to render the professional CV profile card, 
    preview (iframe), and translation logic.
    """
    worker_name = worker_row.get("Full Name:", "Worker")
    # Dynamically find CV column
    cv_col = None
    for c in worker_row.index:
        if "cv" in str(c).lower() or "سيرة" in str(c).lower():
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

    # --- PROFESSIONAL PROFILE CARD ---
    st.markdown(f"<div id='cv-anchor-{key_prefix}'></div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="background-color:#1e2130; padding:20px; border-radius:10px; border-right:5px solid #ffcc00; margin: 20px 0;">
        <h2 style="color:#ffcc00; margin:0;">👤 {worker_name}</h2>

    </div>
    """, unsafe_allow_html=True)
    
    col_a, col_b = st.columns([1, 1])
    with col_a:
        if st.button(f"✨ {t('translate_cv_btn', lang)}", use_container_width=True, type="primary", key=f"btn_trans_{key_prefix}_{selected_idx}"):
            if cv_url and str(cv_url).startswith("http"):
                with st.spinner(t("extracting", lang)):
                    try:
                        import requests
                        file_id = None
                        if "drive.google.com" in cv_url:
                            if "id=" in cv_url: file_id = cv_url.split("id=")[1].split("&")[0]
                            elif "/d/" in cv_url: file_id = cv_url.split("/d/")[1].split("/")[0]

                        if file_id:
                            session = requests.Session()
                            session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"})
                            
                            dl_url = f"https://docs.google.com/uc?export=download&id={file_id}"
                            resp = session.get(dl_url, stream=True, timeout=15)
                            
                            # Handle Drive Virus Warning
                            token = None
                            for k, v in resp.cookies.items():
                                if k.startswith('download_warning'): token = v; break
                            if token:
                                dl_url = f"https://docs.google.com/uc?export=download&confirm={token}&id={file_id}"
                                resp = session.get(dl_url, stream=True, timeout=15)
                            
                            # Fallback: If still 500, try the absolute direct link if available
                            if resp.status_code >= 500:
                                resp = requests.get(cv_url, timeout=15)
                                
                            pdf_content = resp.content
                        else:
                            resp = requests.get(cv_url, timeout=15)
                            pdf_content = resp.content

                        if resp.status_code == 200:
                            if not pdf_content.startswith(b"%PDF"):
                                st.error("⚠️ الملف الذي تم تحميله ليس ملف PDF صالح. قد يكون الرابط محمياً.")
                                if b"google" in pdf_content.lower():
                                    st.info("تأكد أن الملف متاح 'لأي شخص لديه الرابط' في إعدادات Google Drive.")
                            else:
                                tm = TranslationManager()
                                text = tm.extract_text_from_pdf(pdf_content)
                                if text.startswith("Error"): st.error(text)
                                else:
                                    trans = tm.translate_full_text(text)
                                    st.session_state[f"trans_{key_prefix}_{selected_idx}"] = {"orig": text, "trans": trans}
                        else:
                            st.error(f"خطأ في الوصول للملف: (HTTP {resp.status_code}). جرب فتح الرابط يدوياً.")
                            st.info(f"رابط الملف المستخدم: {cv_url}")
                    except Exception as e: st.error(f"Error: {str(e)}")
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
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-screen-wrapper">', unsafe_allow_html=True)
        
        # 1. Image at the very top, centered (CSS makes it smaller)
        if os.path.exists(IMG_PATH):
            st.image(IMG_PATH, width=80) # Explicit width in Streamlit also helps
        
        # 2. Welcome + Signature (Side by Side)
        st.markdown(f"""
            <div class="welcome-signature-container">
                <h1 style='margin:0; padding:0; display:inline-block;'>{t('welcome_back', lang)}</h1>
                <span class="programmer-signature-neon">By: Alsaeed Alwazzan</span>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown(f"<p style='text-align:center; color:#888; letter-spacing:1px; margin-bottom:30px;'>{t('system_title', lang)}</p>", unsafe_allow_html=True)
        
        # 3. Form (Styled via CSS in get_css)
        with st.form("login"):
            u = st.text_input(t("username", lang), label_visibility="collapsed", placeholder=t("username", lang))
            p = st.text_input(t("password", lang), type="password", label_visibility="collapsed", placeholder=t("password", lang))
            
            st.markdown('<div id="login-btn-anchor"></div>', unsafe_allow_html=True)
            if st.form_submit_button(t("login_btn", lang)):
                login_loader = show_loading_hourglass()
                p_norm = p.strip()
                user = st.session_state.auth.authenticate(u, p_norm)
                login_loader.empty()
                if user:
                    user['username'] = u
                    st.session_state.user = user
                    st.session_state.show_welcome = True
                    st.rerun()
                else:
                    st.error(t("invalid_creds", lang))
                    if u.lower() == "admin" and p_norm == "admin123":
                        st.info("💡 Try using your new password instead of the old default.")

            # New Professional Language Toggle inside the form
            st.markdown('<div id="login-lang-new-anchor"></div>', unsafe_allow_html=True)
            if st.form_submit_button("En" if lang == "ar" else "عربي"):
                toggle_lang()
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

def dashboard():
    user = st.session_state.user
    lang = st.session_state.lang
    
    # Welcome Message - Prominent and High Visibility
    if st.session_state.get('show_welcome'):
        # Selection based on UI language
        if lang == 'ar':
            f_name = user.get('first_name_ar', '')
            fa_name = user.get('father_name_ar', '')
        else:
            f_name = user.get('first_name_en', '')
            fa_name = user.get('father_name_en', '')
            
        full_name = f"{f_name} {fa_name}".strip()
        if not full_name: full_name = user.get('username', 'User')
        
        msg = t("welcome_person", lang).format(name=full_name)
        st.success(f"💖 {msg}") # Prominent success banner
        st.toast(msg, icon="🎉")
        del st.session_state.show_welcome

    with st.sidebar:
        # Use columns to force horizontal centering for the image block
        sc1, sc2, sc3 = st.columns([1, 2, 1])
        with sc2:
            if os.path.exists(IMG_PATH):
                st.image(IMG_PATH, use_container_width=True)
        
        # Credit text - Split into two lines for clarity
        st.markdown(f'<div class="programmer-credit">{"برمجة" if lang == "ar" else "By:"}<br>{"السعيد الوزان" if lang == "ar" else "Alsaeed Alwazzan"}</div>', unsafe_allow_html=True)
        
        # Spacing
        st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
        
        # Language Toggle (Using Marker ID)
        st.markdown('<div id="sidebar-lang-anchor"></div>', unsafe_allow_html=True)
        btn_label = "En" if lang == "ar" else "عربي"
        if st.button(btn_label, key="lang_btn_dashboard"):
            toggle_lang()
            st.rerun()
        
        st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)

        if st.button(t("dashboard", lang), use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()
        if st.button(t("smart_search", lang), use_container_width=True):
            st.session_state.page = "search"
            st.rerun()
        if st.button(t("cv_translator", lang), use_container_width=True):
            st.session_state.page = "translator"
            st.rerun()
        if user.get("role") == "admin":
            if st.button(t("permissions", lang), use_container_width=True):
                st.session_state.page = "permissions"
                st.rerun()
            
            # Refresh Data button below Permissions for Admins
            if st.button(t("refresh_data_btn", lang), key="force_refresh_db", use_container_width=True):
                refresh_loader = show_loading_hourglass()
                st.session_state.db.fetch_data(force=True)
                refresh_loader.empty()
                st.success("تم تحديث البيانات من Google Sheets بنجاح!" if lang == 'ar' else "Data refreshed successfully!")
                time.sleep(1)
                st.rerun()
        
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
    elif page == "permissions": render_permissions_content()

def render_dashboard_content():
    lang = st.session_state.lang
    st.markdown('<div class="red-neon-signature">By: Alsaeed Alwazzan</div>', unsafe_allow_html=True)
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
    
    date_col = next((c for c in cols if "contract end" in c.lower() or "انتهاء العقد" in c.lower()), None)
    if not date_col:
        st.error(f"Date column not found. Available: {cols}")
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
                    r['Status'] = "منتهي"
                    r['المتبقى'] = abs(days)
                elif global_status in ['urgent', 'warning']:
                    r['Status'] = "متبقى"
                    r['المتبقى'] = days
                else: # active
                    r['Status'] = "ساري"
                    r['المتبقى'] = days
            else:
                r['Status'] = status['label_en']
                r['Remaining'] = abs(days)

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
    
    cv_col = next((c for c in cols if "cv" in c.lower() or "سيرة" in c.lower()), None)
    
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
        
        # Select columns: Remaining (المتبقى) then Status, then the rest
        rem_col = 'المتبقى' if lang == 'ar' else 'Remaining'
        show_cols = [rem_col, 'Status'] + [c for c in cols if c in d.columns and c not in ["__sheet_row", "__sheet_row_backup", "__days_sort"]]
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

    with t1: show(stats['urgent'], "urgent")
    with t2: show(stats['expired'], "expired")
    with t3: show(stats['active'], "active")

def render_search_content():
    lang = st.session_state.lang
    
    # Absolute Top Signature
    st.markdown('<div class="red-neon-signature">By: Alsaeed Alwazzan</div>', unsafe_allow_html=True)
    
    # 1. Glowing Title at the Absolute Top
    st.markdown('<div class="glowing-title">(AI) البحث الذكي</div>', unsafe_allow_html=True)
    
    # Rest of the content
    lbl_age = t("age", lang) if t("age", lang) != "age" else "العمر"
    lbl_contract = t("contract_end", lang) if t("contract_end", lang) != "contract_end" else "تاريخ انتهاء العقد"
    lbl_reg = t("registration_date", lang) if t("registration_date", lang) != "registration_date" else "تاريخ التسجيل"
    lbl_enable = "تفعيل" if lang == "ar" else "Enable"
    
    # Advanced Filters UI
    with st.expander(t("advanced_filters", lang) if t("advanced_filters", lang) != "advanced_filters" else "تصفية متقدمة"):
        c3, c2, c1 = st.columns(3)
        
        # Registration Date Filter (rightmost in RTL)
        with c1:
            use_reg = st.checkbox(f" {lbl_enable} {lbl_reg}", key="use_reg_filter")
            if use_reg:
                st.caption(lbl_reg)
                today = datetime.now().date()
                first_of_month = today.replace(day=1)
                reg_range = st.date_input("Registration Range", (first_of_month, today), label_visibility="collapsed", key="reg_range")
            else:
                reg_range = []

        # Contract End Filter
        with c2:
            use_contract = st.checkbox(f" {lbl_enable} {lbl_contract}", key="use_contract_filter")
            if use_contract:
                st.caption(lbl_contract)
                today = datetime.now().date()
                next_month = today + timedelta(days=30)
                contract_range = st.date_input("Contract Range", (today, next_month), label_visibility="collapsed", key="contract_range")
            else:
                contract_range = []
        
        # Age Filter (leftmost in RTL)
        with c3:
            use_age = st.checkbox(f" {lbl_enable} {lbl_age}", key="use_age_filter")
            if use_age:
                age_range = st.slider(lbl_age, 18, 60, (20, 45), key="age_slider")
            else:
                age_range = (18, 60)

    query = st.text_input(t("smart_search", lang), placeholder=t("search_placeholder", lang), key="search_query_input")
    
    # 2. Search Button Wrapped in Container for better DOM targeting
    with st.container():
        st.markdown('<div id="search-btn-anchor"></div>', unsafe_allow_html=True)
        search_clicked = st.button(t("search_btn", lang), key="main_search_btn", use_container_width=False)
    
    # Gather Filters
    filters = {}
    
    
    
    # 1. Age (only if enabled)
    if use_age:
        filters['age_enabled'] = True
        filters['age_min'] = age_range[0]
        filters['age_max'] = age_range[1]
    
    # 2. Contract End (only if enabled and valid range)
    if use_contract and len(contract_range) == 2:
        filters['contract_enabled'] = True
        filters['contract_end_start'] = contract_range[0]
        filters['contract_end_end'] = contract_range[1]
        
    # 3. Registration (only if enabled and valid range)
    if use_reg and len(reg_range) == 2:
        filters['date_enabled'] = True
        filters['date_start'] = reg_range[0]
        filters['date_end'] = reg_range[1]
    
    # Check if any filter is actually active
    has_active_filter = bool(filters)
    
    # Trigger on button click OR when query changes (Enter is pressed)
    if search_clicked or query:
        search_loader = show_loading_hourglass() # Custom premium loader
        
        # Debug: Show what filters are being sent
        if filters:
            active_filter_names = []
            if filters.get('age_enabled'): active_filter_names.append(f"{lbl_age}: {filters.get('age_min')}-{filters.get('age_max')}")
            if filters.get('contract_enabled'): active_filter_names.append(f"{lbl_contract}")
            if filters.get('date_enabled'): active_filter_names.append(f"{lbl_reg}")
            if active_filter_names:
                st.info(f"{'الفلاتر النشطة' if lang == 'ar' else 'Active filters'}: {', '.join(active_filter_names)}")

        # Fetch fresh data
        original_data = st.session_state.db.fetch_data()
        total_rows = len(original_data)
        
        if total_rows == 0:
            st.error("لم يتم العثور على أي بيانات في قاعدة البيانات. تأكد من الربط مع Google Sheets.")
            return

        eng = SmartSearchEngine(original_data)
        try:
            res = eng.search(query, filters=filters)
            search_loader.empty() # Clear loader immediately after search results are ready
            
            # --- CUSTOM STATUS LOGIC FOR SEARCH RESULTS ---
            # Try to find date column in results
            res_cols = res.columns.tolist()
            date_col_search = next((c for c in res_cols if "contract end" in c.lower() or "انتهاء العقد" in c.lower()), None)
            
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
                            status_list.append("منتهي")
                            rem_list.append(abs(ds))
                        elif gs in ['urgent', 'warning']:
                            status_list.append("متبقى")
                            rem_list.append(ds)
                        else:
                            status_list.append("ساري")
                            rem_list.append(ds)
                    else:
                        status_list.append(s['label_en'])
                        rem_list.append(abs(ds))
                
                res['Status'] = status_list
                res['المتبقى' if lang == 'ar' else 'Remaining'] = rem_list
                res['__days_sort'] = sort_list
                # Sort Results
                res = res.sort_values(by='__days_sort', ascending=True)
            
            # Show count in UI
            count_found = len(res)
            if count_found > 0:
                st.success(f"{'تم العثور على' if lang == 'ar' else 'Found'} {count_found} {'نتائج من أصل' if lang == 'ar' else 'results out of'} {total_rows}")
            
            # Debug Panel (for diagnosing search issues)
            with st.expander("🔧 تشخيص البحث | Search Debug", expanded=False):
                debug = eng.last_debug
                st.json(debug)
            
            # Handle both DataFrame and list returns
            is_empty = (isinstance(res, list) and len(res) == 0) or (hasattr(res, 'empty') and res.empty)
            
            if is_empty:
                st.warning(t("no_results", lang))
            elif query and count_found == total_rows:
                st.warning("تنبيه: البحث أرجع جميع النتائج. تحقق من تشخيص البحث أعلاه." if lang == 'ar' else "Warning: Search returned all results. Check debug panel above.")
            
            # Clean up internal diagnostic columns before display
            for diag_col in ['__matched_age_col', '__matched_contract_col', '__matched_ts_col', '__days_sort']:
                if diag_col in res.columns:
                    res = res.drop(columns=[diag_col])
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
                new_name = t_col(c, lang)
                original_new_name = new_name
                counter = 1
                while new_name in used_names:
                    counter += 1
                    new_name = f"{original_new_name} ({counter})"
                used_names.add(new_name)
                new_names[c] = new_name
            
            # Hide internal sheet row from display but keep in original 'res' for logic
            res_to_rename = res.copy()
            for int_col in ["__sheet_row", "__sheet_row_backup"]:
                if int_col in res_to_rename.columns:
                    res_to_rename = res_to_rename.drop(columns=[int_col])
            
            # Reorder columns for Search Table (Remaining then Status)
            rem_key = 'المتبقى' if lang == 'ar' else 'Remaining'
            if rem_key in res_to_rename.columns and "Status" in res_to_rename.columns:
                other_cols = [c for c in res_to_rename.columns if c not in [rem_key, "Status"]]
                res_to_rename = res_to_rename[[rem_key, "Status"] + other_cols]

            res_display = res_to_rename.rename(columns=new_names)
            
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

            # Use on_select to capture row selection
            styled_res = style_df(res_display)
            event = st.dataframe(
                styled_res, 
                use_container_width=True,
                on_select="rerun",
                selection_mode="single-row",
                hide_index=True,
                column_config=column_config,
                key="search_results_table"
            )

            # Handle Selection
            if event.selection and event.selection.get("rows"):
                selected_idx = event.selection["rows"][0]
                worker_row = res.iloc[selected_idx]
                render_cv_detail_panel(worker_row, selected_idx, lang, key_prefix="search")


def render_translator_content():
    lang = st.session_state.lang
    st.title(f" {t('translator_title', lang)}")
    st.markdown(t("translator_desc", lang))
    uploaded = st.file_uploader(t("upload_cv", lang), type=["pdf"])
    if uploaded:
        # Avoid redundant translation on every rerun by using session state
        file_id = f"cv_{uploaded.name}_{uploaded.size}"
        if st.session_state.get('last_trans_file') != file_id:
            trans_loader = show_loading_hourglass()
            tm = TranslationManager()
            try:
                # Read once
                file_bytes = uploaded.read()
                text = tm.extract_text_from_pdf(file_bytes)
                if text.startswith("Error"):
                    st.error(text)
                else:
                    trans = tm.translate_full_text(text)
                    st.session_state.last_trans_result = {'text': text, 'trans': trans}
                    st.session_state.last_trans_file = file_id
            except Exception as e:
                st.error(f"{t('error', lang)}: {e}")
            finally:
                trans_loader.empty()

        # Display results if they exist
        res = st.session_state.get('last_trans_result')
        if res and st.session_state.get('last_trans_file') == file_id:
            c1, c2 = st.columns(2)
            with c1:
                st.subheader(t("original", lang))
                st.text_area("Original", res['text'], height=400)
            with c2:
                st.subheader(t("translated", lang))
                st.text_area("Translated", res['trans'], height=400)
            st.download_button(t("download_trans", lang), res['trans'], file_name="translated_cv.txt")
    else:
        # Clear cache if no file is uploaded
        if 'last_trans_file' in st.session_state:
            del st.session_state.last_trans_file
            if 'last_trans_result' in st.session_state:
                del st.session_state.last_trans_result

def render_permissions_content():
    lang = st.session_state.lang
    st.title(f" {t('permissions_title', lang)}")
    
    # Persistent Success Message after Rerun
    if st.session_state.get('permissions_success'):
        st.success(st.session_state.permissions_success)
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
                else: st.error(m)

    st.subheader(t("users_list", lang))
    users = st.session_state.auth.users
    user_list = list(users.keys())
    
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
            
            if st.form_submit_button(t("update_btn", lang)):
                st.session_state.auth.update_role(selected_user, new_role)
                st.session_state.auth.update_profile(selected_user, new_f_ar, new_fa_ar, new_f_en, new_fa_en)
                if new_pass:
                    st.session_state.auth.update_password(selected_user, new_pass)
                
                st.session_state.permissions_success = t("update_success", lang)
                st.rerun()
    
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

# 11. Main Entry
if not st.session_state.user:
    login_screen()
else:
    dashboard()
