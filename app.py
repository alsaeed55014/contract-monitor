import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, date, timedelta
from dateutil import parser
import os
import json
import hashlib
import base64
import requests
import re
import time
try:
    import pdfplumber
    from deep_translator import GoogleTranslator
    HAS_TRANSLATOR = True
except ImportError:
    HAS_TRANSLATOR = False
import io

# Page Config
st.set_page_config(
    page_title="Contract Monitor | مراقب العقود", 
    layout="wide", 
    page_icon="📝",
    initial_sidebar_state="expanded"
)

# ============================================
# CONFIGURATION & CONSTANTS
# ============================================

# --- استيراد الخطوط العالمية ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Dancing+Script:wght@700&family=Orbitron:wght@400;700&family=Cairo:wght@400;700&family=Amiri:wght@400;700&display=swap');
    
    /* Global Styles */
    html, body, [class*="css"] { 
        font-family: 'Cairo', 'Outfit', sans-serif; 
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a252f 0%, #2c3e50 100%);
        color: white;
        border-right: 1px solid rgba(255,255,255,0.1);
    }
    
    /* Main Container */
    .main { 
        background-color: #0d1117; 
    }
    
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        max-width: 100% !important;
    }
    
    /* Sidebar Buttons */
    [data-testid="stSidebar"] div.stButton > button {
        width: 100% !important;
        border-radius: 12px !important;
        height: 48px !important;
        font-weight: 600 !important;
        margin-bottom: 8px !important;
        font-size: 14px !important;
        color: white !important;
        border: 1px solid rgba(255,255,255,0.15) !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2) !important;
        transition: all 0.3s ease !important;
    }
    [data-testid="stSidebar"] div.stButton > button:hover {
        transform: translateY(-2px) scale(1.02) !important;
        box-shadow: 0 8px 25px rgba(0,0,0,0.35) !important;
    }
    
    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #1a252f;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb {
        background: #4a5568;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #718096;
    }
    
    /* Table Container with Scroll */
    .table-container {
        max-height: 400px;
        overflow-y: auto;
        overflow-x: auto;
        border-radius: 12px;
        border: 1px solid #30363d;
        margin-bottom: 20px;
    }
    
    /* Custom Table Styling */
    .custom-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
        white-space: nowrap;
    }
    .custom-table th {
        background: linear-gradient(135deg, #1a252f 0%, #2c3e50 100%);
        color: #fff;
        padding: 12px 15px;
        text-align: right;
        font-weight: 600;
        position: sticky;
        top: 0;
        z-index: 10;
        border-bottom: 2px solid #4a5568;
    }
    .custom-table td {
        padding: 10px 15px;
        border-bottom: 1px solid #30363d;
        color: #e2e8f0;
        transition: background-color 0.2s;
    }
    .custom-table tr:hover td {
        background-color: rgba(255,255,255,0.05);
    }
    
    /* Status Row Colors */
    .row-urgent { background-color: rgba(220, 53, 69, 0.15) !important; }
    .row-urgent td { color: #ff6b7a !important; font-weight: 600; }
    
    .row-expired { background-color: rgba(108, 117, 125, 0.15) !important; }
    .row-expired td { color: #adb5bd !important; }
    
    .row-warning { background-color: rgba(255, 193, 7, 0.1) !important; }
    .row-warning td { color: #ffd54f !important; }
    
    .row-active { background-color: rgba(40, 167, 69, 0.1) !important; }
    .row-active td { color: #69db7c !important; }
    
    /* Section Headers */
    .section-header {
        background: linear-gradient(90deg, #1a252f, #2c3e50);
        padding: 15px 20px;
        border-radius: 12px;
        margin-bottom: 15px;
        border-right: 4px solid;
    }
    .section-header-urgent { border-color: #dc3545; }
    .section-header-expired { border-color: #6c757d; }
    .section-header-active { border-color: #28a745; }
    
    /* Delete Button */
    .delete-btn {
        background: #dc3545;
        color: white;
        border: none;
        padding: 6px 12px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 12px;
        transition: all 0.2s;
    }
    .delete-btn:hover {
        background: #c82333;
        transform: scale(1.05);
    }
    
    /* Welcome Message */
    .welcome-container {
        padding: 15px 0;
        margin-bottom: 10px;
    }
    .welcome-msg {
        font-family: 'Amiri', serif;
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(to right, #bf953f, #fcf6ba, #b38728);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Neon Signature */
    .neon-signature {
        text-align: center;
        font-family: 'Dancing Script', cursive;
        font-size: 1.8rem;
        color: #fff;
        text-shadow: 0 0 10px #2196f3, 0 0 20px #2196f3;
        margin-bottom: 20px;
    }
    
    /* Stats Cards */
    .stats-container {
        display: flex;
        gap: 15px;
        margin-bottom: 20px;
        flex-wrap: wrap;
    }
    .stat-card {
        background: linear-gradient(135deg, #1a252f, #2c3e50);
        padding: 15px 25px;
        border-radius: 12px;
        text-align: center;
        min-width: 120px;
        border: 1px solid #30363d;
    }
    .stat-number {
        font-size: 2rem;
        font-weight: bold;
    }
    .stat-label {
        font-size: 0.85rem;
        color: #a0aec0;
    }
    
    /* Search Input */
    .search-hint {
        color: #718096;
        font-size: 0.85rem;
        margin-top: 5px;
    }
    
    /* Modal/Dialog */
    .confirm-dialog {
        background: #1a252f;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #dc3545;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# DATA LAYER - Helper Functions
# ============================================

def deduplicate_columns(columns):
    """منع تكرار أسماء الأعمدة"""
    new_columns = []
    counts = {}
    for col in columns:
        if not col or str(col).strip() == "":
            col = "Column"
        if col in counts:
            counts[col] += 1
            new_columns.append(f"{col}_{counts[col]}")
        else:
            counts[col] = 0
            new_columns.append(col)
    return new_columns

def safe_parse_date(d_str):
    """معالجة التواريخ"""
    if not d_str:
        return None
    try:
        d_clean = str(d_str).strip().replace('ص', 'AM').replace('م', 'PM')
        return parser.parse(d_clean, fuzzy=True).date()
    except:
        return None

def get_direct_download_link(url):
    """تحويل روابط Google Drive"""
    if not url or "drive.google.com" not in url:
        return url
    try:
        if "id=" in url:
            file_id = url.split("id=")[1].split("&")[0]
            return f"https://drive.google.com/uc?export=download&id={file_id}"
        elif "/d/" in url:
            file_id = url.split("/d/")[1].split("/")[0]
            return f"https://drive.google.com/uc?export=download&id={file_id}"
    except:
        pass
    return url

# ============================================
# PHONE NUMBER PROCESSING LAYER
# ============================================

def normalize_phone_number(phone_str):
    """
    تطبيع رقم الهاتف - إزالة كل شيء ما عدا الأرقام
    المخرج: رقم نظيف بدون فراغات أو رموز
    """
    if not phone_str:
        return ""
    # إزالة كل شيء ما عدا الأرقام
    digits_only = re.sub(r'\D', '', str(phone_str))
    return digits_only

def clean_phone_for_storage(phone_str):
    """
    تنظيف الرقم للتخزين في قاعدة البيانات
    يحذف +966 أو 966 من البداية ويضيف 0
    """
    digits = normalize_phone_number(phone_str)
    
    # إذا بدأ بـ 966، نحذفها ونضيف 0
    if digits.startswith('966') and len(digits) > 9:
        digits = '0' + digits[3:]
    # إذا لم يبدأ بـ 0 وطوله 9 أرقام، نضيف 0
    elif len(digits) == 9 and not digits.startswith('0'):
        digits = '0' + digits
    
    return digits

def format_phone_for_display(phone_str):
    """
    تنسيق الرقم للعرض: +966 57 320 8334
    """
    digits = normalize_phone_number(phone_str)
    
    # إذا بدأ بـ 0، نحوله لـ +966
    if digits.startswith('0'):
        digits = '966' + digits[1:]
    
    # تنسيق: +966 XX XXX XXXX
    if len(digits) >= 12:
        return f"+{digits[:3]} {digits[3:5]} {digits[5:8]} {digits[8:]}"
    elif len(digits) >= 9:
        return f"+966 {digits[-9:-7]} {digits[-7:-4]} {digits[-4:]}"
    
    return phone_str

def extract_phone_digits_for_search(phone_str):
    """
    استخراج الأرقام للبحث - نأخذ آخر 9 أرقام (بدون رمز الدولة)
    """
    digits = normalize_phone_number(phone_str)
    
    # إذا كان يبدأ بـ 966، نحذفها
    if digits.startswith('966'):
        digits = digits[3:]
    
    # إذا لم يبدأ بـ 0، نضيفه
    if not digits.startswith('0') and len(digits) == 9:
        digits = '0' + digits
    
    return digits

def is_phone_number(text):
    """التحقق إذا كان النص رقم هاتف"""
    if not text:
        return False
    digits = normalize_phone_number(str(text))
    # رقم هاتف سعودي: 10 أرقام (مع الصفر) أو 9 بدون الصفر أو 12 مع 966
    return len(digits) >= 9 and len(digits) <= 14

# ============================================
# AUTHENTICATION SYSTEM
# ============================================

USERS_FILE = 'users.json'
DELETED_ROWS_FILE = 'deleted_rows.json'

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("users", {})
        except:
            pass
    return {
        "admin": {
            "password": hashlib.sha256("266519111".encode()).hexdigest(),
            "role": "admin",
            "full_name_ar": "المدير العام",
            "full_name_en": "General Manager",
            "can_manage_users": True
        },
        "samar": {
            "password": hashlib.sha256("123452".encode()).hexdigest(),
            "role": "admin",
            "full_name_ar": "سمر",
            "full_name_en": "Samar",
            "can_manage_users": True
        },
        "maya": {
            "password": hashlib.sha256("123452".encode()).hexdigest(),
            "role": "admin",
            "full_name_ar": "مايا الوزان",
            "full_name_en": "Maya Al-Wazzan",
            "can_manage_users": True
        },
        "alsaeed": {
            "password": hashlib.sha256("123452".encode()).hexdigest(),
            "role": "admin",
            "full_name_ar": "السعيد الوزان",
            "full_name_en": "Alsaeed Alwazzan",
            "can_manage_users": True
        }
    }

def load_deleted_rows():
    if os.path.exists(DELETED_ROWS_FILE):
        try:
            with open(DELETED_ROWS_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except:
            pass
    return set()

def save_deleted_rows(deleted_set):
    with open(DELETED_ROWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(deleted_set), f, ensure_ascii=False, indent=2)

def save_users(users_dict):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump({"users": users_dict}, f, ensure_ascii=False, indent=2)

# ============================================
# GOOGLE SHEETS LAYER
# ============================================

def get_gspread_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            return gspread.authorize(creds)
    except:
        pass
    if os.path.exists('credentials.json'):
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
            return gspread.authorize(creds)
        except:
            return None
    return None

@st.cache_data(ttl=300, show_spinner=False)
def fetch_data():
    """جلب البيانات من Google Sheets"""
    client = get_gspread_client()
    if not client:
        return "ERROR: No Google Client Authorized"
    try:
        sheet_url = "https://docs.google.com/spreadsheets/d/1u87sScIve_-xT_jDG56EKFMXegzAxOqwVJCh3Irerrw/edit"
        sheet = client.open_by_url(sheet_url).get_worksheet(0)
        return sheet.get_all_values()
    except Exception as e:
        return f"ERROR: {str(e)}"

# ============================================
# CONTRACT STATUS CALCULATION LAYER
# ============================================

def calculate_contract_status(expiry_date_str):
    """
    حساب حالة العقد بناءً على تاريخ الانتهاء
    Returns: dict with status info
    """
    today = date.today()
    
    if not expiry_date_str:
        return {
            'days': None,
            'status': 'unknown',
            'status_text_ar': 'غير معروف',
            'status_text_en': 'Unknown',
            'sort_key': 999999,
            'category': 'unknown'
        }
    
    try:
        expiry = safe_parse_date(expiry_date_str)
        if not expiry:
            return {
                'days': None,
                'status': 'invalid',
                'status_text_ar': 'تاريخ غير صالح',
                'status_text_en': 'Invalid Date',
                'sort_key': 999999,
                'category': 'unknown'
            }
        
        diff = (expiry - today).days
        
        if diff < 0:
            # منتهي
            return {
                'days': diff,
                'status': 'expired',
                'status_text_ar': f'منتهي منذ {abs(diff)} يوم',
                'status_text_en': f'Expired {abs(diff)} days ago',
                'sort_key': diff,
                'category': 'expired'
            }
        elif diff == 0:
            # ينتهي اليوم
            return {
                'days': diff,
                'status': 'urgent',
                'status_text_ar': 'ينتهي اليوم',
                'status_text_en': 'Expires today',
                'sort_key': diff,
                'category': 'urgent'
            }
        elif diff <= 7:
            # وشيك (7 أيام أو أقل)
            return {
                'days': diff,
                'status': 'urgent',
                'status_text_ar': f'متبقي {diff} يوم',
                'status_text_en': f'{diff} days remaining',
                'sort_key': diff,
                'category': 'urgent'
            }
        elif diff <= 30:
            # تحذير (أقل من شهر)
            return {
                'days': diff,
                'status': 'warning',
                'status_text_ar': f'متبقي {diff} يوم',
                'status_text_en': f'{diff} days remaining',
                'sort_key': diff,
                'category': 'active'
            }
        else:
            # ساري
            return {
                'days': diff,
                'status': 'active',
                'status_text_ar': f'متبقي {diff} يوم',
                'status_text_en': f'{diff} days remaining',
                'sort_key': diff,
                'category': 'active'
            }
            
    except Exception as e:
        return {
            'days': None,
            'status': 'error',
            'status_text_ar': 'خطأ',
            'status_text_en': 'Error',
            'sort_key': 999999,
            'category': 'unknown'
        }

# ============================================
# SEARCH LAYER - Smart Search with Phone Support
# ============================================

def smart_search_filter(row_series, query_str):
    """
    فلتر البحث الذكي - يدعم البحث بالنص والأرقام بدقة
    """
    if not query_str:
        return True
    
    query_clean = str(query_str).strip().lower()
    query_digits = extract_phone_digits_for_search(query_str)
    
    # التحقق إذا كان البحث برقم هاتف
    is_phone_search = is_phone_number(query_str)
    
    # البحث في جميع الأعمدة
    for col_name, val in row_series.items():
        col_lower = str(col_name).lower()
        cell_str = str(val).lower()
        
        # البحث في أعمدة الهاتف
        if any(kw in col_lower for kw in ["phone", "هاتف", "جوال", "mobile", "tel", "رقم"]):
            cell_digits = extract_phone_digits_for_search(str(val))
            
            if is_phone_search and cell_digits:
                # مقارنة دقيقة للأرقام
                # نبحث إذا كان الرقم المدخل يطابق أو يحتوي على الرقم المخزن
                if query_digits == cell_digits:
                    return True
                if len(query_digits) >= 7 and len(cell_digits) >= 7:
                    # نأخذ آخر 7 أرقام للمقارنة
                    if query_digits[-7:] == cell_digits[-7:]:
                        return True
        
        # البحث النصي العادي
        if query_clean in cell_str:
            return True
    
    return False

# ============================================
# TRANSLATION LAYER
# ============================================

def translate_columns(df, lang='ar'):
    """ترجمة أسماء الأعمدة"""
    col_mapping = {
        "Timestamp": {"ar": "طابع زمني", "en": "Timestamp"},
        "Full Name": {"ar": "الاسم الكامل", "en": "Full Name"},
        "Nationality": {"ar": "الجنسية", "en": "Nationality"},
        "Gender": {"ar": "الجنس", "en": "Gender"},
        "Phone Number": {"ar": "رقم الهاتف", "en": "Phone Number"},
        "Is your contract expired": {"ar": "هل انتهى العقد؟", "en": "Contract Expired?"},
        "When is your contract end date?": {"ar": "تاريخ انتهاء العقد", "en": "Contract End Date"},
        "your age": {"ar": "العمر", "en": "Age"},
        "Are you working now?": {"ar": "هل تعمل حالياً؟", "en": "Currently Working?"},
        "Do you have a valid residency?": {"ar": "هل لديك إقامة؟", "en": "Valid Residency?"},
        "Do you have a valid driving license?": {"ar": "رخصة قيادة؟", "en": "Driving License?"},
        "Will your employer transfer your sponsorship?": {"ar": "هل يتنازل الكفيل؟", "en": "Transferable?"},
        "Are you in Saudi Arabia?": {"ar": "في السعودية؟", "en": "In Saudi?"},
        "Which city do you live in?": {"ar": "المدينة", "en": "City"},
        "How did you hear about us?": {"ar": "كيف سمعت عنا؟", "en": "Source"},
        "Do you speak Arabic?": {"ar": "يتحدث العربية؟", "en": "Speak Arabic?"},
        "Which job are you applying for?": {"ar": "الوظيفة", "en": "Job"},
        "How much experience do you have?": {"ar": "الخبرة", "en": "Experience"},
        "Are you ready to work immediately?": {"ar": "جاهز للعمل؟", "en": "Ready?"},
        "Are you married?": {"ar": "الحالة الاجتماعية", "en": "Marital Status"},
        "Iqama ID Number": {"ar": "رقم الإقامة", "en": "Iqama ID"},
        "Your Iqama Expiry Date": {"ar": "صلاحية الإقامة", "en": "Iqama Expiry"},
        "Download CV": {"ar": "السيرة الذاتية", "en": "CV"},
    }
    
    new_names = {}
    for c in df.columns:
        c_clean = c.strip()
        found = False
        for k, v in col_mapping.items():
            if k.lower() in c_clean.lower():
                new_names[c] = v[lang]
                found = True
                break
        if not found:
            new_names[c] = c
    
    # Deduplicate
    final_names = {}
    seen = {}
    for c in df.columns:
        trans = new_names.get(c, c)
        if trans in seen:
            seen[trans] += 1
            final_names[c] = f"{trans} ({seen[trans]})"
        else:
            seen[trans] = 1
            final_names[c] = trans
    
    return df.rename(columns=final_names)

# ============================================
# UI COMPONENTS
# ============================================

def render_welcome_message():
    """عرض رسالة الترحيب"""
    lang = st.session_state.get('lang', 'ar')
    name_ar = st.session_state.get("current_user_name_ar", "")
    name_en = st.session_state.get("current_user_name_en", "")
    
    if lang == 'ar':
        display_name = name_ar if name_ar else st.session_state.get("current_user", "")
        st.markdown(f"""
        <div class="welcome-container" dir="rtl">
            <div class="welcome-msg">أهلاً بعودتك، {display_name}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        display_name = name_en if name_en else st.session_state.get("current_user", "")
        st.markdown(f"""
        <div class="welcome-container" dir="ltr">
            <div class="welcome-msg">Welcome back, {display_name}</div>
        </div>
        """, unsafe_allow_html=True)

def render_neon_signature():
    """التوقيع النيوني"""
    st.markdown('<div class="neon-signature">Al-Saeed Al-Wazzan Programming</div>', unsafe_allow_html=True)

def render_stats_cards(urgent_count, expired_count, active_count, total_count):
    """عرض بطاقات الإحصائيات"""
    st.markdown(f"""
    <div class="stats-container">
        <div class="stat-card">
            <div class="stat-number" style="color: #dc3545;">{urgent_count}</div>
            <div class="stat-label">{'وشيكة' if st.session_state.lang == 'ar' else 'Urgent'}</div>
        </div>
        <div class="stat-card">
            <div class="stat-number" style="color: #6c757d;">{expired_count}</div>
            <div class="stat-label">{'منتهية' if st.session_state.lang == 'ar' else 'Expired'}</div>
        </div>
        <div class="stat-card">
            <div class="stat-number" style="color: #28a745;">{active_count}</div>
            <div class="stat-label">{'سارية' if st.session_state.lang == 'ar' else 'Active'}</div>
        </div>
        <div class="stat-card">
            <div class="stat-number" style="color: #ffd700;">{total_count}</div>
            <div class="stat-label">{'الكل' if st.session_state.lang == 'ar' else 'Total'}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_table_with_scroll(df, table_id, row_key_func=None, on_delete=None):
    """
    عرض جدول مع شريط تمرير داخلي
    """
    if df.empty:
        st.info("لا توجد بيانات" if st.session_state.lang == 'ar' else "No data")
        return None
    
    # تحديد ألوان الصفوف
    def get_row_class(row):
        if 'status' in row:
            status = row['status']
            if status == 'urgent':
                return 'row-urgent'
            elif status == 'expired':
                return 'row-expired'
            elif status == 'warning':
                return 'row-warning'
            elif status == 'active':
                return 'row-active'
        return ''
    
    # بناء HTML للجدول
    html = f'<div class="table-container" id="{table_id}">'
    html += '<table class="custom-table">'
    
    # Header
    html += '<thead><tr>'
    for col in df.columns:
        if col not in ['_key', '_original_index', 'status']:
            html += f'<th>{col}</th>'
    if on_delete:
        html += '<th>🗑️</th>'
    html += '</tr></thead>'
    
    # Body
    html += '<tbody>'
    for idx, row in df.iterrows():
        row_class = get_row_class(row)
        html += f'<tr class="{row_class}">'
        
        for col in df.columns:
            if col not in ['_key', '_original_index', 'status']:
                val = row[col]
                # تنسيق أرقام الهواتف للعرض
                if any(kw in str(col).lower() for kw in ['phone', 'هاتف', 'جوال', 'mobile']):
                    val = format_phone_for_display(str(val))
                html += f'<td>{val}</td>'
        
        if on_delete:
            row_key = row_key_func(row) if row_key_func else str(idx)
            html += f'<td><button class="delete-btn" onclick="window.deleteRow(\'{row_key}\')">🗑️</button></td>'
        
        html += '</tr>'
    html += '</tbody></table></div>'
    
    st.markdown(html, unsafe_allow_html=True)
    
    # زر الحذف باستخدام Streamlit
    if on_delete:
        for idx, row in df.iterrows():
            col1, col2 = st.columns([10, 1])
            with col2:
                row_key = row_key_func(row) if row_key_func else str(idx)
                if st.button("🗑️", key=f"del_{table_id}_{idx}"):
                    return row_key
    
    return None

# ============================================
# SESSION STATE INITIALIZATION
# ============================================

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = ""
if 'page' not in st.session_state:
    st.session_state.page = "home"
if 'lang' not in st.session_state:
    st.session_state.lang = 'ar'
if 'deleted_rows' not in st.session_state:
    st.session_state.deleted_rows = load_deleted_rows()
if 'show_delete_confirm' not in st.session_state:
    st.session_state.show_delete_confirm = False
if 'delete_target_key' not in st.session_state:
    st.session_state.delete_target_key = None

# ============================================
# SIDEBAR
# ============================================

def sidebar_content():
    with st.sidebar:
        # Language Switch
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🇦🇪 عربي", use_container_width=True, 
                        type="primary" if st.session_state.lang == 'ar' else "secondary"):
                st.session_state.lang = 'ar'
                st.rerun()
        with col2:
            if st.button("🇺🇸 English", use_container_width=True,
                        type="primary" if st.session_state.lang == 'en' else "secondary"):
                st.session_state.lang = 'en'
                st.rerun()
        
        st.markdown("---")
        
        # Logo
        st.markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <div style="font-size: 3rem;">📝</div>
            <div style="color: #d4af37; font-weight: bold;">Contract Monitor</div>
            <div style="color: #888; font-size: 0.8rem;">Al-Saeed Al-Wazzan</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Navigation
        nav_items = [
            ("🏠", "الرئيسية" if st.session_state.lang == 'ar' else "Home", "home"),
            ("🔍", "البحث" if st.session_state.lang == 'ar' else "Search", "search"),
            ("🔑", "الصلاحيات" if st.session_state.lang == 'ar' else "Permissions", "permissions"),
        ]
        
        for icon, label, page in nav_items:
            btn_type = "primary" if st.session_state.page == page else "secondary"
            if st.button(f"{icon} {label}", use_container_width=True, type=btn_type):
                st.session_state.page = page
                st.rerun()
        
        st.markdown("---")
        
        # Refresh & Logout
        if st.button("🔄 تحديث البيانات" if st.session_state.lang == 'ar' else "🔄 Refresh", 
                    use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        if st.button("🚪 خروج" if st.session_state.lang == 'ar' else "🚪 Logout", 
                    use_container_width=True, type="secondary"):
            st.session_state.authenticated = False
            st.session_state.current_user = ""
            st.rerun()

# ============================================
# PAGE: LOGIN
# ============================================

def page_login():
    st.markdown("""
    <style>
    .login-container {
        max-width: 400px;
        margin: 50px auto;
        padding: 40px;
        background: linear-gradient(135deg, #1a252f, #2c3e50);
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.5);
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div class="login-container">
            <div style="font-size: 4rem; margin-bottom: 20px;">🔐</div>
            <h2 style="color: white; margin-bottom: 30px;">تسجيل الدخول</h2>
        </div>
        """, unsafe_allow_html=True)
        
        username = st.text_input("اسم المستخدم" if st.session_state.lang == 'ar' else "Username")
        password = st.text_input("كلمة المرور" if st.session_state.lang == 'ar' else "Password", 
                                type="password")
        
        if st.button("دخول" if st.session_state.lang == 'ar' else "Login", 
                    use_container_width=True, type="primary"):
            USERS = load_users()
            user_key = username.lower().strip()
            
            if user_key in USERS:
                hashed = hashlib.sha256(password.encode()).hexdigest()
                if USERS[user_key]["password"] == hashed:
                    st.session_state.authenticated = True
                    st.session_state.current_user = user_key
                    st.session_state.current_user_name_ar = USERS[user_key].get("full_name_ar", user_key)
                    st.session_state.current_user_name_en = USERS[user_key].get("full_name_en", user_key)
                    st.session_state.page = "home"
                    st.rerun()
                else:
                    st.error("كلمة المرور خاطئة" if st.session_state.lang == 'ar' else "Wrong password")
            else:
                st.error("المستخدم غير موجود" if st.session_state.lang == 'ar' else "User not found")

# ============================================
# PAGE: HOME - CONTRACT ALERTS
# ============================================

def page_home():
    render_welcome_message()
    render_neon_signature()
    
    st.markdown("---")
    
    # Fetch data
    with st.spinner("جاري تحميل البيانات..." if st.session_state.lang == 'ar' else "Loading..."):
        data_raw = fetch_data()
    
    if isinstance(data_raw, str) and "ERROR" in data_raw:
        st.error(f"❌ خطأ: {data_raw}")
        return
    
    if not data_raw or len(data_raw) < 2:
        st.info("لا توجد بيانات" if st.session_state.lang == 'ar' else "No data")
        return
    
    headers = deduplicate_columns(data_raw[0])
    df = pd.DataFrame(data_raw[1:], columns=headers)
    
    # Find contract end date column
    date_col = None
    for h in df.columns:
        if any(kw in h.lower() for kw in ["contract end", "expiry", "انتهاء", "تاريخ"]):
            date_col = h
            break
    
    if not date_col:
        st.error("عمود تاريخ الانتهاء غير موجود")
        return
    
    # Process contracts and categorize
    deleted_rows = st.session_state.deleted_rows
    contracts = []
    
    for idx, row in df.iterrows():
        # Generate unique key
        row_values = row.values.tolist()
        key_parts = [str(v) for v in row_values[:5]]
        row_key = "|".join(key_parts)
        
        # Skip deleted
        if row_key in deleted_rows:
            continue
        
        # Calculate status
        status_info = calculate_contract_status(row.get(date_col))
        
        contract = {
            '_key': row_key,
            '_original_index': idx,
            'status': status_info['status'],
            'days': status_info['days'],
            'status_text': status_info['status_text_ar'] if st.session_state.lang == 'ar' else status_info['status_text_en'],
            'category': status_info['category'],
            'sort_key': status_info['sort_key']
        }
        contract.update(row.to_dict())
        contracts.append(contract)
    
    # Categorize contracts
    urgent_contracts = [c for c in contracts if c['category'] == 'urgent']
    expired_contracts = [c for c in contracts if c['category'] == 'expired']
    active_contracts = [c for c in contracts if c['category'] == 'active']
    
    # Sort each category
    urgent_contracts.sort(key=lambda x: x['sort_key'])
    expired_contracts.sort(key=lambda x: x['sort_key'], reverse=True)  # Most expired first
    active_contracts.sort(key=lambda x: x['sort_key'])
    
    # Display stats
    render_stats_cards(
        len(urgent_contracts),
        len(expired_contracts),
        len(active_contracts),
        len(contracts)
    )
    
    # ============================================
    # TABLE 1: URGENT CONTRACTS (7 days or less)
    # ============================================
    if urgent_contracts:
        st.markdown(f"""
        <div class="section-header section-header-urgent">
            <h4 style="margin: 0; color: #ff6b7a;">
                🔴 {'العقود الوشيكة (7 أيام أو أقل)' if st.session_state.lang == 'ar' else 'Urgent Contracts (7 days or less)'}
                <span style="float: left; background: #dc3545; padding: 2px 10px; border-radius: 10px; font-size: 0.9rem;">
                    {len(urgent_contracts)}
                </span>
            </h4>
        </div>
        """, unsafe_allow_html=True)
        
        urgent_df = pd.DataFrame(urgent_contracts)
        display_cols = ['status_text'] + [c for c in urgent_df.columns if c not in ['_key', '_original_index', 'status', 'days', 'category', 'sort_key', 'status_text']]
        urgent_display = urgent_df[display_cols].copy()
        urgent_display = translate_columns(urgent_display, st.session_state.lang)
        
        # Render table
        render_contracts_table(urgent_display, urgent_contracts, "urgent")
    
    # ============================================
    # TABLE 2: EXPIRED CONTRACTS
    # ============================================
    if expired_contracts:
        st.markdown(f"""
        <div class="section-header section-header-expired">
            <h4 style="margin: 0; color: #adb5bd;">
                ⚫ {'العقود المنتهية' if st.session_state.lang == 'ar' else 'Expired Contracts'}
                <span style="float: left; background: #6c757d; padding: 2px 10px; border-radius: 10px; font-size: 0.9rem;">
                    {len(expired_contracts)}
                </span>
            </h4>
        </div>
        """, unsafe_allow_html=True)
        
        expired_df = pd.DataFrame(expired_contracts)
        display_cols = ['status_text'] + [c for c in expired_df.columns if c not in ['_key', '_original_index', 'status', 'days', 'category', 'sort_key', 'status_text']]
        expired_display = expired_df[display_cols].copy()
        expired_display = translate_columns(expired_display, st.session_state.lang)
        
        render_contracts_table(expired_display, expired_contracts, "expired")
    
    # ============================================
    # TABLE 3: ACTIVE CONTRACTS (more than 7 days)
    # ============================================
    if active_contracts:
        st.markdown(f"""
        <div class="section-header section-header-active">
            <h4 style="margin: 0; color: #69db7c;">
                🟢 {'العقود السارية (أكثر من أسبوع)' if st.session_state.lang == 'ar' else 'Active Contracts (more than a week)'}
                <span style="float: left; background: #28a745; padding: 2px 10px; border-radius: 10px; font-size: 0.9rem;">
                    {len(active_contracts)}
                </span>
            </h4>
        </div>
        """, unsafe_allow_html=True)
        
        active_df = pd.DataFrame(active_contracts)
        display_cols = ['status_text'] + [c for c in active_df.columns if c not in ['_key', '_original_index', 'status', 'days', 'category', 'sort_key', 'status_text']]
        active_display = active_df[display_cols].copy()
        active_display = translate_columns(active_display, st.session_state.lang)
        
        render_contracts_table(active_display, active_contracts, "active")

def render_contracts_table(display_df, contracts_data, table_type):
    """عرض جدول العقود مع أزرار الحذف"""
    
    # Create scrollable table
    st.markdown('<div style="max-height: 400px; overflow-y: auto; border-radius: 12px; border: 1px solid #30363d;">', unsafe_allow_html=True)
    
    # Use st.dataframe with configuration
    st.dataframe(
        display_df,
        use_container_width=True,
        height=350,
        column_config={
            col: st.column_config.Column(
                col,
                width="medium",
                help=col
            ) for col in display_df.columns
        }
    )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Delete functionality
    st.markdown("---")
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Select for deletion
        name_col = [c for c in display_df.columns if "اسم" in c or "Name" in c]
        if name_col:
            names = display_df[name_col[0]].tolist()
            selected = st.selectbox(
                "اختر للحذف:" if st.session_state.lang == 'ar' else "Select to delete:",
                [""] + names,
                key=f"select_{table_type}"
            )
    
    with col2:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        if selected:
            if st.button("🗑️ حذف" if st.session_state.lang == 'ar' else "🗑️ Delete", 
                        type="primary", key=f"del_btn_{table_type}"):
                # Find the key
                for c in contracts_data:
                    if c.get(name_col[0]) == selected or c.get('Full Name') == selected:
                        st.session_state.delete_target_key = c['_key']
                        st.session_state.show_delete_confirm = True
                        st.rerun()
    
    # Confirmation dialog
    if st.session_state.show_delete_confirm and st.session_state.delete_target_key:
        st.warning("⚠️ هل أنت متأكد من الحذف النهائي؟" if st.session_state.lang == 'ar' else "⚠️ Confirm permanent deletion?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ نعم" if st.session_state.lang == 'ar' else "✅ Yes", key="confirm_yes"):
                st.session_state.deleted_rows.add(st.session_state.delete_target_key)
                save_deleted_rows(st.session_state.deleted_rows)
                st.session_state.show_delete_confirm = False
                st.session_state.delete_target_key = None
                st.success("تم الحذف بنجاح!" if st.session_state.lang == 'ar' else "Deleted successfully!")
                time.sleep(1)
                st.rerun()
        with c2:
            if st.button("❌ إلغاء" if st.session_state.lang == 'ar' else "❌ Cancel", key="confirm_no"):
                st.session_state.show_delete_confirm = False
                st.session_state.delete_target_key = None
                st.rerun()

# ============================================
# PAGE: SEARCH
# ============================================

def page_search():
    render_welcome_message()
    render_neon_signature()
    
    st.markdown("---")
    
    # Search input
    search_query = st.text_input(
        "🔍 " + ("البحث الشامل" if st.session_state.lang == 'ar' else "Global Search"),
        placeholder="+966 57 320 8334 أو الاسم أو الجنسية..." if st.session_state.lang == 'ar' else "+966 57 320 8334 or name, nationality...",
        key="search_input"
    )
    
    st.markdown('<p class="search-hint">💡 يمكنك البحث برقم الهاتف بأي تنسيق: +966 57 320 8334، 0573208334، 573208334</p>' if st.session_state.lang == 'ar' else 
                '<p class="search-hint">💡 Search by phone in any format: +966 57 320 8334, 0573208334, 573208334</p>', 
                unsafe_allow_html=True)
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        use_age = st.checkbox("تصفية بالعمر" if st.session_state.lang == 'ar' else "Filter by Age")
        if use_age:
            age_from = st.number_input("من", 18, 80, 18)
            age_to = st.number_input("إلى", 18, 80, 60)
    
    with col2:
        use_expiry = st.checkbox("تصفية بتاريخ الانتهاء" if st.session_state.lang == 'ar' else "Filter by Expiry")
        if use_expiry:
            exp_from = st.date_input("من", date.today())
            exp_to = st.date_input("إلى", date.today() + timedelta(days=30))
    
    with col3:
        pass
    
    # Search button
    if st.button("بحث" if st.session_state.lang == 'ar' else "Search", type="primary", use_container_width=True):
        with st.spinner("جاري البحث..." if st.session_state.lang == 'ar' else "Searching..."):
            # Fetch data
            data_raw = fetch_data()
            
            if isinstance(data_raw, str) and "ERROR" in data_raw:
                st.error(f"❌ خطأ: {data_raw}")
                return
            
            headers = deduplicate_columns(data_raw[0])
            df = pd.DataFrame(data_raw[1:], columns=headers)
            
            # Filter deleted
            deleted_rows = st.session_state.deleted_rows
            df_filtered = df[~df.apply(lambda row: "|".join([str(v) for v in row.values[:5]]) in deleted_rows, axis=1)]
            
            # Apply search
            if search_query:
                # Check if phone search
                if is_phone_number(search_query):
                    search_digits = extract_phone_digits_for_search(search_query)
                    st.info(f"🔍 {'يبحث برقم الهاتف:' if st.session_state.lang == 'ar' else 'Searching by phone:'} {search_digits}")
                
                mask = df_filtered.apply(lambda row: smart_search_filter(row, search_query), axis=1)
                results = df_filtered[mask]
            else:
                results = df_filtered
            
            # Display results
            st.markdown(f"### 🔍 {'النتائج' if st.session_state.lang == 'ar' else 'Results'}: {len(results)}")
            
            if len(results) > 0:
                results_display = translate_columns(results, st.session_state.lang)
                st.dataframe(results_display, use_container_width=True, height=400)
                
                # Delete functionality for search results
                st.markdown("---")
                name_cols = [c for c in results_display.columns if "اسم" in c or "Name" in c]
                if name_cols:
                    names = results_display[name_cols[0]].tolist()
                    selected = st.selectbox(
                        "اختر للحذف:" if st.session_state.lang == 'ar' else "Select to delete:",
                        [""] + names,
                        key="search_delete_select"
                    )
                    
                    if selected and st.button("🗑️ حذف نهائي" if st.session_state.lang == 'ar' else "🗑️ Permanently Delete", 
                                             type="primary"):
                        # Find and delete
                        for idx, row in results.iterrows():
                            if row.get(name_cols[0]) == selected or row.get('Full Name') == selected:
                                row_key = "|".join([str(v) for v in row.values[:5]])
                                st.session_state.deleted_rows.add(row_key)
                                save_deleted_rows(st.session_state.deleted_rows)
                                st.success("تم الحذف!")
                                time.sleep(1)
                                st.rerun()
            else:
                st.info("لا توجد نتائج مطابقة" if st.session_state.lang == 'ar' else "No matching results")

# ============================================
# PAGE: PERMISSIONS
# ============================================

def page_permissions():
    st.markdown("## 🔑 " + ("إدارة الصلاحيات" if st.session_state.lang == 'ar' else "Permissions Management"))
    
    USERS = load_users()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### ➕ " + ("إضافة مستخدم" if st.session_state.lang == 'ar' else "Add User"))
        new_user = st.text_input("اسم المستخدم" if st.session_state.lang == 'ar' else "Username", key="new_user")
        new_pass = st.text_input("كلمة المرور" if st.session_state.lang == 'ar' else "Password", type="password", key="new_pass")
        new_name_ar = st.text_input("الاسم بالعربي" if st.session_state.lang == 'ar' else "Name (AR)", key="new_name_ar")
        new_name_en = st.text_input("الاسم بالإنجليزي" if st.session_state.lang == 'ar' else "Name (EN)", key="new_name_en")
        can_manage = st.checkbox("صلاحية الإدارة" if st.session_state.lang == 'ar' else "Management Permission", key="can_manage")
        
        if st.button("إضافة" if st.session_state.lang == 'ar' else "Add", use_container_width=True):
            if new_user and new_pass:
                if new_user.lower() not in USERS:
                    USERS[new_user.lower()] = {
                        "password": hashlib.sha256(new_pass.encode()).hexdigest(),
                        "full_name_ar": new_name_ar or new_user,
                        "full_name_en": new_name_en or new_user,
                        "can_manage_users": can_manage
                    }
                    save_users(USERS)
                    st.success("تم الإضافة!" if st.session_state.lang == 'ar' else "Added!")
                    st.rerun()
                else:
                    st.error("المستخدم موجود" if st.session_state.lang == 'ar' else "User exists")
    
    with col2:
        st.markdown("### 👥 " + ("المستخدمون" if st.session_state.lang == 'ar' else "Users"))
        for username, data in USERS.items():
            with st.expander(f"{data.get('full_name_ar', username)}"):
                st.write(f"**Username:** {username}")
                st.write(f"**Name (EN):** {data.get('full_name_en', '-')}")
                st.write(f"**Admin:** {'✅' if data.get('can_manage_users') else '❌'}")
                
                if username != "admin" and st.button("🗑️ حذف", key=f"del_user_{username}"):
                    del USERS[username]
                    save_users(USERS)
                    st.rerun()

# ============================================
# MAIN ROUTING
# ============================================

def main():
    if not st.session_state.authenticated:
        page_login()
    else:
        sidebar_content()
        
        if st.session_state.page == "home":
            page_home()
        elif st.session_state.page == "search":
            page_search()
        elif st.session_state.page == "permissions":
            page_permissions()

if __name__ == "__main__":
    main()

