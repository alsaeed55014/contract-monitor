# antigravity_notification.py
# نسخة جاهزة لتطبيق برمبيت Antigravity

import os
import json
import time
import logging
from pathlib import Path
from threading import Thread
from win10toast import ToastNotifier
import gspread
from oauth2client.service_account import ServiceAccountCredentials

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

import subprocess

def send_notification(title, message):
    """Sends a Windows toast notification using a PowerShell script for maximum reliability."""
    try:
        # Use PowerShell to send notification to avoid win10toast crashes
        # Escape double quotes in title and message for PowerShell
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
        # Specify UTF8 encoding for the command input
        subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-Command", command], capture_output=True, check=False)
        logging.info(f"إرسال إشعار عبر PowerShell: {title}")
    except Exception as e:
        logging.error(f"فشل إرسال الإشعار عبر PowerShell: {e}")# -------------------------
# إعداد Google Sheets API
# -------------------------
# محاولة البحث عن ملف الاعتمادات في عدة مسارات
def find_creds_file():
    possible_names = ["credentials.json", "service_account.json"]
    for name in possible_names:
        if os.path.exists(name):
            return name
    return None

GOOGLE_CREDS_FILE = find_creds_file()

# قائمة الجداول التي يجب مراقبتها
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
        logging.info(f"تم الاتصال بنجاح بـ الجدول.")
        return sheet
    except Exception as e:
        logging.error(f"فشل الاتصال بـ Google Sheets: {e}")
        return None

# -------------------------
# تخزين الإشعارات والحالة
# -------------------------
CACHE_FILE = Path("notification_cache.json")
STATE_FILE = Path("state.json")

def load_all_states():
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            try:
                return json.load(f)
            except:
                pass
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

def load_cached_notifications():
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r") as f:
            try:
                content = json.load(f)
                if isinstance(content, list):
                    return content
            except:
                pass
    return []

def save_cached_notifications(notifications):
    with open(CACHE_FILE, "w") as f:
        json.dump(notifications, f)

# -------------------------
# وظيفة معالجة البيانات مع رؤوس مكررة
# -------------------------
def get_safe_records(sheet):
    """جلب البيانات من الجدول ومعالجة الرؤوس المكررة."""
    try:
        data = sheet.get_all_values()
        if not data:
            return []
        
        headers = [str(h).strip() for h in data[0]]
        # التعامل مع الرؤوس المكررة
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
        print(f"خطأ في جلب البيانات الآمن: {e}")
        return []

# -------------------------
# مراقبة Google Sheets
# -------------------------

def get_flag(nat_name):
    """Converts nationality name to emoji flag."""
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
    
    # تهيئة الحالة الأولية لكل جدول
    sheets_data = {}
    for config in WATCH_CONFIG:
        sheet_id = config["id"]
        persisted_row = get_state(sheet_id)
        
        # محاولة الاتصال الأولى
        sheet = get_sheet(config["url"])
        
        if persisted_row is not None:
            last_row = persisted_row
            logging.info(f"جدول {config['name']}: استعادة الحالة ({last_row} صفوف)")
        else:
            if sheet:
                try:
                    records = get_safe_records(sheet)
                    # عند أول تشغيل، نبدأ من الصف السابق للأخير لضمان ظهور إشعار تأكيدي
                    current_len = len(records)
                    last_row = max(0, current_len - 1)
                    save_state(sheet_id, last_row)
                    logging.info(f"جدول {config['name']}: أول تشغيل، تم تعيين البداية عند {last_row} (الإجمالي: {current_len})")
                except:
                    last_row = 0
            else:
                last_row = 0
        
        sheets_data[sheet_id] = {
            "sheet": sheet,
            "last_row": last_row
        }

    while True:
        for config in WATCH_CONFIG:
            sheet_id = config["id"]
            data = sheets_data[sheet_id]
            
            try:
                # إذا فقد الاتصال، حاول استعادته
                if not data["sheet"]:
                    data["sheet"] = get_sheet(config["url"])
                
                if data["sheet"]:
                    records = get_safe_records(data["sheet"])
                    current_count = len(records)
                    last_seen = data["last_row"]
                    
                    # لا نقم بالتحديث إذا كان العدد 0 (قد يكون خطأ في الاتصال) إلا إذا كان الجدول فارغاً فعلاً
                    if current_count == 0 and last_seen > 0:
                        logging.warning(f"تم استلام 0 صفوف من {config['name']}، قد يكون خطأ مؤقت.")
                        continue

                    logging.info(f"فحص {config['name']}... الحالي: {current_count}, المسجل: {last_seen}")
                    
                    if current_count > last_seen:
                        new_rows = records[last_seen:]
                        count = len(new_rows)
                        logging.info(f"تم العثور على {count} تحديثات في {config['name']}")
                        
                        if count > 5:
                            msg = f"لديك {count} تحديثات جديدة في {config['name']}"
                            send_notification(config["notif_title"], msg)
                        else:
                            for i, row in enumerate(new_rows):
                                preview = ""
                                # محاولة البحث عن حقول محددة لإظهارها بشكل جميل
                                important_fields = {
                                    "الجنسية": "الجنسية",
                                    "Nationality": "الجنسية",
                                    "الراتب المتوقع": "💰 الراتب المتوقع",
                                    "Expected salary": "💰 الراتب المتوقع",
                                    "الراتب": "💰 الراتب المتوقع",
                                    "Salary": "💰 الراتب المتوقع",
                                    "نوع العمل": "💪 الفئة",
                                    "الفئة المطلوبة": "💪 الفئة",
                                    "الاسم": "👤 الاسم",
                                    "Name": "👤 الاسم",
                                    "المدينة": "📍 المدينة",
                                    "Location": "📍 المدينة"
                                }
                                
                                found_fields = 0
                                for key, val in row.items():
                                    for field_key, label in important_fields.items():
                                        if field_key.lower() in key.lower():
                                            if "الجنسية" in label:
                                                flag = get_flag(val)
                                                preview += f"{flag} {label}: {val}\n"
                                            else:
                                                preview += f"{label}: {val}\n"
                                            found_fields += 1
                                            break
                                    if found_fields >= 4: break # كفاية 4 حقول
                                
                                # إذا لم نجد حقولاً معروفة، نأخذ أول 3 حقول
                                if not preview:
                                    keys = list(row.keys())[:3]
                                    for k in keys:
                                        preview += f"{k}: {row[k]}\n"
                                
                                send_notification(config["notif_title"], preview)
                                logging.info(f"إرسال إشعار للصف {last_seen + i + 1} في {config['name']}")
                                time.sleep(2)
                        
                        # تحديث الحالة
                        data["last_row"] = current_count
                        save_state(sheet_id, current_count)
                        
            except Exception as e:
                logging.error(f"خطأ في مراقبة {config['name']}: {e}")
                data["sheet"] = None # إعادة المحاولة في الدورة القادمة
                
        time.sleep(30) # فحص كل 30 ثانية لجميع الجداول

# -------------------------
# عند بدء تشغيل البرنامج
# -------------------------
def startup():
    logging.info("===== بدء تشغيل خدمة الإشعارات =====")
    # لا حاجة لإرسال إشعارات سابقة من الكاش هنا، فالمراقبة ستتولى ذلك
    send_notification("Antigravity", "البرنامج نشط الآن ويراقب التحديثات.")
    t = Thread(target=watch_sheets, daemon=True)
    t.start()
    logging.info("تم بدء مراقبة Google Sheets في الخلفية.")

if __name__ == "__main__":
    startup()
    # إبقاء البرنامج يعمل لتلقي الإشعارات في صمت
    while True:
        time.sleep(1)
