import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, date
from dateutil import parser
import os
import json
import hashlib

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

# --- وظيفة معالجة التواريخ لتقابل صيغة الإكسل العربي ---
def safe_parse_date(d_str):
    if not d_str: return None
    try:
        # التعامل مع رموز ص وم وتصحيحها لـ AM/PM
        d_clean = str(d_str).strip().replace('ص', 'AM').replace('م', 'PM')
        # محاولة ذكية للتحويل (مع إعطاء الأولوية لليوم قبل الشهر كما في الإكسل العربي)
        return parser.parse(d_clean, dayfirst=True, fuzzy=True).date()
    except:
        return None

# --- محرك الترجمة للبحث الثنائي (Bilingual) ---
class TranslationManager:
    def __init__(self):
        # القاموس الكامل من البرنامج المكتبي لضمان دقة البحث
        self.mapping = {
            "باريستا": "barista", "طباخ": "cook", "شيف": "chef", "نادل": "waiter", "نادلة": "waitress",
            "ممرض": "nurse", "ممرضة": "nurse", "طبيب": "doctor", "عامل": "worker", "عاملة": "laborer",
            "سائق": "driver", "مندوب": "representative", "محاسب": "accountant", "مدير": "manager",
            "مبرمج": "programmer", "كاشير": "cashier", "حارس": "guard", "ذكر": "male", "أنثى": "female",
            "هندي": "indian", "فلبيني": "filipino", "مصري": "egyptian", "باكستاني": "pakistani",
            "الرياض": "riyadh", "جده": "jeddah", "مكه": "makkah", "الدمام": "dammam", "نعم": "yes", "لا": "no",
            "حلاق": "barber", "خياط": "tailor", "كهربائي": "electrician", "سباك": "plumber", "نجار": "carpenter",
            "مهندس": "engineer", "فني": "technician", "ميكانيكي": "mechanic", "بائع": "sales", "موظف": "employee"
        }
    def translate(self, text):
        text = text.strip().lower()
        if not text: return None
        norm = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه")
        if text in self.mapping: return self.mapping[text]
        if norm in self.mapping: return self.mapping[norm]
        for k, v in self.mapping.items():
            if k in norm or k in text: return v
        return None

translator = TranslationManager()

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
        }
    }

def save_users(users_dict):
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump({"users": users_dict}, f, indent=4)
        return True
    except Exception as e:
        st.error(f"Error saving users: {e}")
        return False

USERS = load_users()

