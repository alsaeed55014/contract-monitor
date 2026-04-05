# src/core/translation.py
import re
import io
<<<<<<< HEAD
import streamlit as st
import hashlib
=======
>>>>>>> 947f1af (update)

try:
    import pdfplumber
    from deep_translator import GoogleTranslator
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

<<<<<<< HEAD
class TranslationManager:
    # Use class-level cache to persist across re-initializations
    _google_cache = {}

=======

class TranslationManager:
>>>>>>> 947f1af (update)
    def __init__(self):

        # -------------------------
        # Jobs / Professions
        # -------------------------
        self.dictionary = {
            # Core Jobs
            "باريستا": "Barista",
            "طباخ": "Cook",
            "شيف": "Chef",
            "حلا": ["Pastry", "Dessert"],
            "حلويات": ["Pastry", "Dessert", "Sweets"],
            "نادل": ["Waiter", "Male"],
            "نادلة": ["Waitress", "Female"],
            "سائق": "Driver",
            "ممرض": "Nurse",
            "ممرضة": "Nurse",
            "طبيب": "Doctor",
            "نظافة": "Cleaner",
<<<<<<< HEAD
            "بائع": "Sales",
            "بائع زهور": "Florist",
            "بائع ورد": "Florist",
            "منسق": "Coordinator",
            "منسق زهور": "Florist",
            "منسق ورد": "Florist",
            "زهور": ["Florist", "Flowers"],
            "ورد": ["Florist", "Flowers"],
=======
>>>>>>> 947f1af (update)
            "عامل نظافة": "Cleaner",
            "عاملة نظافة": "Cleaner",

            # Beauty / Salon
<<<<<<< HEAD
            "بدكير": ["Pedicure", "Nail"],
            "منكير": ["Manicure", "Nail"],
            "حلاق": "Barber",
            "حلاقة": "Barber",
            "كوافير": ["Hairdresser", "Hair Stylist"],
            "كوافيرة": ["Hairdresser", "Hair Stylist"],
            "مصفف": ["Hairdresser", "Hair Stylist", "Stylist"],
            "مصففة": ["Hairdresser", "Hair Stylist", "Stylist"],
            "مصفف شعر": ["Hairdresser", "Hair Stylist"],
            "مصففة شعر": ["Hairdresser", "Hair Stylist"],
            "تجميل": ["Beauty", "Beautician", "Salon"],
            "صالون": ["Salon", "Beauty"],
=======
            "بدكير": ["Pedicure", "Technician"],
            "منكير": ["Manicure", "Technician"],
            "حلاق": "Barber",
            "كوافير": ["Hairdresser", "Hair Stylist"],
            "مصففة": ["Hairdresser", "Hair Stylist"],
>>>>>>> 947f1af (update)
            "بشرة": "Skin",
            "بروتين": "Protein",
            "شعر": "Hair",
            "مساج": ["Massage", "Therapist"],

            # Office / Technical
            "سكرتيرة": "Secretary",
            "كاميرا": "Camera",
            "كاميرات": "Camera",
            "مبرمج": "Programmer",
            "مهندس": "Engineer",
            "فني": "Technician",
            "مطعم": "Restaurant",
            "ايطالي": "Italian",
            "مكتب": "Office",
            "مكتبيه": "Office",
            "اعمال": "Work",
            "ppf": ["PPF", "Installer"],

            # Domestic Workers
            "خادمة": ["Housemaid", "Domestic"],
            "عاملة": ["Housemaid", "Domestic", "Worker"],
            "شغالة": ["Housemaid", "Domestic"],
            "منزلية": "Domestic",

            # -------------------------
            # Nationalities
            # -------------------------
            "فلبيني": "Filipino",
            "فلبينية": "Filipino",
            "هندي": "Indian",
            "هندية": "Indian",
            "باكستاني": "Pakistani",
            "باكستانية": "Pakistani",
            "بنجلاديشي": "Bangladeshi",
            "بنجالية": "Bangladeshi",
            "بنقالي": "Bangladeshi",
            "بنحلاديش": "Bangladesh",
            "مصري": "Egyptian",
            "مصرية": "Egyptian",
            "نيبالي": "Nepali",
            "نيبالية": "Nepali",
            "سيريلانكي": "Sri Lankan",
            "سيريلانكية": "Sri Lankan",
            "سيرلانكي": "Sri Lankan",
            "كيني": "Kenyan",
            "كينية": "Kenyan",
            "اوغندي": "Ugandan",
            "اوغندية": "Ugandan",
            "اثيوبي": "Ethiopian",
            "اثيوبية": "Ethiopian",
<<<<<<< HEAD
            "اندونيسي": ["Indonesian", "Indonesia"],
            "اندونيسية": ["Indonesian", "Indonesia"],
            "اندونيسيا": "Indonesia",
            "اندونيسا": "Indonesia",
            "اندونيسيه": ["Indonesian", "Indonesia"],
=======
            "اندونيسي": "Indonesian",
>>>>>>> 947f1af (update)
            "مغربي": "Moroccan",
            "مغربية": "Moroccan",
            "سوداني": "Sudanese",
            "سودانية": "Sudanese",
            "يمني": "Yemeni",
            "يمنية": "Yemeni",
<<<<<<< HEAD
            "رواندي": ["Rwandan", "Rwanda"],
            "رواندية": ["Rwandan", "Rwanda"],
            "روندي": ["Rwandan", "Rwanda"],
            "روندية": ["Rwandan", "Rwanda"],
            "رواندا": ["Rwanda", "Rwandan"],
            "روندا": ["Rwanda", "Rwandan"],
            "افغاني": ["Afghan", "Afghanistan"],
            "افغانية": ["Afghan", "Afghanistan"],
            "افغانستان": "Afghanistan",
            "افغان": ["Afghan", "Afghanistan"],
            "نيجيري": ["Nigerian", "Nigeria"],
            "نيجيرية": ["Nigerian", "Nigeria"],
            "نيجري": ["Nigerian", "Nigeria"],
            "نيجرية": ["Nigerian", "Nigeria"],
            "نيجريا": "Nigeria",
            "نيجيريا": "Nigeria",
=======
            "نيجيري": "Nigerian",
            "نيجيرية": "Nigerian",
>>>>>>> 947f1af (update)
            "غاني": "Ghanaian",
            "غانية": "Ghanaian",
            "سنغالي": "Senegalese",
            "سنغالية": "Senegalese",
            "تونسي": "Tunisian",
            "تونسية": "Tunisian",
            "تنزاني": "Tanzanian",
            "تنزانية": "Tanzanian",
<<<<<<< HEAD
            "كينيا": "Kenya",
            "اوغندا": "Uganda",
            "اثيوبيا": "Ethiopia",
=======
>>>>>>> 947f1af (update)

            # Africa Continent Mapping
            "افريقي": [
                "Nigeria", "Kenya", "Ghana", "Ethiopia",
                "Senegal", "Sudan", "Morocco", "Tunisia",
                "Tanzania", "Uganda", "Somalia",
                "Eritrea", "Rwanda", "Burundi", "African"
            ],

            # -------------------------
            # Saudi Cities
            # -------------------------
            "الرياض": "Riyadh",
            "جدة": "Jeddah",
            "مكة": "Makkah",
            "مكه": "Makkah",
            "المدينة": "Madinah",
            "الشرقية": ["Eastern", "Dammam", "Khobar", "Dhahran", "Qatif", "Saihat", "Tarout", "Anak", "Safwa", "Jubail", "Al-Ahsa", "Hofuf", "Al Mubarraz", "Hafar Al-Batin", "Khafji", "Nairyah", "Abqaiq", "Ras Tanura", "Qaryat Al Ulya"],
            "الدمام": "Dammam",
            "الخبر": "Khobar",
            "الظهران": "Dhahran",
            "الاحساء": "Al-Ahsa",
            "الهفوف": "Hofuf",
            "الجبيل": "Jubail",
            "القطيف": "Qatif",
            "حفر الباطن": "Hafar Al-Batin",
            "الخفجي": "Khafji",
<<<<<<< HEAD
            "سيهات": "Saihat",
            "بقيق": "Abqaiq",
            "بريدة": ["Buraydah", "Qassim"],
            "عنيزة": ["Unaizah", "Qassim"],
            "الرس": ["Ar Rass", "Qassim"],
=======
            "بريدة": "Buraydah",
            "عنيزة": "Unaizah",
            "الرس": "Ar Rass",
>>>>>>> 947f1af (update)
            "حائل": "Hail",
            "تبوك": "Tabuk",
            "أبها": "Abha",
            "خميس مشيط": "Khamis Mushait",
            "جيزان": "Jizan",
            "نجران": "Najran",
            "الباحة": "Al Bahah",
            "سكاكا": "Sakaka",
            "عرعر": "Arar",
            "القريات": "Al Qurayyat",
            "ينبع": "Yanbu",
            "الطائف": "Taif",
<<<<<<< HEAD
            "الخرج": ["Al Kharj", "Al-Kharj", "Central", "Alkharj", "Kharj"],
            "الدوادمي": ["Al-Duwadmi", "Duwadmi"],
            "المجمعة": ["Al Majma'ah", "Majmaah"],
            "الزلفي": ["Zulfi", "Az Zulfi"],
            "وادي الدواسر": ["Wadi ad-Dawasir", "Wadi Aldawasir"],
=======
            "الخرج": "Al-Kharj",
            "الدوادمي": "Al-Duwadmi",
            "المجمعة": "Al Majma'ah",
            "الزلفي": "Zulfi",
            "وادي الدواسر": "Wadi ad-Dawasir",
>>>>>>> 947f1af (update)
            "شرورة": "Sharurah",
            "صبيا": "Sabya",
            "بيشة": "Bisha",
            "محايل عسير": "Mahayil",
            "القنفذة": "Al Qunfudhah",
            "الليث": "Al Lith",
            "رابغ": "Rabigh",
            "عفيف": "Afif",
            "الدلم": "Al Dilam",
            "شقراء": "Shaqra",
            "ليلى": "Layla",
            "الحريق": "Al Hariq",
            "القويعية": "Quwayiyah",
            "خليص": "Khulais",
            "الكامل": "Al Kamil",
            "بدر": "Badr",
            "خيبر": "Khaybar",
            "العلا": "Al Ula",
            "الحناكية": "Al Hinakiyah",
            "النماص": "Al Namas",
            "تنومة": "Tanomah",
            "بارق": "Bariq",
            "المجاردة": "Al Majardah",
            "سراة عبيدة": "Sarat Abidah",
            "رجال ألمع": "Rijal Alma",
            "أحد رفيدة": "Ahad Rafidah",
            "ظهران الجنوب": "Dhahran Al Janub",
            "طريب": "Tarib",
            "أبو عريش": "Abu Arish",
            "صامطة": "Samtah",
            "الدرب": "Al Darb",
            "فيفاء": "Faifa",
            "ضمد": "Damad",
            "العارضة": "Al Ardah",
            "المخواة": "Almikhwah",
            "بلجرشي": "Baljurashi",
            "تيماء": "Tayma",
            "ضباء": "Duba",
            "الوجه": "Al Wajh",
            "أملج": "Umluj",
            "حقل": "Haql",
            "رفحاء": "Rafha",
            "طريف": "Turaif",
            "دومة الجندل": "Dumat Al-Jandal",
            "طبرجل": "Tubarjal",
            "سيهات": "Saihat",
            "تاروت": "Tarout",
            "عنك": "Anak",
            "صفوى": "Safwa",
            "المبرز": "Al Mubarraz",
            "النعيرية": "Nairyah",
            "بقيق": "Abqaiq",
            "رأس تنورة": "Ras Tanura",
            "قرية العليا": "Qaryat Al Ulya",
            "عسير": ["Asir", "Abha", "Khamis Mushait", "Bisha", "Mahayil", "Al Namas", "Tanomah", "Bariq", "Al Majardah", "Sarat Abidah", "Rijal Alma", "Ahad Rafidah", "Dhahran Al Janub", "Tarib"],
            "الجنوب": ["South", "Jizan", "Sabya", "Abu Arish", "Samtah", "Al Darb", "Faifa", "Damad", "Al Ardah", "Najran", "Sharurah", "Al Bahah", "Almikhwah", "Baljurashi", "Al Qunfudhah", "Abha", "Khamis Mushait"],
            "الشمال": ["North", "Tabuk", "Tayma", "Duba", "Al Wajh", "Umluj", "Haql", "Arar", "Rafha", "Turaif", "Sakaka", "Dumat Al-Jandal", "Al Qurayyat", "Tubarjal"],
            "المنطقة الشمالية": ["North", "Tabuk", "Arar", "Sakaka", "Turaif", "Rafha"],
            "المنطقة الشرقية": ["Eastern", "Dammam", "Khobar", "Jubail", "Al-Ahsa", "Dhahran", "Qatif", "Hafar Al-Batin"],
            "منطقة عسير": ["Asir", "Abha", "Khamis Mushait", "Bisha", "Mahayil", "Al Namas", "Tanomah"],
            "المنطقة الجنوبية": ["South", "Jizan", "Najran", "Asir", "Abha", "Jazan", "Sabya", "Abu Arish"],
<<<<<<< HEAD
            "المنطقة الوسطى": ["Central", "Riyadh", "Al-Kharj", "Al Kharj", "Al Majma'ah", "Zulfi", "Wadi ad-Dawasir"],
            "المنطقة الغربية": ["Western", "Jeddah", "Makkah", "Madinah", "Taif", "Yanbu", "Rabigh", "Al Lith", "Al Qunfudhah"],
            "الوسطى": ["Central", "Riyadh", "Al-Kharj", "Al Kharj", "Al Majma'ah", "Zulfi"],
            "القصيم": ["Qassim", "Buraydah", "Unaizah", "Ar Rass", "Al Qassim", "AL QASSIM", "Qassim Region"],
            "منطقة القصيم": ["Qassim", "Buraydah", "Unaizah", "Ar Rass"],
=======
            "المنطقة الوسطى": ["Central", "Riyadh", "Al-Kharj", "Al Majma'ah", "Zulfi", "Buraydah", "Unaizah", "Ar Rass", "Hail", "Wadi ad-Dawasir"],
            "المنطقة الغربية": ["Western", "Jeddah", "Makkah", "Madinah", "Taif", "Yanbu", "Rabigh", "Al Lith", "Al Qunfudhah"],
            "الوسطى": ["Central", "Riyadh", "Al-Kharj", "Al Majma'ah", "Zulfi", "Buraydah", "Unaizah", "Ar Rass", "Hail"],
>>>>>>> 947f1af (update)
            "الغربية": ["Western", "Jeddah", "Makkah", "Madinah", "Taif", "Yanbu", "Rabigh", "Al Lith", "Al Qunfudhah"],
            "نجد": ["Central", "Riyadh", "Qassim", "Hail"],
            "الحجاز": ["Western", "Jeddah", "Makkah", "Madinah", "Taif"],

            # -------------------------
            # Gender
            # -------------------------
            "بنت": "Female",
            "سيدة": "Female",
            "امرأة": "Female",
            "انثى": "Female",
            "ولد": "Male",
            "رجل": "Male",
            "ذكر": "Male",
        }

    # ---------------------------------
    # Normalization
    # ---------------------------------
    def normalize_text(self, text):
        if not text:
            return ""

        text = str(text).lower().strip()

        # Remove Arabic definite article
        if text.startswith("ال") and len(text) > 4:
            text = text[2:]

        # Normalize Arabic letters
        text = (
            text.replace("أ", "ا")
                .replace("إ", "ا")
                .replace("آ", "ا")
                .replace("ة", "ه")
                .replace("ى", "ي")
        )

        return text

    # ---------------------------------
    # Translation
    # ---------------------------------
    def translate_word(self, word):
        norm_word = self.normalize_text(word)
        for k, v in self.dictionary.items():
            if self.normalize_text(k) == norm_word:
                return v
        return word

