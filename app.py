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
    return {"admin": {"password": "c685e710931707e3e9aaab6c8625a9798cd06a31bcf40cd8d6963e3703400d14", "role": "admin", "can_manage_users": True}}

USERS = load_users()

if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'current_user' not in st.session_state: st.session_state.current_user = ""
if 'page' not in st.session_state: st.session_state.page = "home"
if 'lang' not in st.session_state: st.session_state.lang = 'ar'

# --- الترجمة ---
L = {
    'en': {
        'login_title': "🔒 Login", 'user_lbl': "Username", 'pass_lbl': "Password", 'login_btn': "Login",
        'wrong_pass': "❌ Wrong password", 'user_not_found': "❌ User not found", 'prog_by': "Programmed by",
        'switch_lang': "Switch to Arabic", 'logout': "Logout", 'home_title': "🛡️ Dashboard",
        'alerts_title': "⚠️ Upcoming Contract Expiries", 'search_nav': "🔍 Search & Printing",
        'del_nav': "🗑️ Delete Selected Row", 'refresh_nav': "🔄 Refresh Data", 'perms_nav': "🔑 Permissions Screen",
        'back_nav': "🏠 Return to Main Screen", 'search_page_title': "🔍 Advanced Search System",
        'perms_page_title': "⚙️ Rights & Settings System", 'add_user_title': "Add New User", 'change_pass_title': "Change Your Password",
        'save_btn': "Save Changes", 'add_btn': "Add User", 'status': "Alert Status", 'date_col': "Expiry Date", 
        'name_col': "Full Name", 'search_btn': "Search Now", 'print_btn': "Print Report", 'global_search': "Global Search",
        'filter_reg': "Registration Date", 'filter_exp': "Contract Expiry", 'filter_age': "Age", 'enable': "Enable",
        'from': "From", 'to': "To", 'days_left': "days left", 'week_left': "1 week left", 'info_creds': "⚠️ Connection Error",
        'search_placeholder': "Search for names, jobs, etc...", 'search_criteria': "Search Criteria", 'welcome': "Welcome"
    },
    'ar': {
        'login_title': "🔒 تسجيل الدخول", 'user_lbl': "اسم المستخدم", 'pass_lbl': "كلمة المرور", 'login_btn': "دخول",
        'wrong_pass': "❌ كلمة المرور خاطئة", 'user_not_found': "❌ المستخدم غير موجود", 'prog_by': "برمجة",
        'switch_lang': "Switch to English", 'logout': "خروج من البرنامج", 'home_title': "🛡️ مراقب العقود",
        'alerts_title': "تنبيهات العقود الوشيكة (أسبوع / يومين)", 'search_nav': "🔍 البحث والطباعة",
        'del_nav': "🗑️ حذف الصف المختار", 'refresh_nav': "🔄 تحديث البيانات", 'perms_nav': "🔑 شاشة الصلاحيات",
        'back_nav': "🏠 الرجوع للشاشة الرئيسية", 'search_page_title': "نظام البحث المتقدم",
        'perms_page_title': "نظام الصلاحيات والإعدادات", 'add_user_title': "إضافة مستخدم جديد", 'change_pass_title': "تغيير كلمة مرورك",
        'save_btn': "حفظ التغييرات", 'add_btn': "إضافة مستخدم", 'status': "حالة التنبيه", 'date_col': "تاريخ انتهاء العقد", 
        'name_col': "الاسم الكامل", 'search_btn': "بحث الآن", 'print_btn': "طباعة التقرير", 'global_search': "البحث الشامل",
        'filter_reg': "تاريخ التسجيل", 'filter_exp': "انتهاء العقد", 'filter_age': "السن", 'enable': "تفعيل",
        'from': "من", 'to': "إلى", 'days_left': "باقي يوم", 'week_left': "باقي أسبوع", 'info_creds': "⚠️ خطأ في الاتصال",
        'search_placeholder': "ابحث عن أسماء، وظائف، أو أي بيانات...", 'search_criteria': "معايير البحث", 'welcome': "مرحباً بك"
    }
}
T = L[st.session_state.lang]

# --- جلب البيانات ---
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

