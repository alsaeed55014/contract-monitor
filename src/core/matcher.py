"""
CandidateMatcher - 5-Step Smart Matching Engine
Matches customer requests with available candidates based on:
  1. Nationality
  2. Gender
  3. Location (city / region)
  4. Job title / Skills
  5. Geographic expansion fallback
"""
import re
import pandas as pd


# ═══════════════════════════════════════════════════════════════
# Geographic Data — Regions → Cities (Arabic + English)
# ═══════════════════════════════════════════════════════════════

REGION_MAP = {
    # --- Northern Region ---
    "الشمالية": {
        "aliases_ar": ["الشمالية", "الشمال", "المنطقة الشمالية"],
        "aliases_en": ["northern", "north", "northern region"],
        "cities_ar": [
            "تبوك", "ضباء", "الوجه", "أملج", "حقل", "البدع",
            "عرعر", "رفحاء", "طريف", "العويقيلة",
            "سكاكا", "القريات", "دومة الجندل"
        ],
        "cities_en": [
            "tabuk", "duba", "al wajh", "umluj", "haql", "al bad",
            "arar", "rafha", "turaif", "al uwayqilah",
            "sakaka", "al qurayyat", "dumat al jandal"
        ],
    },
    # --- Eastern Region ---
    "الشرقية": {
        "aliases_ar": ["الشرقية", "الشرق", "المنطقة الشرقية"],
        "aliases_en": ["eastern", "east", "eastern region"],
        "cities_ar": [
            "الدمام", "الخبر", "الظهران", "القطيف", "سيهات", "تاروت", "عنك", "صفوى",
            "الجبيل", "الأحساء", "الهفوف", "المبرز",
            "حفر الباطن", "الخفجي", "النعيرية", "بقيق", "رأس تنورة", "قرية العليا"
        ],
        "cities_en": [
            "dammam", "khobar", "dhahran", "qatif", "saihat", "tarout", "anak", "safwa",
            "jubail", "al ahsa", "al hasa", "hofuf", "al mubarraz",
            "hafar al batin", "khafji", "nairyah", "nariyah", "abqaiq", "ras tanura", "qaryat al ulya"
        ],
    },
    # --- Southern Region ---
    "الجنوبية": {
        "aliases_ar": ["الجنوبية", "الجنوب", "المنطقة الجنوبية"],
        "aliases_en": ["southern", "south", "southern region"],
        "cities_ar": [
            "أبها", "خميس مشيط", "بيشة", "النماص", "محايل عسير", "ظهران الجنوب",
            "جازان", "صبيا", "أبو عريش", "صامطة", "الدرب",
            "نجران", "شرورة",
            "الباحة", "بلجرشي", "المخواة"
        ],
        "cities_en": [
            "abha", "khamis mushait", "bisha", "al namas", "muhayil asir", "dhahran al janub",
            "jazan", "sabya", "abu arish", "samtah", "al darb",
            "najran", "sharurah",
            "al baha", "baljurashi", "al makhwah"
        ],
    },
    # --- Western Region ---
    "الغربية": {
        "aliases_ar": ["الغربية", "الغرب", "المنطقة الغربية"],
        "aliases_en": ["western", "west", "western region"],
        "cities_ar": [
            "مكة المكرمة", "مكة", "جدة", "الطائف", "رابغ", "القنفذة", "الليث",
            "المدينة المنورة", "المدينة", "ينبع", "العلا", "بدر",
            "حائل", "بقعاء"
        ],
        "cities_en": [
            "makkah", "mecca", "jeddah", "taif", "rabigh", "al qunfudhah", "al lith",
            "madinah", "medina", "yanbu", "al ula", "badr",
            "hail", "baqaa"
        ],
    },
    # --- Central Region ---
    "الوسطى": {
        "aliases_ar": ["الوسطى", "الوسط", "المنطقة الوسطى"],
        "aliases_en": ["central", "middle", "central region"],
        "cities_ar": [
            "الرياض", "الخرج", "الدوادمي", "الزلفي", "شقراء", "المجمعة", "وادي الدواسر", "الأفلاج"
        ],
        "cities_en": [
            "riyadh", "al kharj", "al dawadmi", "al zulfi", "shaqra", "al majmaah", "wadi al dawasir", "al aflaj"
        ],
    },
    # --- Al Qassim Region ---
    "القصيم": {
        "aliases_ar": ["القصيم", "منطقة القصيم", "المنطقة القصيم"],
        "aliases_en": ["qassim", "al qassim", "qassim region"],
        "cities_ar": [
            "بريدة", "عنيزة", "الرس", "البكيرية", "البدائع", "الأسياح",
            "النبهانية", "عيون الجواء", "رياض الخبراء", "المذنب", "الشماسية",
            "عقلة الصقور", "ضرية"
        ],
        "cities_en": [
            "buraidah", "unaizah", "ar rass", "al bukayriyah", "al badayea", "al asyah",
            "an nabhaniyah", "uyun al jawa", "riyadh al khabra", "al mithnab", "ash shimasiyah",
            "uqlat as suqur", "dhariyah"
        ],
    },
}