<<<<<<< HEAD
    def _is_arabic(self, text):
        """Check if text contains Arabic characters."""
        return bool(re.search(r'[\u0600-\u06FF]', str(text)))

    def _google_translate_fallback(self, word):
        """Use Google Translate as fallback for words not in local dictionary."""
        if not HAS_DEPS:
            return None
        if not self._is_arabic(word):
            return None
        
        # Check cache first
        cache_key = word.strip().lower()
        if cache_key in TranslationManager._google_cache:
            return TranslationManager._google_cache[cache_key]
        
        try:
            translator = GoogleTranslator(source='ar', target='en')
            result = translator.translate(word)
            if result and result.lower() != word.lower():
                TranslationManager._google_cache[cache_key] = result
                return result
        except Exception:
            pass
        return None

=======
>>>>>>> 947f1af (update)
    # ---------------------------------
    # Query Analyzer
    # ---------------------------------
    def _normalize_query_word(self, word):
        """Helper to normalize a single word for matching"""
        return self.normalize_text(word)

    def analyze_query(self, query):
<<<<<<< HEAD
        clean_query = query.lower().strip()
        ignore_words = ["جميع", "كل", "دول", "دولة", "قارة", "قاره"]
        bundle_list = []

        # --- Step 0: Extract Compound Phrases FIRST ---
        # Sort keys by length (longest first) to catch "مصفف شعر" before "مصفف"
        compound_keys = sorted([k for k in self.dictionary.keys() if len(k.split()) > 1], key=len, reverse=True)
        
        remaining_query = clean_query
        for ck in compound_keys:
            if ck in remaining_query:
                # Found a compound phrase!
                trans = self.dictionary[ck]
                synonyms = {ck}
                if isinstance(trans, list):
                    for t in trans: synonyms.add(t)
                else:
                    synonyms.add(trans)
                
                bundle_list.append(list(synonyms))
                # Remove from remaining query to avoid double matching
                remaining_query = remaining_query.replace(ck, "").strip()

        # --- Step 1: Split and translate remaining words ---
        words = re.split(r'[\s,،/\\|]+', remaining_query)

        for word in words:
            if not word or word in ignore_words or len(word) < 2:
=======

        clean_query = query.lower().strip()
        ignore_words = ["جميع", "كل", "دول", "دولة", "قارة", "قاره"]

        # Split by spaces and common separators like commas
        words = re.split(r'[\s,،/\\|]+', clean_query)
        bundle_list = []

        for word in words:
            if word in ignore_words or len(word) < 2:
>>>>>>> 947f1af (update)
                continue
            
            # Use a Set to avoid duplicates
            synonyms = {word}
            
<<<<<<< HEAD
            # 1. Direct translation from local dictionary
            trans = self.translate_word(word)
            found_local = False
            
            if isinstance(trans, list):
                for t in trans: synonyms.add(t)
                found_local = True
            elif trans and trans.lower() != word.lower():
                synonyms.add(trans)
                found_local = True
                
            # 2. Google Translate fallback for Arabic words NOT found locally
            if not found_local and self._is_arabic(word):
                google_result = self._google_translate_fallback(word)
                if google_result:
                    synonyms.add(google_result)

            bundle_list.append(list(synonyms))

        # 3. Final Fallback: If nothing matched and query is Arabic, try full Google translate
        if not bundle_list and self._is_arabic(clean_query):
            full_google = self._google_translate_fallback(clean_query)
            if full_google:
                bundle_list.append([clean_query, full_google])

