import re
import io

# Try importing dependencies, handle if missing
try:
    import pdfplumber
    from deep_translator import GoogleTranslator
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

class TranslationManager:
    def __init__(self):
        # Dictionary: Maps Arabic keywords to English or multiple English synonyms
        self.dictionary = {
            # --- Jobs / Professions ---
            "باريستا": "Barista", "barista": "باريستا",
            "طباخ": "Cook", "cook": "طباخ",
            "شيف": "Chef", "chef": "شيف",
            "نادل": "Waiter", "waiter": "نادل", "نادلة": "Waitress", "waitress": "نادلة",
            "سائق": "Driver", "driver": "سائق",
            "خادمة": "Housemaid", "housemaid": "خادمة", "خادمه": "Housemaid",
            "عاملة": "Housemaid", "عامله": "Housemaid", "شغالة": "Housemaid",
            "منزلية": "Housemaid", "منزليه": "Housemaid",
            "ممرض": "Nurse", "nurse": "ممرض", "ممرضة": "Nurse",
            "طبيب": "Doctor", "doctor": "طبيب",
            "نظافة": "Cleaner", "cleaner": "نظافة", "عامل نظافة": "Cleaner", "عاملة نظافة": "Cleaner",
            "بدكير": "Pedicure", "pedicure": "بدكير", "منكير": "Manicure", "manicure": "منكير",
            "حلاق": "Barber", "barber": "حلاق", "كوافير": "Hairdresser", "hairdresser": "كوافير", "مصففة": "Hairdresser", "مصففه": "Hairdresser",
            "خياط": "Tailor", "tailor": "خياط",
            "كهربائي": "Electrician", "electrician": "كهربائي",
            "سباك": "Plumber", "plumber": "سباك",
            "عامل": "Worker", "worker": "عامل",
            "فني": "Technician", "technician": "فني",
            "محاسب": "Accountant", "accountant": "محاسب",
            "مبيعات": "Sales", "sales": "مبيعات",
            "استقبال": "Reception", "reception": "استقبال",
            "أمن": "Security", "security": "أمن",
            "نجار": "Carpenter", "carpenter": "نجار",
            "دهان": "Painter", "painter": "دهان",
            "حداد": "Blacksmith", "blacksmith": "حداد",
            "خبير": "Expert", "expert": "خبير",
            "سكرتيرة": "Secretary", "secretary": "سكرتيرة", "سكرتيره": "Secretary",
            "كاميرا": "Camera", "camera": "كاميرا", "كاميرات": "Camera",
            "مبرمج": "Programmer", "مهندس": "Engineer",
            "مساج": "Massage", "massage": "مساج",
            "تنظيف": "Cleaning", "cleaning": "تنظيف",
            "بشرة": "Skin", "بروتين": "Protein", "حلا": "Dessert", "حلويات": "Sweets", "شعر": "Hair",
            "ايطالي": "Italian", "restaurant": "مطعم", "مطعم": "Restaurant",
            "مكتب": "Office", "مكتبيه": "Office", "اعمال": "Work",
            "ppf": "PPF",

            # --- Nationalities ---
            "فلبيني": "Filipino", "filipino": "فلبيني", "فلبينية": "Filipino", "فلبينيه": "Filipino",
            "هندي": "Indian", "indian": "هندي", "هندية": "Indian",
            "باكستاني": "Pakistani", "pakistani": "باكستاني", "باكستانية": "Pakistani",
            "بنجلاديشي": "Bangladeshi", "bangladeshi": "بنجلاديشي", "بنجالية": "Bangladeshi",
            "مصري": "Egyptian", "egyptian": "مصري", "مصرية": "Egyptian",
            "نيبالي": "Nepali", "nepali": "نيبالي", "نيبالية": "Nepali",
            "سيريلانكي": "Sri Lankan", "sri lankan": "سيريلانكي", "سيريلانكية": "Sri Lankan",
            "كينيا": "Kenyan", "كيني": "Kenyan", "كينية": "Kenyan",
            "اوغندي": "Ugandan", "اوغندية": "Ugandan",
            "اثيوبي": "Ethiopian", "اثيوبية": "Ethiopian",
            "مغربي": "Moroccan", "مغربية": "Moroccan",
            "سوداني": "Sudanese", "سودانية": "Sudanese",
            "يمني": "Yemeni", "يمنية": "Yemeni",
            "افريقي": ["Kenyan", "Ugandan", "Ethiopian", "Nigerian", "Ghanaian", "African", "Tanzanian", "Sudanese", "Moroccan", "Eritrean", "Somali", "Burundian", "Rwandan"],
            "أفريقي": ["Kenyan", "Ugandan", "Ethiopian", "Nigerian", "Ghanaian", "African", "Tanzanian", "Sudanese", "Moroccan", "Eritrean", "Somali", "Burundian", "Rwandan"],
            "افريقية": ["Kenyan", "Ugandan", "Ethiopian", "Nigerian", "Ghanaian", "African", "Tanzanian", "Sudanese", "Moroccan", "Eritrean", "Somali", "Burundian", "Rwandan"],

            # --- Gender / Sex ---
            "بنت": "Female", "girl": "Female", "سيدة": "Female", "lady": "Female",
            "امرأة": "Female", "woman": "Female", "انثى": "Female", "أنثى": "Female", "female": "أنثى",
            "ولد": "Male", "boy": "Male", "رجل": "Male", "man": "Male", "ذكر": "Male", "male": "ذكر",
        }

    def normalize_text(self, text):
        if not text: return ""
        text = str(text).lower().strip()
        # Essential normalization for search flexibility
        text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
        text = text.replace("ة", "ه").replace("ى", "ي")
        return text

    def translate_word(self, word):
        norm_word = self.normalize_text(word)
        for k, v in self.dictionary.items():
            if self.normalize_text(k) == norm_word:
                return v
        return word

    def analyze_query(self, query):
        """
        Breaks query into bundles of synonyms.
        Example: "فلبيني باريستا" -> [["فلبيني", "Filipino"], ["باريستا", "Barista"]]
        Supports list of synonyms for a single word.
        """
        clean_query = self.normalize_text(query)
        words = clean_query.split()
        
        bundle_list = []
        for word in words:
            # For each word, create a set of synonyms (Arabic norm + English trans)
            synonyms = {word}
            trans = self.translate_word(word)
            
            if isinstance(trans, list):
                for t in trans:
                    synonyms.add(t.lower())
            elif trans.lower() != word:
                synonyms.add(trans.lower())
                
            bundle_list.append(list(synonyms))
            
        return bundle_list

    # --- PDF TRANSLATION FEATURES ---
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
            # Chunking to avoid limits (5000 chars usually)
            chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
            translated_text = ""
            translator = GoogleTranslator(source='auto', target=target_lang)
            
            for chunk in chunks:
                translated_text += translator.translate(chunk) + "\n"
            
            return translated_text
        except Exception as e:
            return f"Translation Error: {str(e)}"
