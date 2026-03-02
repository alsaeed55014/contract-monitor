import re
import pandas as pd
import io

def format_phone_number(phone):
    """
    Pasha's Global Smart Formatter - Asian & African Edition.
    Automatically detects country by local prefix.
    """
    if not phone:
        return None
    
    # 1. Clean all separators (spaces, dashes, etc.)
    clean = re.sub(r'[^\d+]', '', str(phone))
    
    # 2. If it has + or 00, it's already international
    if clean.startswith('+'):
        return clean if len(clean) > 8 else None
    if clean.startswith('00'):
        return '+' + clean[2:]
    
    s = clean
    
    # -- EGYPT (+20): Starts with 01 (11 digits)
    if s.startswith('01') and len(s) == 11:
        return f"+20{s[1:]}"

    # -- SAUDI ARABIA (+966): Starts with 05 (10 digits)
    if s.startswith('05') and len(s) == 10:
        return f"+966{s[1:]}"
    if s.startswith('5') and len(s) == 9:
        return f"+966{s}"

    # -- PAKISTAN (+92): Starts with 03 (11 digits)
    if s.startswith('03') and len(s) == 11:
        return f"+92{s[1:]}"

    # -- BANGLADESH (+880): Starts with 01 (11 digits)
    if s.startswith('01') and len(s) == 11:
        if s[2] in ['3', '4', '6', '7', '8', '9']:
            return f"+880{s[1:]}"
        return f"+20{s[1:]}"

    # -- INDIA (+91): 10 digits starting with 7, 8, 9
    if len(s) == 10 and s[0] in ['7', '8', '9']:
        return f"+91{s}"

    # -- NEPAL (+977): 10 digits starting with 98 or 97
    if len(s) == 10 and (s.startswith('98') or s.startswith('97')):
        return f"+977{s}"

    # -- PHILIPPINES (+63): Starts with 09 (11 digits)
    if s.startswith('09') and len(s) == 11:
        return f"+63{s[1:]}"

    # -- UAE (+971): Starts with 05 (10 digits)
    if s.startswith('05') and len(s) == 10:
        if s[2] in ['0', '2', '4', '5', '6', '8']:
            return f"+971{s[1:]}"
        return f"+966{s[1:]}"

    # -- JORDAN (+962): Starts with 07 (10 digits)
    if s.startswith('07') and len(s) == 10:
        return f"+962{s[1:]}"

    # -- KUWAIT (+965): 8 digits starting with 5, 6, 9
    if len(s) == 8 and s[0] in ['5', '6', '9']:
        return f"+965{s}"

    # 4. Final Fallback
    if len(s) >= 11:
        return f"+{s}"
    
    return None

def validate_numbers(raw_text):
    if not raw_text:
        return [], [], []

    parts = re.split(r'[,\n\r]+', raw_text)
    valid_all = []
    invalid = []
    seen = set()
    
    for p in parts:
        p = p.strip()
        if not p: continue
        
        formatted = format_phone_number(p)
        if not formatted:
            p_no_space = "".join(p.split())
            formatted = format_phone_number(p_no_space)
            
        if formatted:
            if formatted not in seen:
                valid_all.append(formatted)
                seen.add(formatted)
        else:
            invalid.append(p)
            
    return valid_all, [], invalid

def create_pasha_whatsapp_excel(df):
    """
    Creates a specialized Excel for Pasha's WhatsApp Broadcast.
    Columns: [Name, Phone, Resume Link]
    """
    if df.empty:
        return None
    
    # 1. Map columns to Pasha's requirements
    def find_col(keywords):
        for col in df.columns:
            if any(kw in str(col).lower() for kw in keywords):
                return col
        return None
    
    name_col = find_col(["الاسم الكامل", "полное имя", "full name", "worker name", "الاسم", "name"])
    phone_col = find_col(["رقم الهاتف", "номер телефона", "phone", "mobile", "جوال"])
    cv_col = find_col(["سيرة الذاتية", "резюме", "cv", "resume", "link", "سيرة"])
    
    # Default column names for the output file (Arabic for Pasha)
    OUT_NAME = "اسم العامل"
    OUT_PHONE = "رقم الواتساب"
    OUT_CV = "رابط السيرة الذاتية"
    
    export_data = []
    for _, row in df.iterrows():
        name = str(row[name_col]).strip() if name_col else "عميل"
        raw_phone = str(row[phone_col]).strip() if phone_col else ""
        cv = str(row[cv_col]).strip() if cv_col else ""
        
        # Clean the phone using Pasha's smart cleaning
        clean_phone = format_phone_number(raw_phone)
        if not clean_phone:
            # Try removing spaces manually for Excel
            clean_phone = format_phone_number("".join(raw_phone.split()))
            
        if clean_phone:
            export_data.append({
                OUT_NAME: name,
                OUT_PHONE: clean_phone,
                OUT_CV: cv
            })
            
    export_df = pd.DataFrame(export_data)
    
    if export_df.empty:
        return None
        
    # Generate Excel buffer
    towrite = io.BytesIO()
    export_df.to_excel(towrite, index=False, engine='openpyxl')
    towrite.seek(0)
    return towrite