=======
            # 1. Direct translation
            trans = self.translate_word(word)
            
            if isinstance(trans, list):
                for t in trans: synonyms.add(t)
            elif trans and trans.lower() != word.lower():
                synonyms.add(trans)
                
            # 2. Check for compound word matches in dictionary keys
            # (Simple heuristic: if word is part of a key, add the value)
            norm_word = self.normalize_text(word)
            for k, v in self.dictionary.items():
                if norm_word in self.normalize_text(k) and len(k.split()) > 1:
                     if isinstance(v, list):
                         for t in v: synonyms.add(t)
                     else:
                         synonyms.add(v)

            bundle_list.append(list(synonyms))

>>>>>>> 947f1af (update)
        return bundle_list

    # ---------------------------------
    # PDF FEATURES
    # ---------------------------------
    def extract_text_from_pdf(self, file_bytes):
        if not HAS_DEPS:
            return "Error: Libraries (pdfplumber) not installed."

        text = ""
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            return f"Error reading PDF: {str(e)}"

        return text

    def translate_full_text(self, text, target_lang='ar'):
        if not HAS_DEPS:
            return "Error: Libraries (deep-translator) not installed."
        if not text:
            return ""

<<<<<<< HEAD
        # Global Cache check
        cache_key = f"{target_lang}_{hashlib.md5(str(text).strip().encode()).hexdigest()}"
        if 'translation_cache' not in st.session_state:
            st.session_state.translation_cache = {}
        
        if cache_key in st.session_state.translation_cache:
            return st.session_state.translation_cache[cache_key]