# Proximity order: if searching from one region, which regions are closest?
REGION_PROXIMITY = {
    "الشمالية": ["القصيم", "الوسطى", "الشرقية", "الغربية", "الجنوبية"],
    "الشرقية": ["القصيم", "الوسطى", "الشمالية", "الغربية", "الجنوبية"],
    "الجنوبية": ["الغربية", "الوسطى", "الشرقية", "القصيم", "الشمالية"],
    "الغربية": ["الجنوبية", "الوسطى", "الشرقية", "القصيم", "الشمالية"],
    "الوسطى": ["القصيم", "الشرقية", "الشمالية", "الغربية", "الجنوبية"],
    "القصيم": ["الوسطى", "الشرقية", "الشمالية", "الغربية", "الجنوبية"],
}


# ═══════════════════════════════════════════════════════════════
# Arabic → English Translation Dictionary (for bilingual search)
# ═══════════════════════════════════════════════════════════════

AR_TO_EN = {
    # --- Nationalities ---
    "فلبيني": ["Filipino", "Philippine"], "فلبينية": ["Filipino", "Philippine"],
    "هندي": ["Indian"], "هندية": ["Indian"],
    "باكستاني": ["Pakistani"], "باكستانية": ["Pakistani"],
    "بنجلاديشي": ["Bangladeshi", "Bangladesh"], "بنجالية": ["Bangladeshi"],
    "بنقالي": ["Bangladeshi"], "بنحلاديش": ["Bangladesh", "Bangladeshi"],
    "مصري": ["Egyptian"], "مصرية": ["Egyptian"],
    "نيبالي": ["Nepali", "Nepalese"], "نيبالية": ["Nepali"],
    "سيريلانكي": ["Sri Lankan"], "سيريلانكية": ["Sri Lankan"],
    "سيرلانكي": ["Sri Lankan"],
    "كيني": ["Kenyan"], "كينية": ["Kenyan"],
    "اوغندي": ["Ugandan"], "اوغندية": ["Ugandan"],
    "اثيوبي": ["Ethiopian"], "اثيوبية": ["Ethiopian"],
    "اندونيسي": ["Indonesian"], "اندونيسية": ["Indonesian"],
    "مغربي": ["Moroccan"], "مغربية": ["Moroccan"],
    "سوداني": ["Sudanese"], "سودانية": ["Sudanese"],
    "يمني": ["Yemeni"], "يمنية": ["Yemeni"],
    "نيجيري": ["Nigerian"], "نيجيرية": ["Nigerian"],
    "غاني": ["Ghanaian"], "غانية": ["Ghanaian"],
    "سنغالي": ["Senegalese"], "سنغالية": ["Senegalese"],
    "تونسي": ["Tunisian"], "تونسية": ["Tunisian"],
    "تنزاني": ["Tanzanian"], "تنزانية": ["Tanzanian"],
    "افريقي": ["African", "Nigeria", "Kenya", "Ghana", "Ethiopia"],
    "افريقية": ["African", "Nigeria", "Kenya", "Ghana", "Ethiopia"],

    # --- Gender ---
    "ذكر": ["Male"], "رجل": ["Male"], "ولد": ["Male"],
    "أنثى": ["Female"], "انثى": ["Female"], "بنت": ["Female"],
    "سيدة": ["Female"], "امرأة": ["Female"],

    # --- Jobs / Professions ---
    "باريستا": ["Barista"],
    "طباخ": ["Cook", "Chef"], "شيف": ["Chef", "Cook"],
    "حلا": ["Pastry", "Dessert"], "حلويات": ["Pastry", "Dessert", "Sweets"],
    "نادل": ["Waiter"], "نادلة": ["Waitress"],
    "سائق": ["Driver"],
    "ممرض": ["Nurse"], "ممرضة": ["Nurse"],
    "طبيب": ["Doctor"],
    "نظافة": ["Cleaner"], "عامل نظافة": ["Cleaner"], "عاملة نظافة": ["Cleaner"],
    "بدكير": ["Pedicure", "Technician"], "منكير": ["Manicure", "Technician"],
    "حلاق": ["Barber"],
    "كوافير": ["Hairdresser", "Hair Stylist"],
    "مصففة": ["Hairdresser", "Hair Stylist"],
    "مساج": ["Massage", "Therapist"],
    "سكرتيرة": ["Secretary"],
    "مبرمج": ["Programmer"], "مهندس": ["Engineer"], "فني": ["Technician"],
    "مطعم": ["Restaurant"],
    "خادمة": ["Housemaid", "Domestic"], "عاملة": ["Housemaid", "Worker"],
    "شغالة": ["Housemaid", "Domestic"],

    # --- Cities (Arabic → English) ---
    "الرياض": ["Riyadh"], "الخرج": ["Al Kharj", "Al-Kharj", "Kharj"],
    "الدوادمي": ["Al Dawadmi"], "الزلفي": ["Al Zulfi", "Zulfi"],
    "شقراء": ["Shaqra"], "المجمعة": ["Al Majmaah", "Majmaah"],
    "وادي الدواسر": ["Wadi Al Dawasir"], "الأفلاج": ["Al Aflaj"],
    "جدة": ["Jeddah", "Jiddah"], "مكة": ["Makkah", "Mecca"],
    "مكة المكرمة": ["Makkah", "Mecca"],
    "المدينة المنورة": ["Madinah", "Medina"], "المدينة": ["Madinah", "Medina"],
    "الطائف": ["Taif"], "رابغ": ["Rabigh"],
    "القنفذة": ["Al Qunfudhah"], "الليث": ["Al Lith"],
    "ينبع": ["Yanbu"], "العلا": ["Al Ula"], "بدر": ["Badr"],
    "حائل": ["Hail"], "بقعاء": ["Baqaa"],
    "الدمام": ["Dammam"], "الخبر": ["Khobar", "Al Khobar"],
    "الظهران": ["Dhahran"], "القطيف": ["Qatif"],
    "الجبيل": ["Jubail"], "الأحساء": ["Al Ahsa", "Al Hasa", "Al-Ahsa"],
    "الهفوف": ["Hofuf"], "المبرز": ["Al Mubarraz"],
    "حفر الباطن": ["Hafar Al Batin", "Hafar Al-Batin"],
    "الخفجي": ["Khafji"], "النعيرية": ["Nairyah", "Nariyah"],
    "تبوك": ["Tabuk"], "ضباء": ["Duba"],
    "الوجه": ["Al Wajh"], "أملج": ["Umluj"],
    "حقل": ["Haql"], "عرعر": ["Arar"],
    "رفحاء": ["Rafha"], "طريف": ["Turaif"],
    "سكاكا": ["Sakaka"], "القريات": ["Al Qurayyat"],
    "دومة الجندل": ["Dumat Al Jandal"],
    "أبها": ["Abha"], "خميس مشيط": ["Khamis Mushait"],
    "بيشة": ["Bisha"], "النماص": ["Al Namas"],
    "محايل عسير": ["Muhayil Asir", "Muhayil"], "ظهران الجنوب": ["Dhahran Al Janub"],
    "جازان": ["Jazan", "Jizan"], "صبيا": ["Sabya"],
    "أبو عريش": ["Abu Arish"], "صامطة": ["Samtah"],
    "الدرب": ["Al Darb"], "نجران": ["Najran"],
    "شرورة": ["Sharurah"],
    "الباحة": ["Al Baha", "Al Bahah"], "بلجرشي": ["Baljurashi"],
    "المخواة": ["Al Makhwah", "Almikhwah"],
    "بريدة": ["Buraidah", "Buraydah"], "عنيزة": ["Unaizah", "Unayza", "UNAYZA"],
    "الرس": ["Al Rass", "Ar Rass"],
    "البكيرية": ["Al Bukayriyah"], "البدائع": ["Al Badayea"],
    "الأسياح": ["Al Asyah"], "النبهانية": ["An Nabhaniyah"],
    "عيون الجواء": ["Uyun Al Jawa"], "رياض الخبراء": ["Riyadh Al Khabra"],
    "المذنب": ["Al Mithnab"], "الشماسية": ["Ash Shimasiyah"],
    "عقلة الصقور": ["Uqlat As Suqur"], "ضرية": ["Dhariyah"],
    "سيهات": ["Saihat"], "تاروت": ["Tarout"],
    "صفوى": ["Safwa"], "بقيق": ["Abqaiq"],
    "رأس تنورة": ["Ras Tanura"],

    # --- Regions ---
    "الشرقية": ["Eastern", "East"], "الشرق": ["Eastern", "East"],
    "المنطقة الشرقية": ["Eastern Region", "Eastern"],
    "الغربية": ["Western", "West"], "الغرب": ["Western", "West"],
    "المنطقة الغربية": ["Western Region", "Western"],
    "الوسطى": ["Central", "Middle"], "الوسط": ["Central", "Middle"],
    "المنطقة الوسطى": ["Central Region", "Central"],
    "الشمالية": ["Northern", "North"], "الشمال": ["Northern", "North"],
    "المنطقة الشمالية": ["Northern Region", "Northern"],
    "الجنوبية": ["Southern", "South"], "الجنوب": ["Southern", "South"],
    "المنطقة الجنوبية": ["Southern Region", "Southern"],
    "القصيم": ["Qassim", "Al Qassim", "AL QASSIM"],
    "منطقة القصيم": ["Qassim Region", "Qassim"],
}


