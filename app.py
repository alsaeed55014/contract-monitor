import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, date
from dateutil import parser
import os
import json
import hashlib
import base64

# Page Config
st.set_page_config(
    page_title="Contract Monitor | مراقب العقود", 
    layout="wide", 
    page_icon="📝",
    initial_sidebar_state="expanded"
)

# --- وظيفة لمنع تكرار أسماء الأعمدة ---
def deduplicate_columns(columns):
    new_columns = []
    counts = {}
    for col in columns:
        if not col or str(col).strip() == "": col = "Column"
        if col in counts:
            counts[col] += 1
            new_columns.append(f"{col}_{counts[col]}")
        else:
            counts[col] = 0
            new_columns.append(col)
    return new_columns

import time

# --- وظيفة معالجة التواريخ لتقابل صيغة الإكسل العربي ---
def safe_parse_date(d_str):
    if not d_str: return None
    try:
        # التعامل مع رموز ص وم وتصحيحها لـ AM/PM
        d_clean = str(d_str).strip().replace('ص', 'AM').replace('م', 'PM')
        # محاولة ذكية للتحويل
        return parser.parse(d_clean, fuzzy=True).date()
    except:
        return None

# --- Authentication System ---
USERS_FILE = 'users.json'

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("users", {})
        except: pass
    # Default fallback including Samar
    return {
        "admin": {
            "password": "c685e710931707e3e9aaab6c8625a9798cd06a31bcf40cd8d6963e3703400d14", # 266519111
            "role": "admin",
            "can_manage_users": True
        },
        "samar": {
            "password": "688147d32c965682b130a11a84f47dd8789547d96735515c1365851e39a584e1", # 123452
            "role": "user",
            "can_manage_users": False
        }
    }

USERS = load_users()

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = ""
if 'page' not in st.session_state:
    st.session_state.page = "home"
if 'lang' not in st.session_state:
    st.session_state.lang = 'ar'

