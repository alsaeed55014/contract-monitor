import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
from dateutil import parser
import os
import json

# Page Config
st.set_page_config(page_title="Contract Monitor | مراقب العقود", layout="wide", page_icon="📝")

# --- Language Selection ---
if 'lang' not in st.session_state:
    st.session_state.lang = 'ar'

lang_col1, lang_col2 = st.columns([8, 2])
with lang_col2:
    if st.button("English / العربية", use_container_width=True):
        st.session_state.lang = 'en' if st.session_state.lang == 'ar' else 'ar'
    # Small divider to separate from content
    st.divider()

L = {
    'en': {
        'title': "🛡️ Contract Monitoring System",
        'subtitle': "Developed by: Al-Saeed Al-Wazzan",
        'search_lbl': "🔍 Smart Search",
        'search_placeholder': "(Name, Job, Nationality, Phone...)",
        'results_lbl': "Results found",
        'alerts_lbl': "⚠️ Upcoming Contract Expiries",
        'days_left': "days left",
        'week_left': "1 week left",
        'status': "Status",
        'name': "Name",
        'phone': "Phone",
        'date': "Expiry Date",
        'type': "Alert Type",
        'danger': "Danger",
        'warning': "Warning",
        'success_msg': "No urgent alerts today.",
        'error_google': "Error connecting to Google Sheets",
        'info_creds': "Please ensure credentials.json is present and shared correctly.",
        'dir': 'ltr',
        'align': 'left'
    },
    'ar': {
        'title': "🛡️ نظام مراقبة العقود",
        'subtitle': "برمجة: السعيد الوزان",
        'search_lbl': "🔍 البحث الشامل",
        'search_placeholder': "(الاسم، الوظيفة، الجنسية، رقم الجوال...)",
        'results_lbl': "نتيجة تم العثور عليها",
        'alerts_lbl': "⚠️ تنبيهات العقود الوشيكة",
        'days_left': "يوم متبقي",
        'week_left': "أسبوع متبقي",
        'status': "الحالة",
        'name': "الاسم",
        'phone': "الجوال",
        'date': "تاريخ الانتهاء",
        'type': "نوع التنبيه",
        'danger': "خطير",
        'warning': "تحذير",
        'success_msg': "لا توجد تنبيهات عاجلة اليوم.",
        'error_google': "خطأ في الاتصال بجوجل شيت",
        'info_creds': "يرجى التأكد من ملف credentials.json وإعدادات المشاركة.",
        'dir': 'rtl',
        'align': 'right'
    }
}

lang = st.session_state.lang
texts = L[lang]

# Responsive & RTL Styling
st.markdown(f"""
    <style>
    .main {{ text-align: {texts['align']}; direction: {texts['dir']}; }}
    [data-testid="stSidebar"] {{ direction: {texts['dir']}; }}
    .stTextInput input {{ text-align: {texts['align']}; direction: {texts['dir']}; }}
    .stHeader {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
    /* Responsive Table Adjustments */
    [data-testid="stTable"] {{ overflow-x: auto; }}
    @media (max-width: 600px) {{
        .stTitle {{ font-size: 1.5rem !important; }}
        .stSubheader {{ font-size: 1rem !important; }}
    }}
    </style>
""", unsafe_allow_html=True)

# Google Sheets Initialization
def get_gspread_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        # Try Streamlit Secrets first (for cloud deployment)
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            return gspread.authorize(creds)
    except Exception:
        pass
    # Fall back to local credentials.json file (for local development)
    if os.path.exists('credentials.json'):
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
            return gspread.authorize(creds)
        except:
            return None
    return None

def fetch_data():
    client = get_gspread_client()
    if not client: return None
    try:
        sheet_url = "https://docs.google.com/spreadsheets/d/1u87sScIve_-xT_jDG56EKFMXegzAxOqwVJCh3Irerrw/edit"
        sheet = client.open_by_url(sheet_url).get_worksheet(0)
        return sheet.get_all_values()
    except Exception as e:
        st.error(f"{texts['error_google']}: {e}")
        return None