def _translate_ar_to_en(text):
    """
    Translate Arabic text to all possible English equivalents.
    Returns a list of English strings (may be empty if no translation found).
    """
    if not text:
        return []

    text_clean = str(text).strip()
    results = []

    # Direct lookup
    if text_clean in AR_TO_EN:
        results.extend(AR_TO_EN[text_clean])

    # Normalized lookup
    text_norm = _normalize(text_clean)
    for ar_key, en_vals in AR_TO_EN.items():
        ar_norm = _normalize(ar_key)
        if ar_norm == text_norm:
            results.extend(en_vals)
        elif len(text_norm) > 3 and (text_norm in ar_norm or ar_norm in text_norm):
            results.extend(en_vals)

    return list(set(results))


# ═══════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════

def _normalize(text):
    """Normalize Arabic text for fuzzy matching."""
    if not text:
        return ""
    t = str(text).lower().strip()
    t = t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    t = t.replace("ة", "ه").replace("ى", "ي")
    t = t.replace("ئ", "ي").replace("ؤ", "و").replace("ء", "")
    # Remove common prefixes
    t = re.sub(r'^(ال)', '', t) if len(t) > 4 else t
    return t.strip()


def _find_col(df, keywords):
    """Find a column in df that matches any of the given keywords (fuzzy)."""
    for col in df.columns:
        col_norm = _normalize(col)
        col_lower = str(col).lower().strip()
        for kw in keywords:
            kw_norm = _normalize(kw)
            kw_lower = str(kw).lower().strip()
            # Exact or substring match
            if kw_norm == col_norm:
                return col
            if len(kw_norm) > 3 and kw_norm in col_norm:
                return col
            if len(col_norm) > 3 and col_norm in kw_norm:
                return col
            # English fallback
            if kw_lower in col_lower or col_lower in kw_lower:
                return col
    return None


