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

# --- وظيفة معالجة التواريخ (ص، م، وقت) ---
def safe_parse_date(d_str):
    if not d_str: return None
    try:
        # تنظيف النص من الرموز العربية ص و م
        clean_d = str(d_str).replace('ص', 'AM').replace('م', 'PM').strip()
        # محاولة التحويل الذكي
        parsed_dt = parser.parse(clean_d)
        return parsed_dt.date()
    except:
        return None

# --- وظيفة لمنع تكرار أسماء الأعمدة ---
def deduplicate_columns(columns):
    new_columns = []
    counts = {}
    for col in columns:
        c_str = str(col).strip() if col else "Column"
        if not c_str: c_str = "Column"
        if c_str in counts:
            counts[c_str] += 1
            new_columns.append(f"{c_str}_{counts[c_str]}")
        else:
            counts[c_str] = 0
            new_columns.append(c_str)
    return new_columns

# --- نظام تسجيل الدخول ---
USERS_FILE = 'users.json'
def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f); return data.get("users", {})
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
        'search_placeholder': "Search for names...", 'search_criteria': "Search Criteria", 'welcome': "Welcome"
    },
    'ar': {
        'login_title': "🔒 تسجيل الدخول", 'user_lbl': "اسم المستخدم", 'pass_lbl': "كلمة المرور", 'login_btn': "دخول",
        'wrong_pass': "❌ كلمة المرور خاطئة", 'user_not_found': "❌ المستخدم غير موجود", 'prog_by': "برمجة",
        'switch_lang': "Switch to English", 'logout': "خروج", 'home_title': "🛡️ مراقب العقود",
        'alerts_title': "تنبيهات العقود الوشيكة (أسبوع / يومين)", 'search_nav': "🔍 البحث والطباعة",
        'del_nav': "🗑️ حذف الصف المختار", 'refresh_nav': "🔄 تحديث البيانات", 'perms_nav': "🔑 شاشة الصلاحيات",
        'back_nav': "🏠 الشاشة الرئيسية", 'search_page_title': "نظام البحث المتقدم",
        'perms_page_title': "نظام الصلاحيات والإعدادات", 'add_user_title': "إضافة مستخدم جديد", 'change_pass_title': "تغيير كلمة مرورك",
        'save_btn': "حفظ التغييرات", 'add_btn': "إضافة مستخدم", 'status': "حالة التنبيه", 'date_col': "تاريخ انتهاء العقد", 
        'name_col': "الاسم الكامل", 'search_btn': "بحث الآن", 'print_btn': "طباعة التقرير", 'global_search': "البحث الشامل",
        'filter_reg': "تاريخ التسجيل", 'filter_exp': "انتهاء العقد", 'filter_age': "السن", 'enable': "تفعيل",
        'from': "من", 'to': "إلى", 'days_left': "باقي يوم", 'week_left': "باقي أسبوع", 'info_creds': "⚠️ خطأ اتصال",
        'search_placeholder': "ابحث عن أسماء...", 'search_criteria': "معايير البحث", 'welcome': "مرحباً بك"
    }
}
T = L[st.session_state.lang]

# --- التصميم وإصلاح لون النص ---
st.markdown(f"""
<style>
    [data-testid="stSidebar"] {{ background-color: #1a252f; color: white; }}
    /* إخفاء القائمة في صفحة الدخول */
    {'' if st.session_state.authenticated else 'section[data-testid="stSidebar"] {display: none;}'}
    
    /* إصلاح ألوان الجداول والجوال ليكون النص واضحاً */
    .stTable, .stDataFrame {{ color: black !important; background-color: white !important; }}
    th {{ background-color: #2c3e50 !important; color: white !important; }}
    td {{ color: black !important; }}
    
    .danger-row {{ background-color: #ffcccc !important; color: #900 !important; font-weight: bold; }}
    .warning-row {{ background-color: #fff4cc !important; color: #856404 !important; font-weight: bold; }}
</style>
""", unsafe_allow_html=True)

if st.session_state.lang == 'ar': st.markdown('<div dir="rtl">', unsafe_allow_html=True)
else: st.markdown('<div dir="ltr">', unsafe_allow_html=True)

