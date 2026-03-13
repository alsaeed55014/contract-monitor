import re
import pandas as pd
import io
import os
import streamlit as st
from datetime import datetime

def format_phone_number(phone):
    """
    Pasha's Global Smart Formatter - Asian & African Edition.
    Automatically detects country by local prefix.
    """
    if not phone:
        return None
    
    # 1. Clean characters: Keep ONLY digits. (Handle leading plus separately)
    has_leading_plus = str(phone).strip().startswith('+')
    clean = re.sub(r'[^\d]', '', str(phone))
    
    if not clean: return None
    
    # 2. Re-attach plus if it was there or handle 00
    if has_leading_plus:
        s = clean
        return '+' + s if len(s) > 8 else None
    if str(phone).strip().startswith('00'):
        s = clean
        return '+' + s if len(s) > 8 else None
    
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

def save_to_local_desktop(df, base_filename="المرشحين"):
    """
    Attempts to save a copy of the Excel file to the Windows Desktop.
    Only works if the script is running with access to the local filesystem.
    """
    try:
        # 1. Identify Desktop Path
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        if not os.path.exists(desktop):
            # Fallback for different Windows versions/languages
            desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
        
        # 2. Create Target Folder
        folder_name = "المرشحين للوظائف"
        target_dir = os.path.join(desktop, folder_name)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        
        # 3. Save File
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        filename = f"{base_filename}_{timestamp}.xlsx"
        filepath = os.path.join(target_dir, filename)
        
        df.to_excel(filepath, index=False)
        return filepath
    except Exception as e:
        print(f"Error saving to desktop: {e}")
        return None

def is_local_windows_pc():
    """Detects if we're on a local Windows machine vs Cloud."""
    is_windows = os.name == 'nt'
    # Streamlit Cloud usually mounts code in /mount/
    is_cloud = "/mount/" in __file__.replace("\\", "/") 
    return is_windows and not is_cloud

def normalize_ar(text):
    if not text or not isinstance(text, str): return ""
    text = text.strip()
    # Basic Arabic normalization
    text = re.sub(r'[أإآا]', 'ا', text)
    text = re.sub(r'ة', 'ه', text)
    text = re.sub(r'ى', 'ي', text)
    return text.lower()

def mask_phone(phone_str):
    """Masks entire phone number for viewers with stars (**********)."""
    p = str(phone_str).strip()
    if p == '---' or not p: return '---'
    # Replace all digits and characters with stars
    return "*" * len(p)

def render_pasha_export_button(df, label, filename, base_save_name, key=None):
    """
    Renders either a Desktop Save button (for local PC) or a Download button (for others).
    This prevents duplicate downloads in the 'Downloads' folder on PC.
    """
    st.markdown('<div class="whatsapp-export-btn">', unsafe_allow_html=True)
    if is_local_windows_pc():
        def do_save():
            path = save_to_local_desktop(df, base_save_name)
            if path:
                st.toast(f"تم الحفظ في مجلد المرشحين", icon='📁')
        
        if st.button(label, key=key, use_container_width=True, on_click=do_save):
            st.success("✅ " + ("تم الحفظ بنجاح" if st.session_state.get('lang') == 'ar' else "Saved Successfully"))

    else:
        # Fallback to standard download for mobile/cloud
        towrite = io.BytesIO()
        df.to_excel(towrite, index=False, engine='openpyxl')
        towrite.seek(0)
        st.download_button(
            label=label,
            data=towrite.getvalue(),
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=key,
            use_container_width=True
        )
    st.markdown('</div>', unsafe_allow_html=True)

