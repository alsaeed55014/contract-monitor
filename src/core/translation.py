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
            # --- Jobs / Professions (Comprehensive Specs) ---
            "باريستا": "Barista", "barista": "باريستا",
            "طباخ": "Cook", "cook": "طباخ",
            "شيف": "Chef", "chef": "شيف",
            "حلا": ["Pastry", "Dessert"], "حلويات": ["Pastry", "Dessert", "Sweets"],
            "نادل": ["Waiter", "Male"], "نادله": ["Waitress", "Female"],
            "نادلة": ["Waitress", "Female"], "waiter": "نادل", "waitress": "نادلة",
            "سائق": "Driver", "driver": "سائق",
            "خادمة": ["Housemaid", "Domestic"], "خادمه": ["Housemaid", "Domestic"],
            "عاملة": ["Housemaid", "Domestic", "Worker"], "عامله": ["Housemaid", "Domestic", "Worker"],
            "شغالة": ["Housemaid", "Domestic"], "منزلية": "Domestic", "منزليه": "Domestic",
            "ممرض": "Nurse", "nurse": "ممرض", "ممرضة": "Nurse",
            "طبيب": "Doctor", "doctor": "طبيب",
            "نظافة": "Cleaner", "cleaner": "نظافة", "عامل نظافة": "Cleaner", "عاملة نظافة": "Cleaner",
            "بدكير": ["Pedicure", "Technician"], "منكير": ["Manicure", "Technician"],
            "حلاق": "Barber", "barber": "حلاق", 
            "كوافير": ["Hairdresser", "Hair Stylist"], "hairdresser": "كوافير",
            "مصففة": ["Hairdresser", "Hair Stylist"], "مصففه": ["Hairdresser", "Hair Stylist"],
            "بشرة": "Skin", "بروتين": "Protein", "شعر": "Hair",
            "مساج": ["Massage", "Therapist"], "massage": "مساج",
            "سكرتيرة": "Secretary", "سكرتيره": "Secretary", "secretary": "سكرتيرة",
            "كاميرا": "Camera", "camera": "كاميرا", "كاميرات": "Camera",
            "مبرمج": "Programmer", "مهندس": "Engineer", "فني": "Technician",
            "ايطالي": "Italian", "restaurant": "مطعم", "مطعم": "Restaurant",
            "مكتب": "Office", "مكتبيه": "Office", "اعمال": "Work",
            "ppf": ["PPF", "Installer"],

            # --- Nationalities (Exhaustive African Countries) ---
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
            "نيجيري": "Nigerian", "نيجيرية": "Nigerian",
            "غاني": "Ghanaian", "غانية": "Ghanaian",
            "سنغالي": "Senegalese", "سنغالية": "Senegalese",
            "تونسي": "Tunisian", "تونسية": "Tunisian",
            "تنزاني": "Tanzanian", "تنزانية": "Tanzanian",
            "افريقي": ["Nigeria", "Kenya", "Ghana", "Ethiopia", "Senegal", "Sudan", "Morocco", "Tunisia", "Tanzania", "Uganda", "Somalia", "Eritrea", "Rwanda", "Burundi", "African"],
            "أفريقي": ["Nigeria", "Kenya", "Ghana", "Ethiopia", "Senegal", "Sudan", "Morocco", "Tunisia", "Tanzania", "Uganda", "Somalia", "Eritrea", "Rwanda", "Burundi", "African"],
            "افريقية": ["Nigeria", "Kenya", "Ghana", "Ethiopia", "Senegal", "Sudan", "Morocco", "Tunisia", "Tanzania", "Uganda", "Somalia", "Eritrea", "Rwanda", "Burundi", "African"],
            "أفريقية": ["Nigeria", "Kenya", "Ghana", "Ethiopia", "Senegal", "Sudan", "Morocco", "Tunisia", "Tanzania", "Uganda", "Somalia", "Eritrea", "Rwanda", "Burundi", "African"],

            # --- Gender / Sex ---
            "بنت": "Female", "girl": "Female", "سيدة": "Female", "lady": "Female",
            "امرأة": "Female", "woman": "Female", "انثى": "Female", "أنثى": "Female", "female": "Female",
            "ولد": "Male", "boy": "Male", "رجل": "Male", "man": "Male", "ذكر": "Male", "male": "Male",
        }

    def normalize_text(self, text):
        if not text: return ""
        text = str(text).lower().strip()
        # Remove Arabic definite article "ال" if it starts the word and the word is long enough
        if text.startswith("ال") and len(text) > 4:
            text = text[2:]
        # Essential normalization for search flexibility
        text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
        text = text.replace("ة", "ه").replace("ى", "ي")
        return text

    def translate_word(self, word):
        norm_word = self.normalize_text(word)
        # Check dictionary
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
        clean_query = query.lower().strip() # Initial cleanup
        # Phrases to ignore or skip (optional)
        ignore_words = ["جميع", "كل", "دول", "دولة", "قارة", "قاره"]
        
        words = clean_query.split()
        
        bundle_list = []
        for word in words:
            # Skip very short or ignore-listed words that don't add meaning
            if word in ignore_words or len(word) < 2:
                continue
                
            # For each word, create a set of synonyms (Arabic norm + English trans)
            synonyms = {word}
            trans = self.translate_word(word)
            
            if isinstance(trans, list):
                for t in trans:
                    synonyms.add(t.lower())
            elif trans.lower() != word.lower():
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
