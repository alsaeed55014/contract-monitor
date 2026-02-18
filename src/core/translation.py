import re
import io
from itertools import product

try:
    import pdfplumber
    from deep_translator import GoogleTranslator
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


class TranslationManager:
    def __init__(self):

        # -------------------------
        # Dictionary
        # -------------------------
        self.dictionary = {

            # Jobs
            "باريستا": ["Barista"],
            "طباخ": ["Cook", "Chef"],
            "شيف": ["Chef"],
            "نظافه": ["Cleaner"],
            "عامل نظافه": ["Cleaner"],
            "عامله نظافه": ["Cleaner"],
            "بدكير": ["Pedicure", "Technician"],
            "منكير": ["Manicure", "Technician"],
            "حلاق": ["Barber"],
            "مصفف شعر": ["Hairdresser", "Hair Stylist"],
            "كوافير": ["Hairdresser", "Hair Stylist"],
            "مساج": ["Massage", "Therapist"],
            "سويت": ["Suite"],
            "خادمه": ["Housemaid", "Domestic Worker"],
            "عامله منزليه": ["Housemaid", "Domestic Worker"],
            "عامله": ["Worker"],
            "عامل": ["Worker"],

            # Nationalities
            "فلبيني": ["Filipino"],
            "فلبينيه": ["Filipino"],
            "هندي": ["Indian"],
            "هنديه": ["Indian"],
            "مصري": ["Egyptian"],
            "مغربي": ["Moroccan"],

            # Gender
            "ذكر": ["Male"],
            "رجل": ["Male"],
            "ولد": ["Male"],
            "انثى": ["Female"],
            "بنت": ["Female"],
            "سيده": ["Female"],
            "امراه": ["Female"],
        }

    # ---------------------------------
    # Normalize Arabic
    # ---------------------------------
    def normalize_text(self, text):
        if not text:
            return ""

        text = str(text).lower().strip()

        text = (
            text.replace("أ", "ا")
                .replace("إ", "ا")
                .replace("آ", "ا")
                .replace("ة", "ه")
                .replace("ى", "ي")
        )

        if text.startswith("ال") and len(text) > 3:
            text = text[2:]

        return text

    # ---------------------------------
    # Normalize Phone Numbers
    # ---------------------------------
    def normalize_phone(self, text):
        digits = re.sub(r"\D", "", text)

        variants = set()

        if digits.startswith("966"):
            local = digits[3:]
            variants.add(local)
            variants.add("0" + local)

        if digits.startswith("0"):
            variants.add(digits)
            variants.add(digits[1:])

        if len(digits) == 9:
            variants.add(digits)
            variants.add("0" + digits)

        return list(variants)

    # ---------------------------------
    # Extract multi-word phrases
    # ---------------------------------
    def extract_phrases(self, query):
        words = query.split()
        phrases = []

        # Try 2-word combinations
        for i in range(len(words) - 1):
            two = words[i] + " " + words[i + 1]
            phrases.append(two)

        return phrases

    # ---------------------------------
    # Query Analyzer (Advanced)
    # ---------------------------------
    def analyze_query(self, query):

        query = self.normalize_text(query)

        # Detect phone number
        phone_variants = self.normalize_phone(query)
        if phone_variants:
            return phone_variants

        words = query.split()
        phrases = self.extract_phrases(query)

        bundles = []

        # Check phrases first
        for phrase in phrases:
            norm = self.normalize_text(phrase)
            if norm in self.dictionary:
                bundles.append(self.dictionary[norm])

        # Then single words
        for word in words:
            norm = self.normalize_text(word)

            if norm in self.dictionary:
                bundles.append(self.dictionary[norm])
            else:
                bundles.append([word])

        # Generate combined search possibilities
        combinations = list(product(*bundles))

        final_queries = []
        for combo in combinations:
            final_queries.append(" ".join(combo))

        return final_queries

    # ---------------------------------
    # PDF Features (unchanged)
    # ---------------------------------
    def extract_text_from_pdf(self, file_bytes):
        if not HAS_DEPS:
            return "Error: Libraries not installed."

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
            return "Error: Libraries not installed."
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
