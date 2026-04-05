import json
from pathlib import Path

files = ["state.json","service_account.json","notification_cache.json","credentials.json"]

for f in files:
    p = Path(f)
    if p.exists():
        print(f"{f} exists. Size: {p.stat().st_size} bytes")
        if p.stat().st_size > 5000000:
            print("  - File too large, skipping JSON validation")
            continue
        try:
            with open(f,"r",encoding="utf-8") as file:
                data = json.load(file)
                print(f"  - Valid JSON: {type(data)}")
        except Exception as e:
            print(f"  - Invalid JSON: {e}")
    else:
        print(f"{f} DOES NOT exist.")

try:
    import win10toast
    import gspread
    import oauth2client
    print("All dependencies are installed.")
except ImportError as e:
    print(f"Missing dependency: {e}")