=======
>>>>>>> 947f1af (update)
        try:
            chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
            translated_text = ""
            translator = GoogleTranslator(source='auto', target=target_lang)

            for chunk in chunks:
                translated_text += translator.translate(chunk) + "\n"

<<<<<<< HEAD
            # Save to session cache
            st.session_state.translation_cache[cache_key] = translated_text
=======
>>>>>>> 947f1af (update)
            return translated_text

        except Exception as e:
            return f"Translation Error: {str(e)}"
<<<<<<< HEAD

    def translate_ui_value(self, val, target_lang='ar'):
        """Bidirectional UI value translation using dictionaries and heuristics."""
        if not val: return val
        s = str(val).strip().lower()
        
        # Dictionary for English -> Arabic
        en_to_ar = {
            "pastry chef": "شيف حلويات",
            "male": "ذكر",
            "female": "أنثى",
            "yes": "نعم",
            "no": "لا",
            "waiter": "نادل",
            "waitress": "نادلة",
            "barista": "باريستا",
            "cleaner": "عامل نظافة",
            "cook": "طباخ",
            "chef": "شيف",
            "nurse": "ممرضة",
            "doctor": "طبيب",
            "driver": "سائق",
            "yes | yes": "نعم | نعم",
            "no | no": "لا | لا",
            "tabuk": "تبوك",
            "riyadh": "الرياض",
            "jeddah": "جدة",
            "dammam": "الدمام",
            "madinah": "المدينة المنورة",
            "rizal": "الجنس",
            "rizal | male": "الجنس | ذكر",
            "filipino": "فلبيني",
            "indian": "هندي",
            "bangladeshi": "بنجلاديشي",
            "nepali": "نيبالي",
            "pakistani": "باكستاني"
        }

        if target_lang == 'ar':
            # 1. Exact or partial dictionary check
            if s in en_to_ar: return en_to_ar[s]
            
            # 2. Check if it's already Arabic - if so, preserve it!
            if self._is_arabic(val): return val
            
            # 3. Heuristic for "City | City" or "Category | Gender"
            if '|' in val:
                parts = [self.translate_ui_value(p.strip(), 'ar') for p in val.split('|')]
                return " | ".join(parts)
            
            return val
        else:
            # Arabic to English
            # SPECIAL: If we want EN but it was originally AR, only translate if it's not a location or if needed.
            # But here we don't know the field. the caller (app.py) will handle the location exception.
            for k, v in self.dictionary.items():
                if k.strip().lower() == s:
                    return v[0] if isinstance(v, list) else v
            return val

