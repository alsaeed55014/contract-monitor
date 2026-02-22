import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import pandas as pd
from datetime import datetime
import time
import streamlit as st
import hashlib

class DBClient:
    _instance = None
    _data_cache = None
    _last_fetch = 0
    CACHE_DURATION = 300  # 5 Minutes

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DBClient, cls).__new__(cls)
            cls._instance.client = None
            cls._instance.connect()
        return cls._instance

    def connect(self):
        """Initializes the connection to Google Sheets."""
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            
            # 1. Try connecting via Streamlit Secrets (Recommended for Cloud)
            try:
                if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
                    # Create a dictionary from secrets
                    key_dict = dict(st.secrets["gcp_service_account"])
                    creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
                    self.client = gspread.authorize(creds)
                    print("[DEBUG] Connected to Google Sheets via Secrets")
                    return
            except Exception:
                # Silently ignore if secrets are not configured or file is missing
                print("[DEBUG] Streamlit Secrets not available or not configured")
                pass

            # 2. Fallback to local file (for local testing)
            self.creds_file = 'credentials.json'
            if os.path.exists(self.creds_file):
                creds = ServiceAccountCredentials.from_json_keyfile_name(self.creds_file, scope)
                self.client = gspread.authorize(creds)
                print("[DEBUG] Connected to Google Sheets via File")
            else:
                print("[ERROR] Credentials file not found & No Secrets available")
                
        except Exception as e:
            print(f"[ERROR] Connection Error: {e}")
            st.error(f"Connection Failed: {e}") # Show in UI immediately
            raise e

    def fetch_data(self, url=None, force=False):
        """Fetches data from Google Sheets with caching. 'url' defaults to main worker sheet."""
        current_time = time.time()
        
        # Use main sheet if no URL provided
        if url is None:
            url = "https://docs.google.com/spreadsheets/d/1u87sScIve_-xT_jDG56EKFMXegzAxOqwVJCh3Irerrw/edit"

        cache_key = f"cache_{hashlib.md5(url.encode()).hexdigest()}"
        last_fetch_key = f"last_fetch_{hashlib.md5(url.encode()).hexdigest()}"

        # Initialize storage for this specific URL if not exists
        if not hasattr(self, '_data_caches'): self._data_caches = {}
        if not hasattr(self, '_last_fetches'): self._last_fetches = {}

        # Check if cache exists
        if not force and cache_key in self._data_caches:
            if (current_time - self._last_fetches.get(last_fetch_key, 0) < self.CACHE_DURATION):
                print(f"[DEBUG] Returning cached data for {url[:30]}...")
                return self._data_caches[cache_key]

        if not self.client:
            self.connect()

        try:
            sheet = self.client.open_by_url(url).sheet1
            data = sheet.get_all_values()
            
            if not data:
                return pd.DataFrame()

            headers = [str(h).strip() for h in data[0]]
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
            
            # Inject hidden sheet row index
            row_ids = list(range(2, len(df) + 2))
            if '__sheet_row' not in df.columns:
                df.insert(0, '__sheet_row', row_ids)
            df['__sheet_row_backup'] = row_ids
            
            self._data_caches[cache_key] = df
            self._last_fetches[last_fetch_key] = current_time
            return df

        except Exception as e:
            print(f"[ERROR] Error fetching data: {e}")
            raise e

    def fetch_customer_requests(self, force=False):
        """Specifically fetches the Customer Requests sheet."""
        url = "https://docs.google.com/spreadsheets/d/1ZlLGXqbFSnKrr2J-PRnxRhxykwrNOgOE6Mb34Zei_FU/edit"
        return self.fetch_data(url=url, force=force)

    def find_row_by_data(self, worker_name, phone="", url=None):
        """Fallback: Tries to find the row index by matching name and optionally phone."""
        df = self.fetch_data(url=url)
        if df.empty: return None
        
        name_col = next((c for c in df.columns if "name" in c.lower() or "الاسم" in c), None)
        if not name_col: return None
        
        matches = df[df[name_col].astype(str).str.strip().str.lower() == str(worker_name).strip().lower()]
        
        if len(matches) == 1:
            return matches.iloc[0]['__sheet_row']
        
        if len(matches) > 1 and phone:
            phone_col = next((c for c in df.columns if "phone" in c.lower() or "جوال" in c), None)
            if phone_col:
                final_matches = matches[matches[phone_col].astype(str).str.contains(str(phone))]
                if not final_matches.empty:
                    return final_matches.iloc[0]['__sheet_row']
        
        return None

    def delete_row(self, row_number, url=None):
        """Permanently deletes a row from Google Sheets by its 1-indexed row number."""
        if url is None:
            url = "https://docs.google.com/spreadsheets/d/1u87sScIve_-xT_jDG56EKFMXegzAxOqwVJCh3Irerrw/edit"

        if not self.client:
            self.connect()
        
        try:
            sheet = self.client.open_by_url(url).sheet1
            sheet.delete_rows(int(row_number))
            
            # Clear cache for this URL
            cache_key = f"cache_{hashlib.md5(url.encode()).hexdigest()}"
            if hasattr(self, '_data_caches') and cache_key in self._data_caches:
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
            
            # Clear cache for this URL
            cache_key = f"cache_{hashlib.md5(url.encode()).hexdigest()}"
            if hasattr(self, '_data_caches') and cache_key in self._data_caches:
                del self._data_caches[cache_key]
            
            return True
        except Exception as e:
            print(f"[ERROR] Failed to append row: {e}")
            return False, str(e)

    def get_headers(self, url=None):
        """Returns the list of headers."""
        cache_key = f"cache_{hashlib.md5(url.encode()).hexdigest()}" if url else "cache_default"
        if hasattr(self, '_data_caches') and cache_key in self._data_caches:
            return list(self._data_caches[cache_key].columns)
        return []
