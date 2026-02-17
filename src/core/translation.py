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
        self.dictionary = {
            "باريستا": "Barista", "barista": "باريستا",
            "طباخ": "Cook", "cook": "طباخ",
            "شيف": "Chef", "chef": "شيف",
            "نادل": "Waiter", "waiter": "نادل",
            "نادلة": "Waitress", "waitress": "نادلة",
            "سائق": "Driver", "driver": "سائق",
            "خادمة": "Housemaid", "housemaid": "خادمة",
            "عاملة": "Housemaid", "شغالة": "Housemaid",
            "ممرض": "Nurse", "nurse": "ممرض", "ممرضة": "Nurse",
            "طبيب": "Doctor", "doctor": "طبيب",
            
            "فلبيني": "Filipino", "filipino": "فلبيني", "فلبينية": "Filipino",
            "هندي": "Indian", "indian": "هندي",
            "باكستاني": "Pakistani", "pakistani": "باكستاني",
            "بنجلاديشي": "Bangladeshi", "bangladeshi": "بنجلاديشي",
            "مصري": "Egyptian", "egyptian": "مصري",
            "نيبالي": "Nepali", "nepali": "نيبالي",
            
            "بنت": "Female", "girl": "Female", "سيدة": "Female", "lady": "Female",
            "امرأة": "Female", "woman": "Female", "انثى": "Female", "أنثى": "Female", "female": "أنثى",
            "ولد": "Male", "boy": "Male", "رجل": "Male", "man": "Male", "ذكر": "Male", "male": "ذكر",
        }

    def normalize_text(self, text):
        if not text: return ""
        text = str(text).lower().strip()
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
        clean_query = self.normalize_text(query)
        words = clean_query.split()
        search_terms = set([clean_query])
        tokens_translated = []
        for word in words:
            search_terms.add(word)
            trans = self.translate_word(word)
            if trans.lower() != word:
                search_terms.add(trans.lower())
                tokens_translated.append(trans)
            else:
                tokens_translated.append(word)
        full_trans = " ".join(tokens_translated)
        if full_trans != clean_query:
            search_terms.add(full_trans)
        return list(search_terms)

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