def _fuzzy_match(value, target):
    """
    Bilingual fuzzy match: checks Arabic AND English equivalents.
    value = what's in the database (could be English)
    target = what the user searched for (could be Arabic)
    """
    if not value or not target:
        return False

    v_str = str(value).strip()
    t_str = str(target).strip()

    if not v_str or not t_str or v_str.lower() == "nan" or t_str.lower() == "nan":
        return False

    v_lower = v_str.lower()
    t_lower = t_str.lower()
    v_norm = _normalize(v_str)
    t_norm = _normalize(t_str)

    # 1. Direct Arabic/normalized match
    if t_norm and v_norm:
        if t_norm in v_norm or v_norm in t_norm:
            return True

    # 2. Direct English match (both already in English)
    if t_lower in v_lower or v_lower in t_lower:
        return True

    # 3. Translate target (Arabic) → English, match against value
    en_translations = _translate_ar_to_en(t_str)
    for en in en_translations:
        en_lower = en.lower()
        if en_lower in v_lower or v_lower in en_lower:
            return True

    # 4. Translate value (Arabic) → English, match against target
    en_val_translations = _translate_ar_to_en(v_str)
    for en in en_val_translations:
        en_lower = en.lower()
        if t_lower in en_lower or en_lower in t_lower:
            return True

    return False