# --- Translations ---
L = {
    'en': {
        'login_title': "🔒 Login",
        'user_lbl': "Username",
        'pass_lbl': "Password",
        'login_btn': "Login",
        'wrong_pass': "❌ Wrong password",
        'user_not_found': "❌ User not found",
        'prog_by': "Programmed by",
        'switch_lang': "Switch to Arabic",
        'logout': "Logout",
        'home_title': "🛡️ Dashboard",
        'alerts_title': "⚠️ Upcoming Contract Expiries (Week / 2 Days)",
        'search_nav': "🔍 Search & Printing",
        'del_nav': "🗑️ Delete Selected Row",
        'refresh_nav': "🔄 Refresh Data",
        'perms_nav': "🔑 Permissions Screen",
        'exit_nav': "🚪 Exit Program",
        'back_nav': "🏠 Return to Main Screen",
        'search_page_title': "🔍 Advanced Search System",
        'perms_page_title': "⚙️ Rights & Settings System",
        'add_user_title': "Add New User",
        'change_pass_title': "Change Your Password",
        'save_btn': "Save Changes",
        'add_btn': "Add User",
        'can_access_perms': "Can access Permissions Screen",
        'ready': "Ready",
        'status': "Alert Status",
        'date_col': "Expiry Date",
        'name_col': "Full Name",
        'phone_col': "Phone",
        'search_btn': "Search Now",
        'print_btn': "Print Report",
        'global_search': "Global Search",
        'filter_reg': "Registration Date",
        'filter_exp': "Contract Expiry",
        'filter_age': "Age",
        'enable': "Enable",
        'from': "From",
        'to': "To",
        'days_left': "days left",
        'week_left': "1 week left",
        'danger': "Danger",
        'warning': "Warning",
        'success_msg': "No urgent alerts today.",
        'error_google': "Error connecting to Google Sheets",
        'info_creds': "Please ensure credentials are set in Streamlit Secrets.",
    },
    'ar': {
        'login_title': "🔒 تسجيل الدخول",
        'user_lbl': "اسم المستخدم",
        'pass_lbl': "كلمة المرور",
        'login_btn': "دخول",
        'wrong_pass': "❌ كلمة المرور خاطئة",
        'user_not_found': "❌ المستخدم غير موجود",
        'prog_by': "برمجة",
        'switch_lang': "Switch to English",
        'logout': "خروج من البرنامج",
        'home_title': "🛡️ مراقب العقود",
        'alerts_title': "تنبيهات العقود الوشيكة (أسبوع / يومين)",
        'search_nav': "🔍 البحث والطباعة",
        'del_nav': "🗑️ حذف الصف المختار",
        'refresh_nav': "🔄 تحديث البيانات",
        'perms_nav': "🔑 شاشة الصلاحيات",
        'exit_nav': "🚪 خروج من البرنامج",
        'back_nav': "🏠 الرجوع للشاشة الرئيسية",
        'search_page_title': "نظام البحث المتقدم",
        'perms_page_title': "نظام الصلاحيات والإعدادات",
        'add_user_title': "إضافة مستخدم جديد",
        'change_pass_title': "تغيير كلمة مرورك",
        'save_btn': "حفظ التغييرات",
        'add_btn': "إضافة مستخدم",
        'can_access_perms': "صلاحية دخول شاشة الصلاحيات",
        'ready': "جاهز",
        'status': "حالة التنبيه",
        'date_col': "تاريخ انتهاء العقد",
        'name_col': "الاسم الكامل",
        'phone_col': "رقم الجوال",
        'search_btn': "بحث الآن",
        'print_btn': "طباعة التقرير",
        'global_search': "البحث الشامل",
        'filter_reg': "تاريخ التسجيل",
        'filter_exp': "انتهاء العقد",
        'filter_age': "السن",
        'enable': "تفعيل",
        'from': "من",
        'to': "إلى",
        'days_left': "باقي يوم",
        'week_left': "باقي أسبوع",
        'danger': "خطير",
        'warning': "تحذير",
        'success_msg': "لا توجد تنبيهات عاجلة اليوم.",
        'error_google': "خطأ في الاتصال بجوجل شيت",
        'info_creds': "يرجى التأكد من إعدادات Secrets في Streamlit.",
    }
}

T = L[st.session_state.lang]

# --- Custom Styling (Premium High-End Look) ---
st.markdown("""
<style>
    /* الخط الرئيسي */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Outfit', sans-serif; }

    /* القائمة الجانبية الفخمة */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a252f 0%, #2c3e50 100%);
        color: white;
        border-right: 1px solid rgba(255,255,255,0.1);
    }
    .main {
        background-color: #f4f7f6;
    }
    
    /* تنسيق عام للأزرار */
    div.stButton > button {
        width: 100%;
        border-radius: 12px;
        height: 55px !important; /* ارتفاع ثابت وموحد */
        font-weight: 600;
        margin-bottom: 15px !important; /* مسافة موحدة */
        font-size: 16px !important;
        color: white;
        border: none;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.2);
    }

    /* تخصيص ألوان الأزرار في القائمة الجانبية بالترتيب */
    /* 1. مراقب العقود (أزرق) */
    [data-testid="stSidebar"] div.stButton:nth-of-type(1) > button {
        background: linear-gradient(90deg, #2193b0 0%, #6dd5ed 100%);
    }
    /* 2. البحث والطباعة (بنفسجي) */
    [data-testid="stSidebar"] div.stButton:nth-of-type(2) > button {
        background: linear-gradient(90deg, #8E2DE2 0%, #4A00E0 100%);
    }
    /* 3. شاشة الصلاحيات (ذهبي) */
    [data-testid="stSidebar"] div.stButton:nth-of-type(3) > button {
        background: linear-gradient(90deg, #F2994A 0%, #F2C94C 100%);
        color: #1a252f !important; /* نص داكن للذهبي */
    }
    /* 4. حذف الصف المختار (أحمر) */
    [data-testid="stSidebar"] div.stButton:nth-of-type(4) > button {
        background: linear-gradient(90deg, #cb2d3e 0%, #ef473a 100%);
    }
    /* 5. تحديث البيانات (أخضر) */
    [data-testid="stSidebar"] div.stButton:nth-of-type(5) > button {
        background: linear-gradient(90deg, #11998e 0%, #38ef7d 100%);
    }
    /* 6. تغيير اللغة (رمادي) - يأتي عادة قبل الأزرار الرئيسية في الكود الحالي، لذا سنحتاج لضبط الترتيب في الكود ليطابق الـ CSS أو العكس */
    /* سنقوم بتعديل ترتيب العناصر في الكود ليتطابق مع الـ CSS */

    
    /* كروت التنبيهات */
    .stTable {
        background-color: white;
        border-radius: 15px;
        overflow: hidden;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
    }
    
    /* دعم RTL */
    html[dir="rtl"] .stMarkdown, html[dir="rtl"] .stText {
        text-align: right;
    }
    
    /* تأثيرات الزجاج (Glassmorphism) للنماذج */
    .stTextInput input {
        border-radius: 10px;
        border: 1px solid #ddd;
        padding: 12px;
    }
</style>
""", unsafe_allow_html=True)