if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'current_user' not in st.session_state: st.session_state.current_user = ""
if 'page' not in st.session_state: st.session_state.page = "home"
if 'lang' not in st.session_state: st.session_state.lang = 'ar'
if 'dismissed_ids' not in st.session_state: st.session_state.dismissed_ids = set()

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
        'search_placeholder': "(Name, Job, Nationality, Phone...)",
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
        'search_placeholder': "(الاسم، المهنة، الجنسية، الجوال...)",
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
        'column_missing': "⚠️ لم يتم العثور على عمود 'تاريخ انتهاء العقد' في الملف.",
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
    .main { background-color: #f4f7f6; }
    
    /* أزرار بريميوم - متجاوبة */
    div.stButton > button {
        width: 100%;
        border-radius: 12px;
        height: 3.8em;
        font-weight: 600;
        margin-bottom: 12px;
        font-size: 16px !important;
        background: linear-gradient(90deg, #2193b0 0%, #6dd5ed 100%);
        color: white;
        border: none;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.15);
    }
    
    /* تحسين الجداول للموبيل */
    .stDataFrame, .stTable {
        background-color: white;
        border-radius: 15px;
        overflow-x: auto !important;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
    }
    
    @media (max-width: 768px) {
        .stMarkdown h1, .stMarkdown h2 { font-size: 1.5rem !important; }
        .block-container { padding: 1rem 1rem !important; }
        div.stButton > button { height: 3.5em; font-size: 14px !important; }
    }

    /* كروت التنبيهات */
    .alert-card {
        background: white;
        color: black;
        border-right: 5px solid #2193b0;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }

    /* دعم RTL */
    html[dir="rtl"] .stMarkdown, html[dir="rtl"] .stText { text-align: right; }
    .stTextInput input { border-radius: 10px; border: 1px solid #ddd; padding: 12px; }
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
        # وضع الصورة الشخصية المطلوبة (السعيد) فوق اسم المبرمج
        user_photo = "image/السعيد.jpg"
        if os.path.exists(user_photo):
            st.image(user_photo, use_container_width=True)
        else:
            # Fallback for local testing
            img_path = next((f for f in ["profile.png", "profile.jpg", "image.png"] if os.path.exists(f)), None)
            if img_path: st.image(img_path, use_container_width=True)
        
        st.markdown(f"### {T['prog_by']}: {'السعيد الوزان' if st.session_state.lang == 'ar' else 'Al-Saeed Al-Wazzan'}")
        
        if st.button(T['switch_lang']):
            st.session_state.lang = 'en' if st.session_state.lang == 'ar' else 'ar'
            st.rerun()
        
        st.divider()
        
        # الزر الجديد لمراقبة العقود (الرئيسية)
        if st.button(T['home_title'], type="secondary" if st.session_state.page != "home" else "primary"):
            st.session_state.page = "home"
            st.rerun()

        if st.button(T['search_nav'], type="secondary" if st.session_state.page != "search" else "primary"):
            st.session_state.page = "search"
            st.rerun()
            
        if st.button(T['del_nav']):
            st.warning("Feature not implemented for web yet." if st.session_state.lang == 'en' else "هذه الميزة غير مفعلة للويب حالياً.")
            
        if st.button(T['refresh_nav']):
            st.cache_data.clear()
            st.rerun()
            
        if st.button(T['perms_nav'], type="secondary" if st.session_state.page != "permissions" else "primary"):
            if USERS.get(st.session_state.current_user, {}).get("can_manage_users"):
                st.session_state.page = "permissions"
                st.rerun()
            else:
                st.error("No Permission" if st.session_state.lang == 'en' else "ليس لديك صلاحية")
                
        st.divider()
        if st.button(T['logout'], type="secondary"):
            st.session_state.authenticated = False
            st.session_state.current_user = ""
            st.rerun()

# --- Page: Login ---
def page_login():
    # في الجوال، يفضل أن تكون العناصر تحت بعضها
    st.markdown("<h1 style='text-align:center;'>🛡️</h1>", unsafe_allow_html=True)
    
    # استخدام حاوية واحدة للوسط بدلاً من أعمدة في الشاشات الصغيرة
    with st.container():
        img_path = next((f for f in ["profile.png", "profile.jpg", "image.png"] if os.path.exists(f)), None)
        if img_path: 
            st.image(img_path, width=150)
        
        st.title(T['login_title'])
        
        username = st.text_input(T['user_lbl'])
        password = st.text_input(T['pass_lbl'], type="password")
        
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

# --- Page: Home (Dashboard) ---
def page_home():
    sidebar_content()
    st.title(T['home_title'])
    st.header(T['alerts_title'])
    
    data_raw = fetch_data()
    if not data_raw:
        st.info(T['info_creds']); return

    headers = deduplicate_columns(data_raw[0])
    df = pd.DataFrame(data_raw[1:], columns=headers)
    today = date.today()
    
    # البحث المرن عن عمود التاريخ (أي عمود يحتوي على انتهاء أو تاريخ أو expiry)
    date_keywords = ["انتهاء", "الانتهاء", "expiry", "expire", "تاريخ", "end"]
    date_col = next((h for h in df.columns if any(kw in h.lower() for kw in date_keywords)), "")
    
    if date_col:
        count = 0
        for idx, row in df.iterrows():
            row_id = f"{row[0]}_{row[1]}" # معرف فريد
            if row_id in st.session_state.dismissed_ids: continue
            
            dt = safe_parse_date(row[date_col])
            if dt:
                diff = (dt - today).days
                if 0 <= diff <= 14:
                    count += 1
                    msg = f"باقي {diff} يوم" if diff < 7 else "باقي أسبوع"
                    bg_color = "#fff4cc" if diff >= 7 else "#ffcccc"
                    
                    st.markdown(f"""
                    <div class="alert-card">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <h4 style="margin:0; color:#2c3e50;">{row[1]}</h4>
                                <small style="color:#666;">{row[date_col]}</small>
                            </div>
                            <div style="background:{bg_color}; padding:5px 15px; border-radius:20px; font-weight:bold; color:black;">
                                {msg}
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("✅ إخفاء التنبيه", key=f"hide_{idx}"):
                        st.session_state.dismissed_ids.add(row_id)
                        st.rerun()
                    st.divider()
        if count == 0: st.success(T['success_msg'])
    else:
        st.warning(T['column_missing'])

# --- Page: Search ---
def page_search():
    sidebar_content()
    st.title(T['search_page_title'])
    data_raw = fetch_data()
    if not data_raw: return
    headers = deduplicate_columns(data_raw[0])
    df = pd.DataFrame(data_raw[1:], columns=headers)

    query = st.text_input(T['global_search'], placeholder=T['search_placeholder'])
    search_btn = st.button(T['search_btn'], type="primary")

    results = df
    if query:
        # توسيع البحث ليشمل الترجمة الإنجليزية
        extra_term = translator.translate(query)
        if extra_term:
            mask = results.apply(lambda r: r.astype(str).str.contains(f"{query}|{extra_term}", case=False, na=False).any(), axis=1)
        else:
            mask = results.apply(lambda r: r.astype(str).str.contains(query, case=False, na=False).any(), axis=1)
        results = results[mask]

    # تحسين شكل النتائج بالألوان (التنسيق الشرطي)
    def apply_row_style(row):
        style = [''] * len(row)
        row_str = " ".join(row.astype(str)).lower()
        age_val = 0
        try: 
            # محاولة العثور على السن (رقم بين 15 و 90)
            age_val = int(next((v for v in row if str(v).isdigit() and 15 < int(v) < 90), 0))
        except: pass
        
        # 1. الأسود (السن فوق 40)
        if age_val > 40: style = ['background-color: black; color: white; font-weight: bold'] * len(row)
        # 2. الأخضر (منتهي ولا يعمل)
        if ("expired" in row_str or "منتهي" in row_str) and ("not working" in row_str or "لا يعمل" in row_str):
            style = ['background-color: #d4edda; color: #155724; font-weight: bold'] * len(row)
        # 3. الأحمر (هروب أو التزامات مالية)
        if "huroob" in row_str or "هروب" in row_str or "نعم" in row.values:
            style = ['background-color: #f8d7da; color: #721c24; font-weight: bold'] * len(row)
        
        return style

    st.markdown(f"#### 🔍 {T['ready']}: {len(results)}")
    if not results.empty:
        st.dataframe(results.style.apply(apply_row_style, axis=1), use_container_width=True)
    else:
        st.warning("No results found.")

# --- Page: Permissions ---
def page_permissions():
    sidebar_content()
    st.title(T['perms_page_title'])
    
    # Check if current user has permission
    current_u = st.session_state.current_user
    if not USERS.get(current_u, {}).get("can_manage_users", False):
        st.error("Access Denied / ليس لديك صلاحية")
        if st.button(T['back_nav']):
            st.session_state.page = "home"
            st.rerun()
        return

    st.markdown(f"### {current_u} ، {('Welcome back' if st.session_state.lang == 'en' else 'مرحباً بك')}")
    
    if st.button(T['back_nav']):
        st.session_state.page = "home"
        st.rerun()
        
    col1, col2 = st.columns(2)
    with col1:
        st.header(T['add_user_title'])
        new_u = st.text_input(T['user_lbl'], key="new_u_field")
        new_p = st.text_input(T['pass_lbl'], type="password", key="new_p_field")
        can_p = st.checkbox(T['can_access_perms'], key="can_p_check")
        
        if st.button(T['add_btn']):
            if new_u and new_p:
                if new_u in USERS:
                    st.error("User already exists / المستخدم موجود بالفعل")
                else:
                    hashed = hashlib.sha256(new_p.encode()).hexdigest()
                    USERS[new_u] = {
                        "password": hashed,
                        "role": "user",
                        "can_manage_users": can_p
                    }
                    if save_users(USERS):
                        st.success("User added successfully / تم إضافة المستخدم بنجاح")
            else:
                st.warning("Please fill all fields / يرجى ملء البيانات")
            
    with col2:
        st.header(T['change_pass_title'])
        cur_p = st.text_input("Old Password / كلمة المرور القديمة", type="password")
        n_p = st.text_input("New Password / كلمة المرور الجديدة", type="password")
        
        if st.button(T['save_btn']):
            if cur_p and n_p:
                hashed_old = hashlib.sha256(cur_p.encode()).hexdigest()
                if USERS[current_u]["password"] == hashed_old:
                    USERS[current_u]["password"] = hashlib.sha256(n_p.encode()).hexdigest()
                    if save_users(USERS):
                        st.success("Password updated / تم تحديث كلمة المرور")
                else:
                    st.error("Wrong old password / كلمة المرور القديمة خطأ")
            else:
                st.warning("Please fill all fields / يرجى ملء البيانات")

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
