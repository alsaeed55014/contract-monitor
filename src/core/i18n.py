        # تمت إضافة هذه العناوين الجديدة بناءً على الصورة
        "Are you in Saudi Arabia now": {"ar": "هل أنت في السعودية الآن؟", "en": "Are you in Saudi Arabia now"},
        "If you are Huroob, how many days or months have you been Huroob?": {"ar": "مدة الهروب (إن وجد)", "en": "If you are Huroob..."},
        "Will your employer accept to transfer your sponsorship": {"ar": "هل يقبل كفيلك النقل؟", "en": "Will your employer accept..."},
    }
}

def t(key, lang="ar"):
    return TRANSLATIONS.get(key, {}).get(lang, key)

def t_col(col_name, lang="ar"):
    """Translates a column name with fuzzy matching (ignores case/spaces)."""
    if lang == 'en': return col_name
    
    col_str = str(col_name).strip()
    
    # 1. Try Exact Match
    res = TRANSLATIONS.get("columns", {}).get(col_str, {}).get("ar")
    if res: return res
    
    # 2. Try Case-Insensitive Match
    cols_map = {k.strip().lower(): v.get("ar") for k, v in TRANSLATIONS.get("columns", {}).items()}
    res_fuzzy = cols_map.get(col_str.lower())
    if res_fuzzy: return res_fuzzy
    
    # 3. Fallback for specific partials (تم إضافة شروط ذكية هنا)
    col_lower = col_str.lower()
    if "financial obligations" in col_lower: return "هل لديك التزامات مالية؟"
    if "contract end" in col_lower: return "تاريخ انتهاء العقد"
    if "mobile" in col_lower: return "رقم الجوال"
    if "phone" in col_lower: return "رقم الهاتف"
    if "huroob" in col_lower: return "مدة الهروب (إن وجد)"
    if "saudi arabia" in col_lower and "now" in col_lower: return "هل أنت في السعودية الآن؟"
    if "transfer your sponsorship" in col_lower: return "هل يقبل كفيلك النقل؟"
    
    return col_name
