# src/core/translation.py
import re
import io

try:
    import pdfplumber
    from deep_translator import GoogleTranslator
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


class TranslationManager:
    # Cache for Google Translate results to avoid repeated API calls
    _google_cache = {}

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
            "عامل نظافة": "Cleaner",
            "عاملة نظافة": "Cleaner",

            # Beauty / Salon
            "بدكير": ["Pedicure", "Technician"],
            "منكير": ["Manicure", "Technician"],
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
            "اندونيسي": ["Indonesian", "Indonesia"],
            "اندونيسية": ["Indonesian", "Indonesia"],
            "اندونيسيا": "Indonesia",
            "اندونيسا": "Indonesia",
            "اندونيسيه": ["Indonesian", "Indonesia"],
            "مغربي": "Moroccan",
            "مغربية": "Moroccan",
            "سوداني": "Sudanese",
            "سودانية": "Sudanese",
            "يمني": "Yemeni",
            "يمنية": "Yemeni",
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
            "غاني": "Ghanaian",
            "غانية": "Ghanaian",
            "سنغالي": "Senegalese",
            "سنغالية": "Senegalese",
            "تونسي": "Tunisian",
            "تونسية": "Tunisian",
            "تنزاني": "Tanzanian",
            "تنزانية": "Tanzanian",
            "كينيا": "Kenya",
            "اوغندا": "Uganda",
            "اثيوبيا": "Ethiopia",

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
            "سيهات": "Saihat",
            "بقيق": "Abqaiq",
            "بريدة": ["Buraydah", "Qassim"],
            "عنيزة": ["Unaizah", "Qassim"],
            "الرس": ["Ar Rass", "Qassim"],
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
            "الخرج": ["Al Kharj", "Al-Kharj", "Central", "Alkharj", "Kharj"],
            "الدوادمي": ["Al-Duwadmi", "Duwadmi"],
            "المجمعة": ["Al Majma'ah", "Majmaah"],
            "الزلفي": ["Zulfi", "Az Zulfi"],
            "وادي الدواسر": ["Wadi ad-Dawasir", "Wadi Aldawasir"],
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
            "المنطقة الوسطى": ["Central", "Riyadh", "Al-Kharj", "Al Kharj", "Al Majma'ah", "Zulfi", "Wadi ad-Dawasir"],
            "المنطقة الغربية": ["Western", "Jeddah", "Makkah", "Madinah", "Taif", "Yanbu", "Rabigh", "Al Lith", "Al Qunfudhah"],
            "الوسطى": ["Central", "Riyadh", "Al-Kharj", "Al Kharj", "Al Majma'ah", "Zulfi"],
            "القصيم": ["Qassim", "Buraydah", "Unaizah", "Ar Rass", "Al Qassim", "AL QASSIM", "Qassim Region"],
            "منطقة القصيم": ["Qassim", "Buraydah", "Unaizah", "Ar Rass"],
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

    # ---------------------------------
    # Query Analyzer
    # ---------------------------------
    def _normalize_query_word(self, word):
        """Helper to normalize a single word for matching"""
        return self.normalize_text(word)

    def analyze_query(self, query):

        clean_query = query.lower().strip()
        ignore_words = ["جميع", "كل", "دول", "دولة", "قارة", "قاره"]

        # --- Step 0: Check full query as compound phrase FIRST ---
        compound_trans = self.translate_word(clean_query)
        compound_found = False
        if isinstance(compound_trans, list):
            compound_found = True
        elif compound_trans and compound_trans.lower() != clean_query.lower():
            compound_found = True
        
        if compound_found:
            # The full query matched a compound entry (e.g. "مصفف شعر" -> "Hairdresser")
            synonyms = {clean_query}
            if isinstance(compound_trans, list):
                for t in compound_trans: synonyms.add(t)
            else:
                synonyms.add(compound_trans)
            return [list(synonyms)]

        # --- Step 1: Split and translate word by word ---
        words = re.split(r'[\s,،/\\|]+', clean_query)
        bundle_list = []

        for word in words:
            if word in ignore_words or len(word) < 2:
                continue
            
            # Use a Set to avoid duplicates
            synonyms = {word}
            
            # 1. Direct translation from local dictionary
            trans = self.translate_word(word)
            found_local = False
            
            if isinstance(trans, list):
                for t in trans: synonyms.add(t)
                found_local = True
            elif trans and trans.lower() != word.lower():
                synonyms.add(trans)
                found_local = True
                
            # 2. Check for compound word matches in dictionary keys
            norm_word = self.normalize_text(word)
            for k, v in self.dictionary.items():
                if norm_word in self.normalize_text(k) and len(k.split()) > 1:
                     if isinstance(v, list):
                         for t in v: synonyms.add(t)
                         found_local = True
                     else:
                         synonyms.add(v)
                         found_local = True

            # 3. Google Translate fallback for Arabic words NOT found locally
            if not found_local and self._is_arabic(word):
                google_result = self._google_translate_fallback(word)
                if google_result:
                    synonyms.add(google_result)
                    # Also try the full query as a phrase via Google
                    if len(words) > 1:
                        full_google = self._google_translate_fallback(clean_query)
                        if full_google:
                            synonyms.add(full_google)

            bundle_list.append(list(synonyms))

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

        try:
            chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
            translated_text = ""
            translator = GoogleTranslator(source='auto', target=target_lang)

            for chunk in chunks:
                translated_text += translator.translate(chunk) + "\n"

            return translated_text

        except Exception as e:
            return f"Translation Error: {str(e)}"
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
}


def translate_to_english(keyword: str):
    keyword = keyword.strip().lower()
    return AR_TO_EN.get(keyword, [])