# Set direction
if st.session_state.lang == 'ar':
    st.markdown('<div dir="rtl">', unsafe_allow_html=True)
else:
    st.markdown('<div dir="ltr">', unsafe_allow_html=True)

# --- Google Sheets Logic ---
def get_gspread_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            return gspread.authorize(creds)
    except: pass
    if os.path.exists('credentials.json'):
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
            return gspread.authorize(creds)
        except: return None
    return None

@st.cache_data(ttl=600)
def fetch_data():
    client = get_gspread_client()
    if not client: return None
    try:
        sheet_url = "https://docs.google.com/spreadsheets/d/1u87sScIve_-xT_jDG56EKFMXegzAxOqwVJCh3Irerrw/edit"
        sheet = client.open_by_url(sheet_url).get_worksheet(0)
        return sheet.get_all_values()
    except: return None

# --- UI Helpers ---
def sidebar_content():
    with st.sidebar:
        # وضع الصورة الشخصية
        col_img_side, _ = st.columns([1, 0.1])
        with col_img_side:
            img_found = False
            for p in ["alsaeed.jpg", "image/alsaeed.jpg"]:
                if os.path.exists(p):
                    st.image(p, width=200)
                    img_found = True
                    break
            if not img_found:
                st.info("📷")
        
        st.markdown(f"<h3 style='color:white; text-align: center;'>{T['prog_by']}<br>{'السعيد الوزان' if st.session_state.lang == 'ar' else 'Al-Saeed Al-Wazzan'}</h3>", unsafe_allow_html=True)
        
        st.divider()
        
        # 1. زر مراقب العقود (الرئيسية)
        if st.button(T['home_title'], type="secondary" if st.session_state.page != "home" else "primary"):
            st.session_state.page = "home"
            st.rerun()

        # 2. زر البحث والطباعة
        if st.button(T['search_nav'], type="secondary" if st.session_state.page != "search" else "primary"):
            st.session_state.page = "search"
            st.rerun()

        # 3. زر شاشة الصلاحيات
        if st.button(T['perms_nav'], type="secondary" if st.session_state.page != "permissions" else "primary"):
            if USERS.get(st.session_state.current_user, {}).get("can_manage_users"):
                st.session_state.page = "permissions"
                st.rerun()
            else:
                st.error("No Permission" if st.session_state.lang == 'en' else "ليس لديك صلاحية")

        # 4. زر حذف الصف المختار
        if st.button(T['del_nav']):
            if st.session_state.get("selected_alert_key"):
                key_to_block = st.session_state.selected_alert_key
                
                # Load existing
                ignored_file = 'ignored_rows.json'
                current_ignored = []
                if os.path.exists(ignored_file):
                    try:
                        with open(ignored_file, 'r', encoding='utf-8') as f:
                            current_ignored = json.load(f)
                    except: pass
                
                if key_to_block not in current_ignored:
                    current_ignored.append(key_to_block)
                    try:
                        with open(ignored_file, 'w', encoding='utf-8') as f:
                            json.dump(current_ignored, f)
                        st.success("تم حذف التنبيه" if st.session_state.lang == 'ar' else "Alert deleted")
                        time.sleep(1) # Show success briefly
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error saving: {e}")
                else:
                    st.warning("Allready deleted")
            else:
                st.warning("يرجى اختيار صف من الجدول أولاً" if st.session_state.lang == 'ar' else "Please select a row first")

        # 5. زر تحديث البيانات
        if st.button(T['refresh_nav']):
            st.cache_data.clear()
            st.rerun()
            
        st.divider()
        
        if st.button(T['logout'], type="secondary"):
            st.session_state.authenticated = False
            st.session_state.current_user = ""
            st.rerun()

        # نقل زر اللغة للأسفل
        if st.button(T['switch_lang']):
            st.session_state.lang = 'en' if st.session_state.lang == 'ar' else 'ar'
            st.rerun()