def create_pasha_whatsapp_excel(df, lang='ar'):
    """
    Creates a specialized Excel for Pasha's WhatsApp Broadcast.
    Includes all requested fields for full data context.
    (Pure data generation, no side effects)
    """
    if df.empty:
        return None
    
    # 2026 Premium Localization Update
    is_ar = lang == 'ar'
    iqama_header = "رقم الإقامة" if is_ar else "Iqama ID number"
    name_header = "الاسم" if is_ar else "Candidate Name"
    phone_header = "رقم الجوال" if is_ar else "Mobile Number"
    cv_header = "السيرة الذاتية" if is_ar else "CV / Resume"
    nat_header = "الجنسيه" if is_ar else "Nationality"
    gender_header = "الجنس" if is_ar else "Gender"
    age_header = "العمر" if is_ar else "Age"
    city_header = "المدينة" if is_ar else "City"
    job_header = "الوظيفه المطلوبه" if is_ar else "Requested Job"
    field_exp_header = "الخبرة في هذا المجال" if is_ar else "Field Experience"
    skills_header = "مهارات اخرى" if is_ar else "Other Skills"
    outside_header = "هل يمكنك العمل خارج المدينة" if is_ar else "Work Outside City"
    ready_header = "هل انت جاهز للعمل فورا" if is_ar else "Ready Immediately"
    family_header = "هل معك عائلته" if is_ar else "With Family"
    transfer_header = "عدد مرات نقل الكفالة" if is_ar else "Transfer Count"
    other_jobs_header = "ما هي الوظائف الأخرى التي يمكنك القيام بها" if is_ar else "What other jobs can you do"
    
    # Mapping for all requested fields
    mapping = {
        name_header: ["الاسم الكامل", "full name", "worker name", "الاسم", "name", "candidate name"],
        phone_header: ["رقم الهاتف", "whatsapp", "phone", "mobile", "جوال", "mobile number"],
        cv_header: ["سيرة الذاتية", "cv", "resume", "link", "سيرة", "resume link"],
        nat_header: ["الجنسيه", "nationality", "country"],
        gender_header: ["الجنس", "gender", "sex"],
        age_header: ["العمر", "age"],
        city_header: ["المدينة", "city", "location"],
        job_header: ["الوظيفه المطلوبه", "job", "position", "role", "المهنة", "requested job"],
        field_exp_header: ["الخبرة في هذا المجال", "field experience"],
        skills_header: ["مهارات اخرى", "other skills", "skills"],
        outside_header: ["العمل خارج المدينة", "work outside city", "travel", "work outside city"],
        ready_header: ["جاهز للعمل", "ready for work", "immediately", "ready immediately"],
        family_header: ["مع عائلته", "with family"],
        iqama_header: ["رقم الاقامة", "رقم الإقامة", "iqama", "residency", "iqama id number", "iqama id"],
        transfer_header: ["نقل الكفالة", "transfer count"],
        other_jobs_header: [
            "وظائف أخرى", "وظائف اخرى", "الوظائف الأخرى", "الوظائف الاخرى", "other jobs", "other job",
            "ما هي الوظائف الأخرى التي يمكنك القيام بها", "ما هي الوظائف", "ماهي الوظائف", "وظايف اخرى",
            "what other jobs can you do"
        ]
    }

    def find_actual_col(keywords):
        for c in df.columns:
            if any(k in str(c).lower() for k in keywords):
                return c
        return None

    actual_cols_map = {}
    for standard_name, keywords in mapping.items():
        found = find_actual_col(keywords)
        if found:
            actual_cols_map[standard_name] = found

    export_data = []
    phone_col = actual_cols_map.get(phone_header)
    
    for _, row in df.iterrows():
        raw_phone = str(row[phone_col]).strip() if phone_col and phone_col in row else ""
        clean_phone = format_phone_number(raw_phone)
        if not clean_phone:
            clean_phone = format_phone_number("".join(raw_phone.split()))
            
        if clean_phone:
            entry = {}
            for k, v in row.items():
                if not str(k).startswith("__"):
                    val = str(v).strip() if pd.notna(v) else ""
                    if str(val).lower() == 'nan': val = ""
                    entry[k] = val
                    
            if phone_col:
                entry[phone_col] = clean_phone
            else:
                entry[phone_header] = clean_phone
                
            export_data.append(entry)
            
    export_df = pd.DataFrame(export_data)
    
    if export_df.empty:
        return None
        
    towrite = io.BytesIO()
    export_df.to_excel(towrite, index=False, engine='openpyxl')
    towrite.seek(0)
    return towrite, export_df

def validate_numbers(text):
    """
    Parses a block of text and extracts valid phone numbers.
    Returns (valid_list, invalid_count, total_count).
    """
    if not text:
        return [], 0, 0
    
    # Split by common delimiters: newline, comma, semicolon, space
    raw_entries = re.split(r'[\n,; ]+', str(text).strip())
    
    valid_numbers = []
    invalid_count = 0
    
    for entry in raw_entries:
        entry = entry.strip()
        if not entry: continue
        
        formatted = format_phone_number(entry)
        if formatted:
            valid_numbers.append(formatted)
        else:
            invalid_count += 1
            
    return valid_numbers, invalid_count, len(raw_entries)
