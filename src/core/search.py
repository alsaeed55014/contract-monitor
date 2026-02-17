from .translation import TranslationManager
import re
import pandas as pd
from dateutil import parser as dateutil_parser

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
            return pd.DataFrame()

        results = self.df.copy()
        
        # 1. Text Search
        if query:
            if self.is_phone_query(query):
                # Strict Phone Search
                target_phone = self.normalize_phone(query)
                print(f" Calling Phone Search: {target_phone}")
                
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
                print(f" AI Strings: {keywords}")
                
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

        # 2. Apply Filters
        if filters:
            # Helper to parse dates
            def parse_dt(val):
                try:
                    if val is None or str(val).strip() == '':
                        return pd.NaT
                    
                    # Ensure it's a string and clean it
                    val_str = str(val).strip()
                    
                    # 1. Convert Eastern Arabic numerals to Western
                    arabic_to_western = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
                    val_str = val_str.translate(arabic_to_western)
                    
                    # 2. Extract Date parts if it's very long or contains Arabic markers
                    # Attempt to handle "2026/02/16 م 3:30:43"
                    if 'ص' in val_str or 'م' in val_str:
                        # Move Marker to end
                        marker = 'AM' if 'ص' in val_str else 'PM'
                        # Remove marker and any extra spaces
                        val_str = re.sub(r'[صم]', '', val_str).strip()
                        # Append marker at the end
                        val_str = val_str + " " + marker
                    
                    # 3. Handle standard formats
                    try:
                        # Try parsing with dateutil (aggressive)
                        return pd.Timestamp(dateutil_parser.parse(val_str, dayfirst=False))
                    except:
                        # Fallback to pandas
                        return pd.to_datetime(val_str, errors='coerce')
                except Exception as e:
                    print(f"[DEBUG] Parse Error on '{val}': {e}")
                    return pd.NaT

            # Helper for case-insensitive column finding
            def find_col(keywords):
                for col in results.columns:
                    # Very aggressive cleaning: lowercase, remove non-alphanumeric/non-arabic chars
                    col_raw = str(col).lower()
                    for k in keywords:
                        if k.lower() in col_raw:
                            return col
                return None

            # Filter by Age (only if explicitly enabled)
            if filters.get('age_enabled') and 'age_min' in filters and 'age_max' in filters:
                age_col = find_col(["age", "العمر", "السن", "your age", "عمر"])
                print(f"[SEARCH] Age column found: {age_col}")
                if age_col:
                    # Clean age column (remove non-digits)
                    results['__temp_age'] = pd.to_numeric(results[age_col].astype(str).str.extract(r'(\d+)')[0], errors='coerce')
                    before_count = len(results)
                    results = results[
                        (results['__temp_age'] >= filters['age_min']) & 
                        (results['__temp_age'] <= filters['age_max'])
                    ]
                    results = results.drop(columns=['__temp_age'])
                    print(f"[SEARCH] Age filter: {before_count} -> {len(results)} (range: {filters['age_min']}-{filters['age_max']})")
                else:
                    print(f"[WARN] Age column NOT found. Available columns: {list(results.columns)}")

            # Filter by Contract End Date
            if filters.get('contract_enabled') and 'contract_end_start' in filters and 'contract_end_end' in filters:
                end_col = find_col(["contract end", "انتهاء العقد", "when is your contract", "تاريخ انتهاء", "contract end date"])
                print(f"[SEARCH] Contract end column found: {end_col}")
                if end_col:
                    results['__temp_end_date'] = results[end_col].apply(parse_dt)
                    # Debug: show sample parsed dates
                    sample_raw = results[end_col].head(3).tolist()
                    sample_parsed = results['__temp_end_date'].head(3).tolist()
                    print(f"[SEARCH] Contract date samples - Raw: {sample_raw} -> Parsed: {sample_parsed}")
                    
                    s_date = pd.to_datetime(filters['contract_end_start']).normalize()
                    # End of day
                    e_date = pd.to_datetime(filters['contract_end_end']).normalize() + pd.Timedelta(hours=23, minutes=59, seconds=59)
                    
                    # Drop rows where date couldn't be parsed
                    valid_dates = results['__temp_end_date'].notna()
                    before_count = len(results)
                    results = results[
                        valid_dates &
                        (results['__temp_end_date'] >= s_date) & 
                        (results['__temp_end_date'] <= e_date)
                    ]
                    results = results.drop(columns=['__temp_end_date'])
                    print(f"[SEARCH] Contract filter: {before_count} -> {len(results)} (range: {s_date} to {e_date})")
                else:
                    print(f"[WARN] Contract end column NOT found. Available columns: {list(results.columns)}")

            # Filter by Timestamp (Registration Date)
            if filters.get('date_enabled') and 'date_start' in filters and 'date_end' in filters:
                ts_col = find_col(["timestamp", "طابع زمني", "تاريخ التسجيل", "تاريخ القيد", "registration", "وقت التسجيل"])
                print(f"[SEARCH] Timestamp column found: {ts_col}")
                if ts_col:
                    results['__temp_ts'] = results[ts_col].apply(parse_dt)
                    # Debug: show sample parsed dates
                    sample_raw = results[ts_col].head(3).tolist()
                    sample_parsed = results['__temp_ts'].head(3).tolist()
                    print(f"[SEARCH] Registration date samples - Raw: {sample_raw} -> Parsed: {sample_parsed}")
                    
                    s_date = pd.to_datetime(filters['date_start']).normalize()
                    # End of day
                    e_date = pd.to_datetime(filters['date_end']).normalize() + pd.Timedelta(hours=23, minutes=59, seconds=59)
                    
                    # Drop rows where date couldn't be parsed
                    valid_dates = results['__temp_ts'].notna()
                    before_count = len(results)
                    results = results[
                        valid_dates &
                        (results['__temp_ts'] >= s_date) & 
                        (results['__temp_ts'] <= e_date)
                    ]
                    results = results.drop(columns=['__temp_ts'])
                    print(f"[SEARCH] Registration filter: {before_count} -> {len(results)} (range: {s_date} to {e_date})")
                else:
                    print(f"[WARN] Timestamp column NOT found. Available columns: {list(results.columns)}")

        return results
