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
            
        # 3. Save file with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        final_path = os.path.join(target_dir, f"{base_filename}_{timestamp}.xlsx")
        
        df.to_excel(final_path, index=False, engine='openpyxl')
        return final_path
    except Exception:
        return None

def is_local_windows_pc():
    """Checks if the app is likely running on a local Windows PC."""
    is_windows = os.name == 'nt'
    # Streamlit Cloud usually mounts code in /mount/
    is_cloud = "/mount/" in __file__.replace("\\", "/") 
    return is_windows and not is_cloud

def render_pasha_export_button(df, label, filename, base_save_name, key=None):
    """
    Renders either a Desktop Save button (for local PC) or a Download button (for others).
    This prevents duplicate downloads in the 'Downloads' folder on PC.
    """
    if is_local_windows_pc():
        if st.button(label, key=key, use_container_width=True):
            path = save_to_local_desktop(df, base_save_name)
            if path:
                st.success(f"✅ تم الحفظ في سطح المكتب: {os.path.basename(path)}")
                st.toast(f"تم الحفظ في مجلد المرشحين", icon='📁')
            else:
                st.error("❌ فشل الحفظ في سطح المكتب")
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
    Includes all requested fields for full data context.
    (Pure data generation, no side effects)
    """
    if df.empty:
        return None
    
    # Mapping for all requested fields
    mapping = {
        "الاسم": ["الاسم الكامل", "full name", "worker name", "الاسم", "name"],
        "رقم الجوال": ["رقم الهاتف", "whatsapp", "phone", "mobile", "جوال"],
        "السيرة الذاتية": ["سيرة الذاتية", "cv", "resume", "link", "سيرة"],
        "الجنسيه": ["الجنسيه", "nationality", "country"],
        "الجنس": ["الجنس", "gender", "sex"],
        "العمر": ["العمر", "age"],
        "المدينة": ["المدينة", "city", "location"],
        "الوظيفه المطلوبه": ["الوظيفه المطلوبه", "job", "position", "role", "المهنة"],
        "الخبرة في هذا المجال": ["الخبرة في هذا المجال", "field experience"],
        "مهارات اخرى": ["مهارات اخرى", "other skills", "skills"],
        "الخبرة": ["الخبرة", "experience", "years"],
        "هل يمكنك العمل خارج المدينة": ["العمل خارج المدينة", "work outside city", "travel"],
        "هل انت جاهز للعمل فورا": ["جاهز للعمل", "ready for work", "immediately"],
        "هل معك عائلته": ["مع عائلته", "with family"],
        "رقم الاقامة": ["رقم الاقامة", "iqama", "residency"],
        "عدد مرات نقل الكفالة": ["نقل الكفالة", "transfer count"]
    }

    def find_actual_col(keywords):
        for col in df.columns:
            c_lower = str(col).lower()
            if any(kw.lower() in c_lower for kw in keywords):
                return col
        return None

    # Identify actual columns from the dataframe
    actual_cols_map = {}
    for standard_name, keywords in mapping.items():
        found = find_actual_col(keywords)
        if found:
            actual_cols_map[standard_name] = found

    export_data = []
    # Identify the key columns for essential logic
    phone_col = actual_cols_map.get("رقم الجوال")
    
    for _, row in df.iterrows():
        raw_phone = str(row[phone_col]).strip() if phone_col else ""
        clean_phone = format_phone_number(raw_phone)
        if not clean_phone:
            clean_phone = format_phone_number("".join(raw_phone.split()))
            
        if clean_phone:
            entry = {}
            for standard_name, actual_col in actual_cols_map.items():
                val = str(row[actual_col]).strip() if actual_col in row else ""
                if standard_name == "رقم الجوال":
                    entry[standard_name] = clean_phone
                else:
                    entry[standard_name] = val
            
            
            # Ensure at least Name and Phone exist even if mapping failed for some
            if "رقم الجوال" not in entry: entry["رقم الجوال"] = clean_phone
            if "الاسم" not in entry: 
                name_col = actual_cols_map.get("الاسم")
                entry["الاسم"] = str(row[name_col]).strip() if name_col else "عميل"
                
            export_data.append(entry)
            
    export_df = pd.DataFrame(export_data)
    
    if export_df.empty:
        return None
        
    # Generate Excel buffer
    towrite = io.BytesIO()
    export_df.to_excel(towrite, index=False, engine='openpyxl')
    towrite.seek(0)
    return towrite, export_df