# Translation Helper
def translate_header(text, target_lang):
    m = {
        "full name": {"ar": "الاسم الكامل", "en": "Full Name"}, 
        "الاسم الكامل": {"ar": "الاسم الكامل", "en": "Full Name"}, 
        "nationality": {"ar": "الجنسية", "en": "Nationality"}, 
        "الجنسية": {"ar": "الجنسية", "en": "Nationality"}, 
        "gender": {"ar": "الجنس", "en": "Gender"}, 
        "الجنس": {"ar": "الجنس", "en": "Gender"}, 
        "phone number": {"ar": "رقم الجوال", "en": "Phone Number"},
        "رقم الجوال": {"ar": "رقم الجوال", "en": "Phone Number"}, 
        "when is your contract end date?": {"ar": "تاريخ انتهاء العقد", "en": "Contract End Date"}, 
        "تاريخ انتهاء العقد": {"ar": "تاريخ انتهاء العقد", "en": "Contract End Date"}, 
        "your age": {"ar": "العمر", "en": "Age"}, 
        "العمر": {"ar": "العمر", "en": "Age"}, 
        "timestamp": {"ar": "طابع زمني", "en": "Timestamp"},
        "طابع زمني": {"ar": "طابع زمني", "en": "Timestamp"}, 
        "are you work": {"ar": "هل تعمل حالياً؟", "en": "Currently Working?"},
        "هل تعمل حالياً": {"ar": "هل تعمل حالياً؟", "en": "Currently Working?"}, 
        "do you have a valid residency": {"ar": "هل لديك إقامة سارية؟", "en": "Valid Residency?"},
        "إقامة سارية": {"ar": "هل لديك إقامة سارية؟", "en": "Valid Residency?"}, 
        "do you have a valid driving": {"ar": "هل لديك رخصة قيادة؟", "en": "Driving License?"},
        "رخصة قيادة": {"ar": "هل لديك رخصة قيادة؟", "en": "Driving License?"}, 
        "if you are huroob": {"ar": "كم عدد الهروب", "en": "Huroob Count"},
        "عدد الهروب": {"ar": "كم عدد الهروب", "en": "Huroob Count"}, 
        "will your employer": {"ar": "هل الكفيل يتنازل؟", "en": "Employer Transferable?"},
        "الكفيل يتنازل": {"ar": "هل الكفيل يتنازل؟", "en": "Employer Transferable?"}, 
        "are you in saudi": {"ar": "هل أنت في السعودية؟", "en": "In Saudi?"},
        "أنت في السعودية": {"ar": "هل أنت في السعودية؟", "en": "In Saudi?"}, 
        "which city": {"ar": "المدينة / المنطقة", "en": "City"},
        "المدينة": {"ar": "المدينة / المنطقة", "en": "City"}, 
        "how did you hear": {"ar": "كيف سمعت عنا؟", "en": "How Hear About Us"},
        "كيف سمعت عنا": {"ar": "كيف سمعت عنا؟", "en": "How Hear About Us"}, 
        "what is the nam": {"ar": "اسم الكفيل / المنشأة", "en": "Employer Name"},
        "اسم الكفيل": {"ar": "اسم الكفيل / المنشأة", "en": "Employer Name"}, 
        "do you speak a": {"ar": "هل تتحدث العربية؟", "en": "Speak Arabic?"},
        "تتحدث العربية": {"ar": "هل تتحدث العربية؟", "en": "Speak Arabic?"}, 
        "which job are y": {"ar": "الوظيفة المطلوبة", "en": "Required Job"},
        "الوظيفة المطلوبة": {"ar": "الوظيفة المطلوبة", "en": "Required Job"}, 
        "what other jobs": {"ar": "وظائف أخرى تتقنها", "en": "Other Skills"},
        "وظائف أخرى": {"ar": "وظائف أخرى تتقنها", "en": "Other Skills"}, 
        "how much expe": {"ar": "الخبرة", "en": "Experience"},
        "الخبرة": {"ar": "الخبرة", "en": "Experience"}, 
        "do you have c": {"ar": "هل لديك كرت صحي؟", "en": "Health Card?"},
        "كرت صحي": {"ar": "هل لديك كرت صحي؟", "en": "Health Card?"}, 
        "is the card bala": {"ar": "صلاحية كرت البلدية", "en": "Municipality Card Expiry"},
        "كرت البلدية": {"ar": "صلاحية كرت البلدية", "en": "Municipality Card Expiry"}, 
        "how many mont": {"ar": "عدد الأشهر", "en": "Months Count"},
        "عدد الأشهر": {"ar": "عدد الأشهر", "en": "Months Count"}, 
        "can you work o": {"ar": "هل تعمل وقت إضافي؟", "en": "Overtime?"},
        "وقت إضافي": {"ar": "هل تعمل وقت إضافي؟", "en": "Overtime?"}, 
        "are you ready to": {"ar": "هل أنت جاهز للعمل؟", "en": "Ready to Work?"},
        "جاهز للعمل": {"ar": "هل أنت جاهز للعمل؟", "en": "Ready to Work?"}, 
        "are you married": {"ar": "الحالة الاجتماعية", "en": "Marital Status"},
        "الحالة الاجتماعية": {"ar": "الحالة الاجتماعية", "en": "Marital Status"}, 
        "iqama id numbe": {"ar": "رقم الإقامة", "en": "Iقama ID"},
        "رقم الإقامة": {"ar": "رقم الإقامة", "en": "Iقama ID"}, 
        "what is the occ": {"ar": "المهنة في الإقامة", "en": "Iqama Profession"},
        "المهنة في الإقامة": {"ar": "المهنة في الإقامة", "en": "Iqama Profession"}, 
        "your iqama vali": {"ar": "صلاحية الإقامة", "en": "Iqama Expiry"},
        "صلاحية الإقامة": {"ar": "صلاحية الإقامة", "en": "Iqama Expiry"}, 
        "how many times": {"ar": "عدد مرات التنازل", "en": "Transfer Times"},
        "مرات التنازل": {"ar": "عدد مرات التنازل", "en": "Transfer Times"}, 
        "download cv": {"ar": "تحميل السيرة الذاتية", "en": "Download CV"},
        "السيرة الذاتية": {"ar": "تحميل السيرة الذاتية", "en": "Download CV"}, 
        "is your contract": {"ar": "هل العقد ساري؟", "en": "Contract Valid?"},
        "العقد ساري": {"ar": "هل العقد ساري؟", "en": "Contract Valid?"}, 
        "do you have an": {"ar": "هل لديك أي التزامات مالية تجاه كفيلك السابق", "en": "Financial Commitments?"},
        "التزامات مالية": {"ar": "هل لديك أي التزامات مالية تجاه كفيلك السابق", "en": "Financial Commitments?"}, 
        "do you have to": {"ar": "هل يجب عليك الإبلاغ عن هروب", "en": "Must Report Huroob?"},
        "الإبلاغ عن هروب": {"ar": "هل يجب عليك الإبلاغ عن هروب", "en": "Must Report Huroob?"}
    }
    t = text.lower().strip().replace(':', '')
    for k, v in m.items():
        if k in t: return v[target_lang]
    return text

