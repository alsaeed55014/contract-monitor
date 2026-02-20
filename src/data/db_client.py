import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import pandas as pd
from datetime import datetime
import time
import streamlit as st

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

    def fetch_data(self, force=False):
        """Fetches data from Google Sheets with caching."""
        current_time = time.time()
        
        # Check if cache exists and has the required tracking column
        if not force and self._data_cache is not None:
            if '__sheet_row' in self._data_cache.columns and (current_time - self._last_fetch < self.CACHE_DURATION):
                print("[DEBUG] Returning valid cached data")
                return self._data_cache
            else:
                print("[DEBUG] Cache missing tracking column or expired. Refreshing...")
                force = True

        if not self.client:
            try:
                self.connect()
            except Exception as e:
                raise e
            
            if not self.client:
                 raise Exception("Client failed to initialize even after connect()")

        try:
            # Using the URL provided in previous code
            sheet_url = "https://docs.google.com/spreadsheets/d/1u87sScIve_-xT_jDG56EKFMXegzAxOqwVJCh3Irerrw/edit"
            sheet = self.client.open_by_url(sheet_url).sheet1
            data = sheet.get_all_values()
            
            if not data:
                return pd.DataFrame()

            # Handle headers normalization
            headers = [str(h).strip() for h in data[0]]
            
            # Deduplicate headers
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

            # Create DataFrame
            df = pd.DataFrame(data[1:], columns=clean_headers)
            
            # Inject hidden sheet row index (1-indexed for gspread, starts at 2 because index 1 is header)
            # Triple injection to ensure it's not lost in selection/filtering
            row_ids = list(range(2, len(df) + 2))
            if '__sheet_row' not in df.columns:
                df.insert(0, '__sheet_row', row_ids)
            df['__sheet_row_backup'] = row_ids # Backup at the end
            
            self._data_cache = df
            self._last_fetch = current_time
            print(f"[DEBUG] Data fetched. Total records: {len(df)}. IDs injected at start and end.")
            return df

        except Exception as e:
            print(f"[ERROR] Error fetching data: {e}")
            raise e

    def find_row_by_data(self, worker_name, phone=""):
        """Fallback: Tries to find the row index by matching name and optionally phone."""
        df = self.fetch_data()
        if df.empty: return None
        
        # Search for exact name match
        name_col = next((c for c in df.columns if "name" in c.lower() or "الاسم" in c), None)
        if not name_col: return None
        
        matches = df[df[name_col].astype(str).str.strip().str.lower() == str(worker_name).strip().lower()]
        
        if len(matches) == 1:
            return matches.iloc[0]['__sheet_row']
        
        # If multiple matches, try phone
        if len(matches) > 1 and phone:
            phone_col = next((c for c in df.columns if "phone" in c.lower() or "جوال" in c), None)
            if phone_col:
                final_matches = matches[matches[phone_col].astype(str).str.contains(str(phone))]
                if not final_matches.empty:
                    return final_matches.iloc[0]['__sheet_row']
        
        return None

    def delete_row(self, row_number):
        """Permanently deletes a row from Google Sheets by its 1-indexed row number."""
        if not self.client:
            self.connect()
        
        try:
            sheet_url = "https://docs.google.com/spreadsheets/d/1u87sScIve_-xT_jDG56EKFMXegzAxOqwVJCh3Irerrw/edit"
            sheet = self.client.open_by_url(sheet_url).sheet1
            
            # Perform deletion
            sheet.delete_rows(int(row_number))
            
            # Clear cache to force refresh
            self._data_cache = None
            self._last_fetch = 0
            print(f"[DEBUG] Row {row_number} deleted successfully")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to delete row: {e}")
            return False, str(e)

    def get_headers(self):
        """Returns the list of headers."""
        if self._data_cache is not None:
            return list(self._data_cache.columns)
        return []