def _resolve_region(location_text):
    """
    Determine if the location is a region or a specific city.
    Returns: (is_region: bool, region_key: str or None, target_cities_ar: list, target_cities_en: list)
    """
    loc_norm = _normalize(location_text)
    loc_lower = str(location_text).lower().strip()

    # Check if it matches a region alias
    for region_key, data in REGION_MAP.items():
        for alias in data["aliases_ar"]:
            if _normalize(alias) == loc_norm or loc_norm in _normalize(alias) or _normalize(alias) in loc_norm:
                return True, region_key, data["cities_ar"], data["cities_en"]
        for alias in data["aliases_en"]:
            if alias == loc_lower or loc_lower in alias or alias in loc_lower:
                return True, region_key, data["cities_ar"], data["cities_en"]

    # Not a region — it's a specific city
    return False, None, [location_text], [location_text]


def _find_city_region(city_text):
    """Find which region a city belongs to."""
    city_norm = _normalize(city_text)
    city_lower = str(city_text).lower().strip()
    for region_key, data in REGION_MAP.items():
        for c in data["cities_ar"]:
            if _normalize(c) == city_norm or city_norm in _normalize(c) or _normalize(c) in city_norm:
                return region_key
        for c in data["cities_en"]:
            if c == city_lower or city_lower in c or c in city_lower:
                return region_key
    return None


# ═══════════════════════════════════════════════════════════════
# Column keyword lists for auto-detection
# ═══════════════════════════════════════════════════════════════

NATIONALITY_KEYWORDS = [
    "Nationality", "الجنسية", "جنسية", "nationality", "What is your Nationality",
    "nationalty", "جنسيتك"
]

GENDER_KEYWORDS = [
    "Gender", "الجنس", "جنس", "gender", "Are you male or female",
    "Male or Female", "ذكر أم أنثى", "النوع"
]

CITY_KEYWORDS = [
    "City", "المدينة", "مدينة", "city", "In which city",
    "Which city", "مدينتك", "المنطقة", "اي مدينة", "في أي مدينة"
]

JOB_KEYWORDS = [
    "Job", "الوظيفة", "وظيفة", "المسمى الوظيفي", "job", "profession",
    "What is your job", "المهنة", "مهنة", "عملك", "ماهي وظيفتك",
    "What is your current job", "Your job"
]

SKILLS_KEYWORDS = [
    "Skills", "المهارات", "مهارات", "المهارات الأخرى", "Other Skills",
    "skills", "other skills", "مهارات أخرى", "مهاراتك",
    "What other skills", "Do you have other skills"
]

