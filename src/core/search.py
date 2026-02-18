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
                # Smart Text Search (Compound Search with AND logic)
                # bundles = [[syn1, syn2], [syn3, syn4]]
                bundles = self.translator.analyze_query(query)
                print(f" [SEARCH] Keyword Bundles: {bundles}")
                
                def text_match(row):
                    # Join row to single string and normalize
                    row_text = " ".join(row.astype(str)).lower()
                    row_text_norm = self.translator.normalize_text(row_text)
                    
                    # AND Logic: Every bundle must have at least one synonym matching in the row
                    for bundle in bundles:
                        found_match_for_bundle = False
                        for syn in bundle:
                            if syn in row_text_norm:
                                found_match_for_bundle = True
                                break
                        
                        if not found_match_for_bundle:
                            return False # This bundle failed, so query fails for this row
                            
                    return True # All bundles satisfied

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

            def normalize_str(s):
                if not s: return ""
                # Strip EVERYTHING except letters and numbers (English & Arabic)
                clean = re.sub(r'[^\w\u0600-\u06FF]', '', str(s)).lower()
                # print(f"[DEBUG] Normalizing '{s}' -> '{clean}'") # Internal debug
                return clean

            def find_col(keywords):
                # We'll return the first column that matches ANY of the keywords
                for col in results.columns:
                    c_norm = normalize_str(col)
                    for k in keywords:
                        kn = normalize_str(k)
                        # Match if keyword (normalized) is exactly the column (normalized) 
                        # OR if it's a significant part of it
                        if kn == c_norm or (len(kn) > 3 and kn in c_norm) or (len(c_norm) > 3 and c_norm in kn):
                            return col
                return None

            # Filter by Age (only if explicitly enabled)
            if filters.get('age_enabled') and 'age_min' in filters and 'age_max' in filters:
                age_col = find_col(["your Age:", "العمر", "Age", "السن", "age", "عمر"])
                if age_col:
                    results['__matched_age_col'] = age_col # For UI diagnostic
                    # Clean age column (remove non-digits)
                    results['__temp_age'] = pd.to_numeric(results[age_col].astype(str).str.extract(r'(\d+)')[0], errors='coerce')
                    before_count = len(results)
                    results = results[
                        (results['__temp_age'].notna()) &
                        (results['__temp_age'] >= filters['age_min']) & 
                        (results['__temp_age'] <= filters['age_max'])
                    ]
                    print(f"[SEARCH] Age filter: {before_count} -> {len(results)}")
                    results = results.drop(columns=['__temp_age'])
                else:
                    print(f"[WARN] Age column NOT found. Available: {list(results.columns)}")

            # Filter by Contract End Date
            if filters.get('contract_enabled') and 'contract_end_start' in filters and 'contract_end_end' in filters:
                end_col = find_col(["When is your contract end date?", "تاريخ انتهاء العقد", "انتهاء العقد", "contract end date"])
                if end_col:
                    results['__matched_contract_col'] = end_col # For UI diagnostic
                    results['__temp_end_date'] = results[end_col].apply(parse_dt)
                    s_date = pd.to_datetime(filters['contract_end_start']).normalize()
                    e_date = pd.to_datetime(filters['contract_end_end']).normalize() + pd.Timedelta(hours=23, minutes=59, seconds=59)
                    
                    valid_dates = results['__temp_end_date'].notna()
                    before_count = len(results)
                    results = results[
                        valid_dates &
                        (results['__temp_end_date'] >= s_date) & 
                        (results['__temp_end_date'] <= e_date)
                    ]
                    print(f"[SEARCH] Contract filter used column '{end_col}': {before_count} -> {len(results)} rows. Samples: {results[end_col].head(2).tolist()}")
                    results = results.drop(columns=['__temp_end_date'])
                else:
                    print(f"[WARN] Contract column NOT found. Available: {list(results.columns)}")

            # Filter by Timestamp (Registration Date)
            if filters.get('date_enabled') and 'date_start' in filters and 'date_end' in filters:
                ts_col = find_col(["طابع زمني", "وقت التسجيل", "تاريخ التسجيل", "Timestamp"])
                if ts_col:
                    results['__matched_ts_col'] = ts_col # For UI diagnostic
                    results['__temp_ts'] = results[ts_col].apply(parse_dt)
                    s_date = pd.to_datetime(filters['date_start']).normalize()
                    e_date = pd.to_datetime(filters['date_end']).normalize() + pd.Timedelta(hours=23, minutes=59, seconds=59)
                    
                    valid_dates = results['__temp_ts'].notna()
                    before_count = len(results)
                    results = results[
                        valid_dates &
                        (results['__temp_ts'] >= s_date) & 
                        (results['__temp_ts'] <= e_date)
                    ]
                    print(f"[SEARCH] Timestamp filter: {before_count} -> {len(results)}")
                    results = results.drop(columns=['__temp_ts'])
                else:
                    print(f"[WARN] Timestamp column NOT found. Available: {list(results.columns)}")

        return results
