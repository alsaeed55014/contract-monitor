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

        # =========================================
        # Multi-word phrases (checked FIRST)
        # =========================================
        self.phrases = {
            "عامل نظافة": "Cleaner",
            "عاملة نظافة": "Cleaner",
            "عامل منزلي": ["Housemaid", "Domestic", "Worker"],
            "عاملة منزلية": ["Housemaid", "Domestic", "Worker"],
            "بدكير منكير": ["Pedicure", "Manicure", "Nail", "Beauty", "Technician"],
            "صالون نسائي": ["Ladies Salon", "Beauty", "Salon"],
            # Note: "خادمة افريقية" intentionally NOT here so each word is processed independently (housemaid + African OR-group)
            "خادم منزلي": ["Housemaid", "Domestic", "Worker"],
        }

        # =========================================
        # Single-word dictionary
        # =========================================
        self.dictionary = {
            # ----- Jobs / Professions -----
            "باريستا": "Barista",
            "طباخ": "Cook",
            "طباخة": "Cook",
            "شيف": "Chef",
            "حلا": ["Pastry", "Dessert"],
            "حلويات": ["Pastry", "Dessert", "Sweets"],
            "نادل": ["Waiter", "Male"],
            "نادلة": ["Waitress", "Female"],
            "سائق": "Driver",
            "ممرض": "Nurse",
            "ممرضة": "Nurse",
            "طبيب": "Doctor",
            "طبيبة": "Doctor",
            "نظافة": "Cleaner",
            "عامل": "Worker",
            "عاملة": ["Housemaid", "Domestic", "Worker"],

            # Beauty / Salon
            "بدكير": ["Pedicure", "Technician"],
            "منكير": ["Manicure", "Technician"],
            "صالون": ["Salon", "Beauty"],
            "حلاق": "Barber",
            "كوافير": ["Hairdresser", "Hair Stylist"],
            "كوافيرة": ["Hairdresser", "Hair Stylist"],
            "مصففة": ["Hairdresser", "Hair Stylist"],
            "بشرة": "Skin",
            "بروتين": "Protein",
            "شعر": "Hair",
            "مساج": ["Massage", "Therapist"],

            # Office / Technical
            "سكرتيرة": "Secretary",
            "سكرتير": "Secretary",
            "كاميرا": "Camera",
            "كاميرات": "Camera",
            "مبرمج": "Programmer",
            "مهندس": "Engineer",
            "مهندسة": "Engineer",
            "فني": "Technician",
            "فنية": "Technician",
            "مطعم": "Restaurant",
            "ايطالي": "Italian",
            "مكتب": "Office",
            "مكتبيه": "Office",
            "اعمال": "Work",
            "ppf": ["PPF", "Installer"],

            # Domestic Workers
            "خادمة": ["Housemaid", "Domestic", "Maid"],
            "خادم": ["Housemaid", "Domestic"],
            "شغالة": ["Housemaid", "Domestic", "Maid"],
            "شغاله": ["Housemaid", "Domestic", "Maid"],
            "منزلية": "Domestic",
            "منزلي": "Domestic",

            # ----- Nationalities -----
            "فلبيني": "Filipino",
            "فلبينية": "Filipino",
            "فلبينيه": "Filipino",
            "هندي": "Indian",
            "هندية": "Indian",
            "هنديه": "Indian",
            "باكستاني": "Pakistani",
            "باكستانية": "Pakistani",
            "باكستانيه": "Pakistani",
            "بنجلاديشي": "Bangladeshi",
            "بنجالية": "Bangladeshi",
            "بنقالي": "Bangladeshi",
            "مصري": "Egyptian",
            "مصرية": "Egyptian",
            "مصريه": "Egyptian",
            "نيبالي": "Nepali",
            "نيبالية": "Nepali",
            "سيريلانكي": "Sri Lankan",
            "سيريلانكية": "Sri Lankan",
            "سريلانكي": "Sri Lankan",
            "سريلانكية": "Sri Lankan",
            "كيني": "Kenyan",
            "كينية": "Kenyan",
            "كينيه": "Kenyan",
            "اوغندي": "Ugandan",
            "اوغندية": "Ugandan",
            "اثيوبي": "Ethiopian",
            "اثيوبية": "Ethiopian",
            "حبشي": "Ethiopian",
            "حبشية": "Ethiopian",
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
            "غانيه": "Ghanaian",
            "سنغالي": "Senegalese",
            "سنغالية": "Senegalese",
            "تونسي": "Tunisian",
            "تونسية": "Tunisian",
            "تنزاني": "Tanzanian",
            "تنزانية": "Tanzanian",
            "صومالي": "Somali",
            "صومالية": "Somali",
            "اريتري": "Eritrean",
            "اريترية": "Eritrean",
            "رواندي": "Rwandan",
            "رواندية": "Rwandan",
            "كاميروني": "Cameroonian",
            "كاميرونية": "Cameroonian",
            "مالي": "Malian",
            "اندونيسي": "Indonesian",
            "اندونيسية": "Indonesian",

            # ----- Gender -----
            "ذكر": "Male",
            "انثى": "Female",
            "أنثى": "Female",
            "بنت": "Female",
            "سيدة": "Female",
            "امرأة": "Female",
            "ولد": "Male",
            "رجل": "Male",
        }

        # =========================================
        # African nationalities list (for OR-group expansion)
        # =========================================
        self.african_nationalities = [
            "Nigerian", "Kenyan", "Ghanaian", "Ethiopian",
            "Senegalese", "Sudanese", "Moroccan", "Tunisian",
            "Tanzanian", "Ugandan", "Somali", "Eritrean",
            "Rwandan", "Cameroonian", "Malian", "African",
        ]

        # Arabic words that trigger African expansion
        self.african_triggers = [
            "افريقي", "افريقية", "افريقيه",
            "أفريقي", "أفريقية", "أفريقيه",
        ]

        # Stop words to ignore in queries
        self.ignore_words = {"جميع", "كل", "دول", "دولة", "قارة", "قاره", "من", "في", "على"}

    # ---------------------------------
    # Normalization
    # ---------------------------------
    def normalize_text(self, text):
        if not text:
            return ""

        text = str(text).lower().strip()

        # Remove Arabic definite article "ال" from standalone words
        # For long strings (concatenated rows), don't strip from beginning
        # Only strip from short words (< 20 chars) to avoid stripping from row text
        if len(text) < 20 and text.startswith("ال") and len(text) > 3:
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

    def _normalize_query_word(self, word):
        """Normalize a single query word (strip ال, normalize letters)."""
        w = str(word).lower().strip()
        if w.startswith("ال") and len(w) > 3:
            w = w[2:]
        w = (
            w.replace("أ", "ا")
             .replace("إ", "ا")
             .replace("آ", "ا")
             .replace("ة", "ه")
             .replace("ى", "ي")
        )
        return w

    # ---------------------------------
    # Translation
    # ---------------------------------
    def translate_word(self, word):
        norm_word = self._normalize_query_word(word)
        for k, v in self.dictionary.items():
            if self._normalize_query_word(k) == norm_word:
                return v
        return word

    # ---------------------------------
    # Phrase-aware Query Analyzer
    # ---------------------------------
    def analyze_query(self, query):
        """
        Analyzes a query and returns bundles for search.
        Each bundle is a list of synonyms (OR logic within bundle).
        Bundles are combined with AND logic.
        
        Multi-word phrases are matched first (greedy),
        then remaining single words are translated.
        
        African nationality triggers produce a single OR-bundle
        of all African nationalities.
        """
        if not query or not str(query).strip():
            return []

        clean_query = str(query).lower().strip()

        # Phase 1: Extract multi-word phrases (greedy, longest first)
        remaining = clean_query
        bundle_list = []
        phrase_keys_sorted = sorted(self.phrases.keys(), key=len, reverse=True)

        for phrase_key in phrase_keys_sorted:
            norm_phrase = self._normalize_query_word(phrase_key)
            # Check every possible substring in remaining text
            norm_remaining = self._normalize_query_word(remaining)
            if norm_phrase in norm_remaining:
                # Found a phrase match
                trans = self.phrases[phrase_key]
                synonyms = set()
                synonyms.add(phrase_key)
                if isinstance(trans, list):
                    for t in trans:
                        synonyms.add(t.lower())
                else:
                    synonyms.add(trans.lower())
                bundle_list.append(list(synonyms))

                # Remove the matched phrase from remaining (using normalized comparison)
                # Find and remove the original text
                for variant in [phrase_key, self._normalize_query_word(phrase_key)]:
                    remaining = remaining.replace(variant, " ")
                # Also try to remove from normalized remaining
                words_to_remove = phrase_key.split()
                remaining_words = remaining.split()
                remaining_words = [w for w in remaining_words
                                   if self._normalize_query_word(w) not in
                                   [self._normalize_query_word(pw) for pw in words_to_remove]]
                remaining = " ".join(remaining_words)

        # Phase 2: Process remaining single words
        words = remaining.split()
        for word in words:
            word = word.strip()
            if not word or len(word) < 2:
                continue
            if word in self.ignore_words:
                continue

            norm_word = self._normalize_query_word(word)

            # Check if this is an African trigger
            is_african = False
            for trigger in self.african_triggers:
                if self._normalize_query_word(trigger) == norm_word:
                    is_african = True
                    break

            if is_african:
                # Create an OR-bundle with ALL African nationalities
                african_bundle = [n.lower() for n in self.african_nationalities]
                african_bundle.append(word)  # include original Arabic
                bundle_list.append(african_bundle)
                continue

            # Normal word translation
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