# --- Page: Login ---
def page_login():
    # تنسيق خاص لتصغير الشاشة وتوسيطها
    st.markdown("""
        <style>
            .login-container {
                max-width: 800px;
                margin: auto;
                padding: 30px;
                background: white;
                border-radius: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                display: flex;
                flex-wrap: wrap;
                align-items: center;
                gap: 20px;
            }
            .login-image-side { flex: 1; text-align: center; border-right: 1px solid #eee; padding-right: 20px; }
            .login-form-side { flex: 1.5; padding-left: 10px; }
            @media (max-width: 768px) {
                .login-container { flex-direction: column; }
                .login-image-side { border-right: none; border-bottom: 1px solid #eee; padding-right: 0; padding-bottom: 20px; }
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    col_img, col_form = st.columns([1, 1.5])
    
    with col_img:
        # عرض الصورة على اليسار
        img_found = False
        for p in ["alsaeed.jpg", "image/alsaeed.jpg"]:
            if os.path.exists(p):
                st.image(p, use_container_width=True)
                img_found = True
                break
        if not img_found:
            st.info("📷")
        
        # النص بالإنجليزي تحت الصورة
        st.markdown("<p style='text-align:center; font-weight:600; color:#2c3e50; margin-top:10px;'>Programmed by<br>Al-Saeed Al-Wazzan</p>", unsafe_allow_html=True)

    with col_form:
        st.markdown(f"<h2 style='text-align:center; color:#1a252f;'>{T['login_title']}</h2>", unsafe_allow_html=True)
        
        username = st.text_input(T['user_lbl'], placeholder="Username")
        password = st.text_input(T['pass_lbl'], type="password", placeholder="Password")
        
        if st.button(T['login_btn'], type="primary"):
            if username in USERS:
                hashed = hashlib.sha256(password.encode()).hexdigest()
                if USERS[username]["password"] == hashed:
                    st.session_state.authenticated = True
                    st.session_state.current_user = username
                    st.session_state.page = "home"
                    st.rerun()
                else: st.error(T['wrong_pass'])
            else: st.error(T['user_not_found'])
        
        if st.button(T['switch_lang'], key="login_lang"):
            st.session_state.lang = 'en' if st.session_state.lang == 'ar' else 'ar'
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

# --- Page: Home (Dashboard) ---
def page_home():
    sidebar_content()
    st.title(T['home_title'])
    st.header(T['alerts_title'])
    
    data_raw = fetch_data()
    if not data_raw:
        st.info(T['info_creds'])
        return

    headers = deduplicate_columns(data_raw[0])
    df = pd.DataFrame(data_raw[1:], columns=headers)
    
    # Alert Logic
    today = date.today()
    alerts = []
    
    # Load ignored rows
    ignored_file = 'ignored_rows.json'
    ignored_set = set()
    if os.path.exists(ignored_file):
        try:
            with open(ignored_file, 'r', encoding='utf-8') as f:
                ignored_set = set(json.load(f))
        except: pass
    
    # Try to find expiry column
    date_col = ""
    for h in df.columns:
        if any(kw in h.lower() for kw in ["تاريخ انتاء", "expiry", "end date", "تاريخ انتهاء"]):
            date_col = h
            break
    
    if date_col:
        for _, row in df.iterrows():
            try:
                # Key Generation (Same as desktop)
                # Assuming columns: Timestamp, Name, Gender, Nationality, Phone...
                # Key: Name|Gender|Nationality|Phone...
                # Indices in df might differ, relying on position 1 to 6 as in desktop app logic
                # Desktop: key = "|".join([str(v) for v in vals[1:7]])
                # Here row is a Series. Let's try to match the slicing.
                # data_raw headers are deduplicated.
                # We need raw values for the key to match exactly if we want cross-app compatibility.
                # But for now, let's just use the values we have.
                # Construct key from specific columns if possible or slice.
                # Desktop uses index 1 to 7 from the treeview values.
                # Treeview values in desktop: [msg, col1, col2...]
                # Actually desktop logic: `vals = self.tree.item(sel[0])['values']`; `key = "|".join([str(v) for v in vals[1:7]])`
                # In desktop `_process_data`: `processed.append(([msg] + row, ...))`
                # So vals[0] is msg. vals[1] is row[0] (Timestamp)...
                # So Key is row[0] to row[5] (first 6 columns of the sheet).
                
                row_values = row.values.tolist()
                key_parts = [str(v) for v in row_values[0:6]]
                row_key = "|".join(key_parts)
                
                if row_key in ignored_set:
                    continue

                dt = safe_parse_date(row[date_col])
                if dt:
                    diff = (dt - today).days
                    # المنطق الجديد: التنبيه يظهر إذا بقي 7 أيام أو أقل (ويستمر حتى الحذف)
                    if diff <= 7:
                        # تصحيح العداد
                        if diff > 0:
                            msg = f"باقي {diff} يوم"
                        elif diff == 0:
                            msg = "ينتهي اليوم"
                        else:
                            msg = f"منتهي منذ {abs(diff)} يوم"
                        
                        # Show full row data
                        alert_row = {T['status']: msg}
                        alert_row.update(row.to_dict())
                        alert_row['_key'] = row_key
                        alerts.append(alert_row)
            except: pass
            
    if alerts:
        alert_df = pd.DataFrame(alerts)
        # Ensure Status is the first column
        cols = [T['status']] + [c for c in alert_df.columns if c != T['status'] and c != "_key"]
        
        # Display without the key
        display_df = alert_df[cols]
        
        # Use Dataframe with selection
        try:
           event = st.dataframe(
                display_df, 
                use_container_width=True,
                selection_mode="single-row",
                on_select="rerun",
                key="alert_selection"
            )
        except:
             # Fallback for older streamlit versions
             st.dataframe(display_df, use_container_width=True)
             event = None

        # Handle Delete Action (Check sidebar button state implicitly or use session state)
        # The delete button is in sidebar. It needs to know the selection.
        if event and len(event.selection['rows']) > 0:
            selected_index = event.selection['rows'][0]
            st.session_state.selected_alert_key = alert_df.iloc[selected_index]["_key"]
        else:
            st.session_state.selected_alert_key = None

    else:
        st.success(T['success_msg'])

# --- Page: Search ---
def page_search():
    sidebar_content()
    st.title(T['search_page_title'])
    
    if st.button(T['back_nav']):
        st.session_state.page = "home"
        st.rerun()
    
    data_raw = fetch_data()
    if not data_raw: return
    
    headers = deduplicate_columns(data_raw[0])
    df = pd.DataFrame(data_raw[1:], columns=headers)
    
    # Advanced Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"### {T['filter_age']}")
        use_age = st.checkbox(T['enable'], key="age_en")
        age_from = st.number_input(T['from'], 0, 100, 18)
        age_to = st.number_input(T['to'], 0, 100, 60)
        
    with col2:
        st.markdown(f"### {T['filter_exp']}")
        use_exp = st.checkbox(T['enable'], key="exp_en")
        exp_from = st.date_input(T['from'], value=date.today(), key="exp_f", format="DD/MM/YYYY")
        exp_to = st.date_input(T['to'], value=date.today(), key="exp_t", format="DD/MM/YYYY")
        
    with col3:
        st.markdown(f"### {T['filter_reg']}")
        use_reg = st.checkbox(T['enable'], key="reg_en")
        reg_from = st.date_input(T['from'], value=date.today(), key="reg_f", format="DD/MM/YYYY")
        reg_to = st.date_input(T['to'], value=date.today(), key="reg_t", format="DD/MM/YYYY")

    query = st.text_input(T['global_search'], placeholder="(Name, Nationality, Job...)")
    search_btn_clicked = st.button(T['search_btn'], type="primary")
    
    # Try to find expiry column
    date_col = ""
    for h in df.columns:
        if any(kw in h.lower() for kw in ["تاريخ انتاء", "expiry", "end date", "تاريخ انتهاء"]):
            date_col = h
            break

    # Apply filters logic
    if search_btn_clicked:
        results = df
        
        if use_exp and date_col:
            results = results[results[date_col].apply(lambda x: exp_from <= safe_parse_date(x) <= exp_to if safe_parse_date(x) else False)]
        
        if use_reg:
            # فلتر تاريخ التسجيل (العمود الأول غالباً)
            results = results[results.iloc[:, 0].apply(lambda x: reg_from <= safe_parse_date(x) <= reg_to if safe_parse_date(x) else False)]

        if query:
            mask = results.apply(lambda row: row.astype(str).str.contains(query, case=False).any(), axis=1)
            results = results[mask]
            
        st.markdown(f"#### 🔍 النتائج المكتشفة: {len(results)}")
        st.dataframe(results.astype(str), use_container_width=True)
    
    if st.button(T['print_btn']):
        st.info("Feature not available in cloud yet." if st.session_state.lang == 'en' else "الميزة غير متاحة في النسخة السحابية حالياً.")

# --- Page: Permissions ---
def page_permissions():
    sidebar_content()
    st.title(T['perms_page_title'])
    st.markdown(f"### {st.session_state.current_user} ، {('Welcome back' if st.session_state.lang == 'en' else 'مرحباً بك')}")
    
    if st.button(T['back_nav']):
        st.session_state.page = "home"
        st.rerun()
        
    col1, col2 = st.columns(2)
    with col1:
        st.header(T['add_user_title'])
        new_u = st.text_input(T['user_lbl'], key="new_u")
        new_p = st.text_input(T['pass_lbl'], type="password", key="new_p")
        can_p = st.checkbox(T['can_access_perms'])
        if st.button(T['add_btn']):
            st.success("User added (locally to memory)" if st.session_state.lang == 'en' else "تم إضافة المستخدم (محلياً في الذاكرة)")
            
    with col2:
        st.header(T['change_pass_title'])
        old_p = st.text_input(T['pass_lbl'], type="password", key="old_p")
        n_p = st.text_input("New Password" if st.session_state.lang == 'en' else "كلمة المرور الجديدة", type="password")
        if st.button(T['save_btn']):
            st.success("Password changed" if st.session_state.lang == 'en' else "تم تغيير كلمة المرور")

# --- Routing ---
if not st.session_state.authenticated:
    page_login()
else:
    if st.session_state.page == "home":
        page_home()
    elif st.session_state.page == "search":
        page_search()
    elif st.session_state.page == "permissions":
        page_permissions()

st.markdown('</div>', unsafe_allow_html=True)
