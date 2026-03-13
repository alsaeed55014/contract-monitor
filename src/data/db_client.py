import gspread
import os
import pandas as pd
from datetime import datetime
import time
import streamlit as st
import hashlib

class DBClient:
    _instance = None
    _data_caches = {}
    _last_fetches = {}
    CACHE_DURATION = 300  # Increased to 5 Minutes for better performance
    NOTIF_CACHE_DURATION = 30  # Increased to 30s for background checks

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DBClient, cls).__new__(cls)
            cls._instance.client = None
            cls._instance.connect()
        return cls._instance

    def connect(self):
        """Initializes the connection to Google Sheets using modern gspread auth."""
        self.client = None
        
        # 1. Try connecting via Streamlit Secrets (Recommended for Cloud)
        try:
            if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
                key_dict = dict(st.secrets["gcp_service_account"])
                self.client = gspread.service_account_from_dict(key_dict)
                print("[DEBUG] Connected via Streamlit Secrets")
                return
        except Exception as e:
            print(f"[DEBUG] st.secrets check skipped or failed: {e}")
        
        # 2. Fallback to local file (Recommended for Local Dev)
        try:
            # Use absolute path for reliability
            creds_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'credentials.json')
            if not os.path.exists(creds_file):
                # Fallback to current working directory if not found in root relative to this file
                creds_file = 'credentials.json'

            if os.path.exists(creds_file):
                self.client = gspread.service_account(filename=creds_file)
                print(f"[DEBUG] Connected via {creds_file}")
                return
            else:
                self._error_msg = f"Credentials file not found at {os.path.abspath(creds_file)}"
                print(f"[ERROR] {self._error_msg}")
        except Exception as e:
            self._error_msg = f"Local file auth failed: {e}"
            print(f"[ERROR] {self._error_msg}")

    def fetch_data(self, url=None, force=False, retries=3, is_notif_check=False):
        """Fetches data from Google Sheets with caching and automatic retries."""
        if url is None:
            url = "https://docs.google.com/spreadsheets/d/1u87sScIve_-xT_jDG56EKFMXegzAxOqwVJCh3Irerrw/edit"

        current_time = time.time()
        cache_key = f"cache_{hashlib.md5(url.encode()).hexdigest()}"
        last_fetch_key = f"last_fetch_{hashlib.md5(url.encode()).hexdigest()}"

        # Initialize storage
        if not hasattr(self, '_data_caches'): self._data_caches = {}
        if not hasattr(self, '_last_fetches'): self._last_fetches = {}

        # Cache check
        effective_duration = self.NOTIF_CACHE_DURATION if is_notif_check else self.CACHE_DURATION
        
        if not force and cache_key in self._data_caches:
            if (current_time - self._last_fetches.get(last_fetch_key, 0) < effective_duration):
                print(f"[DEBUG] Cache Hit ({'Notif' if is_notif_check else 'Main'}) for {url[:30]}...")
                return self._data_caches[cache_key]

        if not self.client:
            self.connect()
            if not self.client:
                raise Exception(f"Connection Failed: {getattr(self, '_error_msg', 'Unknown Reason')}")

        for attempt in range(retries):
            try:
                sheet = self.client.open_by_url(url).sheet1
                data = sheet.get_all_values()
                
                if not data:
                    return pd.DataFrame()

                headers = [str(h).strip() for h in data[0]]
                # Handle duplicate headers
                seen = {}
                clean_headers = []
                for h in headers:
                    if not h: h = "Column"
                    if h in seen:
                        seen[h] += 1
                        clean_headers.append(f"{h}_{seen[h]}")
                    else:
                        seen[h] = 0
                        clean_headers.append(h)

                df = pd.DataFrame(data[1:], columns=clean_headers)
                
                # Injection of internal tracking columns
                row_ids = list(range(2, len(df) + 2))
                if '__sheet_row' not in df.columns:
                    df.insert(0, '__sheet_row', row_ids)
                df['__sheet_row_backup'] = row_ids
                
                self._data_caches[cache_key] = df
                self._last_fetches[last_fetch_key] = current_time
                return df

            except Exception as e:
                error_msg = str(e)
                if attempt < retries - 1 and any(x in error_msg.lower() for x in ["503", "unavailable", "quota"]):
                    wait_time = (attempt + 1) * 2
                    print(f"[RETRY] Attempt {attempt+1} failed ({error_msg}). Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                print(f"[ERROR] Spreadsheets API Error for {url[:30]}: {e}")
                raise e

    def fetch_customer_requests(self, force=False, is_notif_check=False):
        """Specifically fetches the Customer Requests sheet."""
        url = "https://docs.google.com/spreadsheets/d/1ZlLGXqbFSnKrr2J-PRnxRhxykwrNOgOE6Mb34Zei_FU/edit"
        return self.fetch_data(url=url, force=force, is_notif_check=is_notif_check)

    def find_row_by_data(self, worker_name, phone="", url=None):
        """Tries to find the row index by matching name and optionally phone."""
        df = self.fetch_data(url=url)
        if df.empty: return None
        
        name_col = next((c for c in df.columns if "name" in str(c).lower() or "الاسم" in str(c)), None)
        if not name_col: return None
        
        matches = df[df[name_col].astype(str).str.strip().str.lower() == str(worker_name).strip().lower()]
        
        if len(matches) == 1:
            return matches.iloc[0]['__sheet_row']
        
        if len(matches) > 1 and phone:
            phone_col = next((c for c in df.columns if "phone" in str(c).lower() or "جوال" in str(c)), None)
            if phone_col:
                final_matches = matches[matches[phone_col].astype(str).str.contains(str(phone))]
                if not final_matches.empty:
                    return final_matches.iloc[0]['__sheet_row']
        
        return None

    def delete_row(self, row_number, url=None):
        """Permanently deletes a row from Google Sheets."""
        if url is None:
            url = "https://docs.google.com/spreadsheets/d/1u87sScIve_-xT_jDG56EKFMXegzAxOqwVJCh3Irerrw/edit"

        if not self.client:
            self.connect()
        
        try:
            sheet = self.client.open_by_url(url).sheet1
            sheet.delete_rows(int(row_number))
            
            # Clear cache
            cache_key = f"cache_{hashlib.md5(url.encode()).hexdigest()}"
            if cache_key in self._data_caches:
                del self._data_caches[cache_key]
            
            return True
        except Exception as e:
            print(f"[ERROR] Failed to delete row: {e}")
            return False, str(e)

    def append_row(self, row_data, url):
        """Appends a new row to the specified Google Sheet."""
        if not self.client:
            self.connect()
        
        try:
            sheet = self.client.open_by_url(url).sheet1
            sheet.append_row(row_data)
            
            # Clear cache
            cache_key = f"cache_{hashlib.md5(url.encode()).hexdigest()}"
            if cache_key in self._data_caches:
                del self._data_caches[cache_key]
            
            return True
        except Exception as e:
            print(f"[ERROR] Failed to append row: {e}")
            return False, str(e)

    def get_headers(self, url=None):
        """Returns the list of headers for the current data."""
        if url is None:
            url = "https://docs.google.com/spreadsheets/d/1u87sScIve_-xT_jDG56EKFMXegzAxOqwVJCh3Irerrw/edit"
        
        cache_key = f"cache_{hashlib.md5(url.encode()).hexdigest()}"
        if cache_key in self._data_caches:
            return list(self._data_caches[cache_key].columns)
        return []
