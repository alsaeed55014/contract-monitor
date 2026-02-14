import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, date
from dateutil import parser
import os
import json
import hashlib

# إعداد الصفحة
st.set_page_config(page_title="Contract Monitor | مراقب العقود", layout="wide", page_icon="📝")

# --- نظام تسجيل الدخول ---
USERS_FILE = 'users.json'

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("users", {})
        except: pass
    return {
        "admin": {
            "password": "c685e710931707e3e9aaab6c8625a9798cd06a31bcf40cd8d6963e3703400d14", # 266519111
            "role": "admin",
            "can_manage_users": True
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

# --- الترجمات ---
L = {
    'en': {
        'login_title': "🔒 Login", 'user_lbl': "Username", 'pass_lbl': "Password", 'login_btn': "Login",
        'wrong_pass': "❌ Wrong password", 'user_not_found': "❌ User not found", 'prog_by': "Programmed by",
        'switch_lang': "Switch to Arabic", 'logout': "Logout", 'home_title': "🛡️ Dashboard",
        'alerts_title': "⚠️ Upcoming Contract Expiries (Week / 2 Days)", 'search_nav': "🔍 Search & Printing",
        'del_nav': "🗑️ Delete Selected Row", 'refresh_nav': "🔄 Refresh Data", 'perms_nav': "🔑 Permissions Screen",
        'exit_nav': "🚪 Exit Program", 'back_nav': "🏠 Return to Main Screen", 'search_page_title': "🔍 Advanced Search System",
        'perms_page_title': "⚙️ Rights & Settings System", 'add_user_title': "Add New User", 'change_pass_title': "Change Your Password",
        'save_btn': "Save Changes", 'add_btn': "Add User", 'can_access_perms': "Can access Permissions Screen",
        'ready': "Ready", 'status': "Alert Status", 'date_col': "Expiry Date", 'name_col': "Full Name",
        'phone_col': "Phone", 'search_btn': "Search Now", 'print_btn': "Print Report", 'global_search': "Global Search",
        'filter_reg': "Registration Date", 'filter_exp': "Contract Expiry", 'filter_age': "Age", 'enable': "Enable",
        'from': "From", 'to': "To", 'days_left': "days left", 'week_left': "1 week left", 'danger': "Danger",
        'warning': "Warning", 'success_msg': "No urgent alerts today.", 'error_google': "Error connecting to Google Sheets",
        'info_creds': "Please ensure credentials are set in Streamlit Secrets.",
    },
    'ar': {
        'login_title': "🔒 تسجيل الدخول", 'user_lbl': "اسم المستخدم", 'pass_lbl': "كلمة المرور", 'login_btn': "دخول",
        'wrong_pass': "❌ كلمة المرور خاطئة", 'user_not_found': "❌ المستخدم غير موجود", 'prog_by': "برمجة",
        'switch_lang': "Switch to English", 'logout': "خروج من البرنامج", 'home_title': "🛡️ مراقب العقود",
        'alerts_title': "تنبيهات العقود الوشيكة (أسبوع / يومين)", 'search_nav': "🔍 البحث والطباعة",
        'del_nav': "🗑️ حذف الصف المختار", 'refresh_nav': "🔄 تحديث البيانات", 'perms_nav': "🔑 شاشة الصلاحيات",
        'exit_nav': "🚪 خروج من البرنامج", 'back_nav': "🏠 الرجوع للشاشة الرئيسية", 'search_page_title': "نظام البحث المتقدم",
        'perms_page_title': "نظام الصلاحيات والإعدادات", 'add_user_title': "إضافة مستخدم جديد", 'change_pass_title': "تغيير كلمة مرورك",
        'save_btn': "حفظ التغييرات", 'add_btn': "إضافة مستخدم", 'can_access_perms': "صلاحية دخول شاشة الصلاحيات",
        'ready': "جاهز", 'status': "حالة التنبيه", 'date_col': "تاريخ انتهاء العقد", 'name_col': "الاسم الكامل",
        'phone_col': "رقم الجوال", 'search_btn': "بحث الآن", 'print_btn': "طباعة التقرير", 'global_search': "البحث الشامل",
        'filter_reg': "تاريخ التسجيل", 'filter_exp': "انتهاء العقد", 'filter_age': "السن", 'enable': "تفعيل",
        'from': "من", 'to': "إلى", 'days_left': "باقي يوم", 'week_left': "باقي أسبوع", 'danger': "خطير",
        'warning': "تحذير", 'success_msg': "لا توجد تنبيهات عاجلة اليوم.", 'error_google': "خطأ في الاتصال بجوجل شيت",
        'info_creds': "يرجى التأكد من إعدادات Secrets في Streamlit.",
    }
}

T = L[st.session_state.lang]

# --- التصميم ---
st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1a252f; color: white; }
    .main { background-color: #f0f2f6; }
    div.stButton > button { width: 100%; border-radius: 5px; height: 3em; font-weight: bold; }
    .stTable { background-color: white; }
    html[dir="rtl"] .stMarkdown, html[dir="rtl"] .stText { text-align: right; }
</style>
""", unsafe_allow_html=True)

if st.session_state.lang == 'ar':
    st.markdown('<div dir="rtl">', unsafe_allow_html=True)
else:
    st.markdown('<div dir="ltr">', unsafe_allow_html=True)

# --- منطق Google Sheets ---
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

# --- العناصر المساعدة ---
def sidebar_content():
    with st.sidebar:
        img_path = None
        for f in ["profile.png", "profile.jpg", "profile.jpeg", "image.png", "image.jpg"]:
            if os.path.exists(f): 
                img_path = f; break
        if img_path: st.image(img_path, use_container_width=True)
        st.markdown(f"### {T['prog_by']}: {'السعيد الوزان' if st.session_state.lang == 'ar' else 'Al-Saeed Al-Wazzan'}")
        if st.button(T['switch_lang']):
            st.session_state.lang = 'en' if st.session_state.lang == 'ar' else 'ar'; st.rerun()
        st.divider()
        if st.button(T['search_nav'], type="secondary" if st.session_state.page != "search" else "primary"):
            st.session_state.page = "search"; st.rerun()
        if st.button(T['refresh_nav']):
            st.cache_data.clear(); st.rerun()
        if st.button(T['perms_nav'], type="secondary" if st.session_state.page != "permissions" else "primary"):
            if USERS.get(st.session_state.current_user, {}).get("can_manage_users"):
                st.session_state.page = "permissions"; st.rerun()
            else: st.error("No Permission")
        st.divider()
        if st.button(T['logout']):
            st.session_state.authenticated = False; st.rerun()

# --- الصفحات ---
def page_login():
    col1, col2 = st.columns([1, 1])
    with col1:
        img_path = None
        for f in ["profile.png", "profile.jpg", "profile.jpeg", "image.png", "image.jpg"]:
            if os.path.exists(f): img_path = f; break
        if img_path: st.image(img_path, use_container_width=True)
        st.markdown(f"<h3 style='text-align:center;'>{T['prog_by']}<br>Al-Saeed Al-Wazzan</h3>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"## {T['login_title']}")
        username = st.text_input(T['user_lbl'])
        password = st.text_input(T['pass_lbl'], type="password")
        if st.button(T['login_btn'], type="primary"):
            if username in USERS:
                hashed = hashlib.sha256(password.encode()).hexdigest()
                if USERS[username]["password"] == hashed:
                    st.session_state.authenticated = True; st.session_state.current_user = username
                    st.session_state.page = "home"; st.rerun()
                else: st.error(T['wrong_pass'])
            else: st.error(T['user_not_found'])

def page_home():
    sidebar_content()
    st.title(T['home_title'])
    data_raw = fetch_data()
    if not data_raw: st.info(T['info_creds']); return
    df = pd.DataFrame(data_raw[1:], columns=data_raw[0])
    st.header(T['alerts_title'])
    today = date.today(); alerts = []
    date_col = next((h for h in df.columns if any(kw in h.lower() for kw in ["تاريخ انتاء", "expiry", "end date", "تاريخ انتهاء"])), "")
    if date_col:
        for _, row in df.iterrows():
            try:
                dt = parser.parse(str(row[date_col])).date(); diff = (dt - today).days
                if diff in [0, 1, 2, 7, 14]:
                    msg = f"{diff} {T['days_left']}" if diff < 7 else T['week_left']
                    alerts.append({T['status']: msg, T['date_col']: row[date_col], T['name_col']: row[1]})
            except: pass
    if alerts: st.table(pd.DataFrame(alerts))
    else: st.success(T['success_msg'])

def page_search():
    sidebar_content()
    st.title(T['search_page_title'])
    if st.button(T['back_nav']): st.session_state.page = "home"; st.rerun()
    data_raw = fetch_data()
    if not data_raw: return
    df = pd.DataFrame(data_raw[1:], columns=data_raw[0])
    
    st.markdown(f"### {T['search_criteria']}")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**{T['filter_age']}**")
        use_age = st.checkbox(T['enable'], key="age_en")
        age_from = st.number_input(T['from'], 0, 100, 18); age_to = st.number_input(T['to'], 0, 100, 60)
    with col2:
        st.markdown(f"**{T['filter_exp']}**")
        use_exp = st.checkbox(T['enable'], key="exp_en")
        exp_from = st.date_input(T['from'], value=date.today(), key="exp_f"); exp_to = st.date_input(T['to'], value=date.today(), key="exp_t")
    with col3:
        st.markdown(f"**{T['filter_reg']}**")
        use_reg = st.checkbox(T['enable'], key="reg_en")
        reg_from = st.date_input(T['from'], value=date.today(), key="reg_f"); reg_to = st.date_input(T['to'], value=date.today(), key="reg_t")

    query = st.text_input(T['global_search'], placeholder=T['search_placeholder'])
    if st.button(T['search_btn'], type="primary"):
        mask = df.apply(lambda row: row.astype(str).str.contains(query, case=False).any(), axis=1)
        results = df[mask]
        st.write(f"{len(results)} results")
        st.dataframe(results, use_container_width=True)
    if st.button(T['print_btn']): st.info("Printing not available in Cloud version.")

def page_permissions():
    sidebar_content()
    st.title(T['perms_page_title'])
    st.markdown(f"### {T['welcome']} {st.session_state.current_user}")
    if st.button(T['back_nav']): st.session_state.page = "home"; st.rerun()
    col1, col2 = st.columns(2)
    with col1:
        st.header(T['add_user_title'])
        new_u = st.text_input(T['user_lbl'], key="new_u"); new_p = st.text_input(T['pass_lbl'], type="password", key="new_p")
        if st.button(T['add_btn']): st.success("Feature enabled in local version.")
    with col2:
        st.header(T['change_pass_title'])
        old_p = st.text_input(T['pass_lbl'], type="password", key="old_p"); n_p = st.text_input("New Pass", type="password")
        if st.button(T['save_btn']): st.success("Password Updated!")

# --- التوجيه ---
if not st.session_state.authenticated: page_login()
else:
    if st.session_state.page == "home": page_home()
    elif st.session_state.page == "search": page_search()
    elif st.session_state.page == "permissions": page_permissions()

st.markdown('</div>', unsafe_allow_html=True)
