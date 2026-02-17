import streamlit as st
import pandas as pd
import os
import sys

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.auth import AuthManager
from src.core.search import SmartSearchEngine
from src.core.contracts import ContractManager
from src.core.translation import TranslationManager
from src.data.db_client import DBClient
from src.ui.streamlit_styles import get_css
from src.config import USERS_FILE, ASSETS_DIR
from src.core.i18n import t

# Page Config
st.set_page_config(
    page_title="Golden Noura | Contract Monitor",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply Styles
st.markdown(get_css(), unsafe_allow_html=True)

# Initialize Core
if 'auth' not in st.session_state:
    st.session_state.auth = AuthManager(USERS_FILE)
if 'db' not in st.session_state:
    st.session_state.db = DBClient()

# Session State & Language
if 'user' not in st.session_state:
    st.session_state.user = None
if 'lang' not in st.session_state:
    st.session_state.lang = 'ar' # Default Arabic

# Constants
IMG_PATH = os.path.join(ASSETS_DIR, "alsaeed.jpg")
if not os.path.exists(IMG_PATH):
    IMG_PATH = "alsaeed.jpg"

def toggle_lang():
    if st.session_state.lang == 'ar': st.session_state.lang = 'en'
    else: st.session_state.lang = 'ar'

# --- LOGIN SCREEN ---
def login_screen():
    lang = st.session_state.lang
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        if os.path.exists(IMG_PATH):
            st.image(IMG_PATH, width=150) # Smaller Image
        else:
            st.warning(t("image_not_found", lang))
            
        st.markdown(f"## {t('welcome_back', lang)}")
        st.markdown(f"### {t('system_title', lang)}")
        
        with st.form("login"):
            # Language Toggle inside form or above? Above is better but form is cleaner
            st.markdown(f'<p style="text-align:right; font-size:0.8em; cursor:pointer;" onclick="window.location.reload()">{"EN" if lang=="ar" else "عربي"}</p>', unsafe_allow_html=True)
            
            u = st.text_input(t("username", lang), label_visibility="collapsed", placeholder=t("username", lang))
            p = st.text_input(t("password", lang), type="password", label_visibility="collapsed", placeholder=t("password", lang))
            
            if st.form_submit_button(t("login_btn", lang)):
                user = st.session_state.auth.authenticate(u, p)
                if user:
                    st.session_state.user = user
                    st.success(t("success", lang))
                    st.rerun()
                else:
                    st.error(t("invalid_creds", lang))
        
        st.markdown(f'<p class="programmer-credit">{t("programmer", lang)}</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Simple Language Toggle Button (Outside box for logic safety)
    with col1:
        if st.button("English / عربي", key="lang_btn_login"):
            toggle_lang()
            st.rerun()

    # --- DEBUG SECTION (REMOVE LATER) ---
    with st.expander("🛠️ Connection Debugger"):
        st.write("Checking Secrets...")
        if hasattr(st, "secrets"):
            st.success("Secrets found!")
            if "gcp_service_account" in st.secrets:
                st.success("Key 'gcp_service_account' found!")
            else:
                st.error("Key 'gcp_service_account' MISSING in secrets.")
        else:
            st.error("No secrets found at all.")
            
        if st.button("Test Connection"):
            try:
                db = DBClient()
                db.connect()
                if db.client:
                    st.success("Client Connected!")
                    data = db.fetch_data(force=True)
                    st.write(f"Data shape: {data.shape}")
                else:
                    st.error("Client connection failed.")
            except Exception as e:
                st.error(f"Error: {e}")

# --- DASHBOARD ---
def dashboard():
    user = st.session_state.user
    lang = st.session_state.lang
    
    with st.sidebar:
        st.image(IMG_PATH, width=100)
        # Removed "User" text, added Programmer Credit
        st.markdown(f'<div style="text-align: center; margin-bottom: 10px; font-size: 0.8em; color: #D4AF37;">{t("programmer", "en")}</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Language Selector
        if st.sidebar.button("English / عربي", key="lang_btn_dashboard"):
            toggle_lang()
            st.rerun()
            
        st.markdown("---")

        if st.button(t("dashboard", lang)):
            st.session_state.page = "dashboard"
            st.rerun()
        if st.button(t("smart_search", lang)):
            st.session_state.page = "search"
            st.rerun()
        if st.button(t("cv_translator", lang)):
            st.session_state.page = "translator"
            st.rerun()
        if user.get("role") == "admin":
            if st.button(t("permissions", lang)):
                st.session_state.page = "permissions"
                st.rerun()
        st.markdown("---")
        if st.button(t("logout", lang), type="primary"):
            st.session_state.user = None
            st.rerun()

    # Sidebar Debugger
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
    st.title(f"📊 {t('contract_dashboard', lang)}")
    
    try:
        df = st.session_state.db.fetch_data()
    except Exception as e:
        st.error(f"{t('error', lang)}: {e}")
        return

    if df.empty:
        st.warning(t("no_data", lang))
        return

    # Translate Headers if Arabic
    if lang == 'ar':
        # Simple mapping heuristic or strict mapping
        # Trying to detect columns dynamically
        pass 

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
            # Translate Status Label
            r['Status'] = status['label_ar'] if lang == 'ar' else status['label_en']
            
            if status['status'] == 'urgent': stats['urgent'].append(r)
            elif status['status'] == 'expired': stats['expired'].append(r)
            elif status['status'] == 'active': stats['active'].append(r)
        except Exception as e:
            continue

    c1, c2, c3 = st.columns(3)
    c1.metric(t("urgent_7_days", lang), len(stats['urgent']), delta_color="inverse")
    c2.metric(t("expired", lang), len(stats['expired']), delta_color="inverse")
    c3.metric(t("active", lang), len(stats['active']))
    
    st.markdown("---")
    
    cv_col = next((c for c in cols if "cv" in c.lower() or "سيرة" in c.lower()), None)
    cfg = {}
    if cv_col:
        cfg[cv_col] = st.column_config.LinkColumn(t("cv_download", lang), display_text=t("download_pdf", lang))

    t1, t2, t3 = st.tabs([t("tabs_urgent", lang), t("tabs_expired", lang), t("tabs_active", lang)])
    
    def show(data):
        if not data: st.info(t("no_data", lang)); return
        d = pd.DataFrame(data)
        # Column selection
        show_cols = ['Status'] + [c for c in cols if c in d.columns]
        st.dataframe(d[show_cols], use_container_width=True, column_config=cfg)

    with t1: show(stats['urgent'])
    with t2: show(stats['expired'])
    with t3: show(stats['active'])

def render_search_content():
    lang = st.session_state.lang
    st.title(f"🔍 {t('smart_search_title', lang)}")
    query = st.text_input(t("smart_search", lang), placeholder=t("search_placeholder", lang))
    if st.button(t("search_btn", lang)) or query:
        eng = SmartSearchEngine(st.session_state.db.fetch_data())
        res = eng.search(query)
        if res.empty: st.warning(t("no_results", lang))
        else: st.dataframe(res, use_container_width=True)

def render_translator_content():
    lang = st.session_state.lang
    st.title(f"📄 {t('translator_title', lang)}")
    st.markdown(t("translator_desc", lang))
    
    uploaded = st.file_uploader(t("upload_cv", lang), type=["pdf"])
    if uploaded:
        if st.button(t("translate_now", lang)):
            tm = TranslationManager()
            with st.spinner(t("extracting", lang)):
                text = tm.extract_text_from_pdf(uploaded.read())
                if text.startswith("Error"):
                    st.error(text)
                else:
                    trans = tm.translate_full_text(text)
                    c1, c2 = st.columns(2)
                    with c1:
                        st.subheader(t("original", lang))
                        st.text_area("Original", text, height=400)
                    with c2:
                        st.subheader(t("translated", lang))
                        st.text_area("Translated", trans, height=400)
                    
                    st.download_button(t("download_trans", lang), trans, file_name="translated_cv.txt")

def render_permissions_content():
    lang = st.session_state.lang
    st.title(f"🔑 {t('permissions_title', lang)}")
    
    # Add User
    with st.expander(t("add_user", lang), expanded=False):
        with st.form("new_user"):
            u = st.text_input(t("username", lang))
            p = st.text_input(t("password", lang), type="password")
            r = st.selectbox(t("role", lang), ["viewer", "admin"])
            if st.form_submit_button(t("add_btn", lang)):
                s, m = st.session_state.auth.add_user(u, p, r)
                if s: st.success(t("user_added", lang))
                else: st.error(m)

    # List & Edit Users
    st.subheader(t("users_list", lang))
    
    users = st.session_state.auth.users
    user_list = list(users.keys())
    
    # Edit User Section
    selected_user = st.selectbox(t("select_user", lang), user_list)
    if selected_user:
        current_data = users[selected_user]
        with st.form("edit_user_form"):
            st.write(f"Editing: **{selected_user}**")
            new_role = st.selectbox(t("role", lang), ["viewer", "admin"], index=0 if current_data["role"]=="viewer" else 1)
            new_pass = st.text_input(t("new_password", lang), type="password")
            
            if st.form_submit_button(t("update_btn", lang)):
                # Update Role
                st.session_state.auth.update_role(selected_user, new_role)
                # Update Password if provided
                if new_pass:
                    st.session_state.auth.update_password(selected_user, new_pass)
                st.success(t("update_success", lang))
                st.rerun()
    
    # Read-only Table
    st.dataframe([{"User": k, "Role": v['role']} for k, v in users.items()], use_container_width=True)

if not st.session_state.user:
    login_screen()
else:
    dashboard()