# App UI
st.title(texts['title'])
st.subheader(texts['subtitle'])

data_raw = fetch_data()

if data_raw:
    # Clean and translate headers, ensuring uniqueness
    headers_raw = data_raw[0]
    headers = []
    seen = {}
    for i, h in enumerate(headers_raw):
        h = h.strip()
        if not h:
            h = f"Column_{i+1}"
        
        trans = translate_header(h, lang)
        
        # Ensure uniqueness
        original_trans = trans
        count = 1
        while trans in seen:
            trans = f"{original_trans}.{count}"
            count += 1
        
        seen[trans] = True
        headers.append(trans)

    df = pd.DataFrame(data_raw[1:], columns=headers)
    
    # Simple Search
    search_query = st.text_input(texts['search_lbl'], placeholder=texts['search_placeholder'])
    
    if search_query:
        mask = df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)
        results = df[mask]
    else:
        results = df

    st.write(f"{len(results)} {texts['results_lbl']}")
    st.dataframe(results, use_container_width=True)

    # Alerts Logic
    st.divider()
    st.header(texts['alerts_lbl'])
    
    # Try to find date column in either language
    date_col = ""
    for h in df.columns:
        if any(kw in h.lower() for kw in ["تاريخ", "contract end", "expiry"]):
            date_col = h
            break
            
    if date_col:
        today = datetime.now().date()
        alerts = []
        for _, row in df.iterrows():
            try:
                dt = parser.parse(str(row[date_col])).date()
                days = (dt - today).days
                if days in [1, 2, 7]:
                    status = texts['danger'] if days <= 2 else texts['warning']
                    msg = f"{days} {texts['days_left']}" if days < 7 else texts['week_left']
                    alerts.append({
                        texts['name']: row.values[1] if len(row) > 1 else "---",
                        texts['status']: msg,
                        texts['date']: row[date_col],
                        texts['phone']: row.values[4] if len(row) > 4 else "---",
                        texts['type']: status
                    })
            except: pass
            
        if alerts:
            alert_df = pd.DataFrame(alerts)
            st.warning(texts['alerts_lbl'])
            st.table(alert_df)
        else:
            st.success(texts['success_msg'])

else:
    st.info(texts['info_creds'])
