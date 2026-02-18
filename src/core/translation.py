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
            "كوافير": ["Hairdresser", "Hair Stylist"],
            "مصففة": ["Hairdresser", "Hair Stylist"],
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
            "مصري": "Egyptian",
            "مصرية": "Egyptian",
            "نيبالي": "Nepali",
            "نيبالية": "Nepali",
            "سيريلانكي": "Sri Lankan",
            "سيريلانكية": "Sri Lankan",
            "كيني": "Kenyan",
            "كينية": "Kenyan",
            "اوغندي": "Ugandan",
            "اوغندية": "Ugandan",
            "اثيوبي": "Ethiopian",
            "اثيوبية": "Ethiopian",
            "مغربي": "Moroccan",
            "مغربية": "Moroccan",
            "سوداني": "Sudanese",
            "سودانية": "Sudanese",
            "يمني": "Yemeni",
            "يمنية": "Yemeni",
            "نيجيري": "Nigerian",
            "نيجيرية": "Nigerian",
            "غاني": "Ghanaian",
            "غانية": "Ghanaian",
            "سنغالي": "Senegalese",
            "سنغالية": "Senegalese",
            "تونسي": "Tunisian",
            "تونسية": "Tunisian",
            "تنزاني": "Tanzanian",
            "تنزانية": "Tanzanian",

            # Africa Continent Mapping
            "افريقي": [
                "Nigeria", "Kenya", "Ghana", "Ethiopia",
                "Senegal", "Sudan", "Morocco", "Tunisia",
                "Tanzania", "Uganda", "Somalia",
                "Eritrea", "Rwanda", "Burundi", "African"
            ],

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

    # ---------------------------------
    # Query Analyzer
    # ---------------------------------
    def analyze_query(self, query):

        clean_query = query.lower().strip()
        ignore_words = ["جميع", "كل", "دول", "دولة", "قارة", "قاره"]

        words = clean_query.split()
        bundle_list = []

        for word in words:
            if word in ignore_words or len(word) < 2:
                continue

            synonyms = {word}
            trans = self.translate_word(word)

            if isinstance(trans, list):
                for t in trans:
                    synonyms.add(t.lower())
            elif trans.lower() != word.lower():
                synonyms.add(trans.lower())

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
