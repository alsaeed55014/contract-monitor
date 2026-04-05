import pandas as pd
import re
from datetime import datetime
import streamlit as st

FLAG_MAP = {
    # Arabic
    "هندي": "in", "هندية": "in", "الهند": "in",
    "فلبيني": "ph", "فلبينية": "ph", "الفلبين": "ph",
    "نيبالي": "np", "نيبالية": "np", "نيبال": "np",
    "بنجلاديشي": "bd", "بنجالية": "bd", "بنجلاديش": "bd", "بنقالي": "bd",
    "باكستاني": "pk", "باكستانية": "pk", "باكستان": "pk",
    "مصري": "eg", "مصرية": "eg", "مصر": "eg",
    "سوداني": "sd", "سودانية": "sd", "السودان": "sd",
    "سيريلانكي": "lk", "سيريلانكية": "lk", "سيريلانكا": "lk",
    "كيني": "ke", "كينية": "ke", "كينيا": "ke",
    "اوغندي": "ug", "اوغندية": "ug", "اوغندا": "ug",
    "اثيوبي": "et", "اثيوبية": "et", "اثيوبيا": "et",
    "مغربي": "ma", "مغربية": "ma", "المغرب": "ma",
    "يمني": "ye", "يمنية": "ye", "اليمن": "ye",
    "اندونيسي": "id", "اندونيسية": "id", "اندونيسيا": "id", "اندونيسا": "id",
    "رواندي": "rw", "رواندية": "rw", "رواندا": "rw", "روندا": "rw", "روندي": "rw", "روندية": "rw",
    "افغاني": "af", "افغانية": "af", "افغانستان": "af", "افغان": "af",
    "نيجيري": "ng", "نيجيرية": "ng", "نيجيريا": "ng", "نيجريا": "ng", "نيجري": "ng", "نيجرية": "ng",
    # English
    "indian": "in", "filipino": "ph", "nepi": "np", "nepali": "np", "nepal": "np",
    "bangla": "bd", "bangladeshi": "bd", "pakistan": "pk", "pakistani": "pk",
    "egypt": "eg", "egyptian": "eg", "sudan": "sd", "sudanese": "sd",
    "sri lanka": "lk", "sri lankan": "lk", "kenya": "ke", "kenyan": "ke",
    "uganda": "ug", "ugandan": "ug", "ethiopia": "et", "ethiopian": "et",
    "indonesian": "id", "indonesia": "id", "rwandan": "rw", "rwanda": "rw",
    "afghan": "af", "afghanistan": "af", "nigerian": "ng", "nigeria": "ng"
}

GENDER_MAP = {
    "ذكر": "🚹", "male": "🚹",
    "أنثى": "🚺", "female": "🚺"
}

def get_flag_emoji(nat_name):
    """Converts nationality name to emoji flag."""
    nat_name = str(nat_name).lower().strip()
    flags = {
        'مصر': '🇪🇬', 'مصري': '🇪🇬', 'egypt': '🇪🇬',
        'السودان': '🇸🇩', 'سوداني': '🇸🇩', 'sudan': '🇸🇩',
        'باكستان': '🇵🇰', 'باكستاني': '🇵🇰', 'pakistan': '🇵🇰',
        'الهند': '🇮🇳', 'هندي': '🇮🇳', 'india': '🇮🇳',
        'اليمن': '🇾🇪', 'يمني': '🇾🇪', 'yemen': '🇾🇪',
        'بنجلاديش': '🇧🇩', 'بنجالي': '🇧🇩', 'bangladesh': '🇧🇩',
        'الفلبين': '🇵🇭', 'فلبيني': '🇵🇭', 'philippines': '🇵🇭',
        'كينيا': '🇰🇪', 'كيني': '🇰🇪', 'kenya': '🇰🇪',
        'أوغندا': '🇺🇬', 'أوغندي': '🇺🇬', 'uganda': '🇺🇬',
        'إثيوبيا': '🇪🇹', 'إثيوبي': '🇪🇹', 'ethiopia': '🇪🇹',
    }
    for k, v in flags.items():
        if k in nat_name: return v
    return '🏁'

