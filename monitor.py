import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
from win10toast import ToastNotifier
import logging
import time
import os

# Setup Logging
logging.basicConfig(
    filename='contracts_report.txt',
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    encoding='utf-8'
)

def check_contracts():
    print("Starting contract check...")
    
    # scope
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # credentials
    creds_file = 'credentials.json'
    if not os.path.exists(creds_file):
        print(f"Error: {creds_file} not found. Please place it in the same directory.")
        return

    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)
        client = gspread.authorize(creds)
    except Exception as e:
        print(f"Error authenticating: {e}")
        return

    # Open Sheet
    # Using the URL provided by the user
    sheet_url = "https://docs.google.com/spreadsheets/d/1u87sScIve_-xT_jDG56EKFMXegzAxOqwVJCh3Irerrw/edit?resourcekey=&gid=2008131#gid=2008131"
    try:
        sheet = client.open_by_url(sheet_url).sheet1 # Assumes first sheet
        # Use get_all_values to avoid duplicate header error
        rows = sheet.get_all_values()
        if not rows:
            print("Sheet is empty.")
            return

        # Strip whitespace from headers first
        headers = [h.strip() for h in rows[0]]
        print(f"DEBUG: Found headers (cleaned): {headers}") # Debugging
        data_rows = rows[1:]

        # Helper to find column index safely
        def get_col_index(name):
            try:
                # Direct match
                return headers.index(name)
            except ValueError:
                # Case insensitive match
                for i, h in enumerate(headers):
                    if h.lower() == name.lower():
                        return i
                return -1

        date_col_idx = get_col_index("When is your contract end date?")
        name_col_idx = get_col_index("Full Name")
        nat_col_idx = get_col_index("Nationality")
        gender_col_idx = get_col_index("Gender")
        phone_col_idx = get_col_index("Phone Number")
        
        print(f"DEBUG: Date Column Index: {date_col_idx}")

        if date_col_idx == -1:
            print("Error: Column 'When is your contract end date?' not found.")
            print("Please check the column name in your sheet exactly.")
            # return # Don't return, let's see if we can find something else

    except Exception as e:
        print(f"Error opening sheet or processing headers: {e}")
        return

    toaster = ToastNotifier()
    
    today = datetime.now().date()
    target_date_2 = today + timedelta(days=2)
    target_date_7 = today + timedelta(days=7)
    
    print(f"Checking for contracts ending on: {target_date_2} (2 days) or {target_date_7} (7 days)")

    found_count = 0
    row_count = 0
    for row in data_rows:
        row_count += 1
        # Get data safely by index
        try:
            date_str = row[date_col_idx] if date_col_idx != -1 and len(row) > date_col_idx else ""
            
            if not date_str:
                continue
                
            # Try parsing multiple formats
            from dateutil import parser
            try:
                contract_end_date = parser.parse(str(date_str)).date()
            except:
                print(f"DEBUG: Failed to parse date: '{date_str}'")
                continue
            
            days_left = (contract_end_date - today).days
            # print(f"DEBUG: Row {row_count} - Date: {contract_end_date} - Days Left: {days_left}") # Uncomment to see every date
            
            if days_left == 2 or days_left == 7:
                print(f"MATCH FOUND: Row {row_count} - Date: {contract_end_date} ({days_left} days)")
                found_count += 1
                
                alert_type = "2 Days" if days_left == 2 else "1 Week"
                
                # Extract required fields
                full_name = row[name_col_idx] if name_col_idx != -1 and len(row) > name_col_idx else "N/A"
                nationality = row[nat_col_idx] if nat_col_idx != -1 and len(row) > nat_col_idx else "N/A"
                gender = row[gender_col_idx] if gender_col_idx != -1 and len(row) > gender_col_idx else "N/A"
                phone = row[phone_col_idx] if phone_col_idx != -1 and len(row) > phone_col_idx else "N/A"
                
                msg = f"Name: {full_name}\nMobile: {phone}\nNat: {nationality}\nGender: {gender}"
                
                # Notification
                print(f"ALERT FOUND ({alert_type}): {msg}")
                toaster.show_toast(
                    f"Contract Expiry Alert ({alert_type})",
                    msg,
                    duration=10,
                    threaded=True
                )
                
                # Log to file
                logging.info(f"CONTRACT EXPIRY ALERT ({alert_type}): {row}")
                
        except Exception as e:
            # print(f"Error processing row: {e}")
            continue
            
    if found_count == 0:
        print(f"No contracts found expiring in exactly 2 days or 7 days. Checked {row_count} rows.")
    else:
        print(f"Found {found_count} contracts expiring in 2 days or 7 days. Checked {row_count} rows.")

if __name__ == "__main__":
    check_contracts()
    # To keep the window open briefly if run via double-click
    input("Press Enter to exit...")