# --- جلب البيانات ---
@st.cache_data(ttl=600)
def fetch_data():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            sheet_url = "https://docs.google.com/spreadsheets/d/1u87sScIve_-xT_jDG56EKFMXegzAxOqwVJCh3Irerrw/edit"
            return client.open_by_url(sheet_url).get_worksheet(0).get_all_values()
    except: pass
    return None

# --- القائمة الجانبية ---
def sidebar_common():
    with st.sidebar:
        st.markdown(f"### {T['prog_by']}: {'السعيد الوزان' if st.session_state.lang == 'ar' else 'Al-Saeed Al-Wazzan'}")
        if st.button(T['switch_lang']): st.session_state.lang = 'en' if st.session_state.lang == 'ar' else 'ar'; st.rerun()
        st.divider()
        if st.button(T['home_title'], type="primary" if st.session_state.page == "home" else "secondary"): st.session_state.page = "home"; st.rerun()
        if st.button(T['search_nav'], type="primary" if st.session_state.page == "search" else "secondary"): st.session_state.page = "search"; st.rerun()
        if st.button(T['refresh_nav']): st.cache_data.clear(); st.rerun()
        if st.button(T['perms_nav']): st.session_state.page = "permissions"; st.rerun()
        st.divider()
        if st.button(T['logout']): st.session_state.authenticated = False; st.rerun()

# --- الصفحات ---
def page_home():
    sidebar_common(); st.title(T['home_title']); st.header(T['alerts_title'])
    data = fetch_data()
    if not data: st.error(T['info_creds']); return
    headers = deduplicate_columns(data[0])
    df = pd.DataFrame(data[1:], columns=headers)
    today = date.today(); alerts = []
    # البحث عن عمود التاريخ
    date_col = next((h for h in df.columns if any(kw in h.lower() for kw in ["تاريخ انتاء", "expiry", "تاريخ انتهاء"])), "")
    if date_col:
        for _, row in df.iterrows():
            dt = safe_parse_date(row[date_col])
            if dt:
                diff = (dt - today).days
                if 0 <= diff <= 14: # تصفية دقيقة للتنبيهات
                    msg = f"باقي {diff} يوم" if diff < 7 else "باقي أسبوع"
                    alerts.append({T['status']: msg, T['date_col']: row[date_col], T['name_col']: row[1] if len(row)>1 else ""})
    
    if alerts:
        # عرض التنبيهات مع تلوين حسب الخطورة
        st.table(pd.DataFrame(alerts))
    else: st.success("🎉 لا توجد تنبيهات عاجلة اليوم")

def page_search():
    sidebar_common(); st.title(T['search_page_title'])
    data = fetch_data()
    if not data: st.error(T['info_creds']); return
    headers = deduplicate_columns(data[0])
    df = pd.DataFrame(data[1:], columns=headers)
    
    col1, col2, col3 = st.columns(3)
    with col1: u_exp = st.checkbox(T['filter_exp'], key="ue"); exp_f = st.date_input("من", key="ef"); exp_t = st.date_input("إلى", key="et")
    query = st.text_input(T['global_search'], placeholder=T['search_placeholder'])
    
    results = df
    if u_exp:
        date_col = next((h for h in df.columns if any(kw in h.lower() for kw in ["تاريخ انتاء", "expiry", "تاريخ انتهاء"])), "")
        if date_col:
            results = results[results[date_col].apply(lambda x: exp_f <= safe_parse_date(x) <= exp_t if safe_parse_date(x) else False)]
    if query:
        results = results[results.apply(lambda r: r.astype(str).str.contains(query, case=False).any(), axis=1)]
    
    st.write(f"النتائج: {len(results)}")
    st.dataframe(results.astype(str), use_container_width=True)

# --- التوجيه ---
if not st.session_state.authenticated:
    st.markdown(f"<h2 style='text-align:center;'>{T['login_title']}</h2>", unsafe_allow_html=True)
    u = st.text_input(T['user_lbl']); p = st.text_input(T['pass_lbl'], type="password")
    if st.button(T['login_btn'], type="primary"): st.session_state.authenticated = True; st.rerun()
else:
    if st.session_state.page == "home": page_home()
    elif st.session_state.page == "search": page_search()
    elif st.session_state.page == "permissions": st.title(T['perms_page_title'])

st.markdown('</div>', unsafe_allow_html=True)