def auto_translate(val, target_lang='en'):
    if not val or not isinstance(val, (str, object)):
        return val
    
    val_str = str(val).strip()
    if not val_str:
        return val
    
    curr_lang = st.session_state.get('lang', 'ar')
    if curr_lang != target_lang:
        return val
        
    has_ar = any('\u0600' <= char <= '\u06FF' for char in val_str)
    if not has_ar:
        return val

    try:
        if 'tm' not in st.session_state or st.session_state.tm is None:
            from src.core.translation import TranslationManager
            st.session_state.tm = TranslationManager()
        
        tm = st.session_state.tm
        if len(val_str.split()) <= 2:
            translated = tm.translate_word(val_str)
            if isinstance(translated, list): translated = translated[0]
            if translated != val_str: return translated
            
        return st.session_state.tm.translate_full_text(val_str, target_lang=target_lang)
    except:
        return val

def style_df(df):
    if not isinstance(df, pd.DataFrame):
        return df

    styled_df = df.copy()
    lang = st.session_state.get('lang', 'ar')
    
    if lang == 'en':
        for col in styled_df.columns:
            if not str(col).startswith("🚩_") and styled_df[col].dtype == 'object':
                styled_df[col] = styled_df[col].apply(lambda x: auto_translate(x, target_lang='en'))

    nat_cols = [c for c in styled_df.columns if any(kw in str(c).lower() for kw in ["nationality", "الجنسية"])]
    for col in nat_cols:
        flag_col = f"🚩_{col}"
        if flag_col not in styled_df.columns:
            def get_flag_url(val):
                if not val: return None
                s_val = str(val).strip().lower()
                sorted_keys = sorted(FLAG_MAP.keys(), key=len, reverse=True)
                for key in sorted_keys:
                    code = FLAG_MAP[key]
                    if len(key) <= 3:
                        pattern = r'(?:^|[\s,:;.\-/])' + re.escape(key) + r'(?:[\s,:;.\-/]|$)'
                        if re.search(pattern, s_val):
                            return f"https://flagsapi.com/{code.upper()}/flat/64.png"
                    else:
                        if key in s_val:
                            return f"https://flagsapi.com/{code.upper()}/flat/64.png"
                return None
            
            idx = list(styled_df.columns).index(col)
            styled_df.insert(idx, flag_col, styled_df[col].apply(get_flag_url))
        
        def clean_val(v):
            if not v: return v
            return re.sub(r'[\U0001F1E6-\U0001F1FF]{2}\s*', '', str(v))
        styled_df[col] = styled_df[col].apply(clean_val)

    gen_cols = [c for c in styled_df.columns if any(kw in str(c).lower() for kw in ["gender", "الجنس"]) and str(c).lower() != "الجنسية"]
    for col in gen_cols:
        def add_gender_icon(val):
            if not val: return val
            s_val = str(val).strip().lower()
            for key, icon in GENDER_MAP.items():
                if key == s_val:
                    return f"{icon} {val}"
            return val
        styled_df[col] = styled_df[col].apply(add_gender_icon)

    def apply_colors(val):
        s_val = str(val).lower()
        if any(k in s_val for k in ["🚹", "ذكر", "male"]):
            return "color: #3498db; font-weight: bold;" 
        if any(k in s_val for k in ["🚺", "أنثى", "female"]):
            return "color: #e91e63; font-weight: bold;"
        return "color: #4CAF50;"

    return styled_df.style.map(apply_colors, subset=[c for c in styled_df.columns if not str(c).startswith("🚩_")])

def clean_date_display(df):
    if not isinstance(df, pd.DataFrame) or df.empty:
        return df
        
    from dateutil import parser as dateutil_parser
    
    def _parse_to_date_str(val):
        if val is None or str(val).strip() == '': return ""
        try:
            val_str = str(val).strip()
            a_to_w = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
            val_str = val_str.translate(a_to_w)
            clean_s = re.sub(r'[صم]', '', val_str).strip()
            dt = dateutil_parser.parse(clean_s, dayfirst=False)
            return dt.strftime('%Y-%m-%d')
        except:
            try:
                dt = pd.to_datetime(val, errors='coerce')
                if pd.isna(dt): return str(val)
                return dt.strftime('%Y-%m-%d')
            except:
                return str(val)

    date_keywords = ["date", "time", "تاريخ", "طابع", "التسجيل", "expiry", "end", "متى"]
    for col in df.columns:
        col_lower = str(col).lower()
        if any(kw in col_lower for kw in date_keywords):
            df[col] = df[col].apply(_parse_to_date_str)
            
    return df
