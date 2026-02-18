import streamlit as st
import pandas as pd
import os
import sys
import json
import hashlib
import time
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
                "first_name": "المدير",
                "father_name": "العام",
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

    def add_user(self, username, password, role="viewer", first_name="", father_name=""):
        username = username.lower().strip()
        if username in self.users:
            return False, "User already exists"
        
        self.users[username] = {
            "password": self.hash_password(password),
            "role": role,
            "first_name": first_name,
            "father_name": father_name,
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

    def update_profile(self, username, first_name=None, father_name=None):
        username = username.lower().strip()
        if username in self.users:
            if first_name is not None: self.users[username]["first_name"] = first_name
            if father_name is not None: self.users[username]["father_name"] = father_name
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
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 5. Apply Styles
st.markdown(get_css(), unsafe_allow_html=True)

# 6. Initialize Core (With Force Re-init for Updates)
if 'auth' not in st.session_state or not hasattr(st.session_state.auth, 'update_profile'):
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

# 10. CV Detail Panel Helper
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
        <p style="color:#ffffff; margin-top:5px;">يمكنك الآن معاينة السيرة الذاتية أو ترجمتها للغة العربية باستخدام الأزرار أدناه.</p>
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
        if os.path.exists(IMG_PATH):
            st.image(IMG_PATH, width=120)
        
        st.markdown(f'<p class="programmer-credit">{t("welcome_subtitle", "en")}</p>', unsafe_allow_html=True)
        st.markdown(f"<h2 style='margin-top:20px;'>{t('welcome_back', lang)}</h2>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='color:#888 !important; font-size:1rem;'>{t('system_title', lang)}</h3>", unsafe_allow_html=True)
        
        with st.form("login"):
            u = st.text_input(t("username", lang), label_visibility="collapsed", placeholder=t("username", lang))
            p = st.text_input(t("password", lang), type="password", label_visibility="collapsed", placeholder=t("password", lang))
            
            if st.form_submit_button(t("login_btn", lang)):
                user = st.session_state.auth.authenticate(u, p)
                if user:
                    st.session_state.user = user
                    st.session_state.show_welcome = True # Trigger welcome message
                    st.rerun()
                else:
                    st.error(t("invalid_creds", lang))

    with col1:
        if st.button("English / عربي", key="lang_btn_login"):
            toggle_lang()
            st.rerun()

def dashboard():
    user = st.session_state.user
    lang = st.session_state.lang
    
    # Welcome Message
    if st.session_state.get('show_welcome'):
        full_name = f"{user.get('first_name', '')} {user.get('father_name', '')}".strip()
        if not full_name: full_name = st.session_state.get('user_id', 'User')
        
        msg = t("welcome_person", lang).format(name=full_name)
        st.toast(msg, icon="🎉")
        del st.session_state.show_welcome

    with st.sidebar:
        st.image(IMG_PATH, width=100)
        st.markdown(f'<p class="programmer-credit" style="font-size:0.7em;">{t("programmer", "en")}</p>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.sidebar.button("English / عربي", key="lang_btn_dashboard"):
            toggle_lang()
            st.rerun()
        
        st.markdown("<div style='margin: 15px 0;'></div>", unsafe_allow_html=True)

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
    st.title(f" {t('contract_dashboard', lang)}")
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
    
    def show(data, tab_id):
        if not data: st.info(t("no_data", lang)); return
        d = pd.DataFrame(data)
        
        # Select columns
        show_cols = ['Status'] + [c for c in cols if c in d.columns and c not in ["__sheet_row", "__sheet_row_backup"]]
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
        
        st.info("💡 **نصيحة**: اضغط على أي صف في الجدول لمشاهدة السيرة الذاتية وترجمتها بالأسفل.")
        event = st.dataframe(
            d_final, 
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
    st.title(f" {t('smart_search_title', lang)}")
    
    # Force Refresh button in sidebar or top
    if st.button(t("refresh_data_btn", lang), key="force_refresh_db"):
        st.session_state.db.fetch_data(force=True)
        st.success("تم تحديث البيانات من Google Sheets بنجاح!" if lang == 'ar' else "Data refreshed successfully!")
        st.rerun()
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

        print(f"[SEARCH] Search triggered - Query: '{query}', Filters: {filters}")
        
        # Fetch fresh data
        original_data = st.session_state.db.fetch_data()
        total_rows = len(original_data)
        
        if total_rows == 0:
            st.error("لم يتم العثور على أي بيانات في قاعدة البيانات. تأكد من الربط مع Google Sheets.")
            return

        eng = SmartSearchEngine(original_data)
        try:
            res = eng.search(query, filters=filters)
            
            # Show count in UI
            count_found = len(res)
            if count_found > 0:
                st.success(f"{'تم العثور على' if lang == 'ar' else 'Found'} {count_found} {'نتائج من أصل' if lang == 'ar' else 'results out of'} {total_rows}")
            
            # Handle both DataFrame and list returns
            is_empty = (isinstance(res, list) and len(res) == 0) or (hasattr(res, 'empty') and res.empty)
            
            if is_empty:
                st.warning(t("no_results", lang))
            elif has_active_filter and count_found == total_rows:
                st.warning("تنبيه: تم تفعيل الفلاتر ولكن لم يتم استبعاد أي نتائج.")
                with st.expander("تشخيص الأعمدة (للمطور)"):
                    st.write("الأعمدة المتوفرة حالياً في الملف:", list(original_data.columns))
                    # Check for diagnostic markers
                    age_c = res['__matched_age_col'].iloc[0] if '__matched_age_col' in res.columns else "لم يتم العثور عليه"
                    contract_c = res['__matched_contract_col'].iloc[0] if '__matched_contract_col' in res.columns else "لم يتم العثور عليه"
                    ts_c = res['__matched_ts_col'].iloc[0] if '__matched_ts_col' in res.columns else "لم يتم العثور عليه"
                    st.info(f"عمود العمر المكتشف: {age_c}")
                    st.info(f"عمود العقد المكتشف: {contract_c}")
                    st.info(f"عمود القيد المكتشف: {ts_c}")
            
            # Clean up internal diagnostic columns before display
            for diag_col in ['__matched_age_col', '__matched_contract_col', '__matched_ts_col']:
                if diag_col in res.columns:
                    res = res.drop(columns=[diag_col])
        except Exception as e:
            st.error(f"حدث خطأ أثناء البحث: {str(e)}")
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
            
            res_display = res_to_rename.rename(columns=new_names)
            
            # --- ROW SELECTION & PROFESSIONAL UI ---
            st.divider()
            st.success("💡 **خطوة إضافية**: اضغط على أي صف في الجدول أدناه لتظهر لك أزرار (المعاينة والترجمة) لهذا العامل بالتحديد.")
            st.subheader(f"{'نتائج البحث' if lang == 'ar' else 'Search Results'}")
            
            # Configure columns for better look
            column_config = {}
            cv_col_name = t_col("Download CV", lang)
            column_config[cv_col_name] = st.column_config.LinkColumn(
                cv_col_name,
                help="Click to open original file",
                validate="^http",
                display_text="فتح الملف 🔗"
            )

            # Use on_select to capture row selection
            event = st.dataframe(
                res_display, 
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
            else:
                st.info("💡 اختر اسماً من الجدول أعلاه لمعاينة السيرة الذاتية وترجمتها.")

def render_translator_content():
    lang = st.session_state.lang
    st.title(f" {t('translator_title', lang)}")
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
    st.title(f" {t('permissions_title', lang)}")
    
    with st.expander(t("add_user", lang), expanded=False):
        with st.form("new_user"):
            u = st.text_input(t("username", lang))
            p = st.text_input(t("password", lang), type="password")
            fn = st.text_input(t("first_name", lang))
            ftn = st.text_input(t("father_name", lang))
            r = st.selectbox(t("role", lang), ["viewer", "admin"])
            if st.form_submit_button(t("add_btn", lang)):
                s, m = st.session_state.auth.add_user(u, p, r, fn, ftn)
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
            new_first = st.text_input(t("first_name", lang), value=current_data.get("first_name", ""))
            new_father = st.text_input(t("father_name", lang), value=current_data.get("father_name", ""))
            new_pass = st.text_input(t("new_password", lang), type="password")
            
            if st.form_submit_button(t("update_btn", lang)):
                st.session_state.auth.update_role(selected_user, new_role)
                st.session_state.auth.update_profile(selected_user, new_first, new_father)
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