NAME_KEYWORDS = [
    "Name", "الاسم", "اسم", "name", "Full Name", "الاسم الكامل",
    "What is your name", "Your name", "اسمك"
]

PHONE_KEYWORDS = [
    "Phone", "الجوال", "جوال", "هاتف", "رقم", "phone", "mobile",
    "Phone Number", "رقم الجوال", "تليفون"
]


# ═══════════════════════════════════════════════════════════════
# Main Matcher Class
# ═══════════════════════════════════════════════════════════════

class CandidateMatcher:
    """
    5-Step Smart Matching Engine.
    Takes a customer request (dict or Series) and a candidates DataFrame,
    and returns matching results following the strict algorithm.
    """

    def __init__(self, candidates_df):
        """
        candidates_df: pandas DataFrame of all available candidates (workers).
        """
        self.candidates = candidates_df if candidates_df is not None else pd.DataFrame()
        self.debug_info = {}

    def set_candidates(self, df):
        self.candidates = df

    # ─────────────────────────────────────────
    # Step 1: Extract Search Criteria
    # ─────────────────────────────────────────
    def extract_criteria(self, request_row):
        """
        Extract nationality, gender, location, and job from a customer request row.
        request_row: dict or pd.Series
        """
        if isinstance(request_row, pd.Series):
            request_row = request_row.to_dict()

        criteria = {
            "nationality": "",
            "gender": "",
            "location": "",
            "job": "",
        }

        # Smart column detection from request
        for key, val in request_row.items():
            key_norm = _normalize(str(key))
            key_lower = str(key).lower().strip()
            val_str = str(val).strip() if val else ""

            if not val_str or val_str == "nan":
                continue

            # Nationality
            if any(_normalize(kw) in key_norm or kw.lower() in key_lower for kw in NATIONALITY_KEYWORDS):
                if not criteria["nationality"]:
                    criteria["nationality"] = val_str

            # Gender
            elif any(_normalize(kw) in key_norm or kw.lower() in key_lower for kw in GENDER_KEYWORDS):
                if not criteria["gender"]:
                    criteria["gender"] = val_str

            # City / Location
            elif any(_normalize(kw) in key_norm or kw.lower() in key_lower for kw in CITY_KEYWORDS):
                if not criteria["location"]:
                    criteria["location"] = val_str

            # Job / Profession
            elif any(_normalize(kw) in key_norm or kw.lower() in key_lower for kw in JOB_KEYWORDS):
                if not criteria["job"]:
                    criteria["job"] = val_str

        self.debug_info["criteria"] = criteria
        return criteria

    # ─────────────────────────────────────────
    # Step 2: Resolve Geographic Scope
    # ─────────────────────────────────────────
    def resolve_geo_scope(self, location):
        """Returns target cities list and region info."""
        is_region, region_key, cities_ar, cities_en = _resolve_region(location)
        geo = {
            "is_region": is_region,
            "region_key": region_key,
            "target_cities_ar": cities_ar,
            "target_cities_en": cities_en,
            "original_location": location,
        }
        self.debug_info["geo_scope"] = geo
        return geo

    # ─────────────────────────────────────────
    # Step 3: Filter by Nationality + Gender + Location
    # ─────────────────────────────────────────
    def _filter_basic(self, nationality, gender):
        """Filter candidates by nationality AND gender (mandatory)."""
        df = self.candidates.copy()
        if df.empty:
            return df

        # Find columns
        nat_col = _find_col(df, NATIONALITY_KEYWORDS)
        gen_col = _find_col(df, GENDER_KEYWORDS)

        self.debug_info["nat_col"] = nat_col
        self.debug_info["gen_col"] = gen_col

        if nat_col and nationality:
            mask = df[nat_col].apply(lambda v: _fuzzy_match(v, nationality))
            df = df[mask]

        if gen_col and gender:
            mask = df[gen_col].apply(lambda v: _fuzzy_match(v, gender))
            df = df[mask]

        return df

    def _filter_by_location(self, df, cities_ar, cities_en):
        """Filter candidates by city within the target cities list."""
        if df.empty:
            return df

        city_col = _find_col(df, CITY_KEYWORDS)
        if not city_col:
            return df

        self.debug_info["city_col"] = city_col

        all_targets = [_normalize(c) for c in cities_ar] + [c.lower() for c in cities_en]

        def city_match(val):
            if not val or str(val).strip() == "" or str(val).strip().lower() == "nan":
                return False
            v_norm = _normalize(str(val))
            v_lower = str(val).lower().strip()
            for t in all_targets:
                if t in v_norm or v_norm in t or t in v_lower or v_lower in t:
                    return True
            return False

        return df[df[city_col].apply(city_match)]

    # ─────────────────────────────────────────
    # Step 3 (cont): Filter by Job / Skills
    # ─────────────────────────────────────────
    def _filter_by_job(self, df, job_text):
        """
        Phase A: Search in Job column.
        Phase B: Search in Skills column.
        Returns (result_df, source) where source is 'job', 'skills', or 'none'.
        """
        if df.empty or not job_text:
            return df, "none"

        job_col = _find_col(df, JOB_KEYWORDS)
        skills_col = _find_col(df, SKILLS_KEYWORDS)

        self.debug_info["job_col"] = job_col
        self.debug_info["skills_col"] = skills_col

        # Phase A: Job column
        if job_col:
            mask = df[job_col].apply(lambda v: _fuzzy_match(v, job_text))
            job_results = df[mask]
            if not job_results.empty:
                return job_results, "job"

        # Phase B: Skills column
        if skills_col:
            mask = df[skills_col].apply(lambda v: _fuzzy_match(v, job_text))
            skills_results = df[mask]
            if not skills_results.empty:
                return skills_results, "skills"

        return pd.DataFrame(), "none"

    # ─────────────────────────────────────────
    # Step 4: Geographic Expansion
    # ─────────────────────────────────────────
    def _expand_geo(self, nationality, gender, job_text, original_region_key, original_location):
        """
        Search all OTHER cities/regions for matching candidates,
        sorted by proximity to the original location.
        Returns list of dicts: [{"city": ..., "region": ..., "candidates": df}, ...]
        """
        base_df = self._filter_basic(nationality, gender)
        if base_df.empty:
            return []

        # Filter by job/skills
        base_df, _ = self._filter_by_job(base_df, job_text)
        if base_df.empty:
            return []

        city_col = _find_col(base_df, CITY_KEYWORDS)
        if not city_col:
            return []

        # Determine proximity order
        if original_region_key and original_region_key in REGION_PROXIMITY:
            ordered_regions = REGION_PROXIMITY[original_region_key]
        else:
            # Find the region of the original city
            found_region = _find_city_region(original_location)
            if found_region and found_region in REGION_PROXIMITY:
                ordered_regions = REGION_PROXIMITY[found_region]
            else:
                ordered_regions = list(REGION_MAP.keys())

        results = []
        for region_key in ordered_regions:
            region_data = REGION_MAP[region_key]
            region_cities_ar = region_data["cities_ar"]
            region_cities_en = region_data["cities_en"]

            region_df = self._filter_by_location(base_df, region_cities_ar, region_cities_en)
            if not region_df.empty:
                # Group by city
                for city_val in region_df[city_col].unique():
                    city_candidates = region_df[region_df[city_col] == city_val]
                    results.append({
                        "city": str(city_val),
                        "region": region_key,
                        "count": len(city_candidates),
                        "candidates": city_candidates,
                    })

        return results

    # ─────────────────────────────────────────
    # Main Match Function (All 5 Steps)
    # ─────────────────────────────────────────
    def match(self, request_row):
        """
        Execute the full 5-step matching algorithm.
        Returns a dict with:
          - criteria: extracted search criteria
          - geo_scope: geographic scope info
          - local_results: DataFrame of local matches (may be empty)
          - local_source: 'job', 'skills', or 'none'
          - expanded_results: list of dicts with alternative cities (if no local results)
          - status: 'found_local', 'found_expanded', 'not_found'
        """
        self.debug_info = {}

        # Step 1: Extract criteria
        criteria = self.extract_criteria(request_row)
        nationality = criteria["nationality"]
        gender = criteria["gender"]
        location = criteria["location"]
        job = criteria["job"]

        # Step 2: Resolve geo scope
        geo = self.resolve_geo_scope(location)

        # Step 3: Filter
        basic_df = self._filter_basic(nationality, gender)
        local_df = self._filter_by_location(basic_df, geo["target_cities_ar"], geo["target_cities_en"])
        local_results, local_source = self._filter_by_job(local_df, job)

        if not local_results.empty:
            return {
                "criteria": criteria,
                "geo_scope": geo,
                "local_results": local_results,
                "local_source": local_source,
                "expanded_results": [],
                "status": "found_local",
            }

        # Step 4: Geographic expansion
        expanded = self._expand_geo(nationality, gender, job, geo["region_key"], location)

        if expanded:
            return {
                "criteria": criteria,
                "geo_scope": geo,
                "local_results": pd.DataFrame(),
                "local_source": "none",
                "expanded_results": expanded,
                "status": "found_expanded",
            }

        # No results at all
        return {
            "criteria": criteria,
            "geo_scope": geo,
            "local_results": pd.DataFrame(),
            "local_source": "none",
            "expanded_results": [],
            "status": "not_found",
        }


