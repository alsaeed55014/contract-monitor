# antigravity_notification.py
# نسخة جاهزة لتطبيق برمبيت Antigravity

import os
import json
import time
import logging
from pathlib import Path
from threading import Thread
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import subprocess

# -------------------------
# إعداد نظام التسجيل (Logging)
# -------------------------
LOG_FILE = "notification_service.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler() # للعرض في الطرفية أيضاً
    ]
)

def send_notification(title, message):
    """Sends a Windows toast notification using a PowerShell script for maximum reliability."""
    try:
        # Use PowerShell to send notification to avoid win10toast crashes
        safe_title = title.replace('"', '`"')
        safe_message = message.replace('"', '`"')
        
        command = f"""
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        $Template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
        $textNodes = $Template.GetElementsByTagName("text")
        $textNodes.Item(0).InnerText = "{safe_title}"
        $textNodes.Item(1).InnerText = "{safe_message}"
        $Notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Antigravity")
        $Notification = [Windows.UI.Notifications.ToastNotification]::new($Template)
        $Notifier.Show($Notification)
        """
        subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-Command", command], capture_output=True, check=False)
        logging.info(f"إرسال إشعار عبر PowerShell: {title}")
    except Exception as e:
        logging.error(f"فشل إرسال الإشعار عبر PowerShell: {e}")

# -------------------------
# إعداد Google Sheets API
# -------------------------
def find_creds_file():
    possible_names = ["credentials.json", "service_account.json"]
    for name in possible_names:
        if os.path.exists(name):
            return name
    return None

GOOGLE_CREDS_FILE = find_creds_file()

WATCH_CONFIG = [
    {
        "id": "candidates",
        "name": "المرشحين",
        "url": "https://docs.google.com/spreadsheets/d/1u87sScIve_-xT_jDG56EKFMXegzAxOqwVJCh3Irerrw/edit",
        "notif_title": "تحديث في بيانات المرشحين"
    },
    {
        "id": "customer_requests",
        "name": "طلبات العملاء",
        "url": "https://docs.google.com/spreadsheets/d/1ZlLGXqbFSnKrr2J-PRnxRhxykwrNOgOE6Mb34Zei_FU/edit",
        "notif_title": "طلب عميل جديد"
    }
]

def get_sheet(url):
    if not GOOGLE_CREDS_FILE:
        logging.error("لم يتم العثور على ملف الاعتمادات (credentials.json أو service_account.json)")
        return None
    try:
        logging.info(f"محاولة الاتصال بـ Google Sheets: {url}...")
        client = gspread.service_account(filename=GOOGLE_CREDS_FILE)
        sheet = client.open_by_url(url).sheet1
        return sheet
    except Exception as e:
        logging.error(f"فشل الاتصال بـ Google Sheets: {e}")
        return None

# -------------------------
# تخزين الحالة
# -------------------------
STATE_FILE = Path("state.json")

def load_all_states():
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            try: return json.load(f)
            except: pass
    return {}

def save_all_states(states):
    with open(STATE_FILE, "w") as f:
        json.dump(states, f)

def get_state(sheet_id):
    states = load_all_states()
    return states.get(f"last_row_{sheet_id}", None)

def save_state(sheet_id, last_row):
    states = load_all_states()
    states[f"last_row_{sheet_id}"] = last_row
    save_all_states(states)

def get_safe_records(sheet):
    """جلب البيانات من الجدول ومعالجة الرؤوس المكررة."""
    try:
        data = sheet.get_all_values()
        if not data: return []
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
        records = []
        for row in data[1:]:
            record = {}
            for i, val in enumerate(row):
                if i < len(clean_headers):
                    record[clean_headers[i]] = val
            records.append(record)
        return records
    except Exception as e:
        logging.error(f"خطأ في جلب البيانات: {e}")
        return []

def get_flag(nat_name):
    nat_name = str(nat_name).lower().strip()
    flags = {
        'مصر': '🇪🇬', 'مصري': '🇪🇬', 'egypt': '🇪🇬',
        'السودان': '🇸🇩', 'سوداني': '🇸🇩', 'sudan': '🇸🇩',
        'باكستان': '🇵🇰', 'باكستاني': '🇵🇰', 'pakistan': '🇵🇰',
        'الهند': '🇮🇳', 'هندي': '🇮🇳', 'india': '🇮🇳',
        'اليمن': '🇾🇪', 'يمني': '🇾🇪', 'yemen': '🇾🇪',
        'بنجلاديش': '🇧🇩', 'بنجالي': '🇧🇩', 'bangladesh': '🇧🇩',
        'الفلبين': '🇵🇭', 'فلبيني': '🇵🇭', 'philippines': '🇵🇭',
        'كينيا': '🇰🇪', 'كيني': '🇰🇪', 'kenya': '🇰🇪',
        'أوغندا': '🇺🇬', 'أوغندي': '🇺🇬', 'uganda': '🇺🇬',
        'إثيوبيا': '🇪🇹', 'إثيوبي': '🇪🇹', 'ethiopia': '🇪🇹',
    }
    for k, v in flags.items():
        if k in nat_name: return v
    return '🏁'

def watch_sheets():
    logging.info("بدء مراقبة الجداول...")
    sheets_data = {}
    for config in WATCH_CONFIG:
        sheet_id = config["id"]
        persisted_row = get_state(sheet_id)
        sheet = get_sheet(config["url"])
        
        if persisted_row is not None:
            last_row = persisted_row
        else:
            if sheet:
                records = get_safe_records(sheet)
                last_row = len(records)
                save_state(sheet_id, last_row)
            else:
                last_row = 0
        
        sheets_data[sheet_id] = {"sheet": sheet, "last_row": last_row}

    while True:
        for config in WATCH_CONFIG:
            sheet_id = config["id"]
            data = sheets_data[sheet_id]
            try:
                if not data["sheet"]: data["sheet"] = get_sheet(config["url"])
                if data["sheet"]:
                    records = get_safe_records(data["sheet"])
                    current_count = len(records)
                    last_seen = data["last_row"]
                    
                    if current_count > last_seen:
                        new_rows = records[last_seen:]
                        count = len(new_rows)
                        logging.info(f"تم العثور على {count} تحديثات في {config['name']}")
                        
                        if count > 5:
                            send_notification(config["notif_title"], f"لديك {count} تحديثات جديدة.")
                        else:
                            for row in new_rows:
                                preview = ""
                                fields = ["الاسم", "Name", "الجنسية", "Nationality", "نوع العمل", "الفئة", "المدينة", "Location"]
                                for k, v in row.items():
                                    if any(f.lower() in k.lower() for f in fields):
                                        label = k
                                        if "الجنسية" in k or "Nationality" in k:
                                            v = f"{get_flag(v)} {v}"
                                        preview += f"{label}: {v}\n"
                                send_notification(config["notif_title"], preview or "تحديث جديد.")
                                time.sleep(2)
                        
                        data["last_row"] = current_count
                        save_state(sheet_id, current_count)
                    elif current_count < last_seen:
                        logging.info(f"نقص عدد الصفوف في {config['name']} ({last_seen} -> {current_count}).")
                        data["last_row"] = current_count
                        save_state(sheet_id, current_count)
            except Exception as e:
                logging.error(f"خطأ في {config['name']}: {e}")
                data["sheet"] = None
        time.sleep(30)

def startup():
    logging.info("===== خدمة الإشعارات نشطة =====")
    send_notification("Antigravity", "البرنامج نشط الآن ويراقب التحديثات.")
    t = Thread(target=watch_sheets, daemon=True)
    t.start()

if __name__ == "__main__":
    startup()
    while True: time.sleep(1)
