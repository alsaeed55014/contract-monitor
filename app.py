import streamlit as st
import os
import sys

# 1. Ensure project root is in path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# 2. Imports from refactored modules
from src.core.auth import AuthManager
from src.ui.streamlit_styles import get_css
from src.ui.streamlit_components import login_screen, render_top_banner
from src.core.notifications import silent_notification_monitor
from src.data.db_client import DBClient
from src.config import USERS_FILE, ASSETS_DIR

# 3. Page Config
st.set_page_config(
    page_title="السعيد الوزان | نظام مراقبة العقود",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 4. Initialize Core
if 'auth' not in st.session_state:
    st.session_state.auth = AuthManager(USERS_FILE)
    st.session_state.db = DBClient()

if 'user' not in st.session_state:
    st.session_state.user = None
if 'lang' not in st.session_state:
    st.session_state.lang = 'ar'

# 5. Apply Styles
st.markdown(get_css(st.session_state.lang), unsafe_allow_html=True)

# 6. Auth Flow
if st.session_state.user is None:
    # Local helpers for login_screen (simplified for example)
    def load_saved_credentials(): return None
    def save_credentials(u, p): pass
    def clear_credentials(): pass
    def toggle_lang():
        st.session_state.lang = 'en' if st.session_state.lang == 'ar' else 'ar'

    login_screen(st.session_state.auth, lambda x, l: x, toggle_lang, load_saved_credentials, save_credentials, clear_credentials)
else:
    # Background Monitor
    silent_notification_monitor()
    
    # Top Banner
    render_top_banner(st.session_state.user, st.session_state.lang, st.session_state.auth)
    
    # Sidebar & Routing
    st.sidebar.title("القائمة")
    if st.sidebar.button("لوحة التحكم"):
        st.session_state.page = "dashboard"
    
    # Render Content (importing dynamically to keep app.py light)
    page = st.session_state.get('page', 'dashboard')
    if page == "dashboard":
        from src.ui.streamlit.dashboard import render_dashboard_content
        render_dashboard_content()
    
    if st.sidebar.button("تسجيل الخروج"):
        st.session_state.user = None
        st.rerun()