# --- العناصر المشتركة ---
def sidebar_common():
    with st.sidebar:
        st.markdown(f"### {T['prog_by']}: {'السعيد الوزان' if st.session_state.lang == 'ar' else 'Al-Saeed Al-Wazzan'}")
        if st.button(T['switch_lang']): st.session_state.lang = 'en' if st.session_state.lang == 'ar' else 'ar'; st.rerun()
        st.divider()
        if st.button(T['search_nav'], type="secondary" if st.session_state.page != "search" else "primary"): st.session_state.page = "search"; st.rerun()
        if st.button(T['refresh_nav']): st.cache_data.clear(); st.rerun()
        if st.button(T['perms_nav'], type="secondary" if st.session_state.page != "permissions" else "primary"): st.session_state.page = "permissions"; st.rerun()
        st.divider()
        if st.button(T['logout']): st.session_state.authenticated = False; st.rerun()

# --- الصفحات ---
def page_home():
    sidebar_common()
    st.title(T['home_title'])
    st.header(T['alerts_title'])
    data = fetch_data()
    if not data: st.error(T['info_creds']); return
    df = pd.DataFrame(data[1:], columns=data[0])
    today = date.today(); alerts = []
    date_col = next((h for h in df.columns if any(kw in h.lower() for kw in ["تاريخ انتاء", "expiry", "end date", "تاريخ انتهاء"])), "")
    if date_col:
        for _, row in df.iterrows():
            try:
                dt = parser.parse(str(row[date_col])).date(); diff = (dt - today).days
                if diff in [0, 1, 2, 7, 14]:
                    alerts.append({T['status']: f"{diff} {T['days_left']}", T['date_col']: row[date_col], T['name_col']: row[1]})
            except: pass
    if alerts: st.table(pd.DataFrame(alerts))
    else: st.success("لا توجد تنبيهات عاجلة")

def page_search():
    sidebar_common()
    st.title(T['search_page_title'])
    if st.button(T['back_nav']): st.session_state.page = "home"; st.rerun()
    st.markdown(f"### {T['search_criteria']}")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**{T['filter_age']}**")
        st.checkbox(T['enable'], key="age_en")
        st.number_input(T['from'], 0, 100, 18, key="af"); st.number_input(T['to'], 0, 100, 60, key="at")
    with col2:
        st.markdown(f"**{T['filter_exp']}**")
        st.checkbox(T['enable'], key="exp_en")
        st.date_input(T['from'], key="exp_f"); st.date_input(T['to'], key="exp_t")
    with col3:
        st.markdown(f"**{T['filter_reg']}**")
        st.checkbox(T['enable'], key="reg_en")
        st.date_input(T['from'], key="reg_f"); st.date_input(T['to'], key="reg_t")

    query = st.text_input(T['global_search'], placeholder=T['search_placeholder'])
    
    data = fetch_data()
    if data:
        df = pd.DataFrame(data[1:], columns=data[0])
        if query:
            results = df[df.apply(lambda row: row.astype(str).str.contains(query, case=False).any(), axis=1)]
            # التعديل المهم هنا: تحويل البيانات لنصوص لضمان عدم حدوث خطأ
            st.dataframe(results.astype(str), use_container_width=True)
    
    if st.button(T['print_btn']): st.info("Printing not available.")

def page_permissions():
    sidebar_common(); st.title(T['perms_page_title'])
    if st.button(T['back_nav']): st.session_state.page = "home"; st.rerun()
    st.write(T['add_user_title'])
    st.text_input(T['user_lbl'], key="nu"); st.text_input(T['pass_lbl'], type="password", key="np")
    st.button(T['add_btn'])

# --- التوجيه ---
if not st.session_state.authenticated:
    sidebar_common() # لإظهار اللغة فقط في شاشة الدخول
    # صفحة الدخول البسيطة
    st.markdown(f"## {T['login_title']}")
    u = st.text_input(T['user_lbl']); p = st.text_input(T['pass_lbl'], type="password")
    if st.button(T['login_btn'], type="primary"):
        st.session_state.authenticated = True; st.rerun()
else:
    if st.session_state.page == "home": page_home()
    elif st.session_state.page == "search": page_search()
    elif st.session_state.page == "permissions": page_permissions()

st.markdown('</div>', unsafe_allow_html=True)
