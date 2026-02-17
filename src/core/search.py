from .translation import TranslationManager
import re

class SmartSearchEngine:
    def __init__(self, data_frame=None):
        self.df = data_frame
        self.translator = TranslationManager()

    def set_data(self, df):
        self.df = df

    def normalize_phone(self, text):
        """
        Normalizes phone numbers:
        +96650... -> 50...
        050... -> 50...
        """
        digits = re.sub(r'\D', '', str(text))
        if digits.startswith('966'):
            digits = digits[3:]
        if digits.startswith('0'):
            digits = digits[1:]
        return digits

    def is_phone_query(self, query):
        """Detects if the query is likely a phone number."""
        clean = re.sub(r'[\s\+\-]', '', query)
        return clean.isdigit() and len(clean) >= 5

    def search(self, query, filters=None):
        """
        Performs a smart search on the dataframe.
        query: str - The search text.
        filters: dict - Optional filters {'age_min': 20, 'age_max': 30, ...}
        """
        if self.df is None or self.df.empty:
            return []

        results = self.df.copy()
        
        # 1. Text Search
        if query:
            if self.is_phone_query(query):
                # Strict Phone Search
                target_phone = self.normalize_phone(query)
                print(f"📞 Calling Phone Search: {target_phone}")
                
                def phone_match(row):
                    # Check all columns for now, or optimizing by checking only phone columns if known
                    row_str = " ".join(row.astype(str))
                    # Quick check
                    if target_phone in self.normalize_phone(row_str):
                        return True
                    return False
                
                mask = results.apply(phone_match, axis=1)
                results = results[mask]
                
            else:
                # Smart Text Search
                keywords = self.translator.analyze_query(query)
                print(f"🤖 AI Strings: {keywords}")
                
                def text_match(row):
                    # Join row to single string
                    row_text = " ".join(row.astype(str)).lower()
                    row_text_norm = self.translator.normalize_text(row_text)
                    
                    # If ANY keyword matches, it's a hit (Or Logic for Synonyms)
                    # Actually, for "Filipino Driver", we want AND logic for the concepts, 
                    # but OR logic for the synonyms of each concept. 
                    # Current simplifiction: If the whole translated phrase matches OR parts match.
                    # Let's try matching ALL original tokens OR their translations.
                    
                    # Better approach: 
                    # 1. Normalize Row
                    # 2. Check if ANY of the generated search_phrases form the full query exist?
                    # No, "Filipino Driver" -> "فلبيني سائق". 
                    # If user types "سائق فلبيني", we want it to match "Filipino Driver" in DB.
                    
                    # Check 1: Is the 'Translated Full Sentence' present?
                    for kw in keywords:
                        if kw.lower() in row_text_norm:
                            return True
                    return False

                mask = results.apply(text_match, axis=1)
                results = results[mask]

        # 2. Apply Filters (Age, Date, Expiry) - To be implemented based on columns
        # For now, we return text search results
        
        return results