# ═══════════════════════════════════════════════════════════════
# Step 5: Format Output (for display in Streamlit)
# ═══════════════════════════════════════════════════════════════

def format_match_result(result, lang="ar"):
    """
    Format the match result dict into a structured text output.
    Returns a tuple: (summary_md, status_icon, detail_items)
    """
    c = result["criteria"]
    geo = result["geo_scope"]
    status = result["status"]

    # Summary section
    if lang == "ar":
        summary = f"""📌 **ملخص الطلب:**
- **الجنسية:** {c['nationality'] or 'غير محدد'}
- **الجنس:** {c['gender'] or 'غير محدد'}
- **موقع العمل:** {geo['original_location'] or 'غير محدد'} {'(منطقة)' if geo['is_region'] else '(مدينة)'}
- **طبيعة العمل:** {c['job'] or 'غير محدد'}"""
    else:
        summary = f"""📌 **Request Summary:**
- **Nationality:** {c['nationality'] or 'N/A'}
- **Gender:** {c['gender'] or 'N/A'}
- **Location:** {geo['original_location'] or 'N/A'} {'(Region)' if geo['is_region'] else '(City)'}
- **Job:** {c['job'] or 'N/A'}"""

    if status == "found_local":
        count = len(result["local_results"])
        source_label = "الوظيفة" if result["local_source"] == "job" else "المهارات"
        if lang != "ar":
            source_label = "Job" if result["local_source"] == "job" else "Skills"

        if lang == "ar":
            status_text = f"✅ **نتائج البحث:** تم العثور على **{count}** مرشح/مرشحة (مطابقة عبر: {source_label})"
        else:
            status_text = f"✅ **Results:** Found **{count}** candidate(s) (matched via: {source_label})"

        return summary, status_text, result["local_results"]

    elif status == "found_expanded":
        if lang == "ar":
            status_text = "⚠️ **لا توجد نتائج في الموقع المطلوب — أقرب البدائل المتاحة:**"
        else:
            status_text = "⚠️ **No results in requested location — Nearest alternatives:**"

        alt_lines = []
        for item in result["expanded_results"]:
            if lang == "ar":
                alt_lines.append(f"→ **{item['city']}** ({item['region']}) — عدد المرشحين: **{item['count']}**")
            else:
                alt_lines.append(f"→ **{item['city']}** ({item['region']}) — Candidates: **{item['count']}**")

        alt_text = "\n".join(alt_lines)
        # Combine all expanded candidates into one df for display
        all_expanded = pd.concat([item["candidates"] for item in result["expanded_results"]], ignore_index=True)

        return summary, status_text + "\n" + alt_text, all_expanded

    else:
        if lang == "ar":
            status_text = "❌ **لا توجد مرشحون متاحون يطابقون هذه المواصفات حالياً.**"
        else:
            status_text = "❌ **No candidates currently match these specifications.**"

        return summary, status_text, pd.DataFrame()
