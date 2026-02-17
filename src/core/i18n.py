TRANSLATIONS = {
    # ... (Login, Sidebar, etc. same as before) ...
    
    # Column Headers (Updated with User Requests)
    "columns": {
        "Name": {"ar": "الاسم", "en": "Name"},
        "Passport Number": {"ar": "رقم الجواز", "en": "Passport Number"},
        "Nationality": {"ar": "الجنسية", "en": "Nationality"},
        "Job": {"ar": "المهنة", "en": "Job"},
        "Sponsor Name": {"ar": "اسم الكفيل", "en": "Sponsor Name"},
        "Mobile": {"ar": "رقم الجوال", "en": "Mobile"},
        "Contract Duration": {"ar": "مدة العقد", "en": "Contract Duration"},
        "Contract End Date": {"ar": "تاريخ انتهاء العقد", "en": "Contract End Date"},
        "Status": {"ar": "الحالة", "en": "Status"},
        "CV": {"ar": "السيرة الذاتية", "en": "CV"},
        "Religion": {"ar": "الديانة", "en": "Religion"},
        "Birth Date": {"ar": "تاريخ الميلاد", "en": "Birth Date"},
        "Arrival Date": {"ar": "تاريخ الوصول", "en": "Arrival Date"},
        "User": {"ar": "المستخدم", "en": "User"},
        "Role": {"ar": "الصلاحية", "en": "Role"},
        
        # New Columns based on your screenshot
        "Gender": {"ar": "الجنس", "en": "Gender"},
        "Phone Number": {"ar": "رقم الهاتف", "en": "Phone Number"},
        "Is your contract expired": {"ar": "هل العقد منتهي؟", "en": "Is your contract expired?"},
        "When is your contract end date?": {"ar": "تاريخ انتهاء العقد", "en": "When is your contract end date?"},
        "your Age:": {"ar": "العمر", "en": "your Age:"},
        "Are you working now?": {"ar": "هل تعمل حالياً؟", "en": "Are you working now?"},
        "Do you have any financial obligations towards your previous employer?": {"ar": "هل لديك التزامات مالية سابقة؟", "en": "Do you have any financial obligations..."},
        "Timestamp": {"ar": "وقت التسجيل", "en": "Timestamp"},
        "notes": {"ar": "ملاحظات", "en": "Notes"},
    }
}

# ... (rest of functions) ...

def t_col(col_name, lang="ar"):
    """Translates a column name if it exists in the dictionary."""
    if lang == 'en': return col_name
    
    # Check exact match first
    res = TRANSLATIONS.get("columns", {}).get(col_name, {}).get("ar")
    if res: return res
    
    # Fallback: Check if it partially matches (for long columns that might be truncated or have extra spaces)
    col_str = str(col_name).lower()
    if "financial obligations" in col_str: return "هل لديك التزامات مالية سابقة؟"
    if "contract end" in col_str: return "تاريخ انتهاء العقد"
    
    return col_name
