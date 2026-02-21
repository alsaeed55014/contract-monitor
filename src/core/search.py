from .translation import TranslationManager
import re
import pandas as pd
from datetime import date
from dateutil import parser as dateutil_parser

class SmartSearchEngine:
    def __init__(self, data_frame=None):
        self.df = data_frame
        self.translator = TranslationManager()
        # Debug info stored after each search (accessible from app.py)
        self.last_debug = {}

    def set_data(self, df):
        self.df = df

    def normalize_phone(self, text):
        """
        Normalizes phone numbers:
        +96650... -> 50...
        050... -> 50...
        +966 59 422 3552 -> 594223552
        """
        digits = re.sub(r'\D', '', str(text))
        if digits.startswith('966'):
            digits = digits[3:]
        if digits.startswith('0'):
            digits = digits[1:]
        return digits

    def is_phone_query(self, query):
        """Detects if the query is likely a phone number."""
        # Strip spaces, plus, dashes first
        clean = re.sub(r'[\s\+\-\(\)]', '', str(query))
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
        
        # Store debug info for UI display
        self.last_debug = {
            'query_raw': query,
            'query_repr': repr(query),
            'query_bool': bool(query),
            'query_stripped': str(query).strip() if query else '',
            'total_before_search': len(results),
        }
        
        # Clean query
        query_clean = str(query).strip() if query else ""
        
        # 1. Text Search
        if query_clean:
            if self.is_phone_query(query_clean):
                # Strict Phone Search
                target_phone = self.normalize_phone(query_clean)
                self.last_debug['search_type'] = 'phone'
                self.last_debug['target_phone'] = target_phone
                
                # Find phone columns first for targeted search
                phone_cols = [c for c in results.columns if any(kw in str(c).lower() for kw in ['phone', 'جوال', 'هاتف', 'رقم', 'mobile', 'تليفون'])]
                
                def phone_match(row):
                    # If we found phone columns, search only those
                    if phone_cols:
                        for col in phone_cols:
                            cell_digits = self.normalize_phone(str(row.get(col, '')))
                            if target_phone and target_phone in cell_digits:
                                return True
                    
                    # Fallback: search all columns
                    for col in row.index:
                        if str(col).startswith('__'):
                            continue
                        cell_val = str(row[col])
                        cell_digits = self.normalize_phone(cell_val)
                        if target_phone and len(cell_digits) >= 5 and target_phone in cell_digits:
                            return True
                    return False
                
                mask = results.apply(phone_match, axis=1)
                results = results[mask]
                self.last_debug['matched_count'] = len(results)
                
            else:
                # Smart Text Search (Compound Search with AND logic)
                bundles = self.translator.analyze_query(query_clean)
                self.last_debug['search_type'] = 'text'
                self.last_debug['bundles'] = str(bundles)
                
                if not bundles:
                    # No meaningful search terms found → return all results
                    self.last_debug['note'] = 'Empty bundles, returning all'
                else:
                    def text_match(row):
                        # Join row to single string and normalize
                        # Skip internal columns
                        parts = []
                        for col in row.index:
                            if not str(col).startswith('__'):
                                parts.append(str(row[col]))
                        row_text = " ".join(parts).lower()
                        
                        # Normalize: only apply Arabic letter normalization, NOT ال-stripping
                        row_text_norm = (
                            row_text
                            .replace("أ", "ا")
                            .replace("إ", "ا")
                            .replace("آ", "ا")
                            .replace("ة", "ه")
                            .replace("ى", "ي")
                        )
                        
                        # AND Logic: Every bundle must have at least one synonym matching
                        for bundle in bundles:
                            found_match_for_bundle = False
                            for syn in bundle:
                                syn_norm = self.translator._normalize_query_word(syn)
                                # Use word-boundary matching for short terms to avoid
                                # substring false positives (e.g. "male" in "female")
                                if len(syn_norm) <= 6:
                                    # Word boundary match
                                    pattern = r'(?:^|[\s,:;.\-/])' + re.escape(syn_norm) + r'(?:[\s,:;.\-/]|$)'
                                    if re.search(pattern, row_text_norm):
                                        found_match_for_bundle = True
                                        break
                                else:
                                    # Longer terms: substring match is safe
                                    if syn_norm in row_text_norm:
                                        found_match_for_bundle = True
                                        break
                            
                            if not found_match_for_bundle:
                                return False
                                
                        return True

                    mask = results.apply(text_match, axis=1)
                    results = results[mask]
                    self.last_debug['matched_count'] = len(results)

        # 2. Apply Filters
        if filters:
            # Helper to parse dates
            def parse_dt(val):
                try:
                    if val is None or str(val).strip() == '':
                        return pd.NaT
                    
                    val_str = str(val).strip()
                    
                    # Convert Eastern Arabic numerals to Western
                    arabic_to_western = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
                    val_str = val_str.translate(arabic_to_western)
                    
                    # Handle Arabic AM/PM markers
                    if 'ص' in val_str or 'م' in val_str:
                        marker = 'AM' if 'ص' in val_str else 'PM'
                        val_str = re.sub(r'[صم]', '', val_str).strip()
                        val_str = val_str + " " + marker
                    
                    try:
                        return pd.Timestamp(dateutil_parser.parse(val_str, dayfirst=False))
                    except:
                        return pd.to_datetime(val_str, errors='coerce')
                except Exception:
                    return pd.NaT

            def normalize_str(s):
                if not s: return ""
                clean = re.sub(r'[^\w\u0600-\u06FF]', '', str(s)).lower()
                return clean

            def find_col(keywords):
                for col in results.columns:
                    c_norm = normalize_str(col)
                    for k in keywords:
                        kn = normalize_str(k)
                        if kn == c_norm or (len(kn) > 3 and kn in c_norm) or (len(c_norm) > 3 and c_norm in kn):
                            return col
                return None

            # Filter by Age (only if explicitly enabled)
            if filters.get('age_enabled') and 'age_min' in filters and 'age_max' in filters:
                age_col = find_col(["your Age:", "العمر", "Age", "السن", "age", "عمر"])
                if age_col:
                    results['__matched_age_col'] = age_col
                    results['__temp_age'] = pd.to_numeric(results[age_col].astype(str).str.extract(r'(\d+)')[0], errors='coerce')
                    results = results[
                        (results['__temp_age'].notna()) &
                        (results['__temp_age'] >= filters['age_min']) & 
                        (results['__temp_age'] <= filters['age_max'])
                    ]
                    results = results.drop(columns=['__temp_age'])

            # Filter by Contract End Date
            if filters.get('contract_enabled') and 'contract_end_start' in filters and 'contract_end_end' in filters:
                end_col = find_col(["When is your contract end date?", "تاريخ انتهاء العقد", "انتهاء العقد", "contract end date"])
                if end_col:
                    results['__matched_contract_col'] = end_col
                    results['__temp_end_date'] = results[end_col].apply(parse_dt)
                    s_date = pd.to_datetime(filters['contract_end_start']).normalize()
                    e_date = pd.to_datetime(filters['contract_end_end']).normalize() + pd.Timedelta(hours=23, minutes=59, seconds=59)
                    
                    valid_dates = results['__temp_end_date'].notna()
                    results = results[
                        valid_dates &
                        (results['__temp_end_date'] >= s_date) & 
                        (results['__temp_end_date'] <= e_date)
                    ]
                    results = results.drop(columns=['__temp_end_date'])

            # New: Filter by Expired Only
            if filters.get('expired_only'):
                end_col = find_col(["When is your contract end date?", "تاريخ انتهاء العقد", "انتهاء العقد", "contract end date"])
                if end_col:
                    results['__matched_contract_col'] = end_col
                    results['__temp_end_date'] = results[end_col].apply(parse_dt)
                    today = pd.Timestamp(date.today()).normalize()
                    
                    results = results[
                        results['__temp_end_date'].notna() &
                        (results['__temp_end_date'] < today)
                    ]
                    # Sorting will be handled in app.py or here? 
                    # User asked for sorting from oldest to newest.
                    results = results.sort_values(by='__temp_end_date', ascending=True)
                    results = results.drop(columns=['__temp_end_date'])

            # New: Filter by Working Status (No)
            if filters.get('not_working_only'):
                work_col = find_col(["Are you working now?", "Are you currently working?", "Are you working", "هل انت تعمل حالياً؟", "هل تعمل حالياً؟", "هل انت تعمل حاليا", "العمل الحالي", "working now"])
                if work_col:
                    results['__matched_work_col'] = work_col
                    # Normalize and check for "no" or "لا"
                    def is_no(val):
                        v = str(val).strip().lower()
                        # Inclusion for variations and potential typos like "No tr"
                        return v in ['no', 'لا', 'none', 'false', '0', 'no ', ' لا', 'n', 'no tr', 'no-tr']
                    results = results[results[work_col].apply(is_no)]

            # New: Filter by Transfer Count (dropdown)
            if filters.get('transfer_count'):
                trans_col = find_col(["How many times did you transfer your sponsorship", "عدد مرات نقل الكفالة", "Transfer Count"])
                if trans_col:
                    target_val = filters['transfer_count']
                    # Use substring or exact match depending on data quality
                    results = results[results[trans_col].astype(str).str.contains(target_val, case=False, na=False)]

            # Filter by Timestamp (Registration Date)
            if filters.get('date_enabled') and 'date_start' in filters and 'date_end' in filters:
                ts_col = find_col(["طابع زمني", "وقت التسجيل", "تاريخ التسجيل", "Timestamp"])
                if ts_col:
                    results['__matched_ts_col'] = ts_col
                    results['__temp_ts'] = results[ts_col].apply(parse_dt)
                    s_date = pd.to_datetime(filters['date_start']).normalize()
                    e_date = pd.to_datetime(filters['date_end']).normalize() + pd.Timedelta(hours=23, minutes=59, seconds=59)
                    
                    valid_dates = results['__temp_ts'].notna()
                    results = results[
                        valid_dates &
                        (results['__temp_ts'] >= s_date) & 
                        (results['__temp_ts'] <= e_date)
                    ]
                    results = results.drop(columns=['__temp_ts'])

        self.last_debug['final_count'] = len(results)
        return results
