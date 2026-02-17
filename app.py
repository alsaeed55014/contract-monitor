import streamlit as st
import pandas as pd
import os
import sys
import json
import hashlib
from datetime import datetime, timedelta

# 1. Ensure project root is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 2. Local Auth Class to prevent Import/Sync Errors
class AuthManager:
    def __init__(self, users_file_path):
        self.users_file = users_file_path
        self.users = {}
        self.load_users()

    def load_users(self):
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.users = data.get("users", {})
            except Exception as e:
                print(f"Error loading users: {e}")
                self.users = {}
        
        # Ensure Default Admin
        if "admin" not in self.users:
            self.users["admin"] = {
                "password": self.hash_password("admin123"), # Default password
                "role": "admin",
                "full_name_ar": "المدير العام",
                "full_name_en": "General Manager",
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

    def add_user(self, username, password, role="viewer", name_ar="", name_en=""):
        username = username.lower().strip()
        if username in self.users:
            return False, "User already exists"
        
        self.users[username] = {
            "password": self.hash_password(password),
            "role": role,
            "full_name_ar": name_ar,
            "full_name_en": name_en,
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

# 3. Imports with Error Handling
try:
    from src.core.search import SmartSearchEngine
    from src.core.contracts import ContractManager
    from src.core.translation import TranslationManager
    from src.data.db_client import DBClient
    from src.ui.streamlit_styles import get_css
    from src.config import USERS_FILE, ASSETS_DIR
    from src.core.i18n import t, t_col # Added t_col
except ImportError as e:
    st.error(f"Critical Import Error: {e}")
    st.stop()
except KeyError as e:
    st.error(f"Configuration Error (KeyError): {e} - Possible issue in i18n or config.")
    st.stop()

# 4. Page Config
st.set_page_config(
    page_title="Golden Noura | Contract Monitor",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 5. Apply Styles
st.markdown(get_css(), unsafe_allow_html=True)

# 6. Initialize Core (With Force Re-init for Updates)
if 'auth' not in st.session_state or not hasattr(st.session_state.auth, 'update_role'):
    st.session_state.auth = AuthManager(USERS_FILE)

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

# 10. Logic Functions
def login_screen():
    lang = st.session_state.lang
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        if os.path.exists(IMG_PATH):
            st.image(IMG_PATH, width=150)
        else:
            st.warning(t("image_not_found", lang))
            
        st.markdown(f"## {t('welcome_back', lang)}")
        st.markdown(f"### {t('system_title', lang)}")
        
        with st.form("login"):
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

    with col1:
        if st.button("English / عربي", key="lang_btn_login"):
            toggle_lang()
            st.rerun()

def dashboard():
    user = st.session_state.user
    lang = st.session_state.lang
    
    with st.sidebar:
        st.image(IMG_PATH, width=100)
        st.markdown(f'<div style="text-align: center; margin-bottom: 10px; font-size: 0.8em; color: #D4AF37;">{t("programmer", "en")}</div>', unsafe_allow_html=True)
        st.markdown("---")
        
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
    st.title(f"📊 {t('contract_dashboard', lang)}")
    try:
        df = st.session_state.db.fetch_data()
    except Exception as e:
        st.error(f"{t('error', lang)}: {e}")
        return

    if df.empty:
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
            r['Status'] = status['label_ar'] if lang == 'ar' else status['label_en']
            
            if global_status == 'urgent': stats['urgent'].append(r)
            elif global_status == 'expired': stats['expired'].append(r)
            elif global_status == 'active': stats['active'].append(r)
        except Exception as e:
            continue

    c1, c2, c3 = st.columns(3)
    c1.metric(t("urgent_7_days", lang), len(stats['urgent']), delta_color="inverse")
    c2.metric(t("expired", lang), len(stats['expired']), delta_color="inverse")
    c3.metric(t("active", lang), len(stats['active']))
    st.markdown("---")
    
    cv_col = next((c for c in cols if "cv" in c.lower() or "سيرة" in c.lower()), None)
    
    # Configuration for LinkColumn needs the TRANSLATED column name if we rename it!
    # But Streamlit LinkColumn config keys must match the dataframe columns.
    
    t1, t2, t3 = st.tabs([t("tabs_urgent", lang), t("tabs_expired", lang), t("tabs_active", lang)])
    
    def show(data):
        if not data: st.info(t("no_data", lang)); return
        d = pd.DataFrame(data)
        
        # Select columns
        show_cols = ['Status'] + [c for c in cols if c in d.columns]
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
        
        st.dataframe(d_final, use_container_width=True, column_config=final_cfg)

    with t1: show(stats['urgent'])
    with t2: show(stats['expired'])
    with t3: show(stats['active'])

def render_search_content():
    lang = st.session_state.lang
    st.title(f"🔍 {t('smart_search_title', lang)}")
    
    # Labels
    lbl_age = t("age", lang) if t("age", lang) != "age" else "العمر"
    lbl_contract = t("contract_end", lang) if t("contract_end", lang) != "contract_end" else "تاريخ انتهاء العقد"
    lbl_reg = t("registration_date", lang) if t("registration_date", lang) != "registration_date" else "تاريخ التسجيل"
    lbl_enable = "تفعيل" if lang == "ar" else "Enable"
    
    # Advanced Filters UI
    with st.expander(t("advanced_filters", lang) if t("advanced_filters", lang) != "advanced_filters" else "تصفية متقدمة"):
        c3, c2, c1 = st.columns(3)
        
        # Registration Date Filter (rightmost in RTL)
        with c1:
            use_reg = st.checkbox(f"🔘 {lbl_enable} {lbl_reg}", key="use_reg_filter")
            if use_reg:
                st.caption(lbl_reg)
                today = datetime.now().date()
                first_of_month = today.replace(day=1)
                reg_range = st.date_input("Registration Range", (first_of_month, today), label_visibility="collapsed", key="reg_range")
            else:
                reg_range = []

        # Contract End Filter
        with c2:
            use_contract = st.checkbox(f"🔘 {lbl_enable} {lbl_contract}", key="use_contract_filter")
            if use_contract:
                st.caption(lbl_contract)
                today = datetime.now().date()
                next_month = today + timedelta(days=30)
                contract_range = st.date_input("Contract Range", (today, next_month), label_visibility="collapsed", key="contract_range")
            else:
                contract_range = []
        
        # Age Filter (leftmost in RTL)
        with c3:
            use_age = st.checkbox(f"🔘 {lbl_enable} {lbl_age}", key="use_age_filter")
            if use_age:
                age_range = st.slider(lbl_age, 18, 60, (20, 45), key="age_slider")
            else:
                age_range = (18, 60)

    query = st.text_input(t("smart_search", lang), placeholder=t("search_placeholder", lang))
    
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
    
    if st.button(t("search_btn", lang)) or query or has_active_filter:
        # Debug: Show what filters are being sent
        if filters:
            active_filter_names = []
            if filters.get('age_enabled'): active_filter_names.append(f"{lbl_age}: {filters.get('age_min')}-{filters.get('age_max')}")
            if filters.get('contract_enabled'): active_filter_names.append(f"{lbl_contract}")
            if filters.get('date_enabled'): active_filter_names.append(f"{lbl_reg}")
            if active_filter_names:
                st.info(f"{'الفلاتر النشطة' if lang == 'ar' else 'Active filters'}: {', '.join(active_filter_names)}")

        print(f"🔎 Search triggered - Query: '{query}', Filters: {filters}")
        
        eng = SmartSearchEngine(st.session_state.db.fetch_data())
        
        # Debug: Print column names
        data = st.session_state.db.fetch_data()
        print(f"📋 Available columns: {list(data.columns)}")
        
        res = eng.search(query, filters=filters)
        
        # Handle both DataFrame and list returns
        is_empty = (isinstance(res, list) and len(res) == 0) or (hasattr(res, 'empty') and res.empty)
        
        if is_empty:
            st.warning(t("no_results", lang))
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
            
            res_display = res.rename(columns=new_names)
            st.success(f"{'تم العثور على' if lang == 'ar' else 'Found'} {len(res_display)} {'نتيجة' if lang == 'ar' else 'results'}")
            st.dataframe(res_display, use_container_width=True)

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
    
    with st.expander(t("add_user", lang), expanded=False):
        with st.form("new_user"):
            u = st.text_input(t("username", lang))
            p = st.text_input(t("password", lang), type="password")
            r = st.selectbox(t("role", lang), ["viewer", "admin"])
            if st.form_submit_button(t("add_btn", lang)):
                s, m = st.session_state.auth.add_user(u, p, r)
                if s: st.success(t("user_added", lang))
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
            new_pass = st.text_input(t("new_password", lang), type="password")
            
            if st.form_submit_button(t("update_btn", lang)):
                st.session_state.auth.update_role(selected_user, new_role)
                if new_pass:
                    st.session_state.auth.update_password(selected_user, new_pass)
                st.success(t("update_success", lang))
                st.rerun()
    
    # Translate table keys for Users Table
    table_data = []
    for k, v in users.items():
        table_data.append({
            t_col("User", lang): k,
            t_col("Role", lang): v.get('role', 'viewer')
        })
    st.dataframe(table_data, use_container_width=True)

# 11. Main Entry
if not st.session_state.user:
    login_screen()
else:
    dashboard()
