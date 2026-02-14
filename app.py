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
            "full_name": "المدير العام",
            "can_manage_users": True
        },
        "samar": {
            "password": "2d75c1a2d01521e3026aa1719256a06604e7bc99aab149cb8cc7de8552fa820d", # 123452
            "role": "user",
            "full_name": "سمر",
            "can_manage_users": False
        }
    }

def save_users(users_dict):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump({"users": users_dict}, f, ensure_ascii=False, indent=2)

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
    
    /* إزالة الفراغات العلوية مع ترك مسافة للعنوان */
    .block-container {
        padding-top: 2.5rem !important;
        padding-bottom: 1rem !important;
    }
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 0rem !important;
    }
    
    /* تنسيق فاخر للأزرار */
    [data-testid="stSidebar"] div.stButton > button {
        width: 100% !important;
        display: block !important;
        margin-left: auto !important;
        margin-right: auto !important;
        border-radius: 14px !important;
        height: 52px !important;
        font-weight: 600 !important;
        margin-bottom: 10px !important;
        font-size: 15px !important;
        color: white !important;
        border: 1px solid rgba(255,255,255,0.15) !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.1) !important;
        transition: all 0.3s ease !important;
        letter-spacing: 0.5px !important;
        backdrop-filter: blur(10px) !important;
    }
    [data-testid="stSidebar"] div.stButton > button:hover {
        transform: translateY(-2px) scale(1.02) !important;
        box-shadow: 0 8px 30px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.2) !important;
        border: 1px solid rgba(255,255,255,0.3) !important;
    }
    [data-testid="stSidebar"] div.stButton > button:active {
        transform: translateY(0px) scale(0.98) !important;
        background-color: rgba(0,0,0,0.2) !important;
    }

    /* 1. مراقب العقود - أزرق ملكي */
    [data-testid="stSidebar"] div.stButton:nth-of-type(1) > button {
        background: linear-gradient(135deg, #0c3483 0%, #2196f3 50%, #0c3483 100%) !important;
    }
    /* 2. البحث والطباعة - بنفسجي فاخر */
    [data-testid="stSidebar"] div.stButton:nth-of-type(2) > button {
        background: linear-gradient(135deg, #4a0072 0%, #9c27b0 50%, #4a0072 100%) !important;
    }
    /* 3. شاشة الصلاحيات - ذهبي فخم */
    [data-testid="stSidebar"] div.stButton:nth-of-type(3) > button {
        background: linear-gradient(135deg, #8b6914 0%, #d4af37 50%, #8b6914 100%) !important;
        color: #fff !important;
    }
    /* 4. حذف الصف المختار - أحمر داكن */
    [data-testid="stSidebar"] div.stButton:nth-of-type(4) > button {
        background: linear-gradient(135deg, #7f0000 0%, #c62828 50%, #7f0000 100%) !important;
    }
    /* 5. تحديث البيانات - أخضر زمردي */
    [data-testid="stSidebar"] div.stButton:nth-of-type(5) > button {
        background: linear-gradient(135deg, #004d40 0%, #00897b 50%, #004d40 100%) !important;
    }

    
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
        margin-top: -10px !important;
    }
    
    /* تقليل الفراغات بين العناصر - بدون التأثير على العنوان الرئيسي */
    div.stMarkdown { margin-bottom: -10px; }
    h2, h3 { margin-top: -10px !important; padding-top: 0px !important; }
    h1 { margin-top: 0px !important; padding-top: 10px !important; }
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

def translate_columns(df):
    col_mapping_exact = {
        "Timestamp": {"ar": "وقت التسجيل", "en": "Timestamp"},
        "Full Name": {"ar": "الاسم الكامل", "en": "Full Name"},
        "Nationality": {"ar": "الجنسية", "en": "Nationality"},
        "Gender": {"ar": "الجنس", "en": "Gender"},
        "Phone Number": {"ar": "رقم الهاتف", "en": "Phone Number"},
        "Is your contract expired": {"ar": "هل انتهى العقد؟", "en": "Contract Expired?"},
        "When is your contract end date?": {"ar": "تاريخ انتهاء العقد", "en": "Contract End Date"},
        "your age": {"ar": "العمر", "en": "Age"},
        "Are you working now?": {"ar": "هل تعمل حالياً؟", "en": "Currently Working?"},
        "Do you have a valid residency?": {"ar": "هل لديك إقامة سارية؟", "en": "Valid Residency?"},
        "Do you have a valid driving license?": {"ar": "هل لديك رخصة قيادة؟", "en": "Driving License?"},
        "If you are Huroob, how many days or months h...": {"ar": "كم عدد الهروب", "en": "Huroob Count"},
        "Will your employer transfer your sponsorship?": {"ar": "هل الكفيل يتنازل؟", "en": "Employer Transferable?"},
        "Are you in Saudi Arabia?": {"ar": "هل أنت في السعودية؟", "en": "In Saudi?"},
        "Which city do you live in?": {"ar": "المدينة / المنطقة", "en": "City"},
        "How did you hear about us?": {"ar": "كيف سمعت عنا؟", "en": "How Hear About Us"},
        "What is the name of your sponsor/establishment?": {"ar": "اسم الكفيل / المنشأة", "en": "Employer Name"},
        "Do you speak Arabic?": {"ar": "هل تتحدث العربية؟", "en": "Speak Arabic?"},
        "Which job are you applying for?": {"ar": "الوظيفة المطلوبة", "en": "Required Job"},
        "What other jobs can you do?": {"ar": "وظائف أخرى تتقنها", "en": "Other Skills"},
        "How much experience do you have?": {"ar": "الخبرة", "en": "Experience"},
        "Do you have a health card?": {"ar": "هل لديك كرت صحي؟", "en": "Health Card?"},
        "Is the card baladiya valid?": {"ar": "صلاحية كرت البلدية", "en": "Municipality Card Expiry"},
        "How many months?": {"ar": "عدد الأشهر", "en": "Months Count"},
        "Can you work overtime?": {"ar": "هل تعمل وقت إضافي؟", "en": "Overtime?"},
        "Are you ready to work immediately?": {"ar": "هل أنت جاهز للعمل؟", "en": "Ready to Work?"},
        "Are you married?": {"ar": "الحالة الاجتماعية", "en": "Marital Status"},
        "Iqama ID Number": {"ar": "رقم الإقامة", "en": "Iqama ID"},
        "What is the profession in Iqama?": {"ar": "المهنة في الإقامة", "en": "Iqama Profession"},
        "Your Iqama Expiry Date": {"ar": "صلاحية الإقامة", "en": "Iqama Expiry"},
        "How many times have you been transferred?": {"ar": "عدد مرات التنازل", "en": "Transfer Times"},
        "Download CV": {"ar": "تحميل السيرة الذاتية", "en": "Download CV"},
        "Do you have any financial obligations towards your previous sponsor": {"ar": "هل لديك التزامات مالية؟", "en": "Financial Obligations?"},
        "Do you have to report Huroob": {"ar": "هل لديك بلاغ هروب؟", "en": "Report Huroob?"}
    }

    # Partial match mapping (ORDER IS IMPORTANT: specific matches first)
    col_mapping_partial = {
        # High specificity
        
        # New additions for user's screenshot
        "days or months have you been huroob": {"ar": "مدة الهروب (أيام/أشهر)", "en": "Huroob Duration"},
        "accept to transfer your sponsorship": {"ar": "هل يقبل الكفيل التنازل؟", "en": "Sponsor Accepts Transfer?"},
        "are you in saudi arabia now": {"ar": "هل أنت في السعودية الآن؟", "en": "In Saudi Now?"},
        "which city in saudi": {"ar": "المدينة في السعودية؟", "en": "City in Saudi?"},
        "which city in saudi arabia are you in": {"ar": "المدينة في السعودية؟", "en": "City in Saudi?"},
        "what is the name of the area where you live": {"ar": "اسم الحي / المنطقة", "en": "Area Name"},
        "which job are you looking for": {"ar": "الوظيفة المطلوبة", "en": "Desired Job"},
        "how much experience do you have in this field": {"ar": "الخبرة في هذا المجال", "en": "Field Experience"},
        "what other jobs can you do": {"ar": "وظائف أخرى تتقنها", "en": "Other Jobs"},
        "do you have card baladiya": {"ar": "هل لديك كرت بلدية؟", "en": "Baladiya Card?"},
        "is the card baladiya valid": {"ar": "هل كرت البلدية ساري؟", "en": "Is Baladiya Valid?"},
        "how many months card baladiya valid": {"ar": "مدة صلاحية البلدية (أشهر)", "en": "Baladiya Validity (Months)"},
        "how many months card baladiya expires": {"ar": "كم شهر وينتهي كرت البلدية", "en": "Baladiya Expiry (Months)"},
        "can you work outside your city": {"ar": "العمل خارج المدينة؟", "en": "Work Outside City?"},
        "married and do your children reside": {"ar": "متزوج والأبناء في السعودية؟", "en": "Married & Family in KSA?"},
        "iqama is valid, how many months are left": {"ar": "مدة صلاحية الإقامة (أشهر)", "en": "Iqama Validity Remaining"},
        "if the iqama expired how many months ago": {"ar": "منذ متى انتهت الإقامة؟", "en": "Months Since Iqama Expired"},
        "how many times did you transfer your sponsorship": {"ar": "عدد مرات نقل الكفالة", "en": "Transfer Count"},
        "how did you know": {"ar": "كيف عرفت عنا؟", "en": "How check us"},

        "how much experience do you": {"ar": "سنوات الخبرة", "en": "Years of Experience"},
        
        "report huroob": {"ar": "بلاغ هروب", "en": "Huroob Report"},
        "huroob": {"ar": "عدد الهروب", "en": "Huroob Count"}, # Fallback for other huroob strings
        
        "iqama expiry": {"ar": "صلاحية الإقامة", "en": "Iqama Expiry"},
        "profession": {"ar": "المهنة في الإقامة", "en": "Iqama Profession"},
        "id number": {"ar": "رقم الإقامة", "en": "Iqama ID"},
        "iqama": {"ar": "الإقامة", "en": "Iqama"},
        
        "contract end": {"ar": "تاريخ انتهاء العقد", "en": "Contract End Date"},
        "contract expired": {"ar": "هل انتهى العقد؟", "en": "Contract Expired?"},
        "financial": {"ar": "التزامات مالية", "en": "Financial Obligations"},
        
        "sponsor": {"ar": "اسم الكفيل", "en": "Sponsor Name"},
        "sponsorship": {"ar": "نقل كفالة", "en": "Sponsorship"},
        
        "driving": {"ar": "رخصة قيادة", "en": "Driving License"},
        "residency": {"ar": "إقامة", "en": "Residency"},
        
        "saudi": {"ar": "هل أنت في السعودية؟", "en": "In Saudi?"},
        "city": {"ar": "المدينة", "en": "City"},
        "hear": {"ar": "كيف سمعت عنا؟", "en": "Source"},
        "speak": {"ar": "هل تتحدث العربية؟", "en": "Speak Arabic?"},
        "health": {"ar": "كرت صحي", "en": "Health Card"},
        "baladiya": {"ar": "بلدية", "en": "Baladiya"},
        "months": {"ar": "عدد الأشهر", "en": "Months Count"},
        "overtime": {"ar": "وقت إضافي", "en": "Overtime?"},
        "ready": {"ar": "هل أنت جاهز للعمل؟", "en": "Ready to Work?"},
        "married": {"ar": "الحالة الاجتماعية", "en": "Marital Status"},
        "transfer": {"ar": "عدد مرات التنازل", "en": "Transfer Times"},
        "cv": {"ar": "السيرة الذاتية", "en": "CV"},
        
        # General / Short words last
        "timestamp": {"ar": "وقت التسجيل", "en": "Timestamp"},
        "full name": {"ar": "الاسم الكامل", "en": "Full Name"},
        "nationality": {"ar": "الجنسية", "en": "Nationality"},
        "phone": {"ar": "رقم الهاتف", "en": "Phone Number"},
        "name": {"ar": "الاسم", "en": "Name"},
        "age": {"ar": "العمر", "en": "Age"},
        "gender": {"ar": "الجنس", "en": "Gender"},
        "job": {"ar": "الوظيفة", "en": "Job"},
        "experience": {"ar": "الخبرة", "en": "Experience"},
    }
    
    new_names = {}
    for c in df.columns:
        c_clean = c.strip()
        c_lower = c_clean.lower()
        
        # 1. Exact match
        if c_clean in col_mapping_exact:
            new_names[c] = col_mapping_exact[c_clean][st.session_state.lang]
            continue
            
        # 2. Key contains part match (First match wins)
        found = False
        for k, v in col_mapping_partial.items():
            if k in c_lower:
                new_names[c] = v[st.session_state.lang]
                found = True
                break
        
        if not found:
            new_names[c] = c
            
    # Deduplicate column names to avoid Pyarrow errors
    final_names = {}
    seen_counts = {}
    
    for c in df.columns:
        trans = new_names.get(c, c)
        if trans in seen_counts:
            seen_counts[trans] += 1
            unique_trans = f"{trans} ({seen_counts[trans]})"
        else:
            seen_counts[trans] = 1
            unique_trans = trans
        final_names[c] = unique_trans
            
    return df.rename(columns=final_names)



def translate_search_term(term):
    """
    Translates Arabic search terms to English for filtering the dataframe.
    """
    term = term.strip().lower()
    
    # Mapping dictionary (Arabic -> English)
    mapping = {
        # Genders
        "ذكر": "Male",
        "انثى": "Female",
        "أنثى": "Female",
        
        # Marital Status
        "اعزب": "Single",
        "أعزب": "Single",
        "متزوج": "Married",
        "متزوجة": "Married",
        
        # Cities (Saudi)
        "الرياض": "Riyadh",
        "جدة": "Jeddah",
        "مكة": "Makkah",
        "المدينة": "Madinah",
        "المدينة المنورة": "Madinah",
        "الدمام": "Dammam",
        "الخبر": "Khobar",
        "أبها": "Abha",
        "تبوك": "Tabuk",
        "حائل": "Hail",
        "جازان": "Jazan",
        "نجران": "Najran",
        "الطائف": "Taif",
        "القصيم": "Qassim",
        "بريدة": "Buraydah",
        
        # Nationalities
        "سعودي": "Saudi",
        "سعودية": "Saudi",
        "مصر": "Egypt",
        "مصري": "Egyptian",
        "مصرية": "Egyptian",
        "هندي": "Indian",
        "هندية": "Indian",
        "باكستاني": "Pakistani",
        "باكستانية": "Pakistani",
        "فلبيني": "Filipino",
        "فلبينية": "Filipino",
        "بنغلاديشي": "Bangladeshi",
        "سوداني": "Sudanese",
        "يمني": "Yemeni",
        "سوري": "Syrian",
        "أردني": "Jordanian",
        "لبناني": "Lebanese",
        
        # Jobs
        "باريستا": "Barista",
        "نادل": "Waiter",
        "طباخ": "Chef",
        "شيف": "Chef",
        "طاهي": "Chef",
        "سائق": "Driver",
        "عامل نظافة": "Cleaner",
        "منظف": "Cleaner",
        "محاسب": "Accountant",
        "مدير": "Manager",
        "مبيعات": "Sales",
        "استقبال": "Reception",
        "موظف استقبال": "Receptionist",
        "حارس": "Security",
        "امن": "Security",
        "فني": "Technician",
        "مهندس": "Engineer",
        "طبيب": "Doctor",
        "ممرض": "Nurse",
        "ممرضة": "Nurse",
        "عامل": "Worker",
        "حداد": "Blacksmith",
        "نجار": "Carpenter",
        "سباك": "Plumber",
        "كهربائي": "Electrician",
        "مشرف": "Supervisor"
    }
    
    # Check for exact match first
    if term in mapping:
        return mapping[term]
        
    # Check if any key is PART of the search term (simple partial match)
    for k, v in mapping.items():
        if k in term:
            return v
            
    return term

# --- UI Helpers ---
def sidebar_content():
    with st.sidebar:
        # === زر تبديل اللغة أعلى شيء ===
        lang_col1, lang_col2 = st.columns(2)
        with lang_col1:
            if st.button("ع", key="lang_ar", type="primary" if st.session_state.lang == 'ar' else "secondary", use_container_width=True):
                st.session_state.lang = 'ar'
                st.rerun()
        with lang_col2:
            if st.button("EN", key="lang_en", type="primary" if st.session_state.lang == 'en' else "secondary", use_container_width=True):
                st.session_state.lang = 'en'
                st.rerun()
        
        st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)
        
        # === الصورة الشخصية ===
        img_found = False
        for p in ["alsaeed.jpg", "image/alsaeed.jpg"]:
            if os.path.exists(p):
                _, img_col, _ = st.columns([1, 2, 1])
                with img_col:
                    st.image(p, width=130)
                img_found = True
                break
        if not img_found:
            st.info("📷")
        
        st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)
        
        # === اسم المبرمج ===
        st.markdown("""
            <div style='text-align:center;'>
                <span style='color:#c0a060; font-size:11px; letter-spacing:2px; text-transform:uppercase;'>✦ Programmed by ✦</span><br>
                <span style='background: linear-gradient(90deg, #d4af37, #f5d991, #d4af37); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size:18px; font-weight:700; letter-spacing:1px;'>Al-Saeed Al-Wazzan</span>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)
        
        st.divider()
        
        st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)
        
        # 1. زر مراقب العقود (الرئيسية)
        if st.button(T['home_title'], type="secondary" if st.session_state.page != "home" else "primary", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()

        # 2. زر البحث والطباعة
        if st.button(T['search_nav'], type="secondary" if st.session_state.page != "search" else "primary", use_container_width=True):
            st.session_state.page = "search"
            st.rerun()

        # 3. زر شاشة الصلاحيات
        if st.button(T['perms_nav'], type="secondary" if st.session_state.page != "permissions" else "primary", use_container_width=True):
            if USERS.get(st.session_state.current_user, {}).get("can_manage_users"):
                st.session_state.page = "permissions"
                st.rerun()
            else:
                st.error("No Permission" if st.session_state.lang == 'en' else "ليس لديك صلاحية")

        # 4. زر حذف الصف المختار
        if st.button(T['del_nav'], use_container_width=True):
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
        if st.button(T['refresh_nav'], use_container_width=True):
            st.cache_data.clear()
            st.rerun()
            
        st.divider()
        
        if st.button(T['logout'], type="secondary", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.current_user = ""
            st.rerun()

# --- Page: Login ---
def page_login():
    # تنسيق خاص لشاشة الدخول
    st.markdown("""
        <style>
            [data-testid="stAppViewContainer"] { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); }
            .login-card {
                max-width: 420px;
                margin: 40px auto;
                padding: 40px 30px;
                background: rgba(30, 41, 59, 0.95);
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.4);
                border: 1px solid rgba(255,255,255,0.1);
                text-align: center;
            }
            .login-card h2 { color: white !important; margin-bottom: 25px; }
            .login-card p, .login-card label { color: #cbd5e1 !important; }
            .programmer-text { 
                color: #94a3b8 !important; 
                font-size: 14px; 
                margin-top: 8px;
                font-weight: 500;
            }
            /* White labels */
            [data-testid="stAppViewContainer"] label { color: white !important; }
            [data-testid="stAppViewContainer"] .stTextInput label { color: white !important; }
        </style>
    """, unsafe_allow_html=True)

    # توسيط المحتوى
    spacer1, center_col, spacer2 = st.columns([1, 1.5, 1])
    
    with center_col:
        # الصورة الشخصية بحجم صغير
        img_found = False
        for p in ["alsaeed.jpg", "image/alsaeed.jpg"]:
            if os.path.exists(p):
                st.image(p, width=90)
                img_found = True
                break
        if not img_found:
            st.markdown("<div style='text-align:center; font-size:40px;'>📷</div>", unsafe_allow_html=True)
        
        # النص تحت الصورة بشكل فخم
        st.markdown("""
            <div style='text-align:center; margin-top:5px;'>
                <span style='color:#8a7a5a; font-size:10px; letter-spacing:2px; text-transform:uppercase;'>✦ Programmed by ✦</span><br>
                <span style='background: linear-gradient(90deg, #d4af37, #f5d991, #d4af37); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size:16px; font-weight:700; letter-spacing:1px;'>Al-Saeed Al-Wazzan</span>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # عنوان تسجيل الدخول
        st.markdown(f"<h2 style='text-align:center; color:white;'>🔐 {T['login_title']}</h2>", unsafe_allow_html=True)
        
        username = st.text_input(T['user_lbl'], placeholder="Username")
        password = st.text_input(T['pass_lbl'], type="password", placeholder="Password")
        
        if st.button(T['login_btn'], type="primary", use_container_width=True):
            if username in USERS:
                hashed = hashlib.sha256(password.encode()).hexdigest()
                if USERS[username]["password"] == hashed:
                    st.session_state.authenticated = True
                    st.session_state.current_user = username
                    # حفظ الاسم الكامل في الجلسة لاستخدامه في الترحيب
                    st.session_state.current_user_name = USERS[username].get("full_name", username)
                    st.session_state.page = "home"
                    st.rerun()
                else: st.error(T['wrong_pass'])
            else: st.error(T['user_not_found'])
        
        st.markdown("")
        if st.button(T['switch_lang'], key="login_lang", use_container_width=True):
            st.session_state.lang = 'en' if st.session_state.lang == 'ar' else 'ar'
            st.rerun()

# --- Page: Home (Dashboard) ---
def page_home():
    sidebar_content()
    
    # رسالة الترحيب في الرئيسية
    welcome_name = st.session_state.get("current_user_name", st.session_state.current_user)
    st.title(f"{T['home_title']} - {welcome_name}")
    
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
        
        # --- ترجمة العناوين (Columns Translation) ---
        display_df = translate_columns(display_df)
        # -------------------------------------------
        # -------------------------------------------
        
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
            # Smart translation for search
            translated_query = translate_search_term(query)
            
            # If translation happened, show toast or info (Optional, helps user know what happened)
            if translated_query.lower() != query.lower():
                st.toast(f"Searching for: {translated_query} ({query})")
            
            # Search with both original and translated query to be safe, OR just translated
            # User asked: "write x -> search y". So we search for translated version.
            # But safety net: search for EITHER to avoid missing mixed content?
            # User specifically said: "write barista -> search barista" (English).
            # So we use the translated term.
            
            mask = results.apply(lambda row: row.astype(str).str.contains(translated_query, case=False).any(), axis=1)
            results = results[mask]
            
        st.markdown(f"#### 🔍 النتائج المكتشفة: {len(results)}")
        
        # ترجمة الأعمدة قبل العرض
        results_dys = translate_columns(results)
        st.dataframe(results_dys.astype(str), use_container_width=True)
    
    if st.button(T['print_btn']):
        st.info("Feature not available in cloud yet." if st.session_state.lang == 'en' else "الميزة غير متاحة في النسخة السحابية حالياً.")

# --- Page: Permissions ---
def page_permissions():
    global USERS
    sidebar_content()
    st.title(T['perms_page_title'])
    
    # رسالة الترحيب بالاسم الكامل
    welcome_name = st.session_state.get("current_user_name", st.session_state.current_user)
    st.markdown(f"### {'Welcome back' if st.session_state.lang == 'en' else 'مرحباً بك'} ، {welcome_name}")
    
    if st.button(T['back_nav']):
        st.session_state.page = "home"
        st.rerun()
    
    st.markdown("---")
    
    # إعادة تحميل المستخدمين لضمان أحدث البيانات
    USERS = load_users()
    user_list = list(USERS.keys())
        
    col1, col2, col3 = st.columns(3)
    
    # === تغيير كلمة المرور ===
    with col1:
        st.markdown(f"### 🔒 {'تغيير كلمة المرور' if st.session_state.lang == 'ar' else 'Change Password'}")
        
        # اختيار المستخدم
        target_user = st.selectbox(
            "اختر المستخدم" if st.session_state.lang == 'ar' else "Select User",
            user_list, key="change_pass_user"
        )
        
        n_p = st.text_input("كلمة المرور الجديدة" if st.session_state.lang == 'ar' else "New Password", type="password", key="new_pass")
        n_p2 = st.text_input("تأكيد كلمة المرور" if st.session_state.lang == 'ar' else "Confirm Password", type="password", key="confirm_pass")
        
        if st.button(T['save_btn'], key="save_pass_btn"):
            if not n_p:
                st.error("يرجى إدخال كلمة المرور الجديدة" if st.session_state.lang == 'ar' else "Please enter new password")
            elif n_p != n_p2:
                st.error("كلمة المرور غير متطابقة" if st.session_state.lang == 'ar' else "Passwords do not match")
            elif target_user not in USERS:
                st.error("المستخدم غير موجود" if st.session_state.lang == 'ar' else "User not found")
            else:
                USERS[target_user]["password"] = hashlib.sha256(n_p.encode()).hexdigest()
                save_users(USERS)
                st.success(f"✅ تم تغيير كلمة مرور {target_user} بنجاح" if st.session_state.lang == 'ar' else f"✅ Password changed for {target_user}")
    
    # === إضافة مستخدم جديد ===
    with col2:
        st.markdown(f"### ➕ {T['add_user_title']}")
        new_name = st.text_input("الاسم الكامل" if st.session_state.lang == 'ar' else "Full Name", key="new_full_name")
        new_u = st.text_input(T['user_lbl'], key="new_u")
        new_p = st.text_input(T['pass_lbl'], type="password", key="new_p")
        new_p2 = st.text_input("تأكيد كلمة المرور" if st.session_state.lang == 'ar' else "Confirm Password", type="password", key="confirm_new_p")
        can_p = st.checkbox(T['can_access_perms'], key="can_perms_cb")
        
        if st.button(T['add_btn'], key="add_user_btn"):
            if not new_u or not new_p:
                st.error("يرجى إدخال اسم المستخدم وكلمة المرور" if st.session_state.lang == 'ar' else "Please enter username and password")
            elif new_p != new_p2:
                st.error("كلمة المرور غير متطابقة" if st.session_state.lang == 'ar' else "Passwords do not match")
            elif new_u in USERS:
                st.error("اسم المستخدم موجود مسبقاً" if st.session_state.lang == 'ar' else "Username already exists")
            else:
                USERS[new_u] = {
                    "password": hashlib.sha256(new_p.encode()).hexdigest(),
                    "role": "admin" if can_p else "user",
                    "full_name": new_name if new_name else new_u,
                    "can_manage_users": can_p
                }
                save_users(USERS)
                st.success(f"✅ تم إضافة {new_u} ({new_name}) بنجاح" if st.session_state.lang == 'ar' else f"✅ User {new_u} added")
                st.rerun()
    
    # === حذف مستخدم ===
    with col3:
        st.markdown(f"### 🗑️ {'حذف مستخدم' if st.session_state.lang == 'ar' else 'Delete User'}")
        
        # لا تسمح بحذف المستخدم الحالي أو admin
        deletable_users = [u for u in user_list if u != st.session_state.current_user and u != "admin"]
        
        if deletable_users:
            del_user = st.selectbox(
                "اختر المستخدم للحذف" if st.session_state.lang == 'ar' else "Select User to Delete",
                deletable_users, key="del_user_select"
            )
            
            st.warning(f"⚠️ {'سيتم حذف المستخدم نهائياً' if st.session_state.lang == 'ar' else 'User will be permanently deleted'}")
            
            if st.button("🗑️ حذف" if st.session_state.lang == 'ar' else "🗑️ Delete", key="del_user_btn"):
                if del_user in USERS:
                    del USERS[del_user]
                    save_users(USERS)
                    st.success(f"✅ تم حذف {del_user} بنجاح" if st.session_state.lang == 'ar' else f"✅ {del_user} deleted")
                    st.rerun()
        else:
            st.info("لا يوجد مستخدمين يمكن حذفهم" if st.session_state.lang == 'ar' else "No users to delete")
    
    # === عرض المستخدمين الحاليين ===
    st.markdown("---")
    st.markdown(f"### 👥 {'المستخدمون الحاليون' if st.session_state.lang == 'ar' else 'Current Users'}")
    
    for uname, udata in USERS.items():
        role_label = "👑 مدير" if udata.get("can_manage_users") else "👤 مستخدم"
        if st.session_state.lang == 'en':
            role_label = "👑 Admin" if udata.get("can_manage_users") else "👤 User"
        st.markdown(f"- **{uname}** — {role_label}")

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
