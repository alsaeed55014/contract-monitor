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

# Session State
if 'user' not in st.session_state:
    st.session_state.user = None

# Constants
IMG_PATH = os.path.join(ASSETS_DIR, "alsaeed.jpg")
if not os.path.exists(IMG_PATH):
    IMG_PATH = "alsaeed.jpg"

# --- LOGIN SCREEN ---
def login_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        if os.path.exists(IMG_PATH):
            st.image(IMG_PATH, width=200)
        else:
            st.warning("⚠️ Image not found")
            
        st.markdown("## WELCOME BACK")
        st.markdown("### Contract Monitor System")
        
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("LOGIN"):
                user = st.session_state.auth.authenticate(u, p)
                if user:
                    st.session_state.user = user
                    st.success("Welcome!")
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        st.markdown('<p class="programmer-credit">Programmed by Alsaeed Alwazzan</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- DEBUG SECTION (REMOVE LATER) ---
    with st.expander("🛠️ Connection Debugger"):
        st.write("Checking Secrets...")
        if hasattr(st, "secrets"):
            st.success("Secrets found!")
            if "gcp_service_account" in st.secrets:
                st.success("Key 'gcp_service_account' found!")
                # st.json(dict(st.secrets["gcp_service_account"])) 
            else:
                st.error("Key 'gcp_service_account' MISSING in secrets.")
        else:
            st.error("No secrets found at all.")

# --- DASHBOARD ---
def dashboard():
    user = st.session_state.user
    with st.sidebar:
        st.image(IMG_PATH, width=100)
        st.subheader(f"👤 {user.get('full_name_en', 'User')}")
        st.markdown("---")
        
        if st.button("🏠 Dashboard"):
            st.session_state.page = "dashboard"
            st.rerun()
        if st.button("🔍 Smart Search"):
            st.session_state.page = "search"
            st.rerun()
        if st.button("📄 CV Translator"):
            st.session_state.page = "translator"
            st.rerun()
        if user.get("role") == "admin":
            if st.button("🔑 Permissions"):
                st.session_state.page = "permissions"
                st.rerun()
        st.markdown("---")
        if st.button("🚪 Logout", type="primary"):
            st.session_state.user = None
            st.rerun()

    # Sidebar Debugger
    if user.get("role") == "admin":
        with st.sidebar.expander("🛠️ Debug"):
            if st.button("Test DB"):
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
    st.title("📊 Contract Dashboard")
    
    try:
        df = st.session_state.db.fetch_data()
    except Exception as e:
        st.error(f"Database Error: {e}")
        return

    if df.empty:
        st.warning("No data found. Please check 'Test DB' in sidebar.")
        return

    cols = df.columns.tolist()
    date_col = next((c for c in cols if "contract end" in c.lower() or "انتهاء العقد" in c.lower()), None)
    if not date_col:
        st.error(f"Date column not found. Available columns: {cols}")
        return

    stats = {'urgent': [], 'expired': [], 'active': []}
    for _, row in df.iterrows():
        try:
            status = ContractManager.calculate_status(row[date_col])
            r = row.to_dict()
            r['Status'] = status['label_en']
            if status['status'] == 'urgent': stats['urgent'].append(r)
            elif status['status'] == 'expired': stats['expired'].append(r)
            elif status['status'] == 'active': stats['active'].append(r)
        except Exception as e:
            continue

    c1, c2, c3 = st.columns(3)
    c1.metric("Urgent (7 Days)", len(stats['urgent']), delta_color="inverse")
    c2.metric("Expired", len(stats['expired']), delta_color="inverse")
    c3.metric("Active", len(stats['active']))
    
    st.markdown("---")
    
    cv_col = next((c for c in cols if "cv" in c.lower() or "سيرة" in c.lower()), None)
    cfg = {}
    if cv_col:
        cfg[cv_col] = st.column_config.LinkColumn("CV Download", display_text="Download PDF")

    t1, t2, t3 = st.tabs(["🔴 Urgent", "⚫ Expired", "🟢 Active"])
    
    def show(data):
        if not data: st.info("No contracts."); return
        d = pd.DataFrame(data)
        st.dataframe(d[['Status'] + [c for c in cols if c in d.columns]], use_container_width=True, column_config=cfg)

    with t1: show(stats['urgent'])
    with t2: show(stats['expired'])
    with t3: show(stats['active'])

def render_search_content():
    st.title("🔍 Smart AI Search")
    query = st.text_input("Smart Search", placeholder="e.g. Filipino Driver, +96650...")
    if st.button("Search") or query:
        eng = SmartSearchEngine(st.session_state.db.fetch_data())
        res = eng.search(query)
        if res.empty: st.warning("No results.")
        else: st.dataframe(res, use_container_width=True)

def render_translator_content():
    st.title("📄 CV Translator")
    st.markdown("Upload a CV (PDF) to translate it from English to Arabic automatically.")
    
    uploaded = st.file_uploader("Upload CV", type=["pdf"])
    if uploaded:
        if st.button("Translate Now"):
            tm = TranslationManager()
            with st.spinner("Extracting & Translating..."):
                text = tm.extract_text_from_pdf(uploaded.read())
                if text.startswith("Error"):
                    st.error(text)
                else:
                    trans = tm.translate_full_text(text)
                    c1, c2 = st.columns(2)
                    with c1:
                        st.subheader("Original (English)")
                        st.text_area("Original", text, height=400)
                    with c2:
                        st.subheader("Translated (Arabic)")
                        st.text_area("Translated", trans, height=400)
                    
                    st.download_button("Download Translation", trans,file_name="translated_cv.txt")

def render_permissions_content():
    st.title("🔑 Permissions")
    with st.form("new_user"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        r = st.selectbox("Role", ["viewer", "admin"])
        if st.form_submit_button("Add User"):
            s, m = st.session_state.auth.add_user(u, p, r)
            if s: st.success(m)
            else: st.error(m)
    
    st.subheader("Users")
    st.dataframe([{"User": k, "Role": v['role']} for k, v in st.session_state.auth.users.items()], use_container_width=True)

if not st.session_state.user:
    login_screen()
else:
    dashboard()