=======
>>>>>>> 947f1af (update)
AR_TO_EN = {
    "بدكير": ["Manicure", "Nail Technician"],
    "منكير": ["Pedicure", "Nail Technician"],
    "بدكير منكير": ["Manicure", "Pedicure", "Nail Technician"],
    "مصففة شعر": ["Hair Stylist", "Hairdresser"],
    "تنظيف بشرة": ["Skin Care", "Facial Specialist"],
    "خادمة منزلية": ["Housemaid", "Domestic Worker"],
    "عاملة منزلية": ["Domestic Worker"],
    "شيف حلويات": ["Pastry Chef", "Dessert Chef"],
    "نادلة": ["Waitress"],
    "نادل": ["Waiter"],
    "باريستا": ["Barista"],
    "افريقي": ["Nigeria", "Kenya", "Ghana", "Ethiopia", "Sudan", "Morocco", "Tunisia", "Senegal"],
    "افريقية": ["Nigeria", "Kenya", "Ghana", "Ethiopia", "Sudan", "Morocco", "Tunisia", "Senegal"],
<<<<<<< HEAD
    "لا توجد خبرة": "No experience",
    "خبرة": "Experience",
}

=======
}


>>>>>>> 947f1af (update)
def translate_to_english(keyword: str):
    keyword = keyword.strip().lower()
    return AR_TO_EN.get(keyword, [])
