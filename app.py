fixed_login_code = '''import streamlit as st
import pandas as pd
import os
import sys
import json
import hashlib
import time
from datetime import datetime, timedelta

import os
import sys
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

class AuthManager:
    def __init__(self, users_file_path):
        self.users_file = users_file_path
        self.users = {}
        self.is_bilingual = True
        self.load_users()

    def load_users(self):
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.users = data.get("users", {})
            except Exception as e:
                self.load_error = str(e)
                self.users = {}
        
        if "admin" not in self.users:
            self.users["admin"] = {
                "password": self.hash_password("266519111"),
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
        username = str(username).strip()
        target = None
        for u in self.users:
            if u.lower() == username.lower():
                target = u
                break
        
        if target:
            if f_ar is not None: self.users[target]["first_name_ar"] = f_ar
            if fa_ar is not None: self.users[target]["father_name_ar"] = fa_ar
            if f_en is not None: self.users[target]["first_name_en"] = f_en
            if fa_en is not None: self.users[target]["father_name_en"] = fa_en
            self.save_users()
            return True
        return False

def get_css():
    return """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700&family=Inter:wght@300;400;500;600;700&family=Cinzel:wght@500;700&family=Alex+Brush&display=swap');
        
        :root {
            --luxury-gold: #D4AF37;
            --deep-gold: #B8860B;
            --glass-bg: rgba(26, 26, 26, 0.85);
            --solid-dark: #0A0A0A;
            --accent-green: #00FF41;
            --text-main: #F4F4F4;
            --border-glow: rgba(212, 175, 55, 0.3);
        }

        .stApp {
            background: radial-gradient(circle at top right, #1A1A1A, #050505);
            color: var(--text-main);
            font-family: 'Inter', 'Tajawal', sans-serif;
        }

        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: #050505; }
        ::-webkit-scrollbar-thumb { 
            background: linear-gradient(180deg, #333, #D4AF37); 
            border-radius: 10px; 
        }

        .main .block-container {
            padding-top: 2rem !important;
            padding-bottom: 5rem !important;
            max-width: 1400px !important;
        }

        h1, h2, h3 {
            font-family: 'Cinzel', serif !important;
            letter-spacing: 2px !important;
            text-transform: uppercase !important;
            background: linear-gradient(to bottom, #FFFFFF 0%, #D4AF37 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 2px 4px 10px rgba(0,0,0,0.4);
            margin-bottom: 1.5rem !important;
        }

        /* Login Screen Fixes */
        .login-container {
            max-width: 450px !important;
            margin: 0 auto !important;
            padding: 40px 30px !important;
            background: rgba(20, 20, 20, 0.9) !important;
            border-radius: 20px !important;
            border: 1px solid rgba(212, 175, 55, 0.3) !important;
            box-shadow: 0 20px 60px rgba(0,0,0,0.8) !important;
        }
        
        .login-title {
            text-align: center !important;
            margin-bottom: 30px !important;
        }
        
        .login-title h1 {
            font-size: 1.8rem !important;
            margin-bottom: 10px !important;
        }
        
        .login-subtitle {
            text-align: center;
            color: #888;
            font-size: 0.9rem;
            margin-bottom: 30px;
            letter-spacing: 1px;
        }

        div[data-testid="stForm"] {
            background: transparent !important;
            border: none !important;
            padding: 0 !important;
            box-shadow: none !important;
        }

        .stTextInput input {
            background-color: rgba(40, 40, 40, 0.8) !important;
            border: 1px solid rgba(212, 175, 55, 0.3) !important;
            border-radius: 10px !important;
            color: #FFFFFF !important;
            padding: 12px 16px !important;
            font-size: 1rem !important;
        }

        .stTextInput input:focus {
            border-color: var(--luxury-gold) !important;
            box-shadow: 0 0 0 3px rgba(212, 175, 55, 0.2) !important;
        }

        .stButton button {
            background: linear-gradient(135deg, #D4AF37 0%, #B8860B 100%) !important;
            color: #000 !important;
            border: none !important;
            border-radius: 10px !important;
            padding: 12px 30px !important;
            font-weight: 700 !important;
            font-size: 1rem !important;
            letter-spacing: 1px !important;
            width: 100% !important;
            transition: all 0.3s ease !important;
        }

        .stButton button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 10px 30px rgba(212, 175, 55, 0.4) !important;
        }

        .lang-toggle-btn {
            background: transparent !important;
            border: 1px solid rgba(212, 175, 55, 0.5) !important;
            color: #D4AF37 !important;
            padding: 8px 20px !important;
            border-radius: 20px !important;
            font-weight: 600 !important;
        }

        .programmer-signature {
            font-family: 'Alex Brush', cursive !important;
            color: #D4AF37 !important;
            font-size: 1.5rem !important;
            text-align: center !important;
            margin-bottom: 20px !important;
        }

        .logo-container {
            text-align: center !important;
            margin-bottom: 20px !important;
        }

        /* Table Scrollbar Fix */
        .stDataFrame {
            overflow-x: auto !important;
        }
        
        .stDataFrame > div {
            overflow-x: auto !important;
            min-width: 100%;
        }
        
        /* Status Badges */
        .status-badge {
            display: inline-block;
            padding: 6px 14px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.85rem;
            text-align: center;
        }
        
        .status-active {
            background: rgba(0, 255, 65, 0.2);
            color: #00FF41;
            border: 1px solid rgba(0, 255, 65, 0.4);
        }
        
        .status-expired {
            background: rgba(255, 49, 49, 0.2);
            color: #FF3131;
            border: 1px solid rgba(255, 49, 49, 0.4);
        }
        
        .status-urgent {
            background: rgba(255, 145, 0, 0.2);
            color: #FF9100;
            border: 1px solid rgba(255, 145, 0, 0.4);
        }

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
        }
        
        .programmer-credit.en {
            font-family: 'Cinzel', serif !important;
            font-size: 1.1rem;
            letter-spacing: 1px;
        }

        .streamlit-expanderHeader {
            background-color: rgba(255, 255, 255, 0.03) !important;
            border: 1px solid rgba(212, 175, 55, 0.1) !important;
            border-radius: 16px !important;
            padding: 1rem !important;
            font-weight: 600 !important;
            color: var(--luxury-gold) !important;
        }

        .metric-container {
            background: rgba(255, 255, 255, 0.05) !important;
            border-radius: 16px !important;
            border: 1px solid rgba(212, 175, 55, 0.1) !important;
            padding: 1.5rem !important;
            text-align: center !important;
        }
        
        .metric-value {
            font-size: 2.5rem !important;
            font-weight: 700 !important;
            color: #D4AF37 !important;
        }
        
        .metric-label {
            color: #888 !important;
            font-size: 0.9rem !important;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
    </style>
    """

def style_df(df):
    if isinstance(df, pd.DataFrame):
        return df.style.map(lambda _: "color: #4CAF50;")
    return df

def clean_date_display(df):
    if not isinstance(df, pd.DataFrame) or df.empty:
        return df
        
    import re
    from dateutil import parser as dateutil_parser
    
    def _parse_to_date_str(val):
        if val is None or str(val).strip() == '': return ""
        try:
            val_str = str(val).strip()
            a_to_w = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
            val_str = val_str.translate(a_to_w)
            clean_s = re.sub(r'[صم]', '', val_str).strip()
            dt = dateutil_parser.parse(clean_s, dayfirst=False)
            return dt.strftime('%Y-%m-%d')
        except:
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

def show_loading_hourglass(text=None, container=None):
    if text is None:
        text = "جاري التحميل..." if st.session_state.get('lang') == 'ar' else "Loading..."
    
    target = container if container else st.empty()
    with target:
        st.markdown(f"""
            <div style="text-align: center; padding: 40px;">
                <div style="font-size: 3rem; animation: pulse 1s infinite;">⏳</div>
                <div style="color: #D4AF37; margin-top: 10px;">{text}</div>
            </div>
            <style>
                @keyframes pulse {{
                    0% {{ opacity: 0.5; }}
                    50% {{ opacity: 1; }}
                    100% {{ opacity: 0.5; }}
                }}
            </style>
        """, unsafe_allow_html=True)
    return target

try:
    from src.core.search import SmartSearchEngine
    from src.core.contracts import ContractManager
    from src.core.translation import TranslationManager
    from src.data.db_client import DBClient
    from src.config import USERS_FILE, ASSETS_DIR
    from src.core.i18n import t, t_col
except ImportError as e:
    import os
    src_exists = os.path.isdir(os.path.join(ROOT_DIR, "src"))
    st.error(f"Critical Import Error: {e}")
    if not src_exists:
        st.warning(f"⚠️ 'src' directory not found in: {ROOT_DIR}")
    else:
        st.info(f"💡 'src' found at {ROOT_DIR}. Internal module error.")
    st.stop()

st.set_page_config(
    page_title="السعيد الوزان | نظام مراقبة العقود",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(get_css(), unsafe_allow_html=True)

if 'auth' not in st.session_state or not hasattr(st.session_state.auth, 'v8_marker'):
    loading = show_loading_hourglass()
    time.sleep(0.4)
    st.session_state.auth = AuthManager(USERS_FILE)
    st.session_state.auth.v8_marker = True
    st.session_state.db = DBClient()
    loading.empty()

if hasattr(st.session_state.auth, 'load_error'):
    st.error(f"⚠️ Error Loading User Database: {st.session_state.auth.load_error}")

if 'db' not in st.session_state or not hasattr(st.session_state.db, 'fetch_customer_requests'):
    st.session_state.db = DBClient()

if 'user' not in st.session_state:
    st.session_state.user = None
if 'lang' not in st.session_state:
    st.session_state.lang = 'ar' 

IMG_PATH = os.path.join(ASSETS_DIR, "alsaeed.jpg")
if not os.path.exists(IMG_PATH):
    IMG_PATH = "alsaeed.jpg"

def toggle_lang():
    if st.session_state.lang == 'ar': st.session_state.lang = 'en'
    else: st.session_state.lang = 'ar'

def get_contract_status_badge(status, days, lang):
    if status == 'expired':
        if lang == 'ar':
            return f'<span class="status-badge status-expired">❌ منتهي</span>'
        else:
            return f'<span class="status-badge status-expired">Expired</span>'
    elif status in ['urgent', 'warning']:
        if lang == 'ar':
            return f'<span class="status-badge status-urgent">⚠️ عاجل</span>'
        else:
            return f'<span class="status-badge status-urgent">Urgent</span>'
    else:
        if lang == 'ar':
            return f'<span class="status-badge status-active">✅ ساري</span>'
        else:
            return f'<span class="status-badge status-active">Active</span>'

def login_screen():
    lang = st.session_state.lang
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        # Signature
        st.markdown('<div class="programmer-signature">By: Alsaeed Alwazzan</div>', unsafe_allow_html=True)
        
        # Logo
        if os.path.exists(IMG_PATH):
            st.markdown('<div class="logo-container">', unsafe_allow_html=True)
            st.image(IMG_PATH, width=100)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Title
        st.markdown(f'''
            <div class="login-title">
                <h1>{t("welcome_back", lang)}</h1>
            </div>
            <div class="login-subtitle">{t("system_title", lang)}</div>
        ''', unsafe_allow_html=True)
        
        # Login Form
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input(
                t("username", lang), 
                placeholder=t("username", lang),
                label_visibility="collapsed"
            )
            password = st.text_input(
                t("password", lang), 
                type="password",
                placeholder=t("password", lang),
                label_visibility="collapsed"
            )
            
            col_btn1, col_btn2 = st.columns([3, 1])
            
            with col_btn1:
                submitted = st.form_submit_button(
                    t("login_btn", lang),
                    use_container_width=True
                )
            
            with col_btn2:
                lang_btn = st.form_submit_button(
                    "EN" if lang == "ar" else "عربي",
                    use_container_width=True
                )
                if lang_btn:
                    toggle_lang()
                    st.rerun()
            
            if submitted:
                if username and password:
                    with st.spinner(""):
                        user = st.session_state.auth.authenticate(username, password)
                        if user:
                            user['username'] = username
                            st.session_state.user = user
                            st.session_state.show_welcome = True
                            st.rerun()
                        else:
                            st.error(t("invalid_creds", lang))
                else:
                    st.warning("الرجاء إدخال اسم المستخدم وكلمة المرور" if lang == 'ar' else "Please enter username and password")
        
        st.markdown('</div>', unsafe_allow_html=True)

def render_cv_detail_panel(worker_row, selected_idx, lang, key_prefix="search"):
    name_keys = ["Full Name:", "الاسم الكامل", "Name", "الاسم"]
    worker_name = "Worker"
    for nk in name_keys:
        if nk in worker_row.index:
            worker_name = worker_row[nk]
            break
            
    cv_col = None
    for c in worker_row.index:
        c_clean = str(c).lower()
        if "cv" in c_clean or "سيرة" in c_clean or "download" in c_clean:
            cv_col = c
            break
    cv_url = worker_row.get(cv_col, "") if cv_col else ""
    
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
                            session.headers.update({"User-Agent": "Mozilla/5.0"})
                            
                            dl_url = f"https://docs.google.com/uc?export=download&id={file_id}"
                            resp = session.get(dl_url, stream=True, timeout=15)
                            
                            token = None
                            for k, v in resp.cookies.items():
                                if k.startswith('download_warning'): token = v; break
                            if token:
                                dl_url = f"https://docs.google.com/uc?export=download&confirm={token}&id={file_id}"
                                resp = session.get(dl_url, stream=True, timeout=15)
                                
                            if resp.status_code >= 500:
                                resp = requests.get(cv_url, timeout=15)
                                
                            pdf_content = resp.content
                        else:
                            resp = requests.get(cv_url, timeout=15)
                            pdf_content = resp.content

                        if resp.status_code == 200:
                            if not pdf_content.startswith(b"%PDF"):
                                st.error("⚠️ الملف ليس PDF صالح")
                            else:
                                tm = TranslationManager()
                                text = tm.extract_text_from_pdf(pdf_content)
                                if text.startswith("Error"): st.error(text)
                                else:
                                    trans = tm.translate_full_text(text)
                                    st.session_state[f"trans_{key_prefix}_{selected_idx}"] = {"orig": text, "trans": trans}
                        else:
                            st.error(f"خطأ في الوصول للملف: HTTP {resp.status_code}")
                    except Exception as e: st.error(f"Error: {str(e)}")
            else: st.warning("رابط السيرة الذاتية غير موجود")

    sheet_row = worker_row.get('__sheet_row')
    if not sheet_row: sheet_row = worker_row.get('__sheet_row_backup')
    
    if not sheet_row:
        if hasattr(st.session_state.db, "find_row_by_data"):
            with st.spinner("⏳ محاولة البحث..."):
                sheet_row = st.session_state.db.find_row_by_data(worker_name)

    if sheet_row:
        with st.popover(f"🗑️ {t('delete_btn', lang)}", use_container_width=True):
            st.warning(t("confirm_delete_msg", lang))
            if st.button(t("confirm_btn", lang), type="primary", use_container_width=True, key=f"del_confirm_{key_prefix}_{selected_idx}"):
                with st.spinner("⏳ جارٍ الحذف..."):
                    success = st.session_state.db.delete_row(sheet_row)
                    if success == True:
                        st.success(t("delete_success", lang))
                        time.sleep(1)
                        if f"last_scroll_{key_prefix}" in st.session_state: del st.session_state[f"last_scroll_{key_prefix}"]
                        st.rerun()
                    else:
                        st.error(f"{t('delete_error', lang)}: {success}")
    else:
        st.error(f"⚠️ {t('delete_error', lang)} (ID Missing)")

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
    else: st.info("لا يتوفر رابط معاينة")

def dashboard():
    user = st.session_state.user
    lang = st.session_state.lang
    
    if st.session_state.get('show_welcome'):
        if lang == 'ar':
            f_name = user.get('first_name_ar', '')
            fa_name = user.get('father_name_ar', '')
        else:
            f_name = user.get('first_name_en', '')
            fa_name = user.get('father_name_en', '')
            
        full_name = f"{f_name} {fa_name}".strip()
        if not full_name: full_name = user.get('username', 'User')
        
        msg = t("welcome_person", lang).format(name=full_name)
        st.success(f"💖 {msg}")
        st.toast(msg, icon="🎉")
        del st.session_state.show_welcome

    with st.sidebar:
        sc1, sc2, sc3 = st.columns([1, 2, 1])
        with sc2:
            if os.path.exists(IMG_PATH):
                st.image(IMG_PATH, use_container_width=True)
        
        credit_class = "programmer-credit en" if lang == "en" else "programmer-credit"
        line1 = "برمجة" if lang == "ar" else "By:"
        line2 = "السعيد الوزان" if lang == "ar" else "Alsaeed Alwazzan"
        st.markdown(f'<div class="{credit_class}">{line1}<br>{line2}</div>', unsafe_allow_html=True)
        
        st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
        
        if st.button("🌐 " + ("English" if lang == "ar" else "العربية"), key="lang_btn_dashboard", use_container_width=True):
            toggle_lang()
            st.rerun()
        
        st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)

        if st.button("📊 " + t("dashboard", lang), use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()
        if st.button("🔍 " + t("smart_search", lang), use_container_width=True):
            st.session_state.page = "search"
            st.rerun()
        if st.button("📝 " + t("cv_translator", lang), use_container_width=True):
            st.session_state.page = "translator"
            st.rerun()
        if st.button("📋 " + t("customer_requests", lang), use_container_width=True):
            st.session_state.page = "customer_requests"
            st.rerun()
        if st.button("⚙️ " + t("order_processing", lang), use_container_width=True):
            st.session_state.page = "order_processing"
            st.rerun()
        if user.get("role") == "admin":
            if st.button("🔐 " + t("permissions", lang), use_container_width=True):
                st.session_state.page = "permissions"
                st.rerun()
            
            if st.button("🔄 " + t("refresh_data_btn", lang), key="force_refresh_db", use_container_width=True):
                refresh_loader = show_loading_hourglass()
                st.session_state.db.fetch_data(force=True)
                refresh_loader.empty()
                st.success("تم التحديث!" if lang == 'ar' else "Updated!")
                time.sleep(1)
                st.rerun()
        
        st.markdown("<div style='margin: 15px 0;'></div>", unsafe_allow_html=True)
        
        if st.button("🚪 " + t("logout", lang), type="primary", use_container_width=True):
            st.session_state.user = None
            st.rerun()
        
        st.sidebar.divider()
        with st.sidebar.expander(t("deep_reset", lang)):
            st.caption(t("deep_reset_desc", lang))
            if st.button(t("deep_reset", lang), key="sidebar_deep_reset", use_container_width=True):
                for k in list(st.session_state.keys()):
                    if any(k.startswith(prefix) for prefix in ["dash_table_", "last_scroll_", "trans_", "search_results"]):
                        del st.session_state[k]
                st.session_state.db.fetch_data(force=True)
                st.success("تم التنظيف!")
                time.sleep(1)
                st.rerun()

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
    elif page == "customer_requests": render_customer_requests_content()
    elif page == "order_processing": render_order_processing_content()
    elif page == "permissions": render_permissions_content()
'''

print(fixed_login_code[:3000])
print("\n... [continued] ...")
