import os
import time
import shutil
import base64
import io
import random
import subprocess
import re
import json
from datetime import datetime, date

def __dbg_log(hypothesis_id, msg, data=None, run_id="fix", location=""):
    """No-op logger to prevent network delays during message sending."""
    pass

def _copy_text_to_clipboard(text: str) -> bool:
    """نسخ النص إلى حافظة ويندوز بدعم كامل لليونيكود واللغة العربية والإيموجي والأسطر المتعددة"""
    try:
        p = subprocess.Popen(['clip'], stdin=subprocess.PIPE, shell=True)
        p.communicate(text.encode('utf-16le'))
        return p.returncode == 0
    except Exception:
        return False

# ============================================================
# 🛡️ LIMITES GLOBAUX DE SÉCURITÉ ANTI-BAN 2026
# Ces valeurs sont des planchers de sécurité ABSOLUS
# Même si l'utilisateur force une valeur inférieure, ce plancher sera appliqué.
# ============================================================
ANTIBAN = {
    "MIN_INTER_MESSAGE_SEC": 20,       # Ne JAMAIS descendre sous 20 secondes entre 2 messages
    "MIN_BATCH_BREAK_SEC": 300,        # 5 minutes minimum entre deux paquets
    "MIN_MESSAGES_BEFORE_BREAK": 5,    # Au moins 5 messages avant une pause
    "DAILY_HARD_LIMIT_NEW": 40,        # < 40 msg/jour pour les comptes < 7 jours
    "DAILY_HARD_LIMIT_ESTABLISHED": 180,  # < 180 msg/jour pour comptes établis
    "FAILURE_RATE_STOP_PCT": 28,       # Arrêt si > 28% d'échecs (numéros invalides)
    "FAILURE_RATE_SLOWDOWN_PCT": 15,   # Ralentir si > 15% d'échecs
    "MAX_INVALID_IN_A_ROW": 8,         # إيقاف بعد 8 أرقام غير صالحة متتالية (كان 4)
}

_DAILY_LOG_FILE = None  # sera initialisé par WhatsAppService

def _today_str():
    return date.today().isoformat()

# --- Helper obfuscation functions (Module-level) ---
def parse_spintax(text: str) -> str:
    """تحليل Spintax مثل {مرحباً|أهلاً|السلام عليكم} واختيار إحدى الخيارات عشوائياً"""
    if not text: return ""
    pattern = r'\{([^{}]+)\}'
    while re.search(pattern, text):
        def repl(match):
            options = match.group(1).split('|')
            return random.choice(options)
        text = re.sub(pattern, repl, text)
    return text

def strip_zero_width_chars(text: str) -> str:
    """إزالة الرموز المخفية تماماً لمنع اكتشاف الرسالة كسبام أو احتيال من خوارزميات ميتا"""
    if not text: return ""
    for ch in ['\u200b', '\u200c', '\u200d', '\ufeff', '\u200e', '\u200f', '\u202a', '\u202b', '\u202c', '\u202d', '\u202e']:
        text = text.replace(ch, '')
    return text

def obfuscate_message(text: str) -> str:
    """تحليل Spintax وتنظيف الرسالة لضمان نص طبيعي وبشري 100%"""
    if not text: return ""
    text = parse_spintax(text)
    text = strip_zero_width_chars(text)
    return text


class WhatsAppService:
    def __init__(self, session_id="wa_pasha_stable"):
        # 2026 Persistent Session: support BOTH folders (visible & hidden)
        base_no_dot = os.path.join(os.getcwd(), "whatsapp_session")
        base_with_dot = os.path.join(os.getcwd(), ".whatsapp_session")
        if os.path.exists(base_no_dot):
            self.base_session_dir = base_no_dot
        elif os.path.exists(base_with_dot):
            self.base_session_dir = base_with_dot
        else:
            self.base_session_dir = base_no_dot  # default: visible folder for debugging
        self.session_path = os.path.join(self.base_session_dir, session_id)
        self.driver = None
        self.last_error = ""

        # 🛡️ COMPTEURS ANTI-BAN – état global de la session
        self._daily_stats_file = os.path.join(self.base_session_dir, "wa_daily_stats.json")
        self._runtime_stats_file = os.path.join(self.base_session_dir, "wa_runtime_stats.json")
        os.makedirs(self.base_session_dir, exist_ok=True)

    # ============================================================
    # 🛡️ GESTION DES LIMITES QUOTIDIENNES, TAUX D'ÉCHEC, ETC.
    # ============================================================
    def _load_json_file(self, path, default):
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except:
            pass
        return default

    def _save_json_file(self, path, data):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except:
            return False

    def get_daily_stats(self):
        """Retourne les statistiques du jour (msg envoyés, échoués, séquence invalide...)"""
        today = _today_str()
        data = self._load_json_file(self._daily_stats_file, {})
        if data.get("date") != today:
            data = {
                "date": today,
                "sent_ok": 0,
                "sent_fail": 0,
                "invalid_sequential": 0,
                "last_reset": datetime.now().isoformat()
            }
            self._save_json_file(self._daily_stats_file, data)
        return data

    def update_daily_stats(self, success: bool, is_invalid_number: bool = False):
        """Mise à jour des statistiques après chaque tentative d'envoi"""
        stats = self.get_daily_stats()
        if success:
            stats["sent_ok"] += 1
            stats["invalid_sequential"] = 0
        else:
            stats["sent_fail"] += 1
            if is_invalid_number:
                stats["invalid_sequential"] = stats.get("invalid_sequential", 0) + 1
            else:
                # Ne pas compter les erreurs techniques comme numéros invalides
                stats["invalid_sequential"] = 0
        self._save_json_file(self._daily_stats_file, stats)
        return stats

    def check_send_allowed(self) -> tuple[bool, str]:
        """🛡️ التحقق من إمكانية الإرسال اليوم. يُرجع (مسموح, السبب)."""
        stats = self.get_daily_stats()
        total = stats["sent_ok"] + stats["sent_fail"]
        ok_count = stats["sent_ok"]
        fail_count = stats["sent_fail"]
        seq_invalid = stats.get("invalid_sequential", 0)

        # 1) الحد اليومي الأقصى (للحسابات المستقرة)
        daily_limit = ANTIBAN["DAILY_HARD_LIMIT_ESTABLISHED"]
        if total >= daily_limit:
            return False, f"تم الوصول للحد اليومي ({daily_limit} رسالة). يُرجى الإرسال غداً."

        # 2) معدل الفشل العام
        if total >= 8:
            fail_pct = (fail_count / total) * 100
            if fail_pct >= ANTIBAN["FAILURE_RATE_STOP_PCT"]:
                return (False,
                        f"معدل فشل حرج: {fail_pct:.0f}٪ "
                        f"({fail_count}/{total} رسالة). قائمة الأرقام تحتوي أرقاماً غير صالحة كثيرة — خطر حظر الحساب. تم الإيقاف.")
            if fail_pct >= ANTIBAN["FAILURE_RATE_SLOWDOWN_PCT"]:
                # مسموح لكن مع تحذير (يمكن للمستدعي تبطيء الإرسال)
                pass

        # 3) تسلسل أرقام غير صالحة متتالية
        if seq_invalid >= ANTIBAN["MAX_INVALID_IN_A_ROW"]:
            return (False,
                    f"تم الإيقاف: {seq_invalid} أرقام متتالية غير مسجلة في واتساب. "
                    "يُرجى مراجعة قائمة الأرقام وإزالة الأرقام غير الصحيحة قبل الاستمرار.")

        return True, f"مسموح ({ok_count} نجح / {fail_count} فشل / {total} إجمالي اليوم)"

    def reset_sequential_counter(self):
        """🔄 إعادة ضبط عداد الأرقام غير الصالحة المتتالية — يُستدعى عند بدء كل حملة إرسال جديدة.
        يمنع تراكم الأخطاء من حملة سابقة وإيقاف الحملة الجديدة بشكل غير مبرر."""
        try:
            stats = self.get_daily_stats()
            stats["invalid_sequential"] = 0
            self._save_json_file(self._daily_stats_file, stats)
            print(f"[{time.strftime('%H:%M:%S')}] 🔄 تم إعادة ضبط عداد الأرقام الخاطئة المتتالية")
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] ⚠️ تحذير: فشل إعادة ضبط العداد: {e}")

    # ============================================================
    # 🛡️ SIMULATION DE COMPORTEMENT HUMAIN PENDANT LA SESSION
    # ============================================================
    def simulate_human_browsing(self):
        """وقفة طبيعية قبل الإرسال لمحاكاة السلوك البشري الطبيعي"""
        if not self.driver:
            return
        time.sleep(random.uniform(0.8, 1.8))

    def _get_chrome_version(self):
        """Detect Chrome version from the system to ensure UC compatibility"""
        try:
            if os.name == 'nt':
                output = subprocess.check_output(r'reg query "HKEY_CURRENT_USER\Software\Google\Chrome\BLBeacon" /v version', shell=True)
                version = re.search(r'\d+', output.decode()).group()
                return int(version)
        except:
            pass
        return None

    def _get_random_ua(self, version=None):
        """توليد User-Agent عشوائي متوافق مع نسخة كروم الحالية"""
        ver = version or self._get_chrome_version() or 146
        common_uas = [
            f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36",
            f"Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36",
            f"Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36",
            f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36"
        ]
        return random.choice(common_uas)

    def start_driver(self, headless=True, force_clean=False):
        if self.driver: 
            try:
                self.driver.current_url
                return True, "Active"
            except: 
                self.close()

        # --- Clean Existing Locks ---
        if force_clean and os.path.exists(self.session_path):
            shutil.rmtree(self.session_path, ignore_errors=True)
        
        os.makedirs(self.session_path, exist_ok=True)
        
        # Aggressive cleaning of lock files that cause UC to hang
        for lf in ["SingletonLock", "SingletonSocket", "SingletonCookie", "lockfile", "DevToolsActivePort"]:
            p = os.path.join(self.session_path, lf)
            try:
                if os.path.exists(p): os.remove(p)
            except: pass
        
        # --- Stealth & Environment Setup ---
        is_cloud = "/mount/" in __file__.replace("\\", "/") or os.path.exists("/mount")
        use_headless = headless or is_cloud
        ver = self._get_chrome_version()
        ua = self._get_random_ua(ver)
        binary = self._find_chrome_binary()

        def create_chrome_options(with_user_dir=True):
            from selenium.webdriver.chrome.options import Options as StdOptions
            o = StdOptions()
            if use_headless:
                o.add_argument("--headless=new")
            o.add_argument("--no-sandbox")
            o.add_argument("--disable-dev-shm-usage")
            o.add_argument("--disable-gpu")
            o.add_argument(f"--user-agent={ua}")
            o.add_argument("--lang=ar,en-US,en;q=0.9")
            o.add_argument("--disable-blink-features=AutomationControlled")
            o.add_argument("--use-fake-ui-for-media-stream")
            o.add_argument("--disable-notifications")
            o.add_argument("--disable-extensions")
            o.add_argument("--disable-infobars")
            o.add_argument("--ignore-certificate-errors")
            o.add_argument("--disable-browser-side-navigation")
            o.add_argument("--disable-features=IsolateOrigins,site-per-process")
            o.add_argument("--password-store=basic")
            o.add_argument("--disable-background-timer-throttling")
            o.add_argument("--disable-backgrounding-occluded-windows")
            o.add_argument("--disable-renderer-backgrounding")
            o.add_argument("--memory-pressure-off")
            o.add_argument("--js-flags=--max-old-space-size=4096")
            if with_user_dir:
                o.add_argument(f"--user-data-dir={self.session_path}")
            if binary:
                o.binary_location = binary
            return o

        # 🚀 ATTEMPT 1: Standard Stealth Selenium (Fastest & 100% Reliable across Cloud & Local)
        try:
            print(f"[{time.strftime('%H:%M:%S')}] Launching Primary Stealth Engine (Headless: {use_headless})...")
            from selenium import webdriver
            from selenium_stealth import stealth
            
            std_opts = create_chrome_options(with_user_dir=True)
            self.driver = webdriver.Chrome(options=std_opts)
            
            try:
                self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                    'source': '''
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        });
                        window.navigator.chrome = {
                            runtime: {},
                        };
                    '''
                })
            except Exception:
                pass

            stealth(self.driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
            )
            
            self.driver.get("https://web.whatsapp.com")
            self._wait_for_qr_or_login(timeout=15)
            print(f"[{time.strftime('%H:%M:%S')}] Engine Ready!")
            return True, "Ready (Stealth Engine)"
        except Exception as e1:
            print(f"[{time.strftime('%H:%M:%S')}] Attempt 1 Error: {e1}")
            self.last_error = f"Primary Engine Err: {str(e1)[:120]}"

        # 🚀 ATTEMPT 2: Fresh Session Cleanup & Retry
        try:
            print(f"[{time.strftime('%H:%M:%S')}] Retrying with fresh session...")
            self._kill_zombies()
            shutil.rmtree(self.session_path, ignore_errors=True)
            os.makedirs(self.session_path, exist_ok=True)
            
            from selenium import webdriver
            from selenium_stealth import stealth
            
            std_opts = create_chrome_options(with_user_dir=True)
            self.driver = webdriver.Chrome(options=std_opts)
            
            try:
                self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                    'source': '''
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        });
                        window.navigator.chrome = {
                            runtime: {},
                        };
                    '''
                })
            except Exception:
                pass

            stealth(self.driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
            )
            self.driver.get("https://web.whatsapp.com")
            self._wait_for_qr_or_login(timeout=15)
            return True, "Ready (Fresh Session Engine)"
        except Exception as e2:
            print(f"[{time.strftime('%H:%M:%S')}] Attempt 2 Error: {e2}")
            self.last_error += f" | Attempt 2 Err: {str(e2)[:100]}"

        # 🚀 ATTEMPT 3: Undetected Chromedriver (UC) Fallback
        try:
            import undetected_chromedriver as uc
            print(f"[{time.strftime('%H:%M:%S')}] UC Fallback Engine...")
            opts = create_chrome_options(with_user_dir=False)
            self.driver = uc.Chrome(
                options=opts,
                user_data_dir=self.session_path,
                browser_executable_path=binary,
                headless=use_headless,
                version_main=ver
            )
            self.driver.get("https://web.whatsapp.com")
            self._wait_for_qr_or_login(timeout=15)
            return True, "Ready (UC Engine)"
        except Exception as e3:
            print(f"[{time.strftime('%H:%M:%S')}] UC Fallback Error: {e3}")
            self.last_error += f" | UC Err: {str(e3)[:100]}"
            return False, self.last_error

    def _wait_for_qr_or_login(self, timeout=15):
        """انتظار تحميل الباركود أو تسجيل الدخول في المتصفح لضمان الجاهزية الفورية"""
        from selenium.webdriver.common.by import By
        start_t = time.time()
        while time.time() - start_t < timeout:
            try:
                if not self.driver: break
                elements = self.driver.find_elements(By.XPATH, '//*[@id="side"] | //div[@id="main"] | //div[@contenteditable="true"] | //div[@data-tab="3"]')
                qr_elements = self.driver.find_elements(By.XPATH, '//canvas | //*[@data-ref] | //*[contains(@data-testid, "qr")] | //*[contains(@aria-label, "QR")] | //*[contains(@aria-label, "Scan")]')
                if elements or qr_elements:
                    return True
            except: pass
            time.sleep(0.4)
        return False

    def _find_chrome_binary(self):
        if os.name == 'nt':
            win_paths = [
                os.environ.get("PROGRAMFILES", "C:\\Program Files") + "\\Google\\Chrome\\Application\\chrome.exe",
                os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)") + "\\Google\\Chrome\\Application\\chrome.exe",
                os.environ.get("LOCALAPPDATA", "") + "\\Google\\Chrome\\Application\\chrome.exe"
            ]
            for b in win_paths:
                if os.path.exists(b): return b
        else:
            linux_paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/chromium",
                "/usr/bin/chromium-browser",
                "/usr/bin/google-chrome-stable"
            ]
            for b in linux_paths:
                if os.path.exists(b): return b
            try:
                import subprocess
                for cmd in ['google-chrome', 'chromium', 'google-chrome-stable']:
                    path = subprocess.check_output(['which', cmd]).decode().strip()
                    if path: return path
            except: pass
            
        return None

    def _kill_zombies(self):
        try:
            if os.name == 'nt':
                os.system('taskkill /F /IM chromedriver.exe /T >nul 2>&1')
                os.system('taskkill /F /IM chrome.exe /FI "WINDOWTITLE eq chrome*" /FI "MEMUSAGE gt 1" >nul 2>&1')
            else:
                os.system('pkill -f chromedriver > /dev/null 2>&1')
                os.system('pkill -f chrome > /dev/null 2>&1')
        except: pass

    def keep_alive(self):
        """Pings Chrome JavaScript engine to prevent tab sleeping, renderer suspension, and DevTools timeout"""
        if not self.driver: return False
        try:
            self.driver.execute_script("return document.readyState;")
            return True
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] Keep-alive check failed: {e}")
            return False

    def get_status(self):
        from selenium.webdriver.common.by import By
        import streamlit as st
        if not self.driver: return "Disconnected"
        try:
            _ = self.driver.window_handles
        except:
            self.driver = None
            return "Disconnected"

        try:
            # Check for active WhatsApp DOM elements (Logged in)
            elements = self.driver.find_elements(By.XPATH, '//*[@id="side"] | //div[@id="main"] | //div[@contenteditable="true"] | //div[@data-tab="3"]')
            if elements:
                return "Connected"
            
            # Check for QR / Login elements
            qr_elements = self.driver.find_elements(By.XPATH, '//canvas | //*[@data-ref] | //*[contains(@data-testid, "qr")] | //*[contains(@aria-label, "QR")] | //*[contains(@aria-label, "Scan")]')
            if qr_elements:
                return "Awaiting Login"

            # If sending loop is running, maintain Connected status
            if st.session_state.get('wa_running', False):
                return "Connected"

            # Fallback for loading state on WhatsApp URL
            if self.driver.current_url and "web.whatsapp.com" in self.driver.current_url.lower():
                return "Awaiting Login"

            return "Loading..."
        except:
            if st.session_state.get('wa_running', False) and self.driver:
                return "Connected"
            return "Disconnected"

    def wait_for_connection(self, timeout=30):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        if not self.driver: return False
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="side"] | //div[@id="main"]'))
            )
            return True
        except:
            return False

    def _auto_click_qr_reload(self):
        """تفريغ التنبيه والتثبيت بالنقر التلقائي على زر إعادة تحميل الباركود إذا انتهت صلاحيته"""
        if not self.driver: return
        from selenium.webdriver.common.by import By
        try:
            reload_btns = self.driver.find_elements(
                By.XPATH, 
                '//button[contains(., "Reload") or contains(., "إعادة") or contains(., "انقر")] | '
                '//span[@data-icon="refresh"] | '
                '//div[contains(@class, "qr")]//button | '
                '//div[@data-ref]//button'
            )
            if reload_btns:
                print(f"[{time.strftime('%H:%M:%S')}] Auto-clicking QR reload button...")
                reload_btns[0].click()
                time.sleep(1.0)
        except Exception: pass

    def get_qr_hd(self):
        if not self.driver: return None
        from selenium.webdriver.common.by import By
        from PIL import Image, ImageOps

        # Check & auto-click QR reload button if expired
        self._auto_click_qr_reload()

        for _ in range(3):
            # --- Method 1: JS Canvas dataURL ---
            try:
                data_url = self.driver.execute_script(
                    """
                    let c = document.querySelector('canvas');
                    if (c) return c.toDataURL('image/png');
                    let container = document.querySelector('div[data-ref], div[data-testid="qrcode"], [aria-label*="QR"], [aria-label*="Scan"]');
                    if (container) {
                        let c2 = container.querySelector('canvas');
                        if (c2) return c2.toDataURL('image/png');
                    }
                    return null;
                    """
                )
                if data_url and len(data_url) > 100:
                    header, b64data = data_url.split(",", 1)
                    raw_bytes = base64.b64decode(b64data)
                    img = Image.open(io.BytesIO(raw_bytes))
                    
                    img = img.convert("L") # Greyscale
                    img = ImageOps.autocontrast(img, cutoff=2)
                    
                    new_size = (img.width * 4, img.height * 4)
                    img_big = img.resize(new_size, Image.NEAREST)
                    border = 30
                    final = Image.new("RGB", (img_big.width + border*2, img_big.height + border*2), "white")
                    final.paste(img_big, (border, border))
                    buf = io.BytesIO()
                    final.save(buf, format="PNG", optimize=True)
                    buf.seek(0)
                    return base64.b64encode(buf.read()).decode()
            except Exception: pass
            
            # --- Method 2: Element Screenshot ---
            try:
                elements = self.driver.find_elements(
                    By.XPATH,
                    '//canvas | //div[@data-ref] | //div[contains(@data-testid, "qr")] | //*[contains(@aria-label, "QR")] | //*[contains(@aria-label, "Scan")]'
                )
                for elem in elements:
                    b64_str = elem.screenshot_as_base64
                    if b64_str and len(b64_str) > 100:
                        return b64_str
            except Exception: pass

            time.sleep(0.4)

        # --- Method 3: Full Page Diagnostic Screenshot Fallback ---
        try:
            return self.get_diagnostic_screenshot()
        except Exception: pass

        return None

    def get_diagnostic_screenshot(self):
        if not self.driver: return None
        try: return self.driver.get_screenshot_as_base64()
        except: return None

    def _type_human_like(self, element, text):
        """محاكاة كتابة بشرية واقعية جداً مع تنوع سرعتها واستخدام Shift+Enter للأسطر الجديدة لمنع الإرسال المبكر"""
        from selenium.webdriver.common.keys import Keys
        for char in text:
            try:
                if char == '\n':
                    element.send_keys(Keys.SHIFT + Keys.ENTER)
                else:
                    element.send_keys(char)
            except:
                try:
                    self.driver.execute_script(
                        """
                        arguments[0].focus();
                        document.execCommand('insertText', false, arguments[1]);
                        arguments[0].dispatchEvent(new Event('input', {bubbles:true}));
                        """,
                        element, char
                    )
                except: pass
            base_delay = random.uniform(0.02, 0.08)
            if char in [" ", "\n", ".", ",", "!", "?", "،", "؛"]:
                base_delay += random.uniform(0.08, 0.22)
            elif char.isupper():
                base_delay += random.uniform(0.04, 0.12)
                
            time.sleep(base_delay)
            
            if random.random() < 0.015:
                time.sleep(random.uniform(0.3, 0.7))

    def _find_send_button(self):
        """العثور على زر الإرسال الحقيقي لواتساب ويب (نسخة 2024-2026) مع استبعاد أزرار الميكروفون والإيموجي والإرفاق تماماً"""
        from selenium.webdriver.common.by import By
        if not self.driver:
            return None
        selectors = [
            # === الـ selectors الرسمية لزر الإرسال الحقيقي ===
            '//button[@data-testid="compose-btn-send"]',
            '//div[@data-testid="compose-btn-send"]',
            '//button[contains(@data-testid, "compose-btn-send")]',
            '//footer//button[contains(@data-testid, "send")]',
            '//footer//*[@data-testid="send"]',
            # Span/SVG بأيقونة send الصريحة
            '//span[@data-icon="send"]/parent::button',
            '//span[@data-icon="send"]/ancestor::button',
            '//span[@data-icon="send"]/ancestor::*[@role="button"]',
            '//span[@data-icon="send"]/parent::*',
            '//span[@data-testid="send"]/ancestor::button',
            '//span[@data-testid="send"]/ancestor::*[@role="button"]',
            '//span[@data-testid="send"]/parent::*',
            # تسميات أزرار الإرسال الصريحة في الفوتر
            '//footer//button[@aria-label="Send" or @aria-label="إرسال" or @aria-label="ارسل"]',
            '//footer//*[@role="button"][@aria-label="Send" or @aria-label="إرسال" or @aria-label="ارسل"]',
            '//*[name()="svg" and contains(@data-icon, "send")]/ancestor::*[self::button or @role="button"][1]',
            '//div[contains(@data-testid, "media-send-button")]',
        ]
        for sel in selectors:
            try:
                elems = self.driver.find_elements(By.XPATH, sel)
                for e in elems:
                    try:
                        if not e.is_displayed() or not e.is_enabled():
                            continue
                        size = e.size
                        if size.get("width", 0) < 10 or size.get("height", 0) < 10:
                            continue
                        # حماية قصوى: التأكد من أنه ليس زر الميكروفون أو الإيموجي أو الإرفاق
                        aria = (e.get_attribute("aria-label") or "").lower()
                        dicon = (e.get_attribute("data-icon") or "").lower()
                        if any(mic in aria for mic in ["voice", "audio", "صوتي", "ميكروفون", "تسجيل"]):
                            continue
                        if any(mic in dicon for mic in ["ptt", "mic"]):
                            continue
                        if any(em in aria for em in ["emoji", "smiley", "ملصق", "رمز تعبيري", "تعبيرية"]):
                            continue
                        if any(em in dicon for em in ["emoji", "smiley", "sticker"]):
                            continue
                        if any(att in aria for att in ["attach", "إرفاق", "مرفق"]):
                            continue
                        return e
                    except Exception:
                        continue
            except Exception:
                continue
        return None

    def _find_input_box(self):
        """العثور على صندوق كتابة الرسالة في المحادثة (داخل الفوتر أو main حصراً) مع استبعاد شريط البحث في side"""
        from selenium.webdriver.common.by import By
        if not self.driver:
            return None
        selectors = [
            # 1. المعرف الرسمي لـ compose box
            '//footer//*[@data-testid="conversation-compose-box-input"]',
            '//*[@id="main"]//footer//*[@data-testid="conversation-compose-box-input"]',
            '//*[@data-testid="conversation-compose-box-input"]',
            # 2. حقول contenteditable داخل الفوتر
            '//footer//div[@contenteditable="true"][@data-tab="10"]',
            '//*[@id="main"]//footer//div[@contenteditable="true"]',
            '//footer//div[@contenteditable="true"]',
            '//footer//*[@role="textbox"][@contenteditable="true"]',
            # 3. أي contenteditable داخل main مع استبعاد الشريط الجانبي
            '//*[@id="main"]//*[@contenteditable="true"]',
        ]
        for sel in selectors:
            try:
                elems = self.driver.find_elements(By.XPATH, sel)
                for e in elems:
                    try:
                        if not e.is_displayed():
                            continue
                        size = e.size
                        if size.get("width", 0) < 20 or size.get("height", 0) < 10:
                            continue
                        # التأكد القاطع من أنه ليس حقل البحث
                        data_tab = (e.get_attribute("data-tab") or "").strip()
                        if data_tab == "3":
                            continue
                        data_testid = (e.get_attribute("data-testid") or "").lower()
                        if "search" in data_testid:
                            continue
                        # التأكد من أنه ليس داخل #side (الشريط الجانبي)
                        is_in_side = self.driver.execute_script(
                            "return Boolean(arguments[0].closest('#side'));", e
                        )
                        if is_in_side:
                            continue
                        return e
                    except Exception:
                        continue
            except Exception:
                continue
        return None

    def _inject_text_to_input(self, msg_input, text: str) -> bool:
        """إدخال النص في صندوق الرسالة بطرق متعددة ومضمونة (Clipboard paste ثم send_keys ثم JS)"""
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.common.action_chains import ActionChains

        if not msg_input or not text:
            return False

        # 1. التركيز على صندوق الكتابة
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'}); arguments[0].focus();", msg_input)
        except Exception:
            pass
        time.sleep(0.3)
        try:
            msg_input.click()
        except Exception:
            pass
        time.sleep(0.3)

        # تفريغ أي نص موجود مسبقاً
        try:
            self.driver.execute_script("""
                var el = arguments[0];
                el.focus();
                document.execCommand('selectAll', false, null);
                document.execCommand('delete', false, null);
            """, msg_input)
        except Exception:
            pass
        time.sleep(0.2)

        # الطريقة الأولى (الأفضل والأضمن للعربية والإيموجي والأسطر المتعددة): Clipboard Paste (Ctrl+V)
        copied = _copy_text_to_clipboard(text)
        if copied:
            try:
                ActionChains(self.driver).move_to_element(msg_input).click().key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                time.sleep(0.6)
                curr_text = self.driver.execute_script("return (arguments[0].innerText || arguments[0].textContent || '').trim();", msg_input)
                if len(curr_text) > 0:
                    return True
            except Exception:
                pass

        # الطريقة الثانية: send_keys سطر بسطر مع Shift+Enter
        try:
            lines = text.split("\n")
            for l_idx, line in enumerate(lines):
                if line:
                    msg_input.send_keys(line)
                if l_idx < len(lines) - 1:
                    ActionChains(self.driver).key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT).perform()
                time.sleep(0.04)
            time.sleep(0.5)
            curr_text = self.driver.execute_script("return (arguments[0].innerText || arguments[0].textContent || '').trim();", msg_input)
            if len(curr_text) > 0:
                return True
        except Exception:
            pass

        # الطريقة الثالثة: JS insertText مع أحداث React InputEvent
        try:
            encoded = json.dumps(text)
            self.driver.execute_script(f"""
                var el = arguments[0];
                var str = {encoded};
                el.focus();
                document.execCommand('selectAll', false, null);
                document.execCommand('insertText', false, str);
                el.dispatchEvent(new InputEvent('beforeinput', {{ bubbles: true, cancelable: true, data: str, inputType: 'insertText' }}));
                el.dispatchEvent(new InputEvent('input', {{ bubbles: true, cancelable: true, data: str, inputType: 'insertText' }}));
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            """, msg_input)
            time.sleep(0.5)
            curr_text = self.driver.execute_script("return (arguments[0].innerText || arguments[0].textContent || '').trim();", msg_input)
            return len(curr_text) > 0
        except Exception:
            pass

        return False

    def _dismiss_modals(self):
        """إغلاق أي نوافذ منبثقة أو تنبيهات أرقام غير صالحة بأمان فقط عند وجود نافذة منبثقة دون المساس بالمحادثة"""
        from selenium.webdriver.common.by import By
        try:
            modal_containers = self.driver.find_elements(By.XPATH,
                '//div[@data-animate-modal-popup="true"] | '
                '//div[@role="alertdialog"] | '
                '//div[@role="dialog"] | '
                '//div[contains(@data-testid, "popup-modal")] | '
                '//div[contains(@data-testid, "modal")]'
            )
            for modal in modal_containers:
                try:
                    if not modal.is_displayed():
                        continue
                    btns = modal.find_elements(By.XPATH, './/button | .//*[@role="button"]')
                    for btn in btns:
                        try:
                            if not btn.is_displayed():
                                continue
                            txt = (btn.text or "").strip().lower()
                            aria = (btn.get_attribute("aria-label") or "").strip().lower()
                            data_icon = btn.find_elements(By.XPATH, './/span[@data-icon="x" or @data-icon="X"]')
                            if txt in ["ok", "موافق", "حسناً", "حسنا", "close", "إغلاق", "dismiss"] or \
                               aria in ["close", "إغلاق", "ok", "موافق"] or len(data_icon) > 0:
                                try: btn.click()
                                except: self.driver.execute_script("arguments[0].click();", btn)
                                time.sleep(0.4)
                                return
                        except Exception:
                            continue
                except Exception:
                    continue
        except Exception:
            pass

    def _verify_message_sent(self, baseline_msgout_count: int = -1, prev_last_msgout_text: str = "",
                              expected_msg_fragment: str = "", is_attachment: bool = False) -> bool:
        """
        🛡️ التحقق الصارم الفعلي من نجاح الإرسال (افتراضياً False = غير مُرسل حتى يثبت العكس!).
        — القاعدة الذهبية: لا يعيد True أبداً بدون دليل مادي في الـ DOM يثبت ظهور رسالة جديدة.
        :param baseline_msgout_count: عدد الرسائل الصادرة قبل محاولة الإرسال
        :param prev_last_msgout_text: نص آخر رسالة صادرة قبل الإرسال (للمقارنة)
        :param expected_msg_fragment: مقطع من نص الرسالة المتوقع ظهوره بعد الإرسال (بعد تنظيف الرموز المخفية)
        :param is_attachment: هل هي مرفق (يبحث عن وسائط بدلاً من النص)
        :return: True فقط إذا وُجد دليل حقيقي على إرسال رسالة جديدة
        """
        from selenium.webdriver.common.by import By
        try:
            if not self.driver:
                return False

            _msgout_xpath = '//div[contains(@data-testid, "msg-out")] | //div[contains(@class, "message-out")] | //div[contains(@data-testid, "message-out")]'
            _current_msgouts = self.driver.find_elements(By.XPATH, _msgout_xpath)
            _current_count = len(_current_msgouts)

            # ─────────────────────────────────────────────────────────────────
            # 🔴 مستوى 1 (الأقوى فعلياً): زيادة عدد الرسائل الصادرة عن BASELINE
            # ─────────────────────────────────────────────────────────────────
            if baseline_msgout_count >= 0 and _current_count > baseline_msgout_count:
                return True

            # ─────────────────────────────────────────────────────────────────
            # 🟠 مستوى 2 (قوي): نص آخر رسالة صادرة يطابق الرسالة المتوقعة
            # ─────────────────────────────────────────────────────────────────
            if _current_msgouts:
                try:
                    _last_e = _current_msgouts[-1]
                    # استخدام JS للحصول على النص الحقيقي من DOM بدون React artifacts
                    _last_norm = self.driver.execute_script("""
                        (function(el){
                            if (!el) return '';
                            var t = (el.innerText || el.textContent || '').toString();
                            // إزالة الرموز المخفية والمسافات الزائدة
                            t = t.replace(/[\\u200B-\\u200F\\u202A-\\u202E\\u00AD\\u2060\\uFEFF]/g, '');
                            t = t.replace(/\\s+/g, ' ').trim();
                            return t.toLowerCase();
                        })(arguments[0]);
                    """, _last_e)

                    if expected_msg_fragment and len(expected_msg_fragment) > 3:
                        if expected_msg_fragment in _last_norm:
                            # التأكد أنها رسالة جديدة وليست رسالة قديمة بنفس المحتوى
                            _prev_norm = re.sub(r'[\u200B-\u200F\u202A-\u202E\u00AD\u2060\uFEFF\s]', '',
                                                prev_last_msgout_text or '').lower()
                            _expected_in_prev = expected_msg_fragment in _prev_norm
                            if not _expected_in_prev or (baseline_msgout_count >= 0 and _current_count > baseline_msgout_count):
                                return True
                            # حتى لو تطابق المحتوى القديم: تأكد أن الـ DOM changed
                            if _last_norm != _prev_norm:
                                return True

                    # للمرفقات: نتحقق من وجود وسائط (IMG / VIDEO / PDF preview) في آخر رسالة صادرة
                    if is_attachment:
                        try:
                            has_media_children = self.driver.execute_script("""
                                (function(el){
                                    if (!el) return false;
                                    // البحث عن صورة، فيديو، مستند، أو أيقونة ملف
                                    var has = el.querySelector('img, video, [data-testid*="image"], [data-testid*="video"], [data-testid*="document"], [aria-label*="file"], [data-testid*="media"]');
                                    if (has) return true;
                                    // البحث عن اسم ملف أو حجم الملف
                                    var html = el.innerHTML || '';
                                    if ((html.indexOf('.pdf') > -1 || html.indexOf('.docx') > -1 || html.indexOf('.xlsx') > -1)
                                        && (html.indexOf('KB') > -1 || html.indexOf('MB') > -1 || html.indexOf('bytes') > -1)) return true;
                                    return false;
                                })(arguments[0]);
                            """, _last_e)
                            if has_media_children and (_last_norm != (prev_last_msgout_text or '').strip().lower()
                                                      or (baseline_msgout_count >= 0 and _current_count > baseline_msgout_count)):
                                return True
                        except Exception:
                            pass
                except Exception:
                    pass

            # ─────────────────────────────────────────────────────────────────
            # 🟡 مستوى 3 (متوسط): علامات الحالة في آخر رسالة صادرة فقط
            #   — لا نعتبر مجرد وجود أي msg-out كنجاح (هذا هو خطأ سابقة)
            #   — نبحث عن علامات msg-time/check/dblcheck DIRECTLY داخل آخر msg-out فقط
            # ─────────────────────────────────────────────────────────────────
            if _current_msgouts:
                try:
                    _last_e = _current_msgouts[-1]
                    _icons = _last_e.find_elements(By.XPATH,
                        './/*[contains(@data-icon, "msg-time") or contains(@data-icon, "msg-check") or contains(@data-icon, "msg-dblcheck")]')
                    if _icons:
                        # التأكد من أنها ليست نفس رسالة قديمة (محتوى جديد أو زيادة في العدد)
                        _is_new_content = (baseline_msgout_count >= 0 and _current_count > baseline_msgout_count)
                        try:
                            if not _is_new_content:
                                _last_txt = (_last_e.text or "").strip()
                                _prev_txt = (prev_last_msgout_text or "").strip()
                                if _last_txt and _prev_txt and _last_txt != _prev_txt:
                                    _is_new_content = True
                                elif expected_msg_fragment and len(expected_msg_fragment) > 3:
                                    _ln = (_last_txt or '').lower()
                                    _pn = (_prev_txt or '').lower()
                                    if expected_msg_fragment in _ln and expected_msg_fragment not in _pn:
                                        _is_new_content = True
                        except Exception:
                            pass
                        if _is_new_content:
                            return True
                except Exception:
                    pass

            # ─────────────────────────────────────────────────────────────────
            # 🔵 مستوى 4 (ضعيف جداً): نجاح في مصدر الصفحة
            #   — فقط إذا كان هناك فشل مؤكد، نعيد False
            #   — الافتراضي نعيد False صارمة! لا نعطي نجاح ساهل
            # ─────────────────────────────────────────────────────────────────
            try:
                src_last = (self.driver.page_source or "")[-8000:].lower()
                bad_words = [
                    "couldn't send", "can't send this message",
                    "غير قادر على الإرسال", "فشل إرسال الرسالة",
                    "failed to send", "message not delivered",
                    "only admins can send", "blocked", "you need to save",
                    "you are blocked", "تم حظرك", "لا يمكن الإرسال",
                    "red clock", "error",
                ]
                if any(w in src_last for w in bad_words):
                    return False  # فشل مؤكد
            except Exception:
                pass

            # ===== ⚠️ افتراضي صارم: False (لا نجاح بدون دليل قاطع!) =====
            return False
        except Exception:
            return False

    def _normalize_phone(self, phone: str) -> str:
        """Standardize phone to international digits format (e.g. 9665XXXXXXXX)."""
        if not phone:
            return ""
        # 1. استخدام formatter الذكي من phone_utils إن أمكن
        try:
            from src.utils.phone_utils import format_phone_number
            fmt = format_phone_number(phone)
            if fmt:
                clean_fmt = "".join(filter(str.isdigit, str(fmt)))
                if len(clean_fmt) >= 8:
                    return clean_fmt
        except Exception:
            pass

        # 2. تنظيف مباشر للأرقام
        clean = "".join(filter(str.isdigit, str(phone)))
        if not clean:
            return ""
        # Local Saudi numbers
        if clean.startswith("05") and len(clean) == 10:
            return "966" + clean[1:]
        if clean.startswith("5") and len(clean) == 9:
            return "966" + clean
        if clean.startswith("00"):
            return clean[2:]
        return clean

    def _auto_handle_popups(self):
        """Automatically dismiss or accept common WhatsApp Web popups (Use Here, etc.) — 2026 Edition."""
        if not self.driver: return
        from selenium.webdriver.common.by import By
        try:
            # 1. 'Use Here' / 'استخدام هنا' popup — أحدث النسخ 2024-2026
            use_here_selectors = [
                '//button[contains(normalize-space(.), "Use Here") or contains(normalize-space(.), "استخدام هنا") or contains(normalize-space(.), "استخدم هنا") or contains(normalize-space(.), "Use on this device") or contains(normalize-space(.), "استخدم على هذا الجهاز")]',
                '//div[@role="button"][contains(normalize-space(.), "Use Here") or contains(normalize-space(.), "استخدام هنا") or contains(normalize-space(.), "استخدم هنا") or contains(normalize-space(.), "Use on this device") or contains(normalize-space(.), "استخدم على هذا الجهاز")]',
                # data-testid الجديد لـ Use Here
                '//*[contains(@data-testid, "use-here")]//button',
                '//*[contains(@data-testid, "use-here")]//*[@role="button"]',
            ]
            for sel in use_here_selectors:
                use_here_btns = self.driver.find_elements(By.XPATH, sel)
                for btn in use_here_btns:
                    try:
                        if btn.is_displayed():
                            try:
                                btn.click()
                            except:
                                try:
                                    self.driver.execute_script("arguments[0].click();", btn)
                                except:
                                    pass
                            time.sleep(1.0)
                            return
                    except: pass
            # 2. إشعارات الواتساب (Turn on notifications / تفعيل الإشعارات)
            try:
                notif_close_selectors = [
                    '//div[contains(@data-testid, "popup-notification")]//span[@data-icon="x"]/parent::*',
                    '//*[contains(@data-testid, "notification-attention")]//*[@role="button" and contains(@aria-label,"Close")]',
                ]
                for sel in notif_close_selectors:
                    btns = self.driver.find_elements(By.XPATH, sel)
                    for btn in btns:
                        try:
                            if btn.is_displayed():
                                btn.click()
                                time.sleep(0.8)
                        except: pass
            except Exception: pass
        except Exception: pass

    def send_message(self, phone, message, attachment_path=None):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.common.action_chains import ActionChains
        import urllib.parse

        if not self.driver:
            return False, "Engine Offline (المحرك غير متصل)"
        try:
            _ = self.driver.window_handles
        except Exception:
            self.driver = None
            return False, "Engine Disconnected (المتصفح مغلق)"

        # 🛡️ 1. فحص حدود الأمان
        allowed, allow_reason = self.check_send_allowed()
        if not allowed:
            self.last_error = f"BLOCKED ANTI-BAN: {allow_reason}"
            print(f"[{time.strftime('%H:%M:%S')}] 🚫 ANTI-BAN BLOCK: {allow_reason}")
            return False, f"🛑 أمان: {allow_reason}"

        self.simulate_human_browsing()

        try:
            clean_phone = self._normalize_phone(phone)
            if message:
                message = obfuscate_message(message)

            if len(clean_phone) < 8:
                self.update_daily_stats(False, is_invalid_number=True)
                return False, f"رقم غير صالح ({phone})"

            # إغلاق أي نوافذ منبثقة سابقة
            self._auto_handle_popups()
            self._dismiss_modals()
            time.sleep(0.4)

            # 🌐 2. التنقل المباشر لرابط المحادثة مع السلاش الصحيح
            target_url = f"https://web.whatsapp.com/send/?phone={clean_phone}"
            print(f"[{time.strftime('%H:%M:%S')}] 🚀 Navigating to: {clean_phone}...")

            # محاولة التنقل الداخلي لتجنب إعادة تحميل الصفحة الكاملة
            navigated = False
            try:
                curr_url = self.driver.current_url or ""
                if "web.whatsapp.com" in curr_url:
                    self.driver.execute_script(f"""
                        var a = document.getElementById('__wa_nav_link');
                        if (!a) {{
                            a = document.createElement('a');
                            a.id = '__wa_nav_link';
                            a.style.display = 'none';
                            document.body.appendChild(a);
                        }}
                        a.href = '{target_url}';
                        a.click();
                    """)
                    navigated = True
            except Exception:
                navigated = False

            if not navigated:
                try:
                    self.driver.get(target_url)
                except Exception as e_nav:
                    print(f"[{time.strftime('%H:%M:%S')}] Navigation retry via JS: {e_nav}")
                    self.driver.execute_script(f"window.location.href = '{target_url}';")

            # فترة انتظار أولية لتهيئة واجهة المحادثة
            time.sleep(random.uniform(2.5, 4.0))

            # ⏳ 3. حلقة انتظار ظهور صندوق الكتابة أو نافذة خطأ الرقم غير المسجل (حتى 35 ثانية)
            wait_start = time.time()
            msg_input = None
            is_invalid_num = False
            invalid_reason = "رقم غير مسجل في الواتساب"

            while time.time() - wait_start < 35:
                self._auto_handle_popups()

                # A. التحقق من ظهور نافذة رقم غير مسجل
                try:
                    dialogs = self.driver.find_elements(By.XPATH,
                        '//div[@data-animate-modal-popup="true"] | '
                        '//div[@role="alertdialog"] | //div[@role="dialog"] | '
                        '//div[contains(@data-testid, "popup-modal")] | '
                        '//div[contains(@data-testid, "modal")]'
                    )
                    bad_phrases = [
                        "phone number shared via url is invalid",
                        "this phone number is not on whatsapp",
                        "رقم الهاتف غير مسجل في الواتساب",
                        "رقم الهاتف الذي شاركته عبر الرابط غير صالح",
                        "رقم الهاتف الذي تمت مشاركته عبر رابط غير صالح",
                        "الرقم غير مسجل في الواتساب",
                        "الرقم غير مسجل في واتساب",
                        "الرقم الذي أدخلته غير صالح",
                        "رقم الهاتف غير صالح",
                        "not on whatsapp",
                        "url is invalid",
                        "invalid url",
                        "هذا الرقم ليس مسجلاً",
                    ]
                    for d in dialogs:
                        try:
                            if not d.is_displayed():
                                continue
                            d_text = (d.text or "").strip().lower()
                            if len(d_text) < 8:
                                continue
                            if any(bp in d_text for bp in bad_phrases):
                                is_invalid_num = True
                                invalid_reason = "رقم غير مسجل في الواتساب"
                                break
                        except Exception:
                            continue
                    if is_invalid_num:
                        break
                except Exception:
                    pass

                # B. التحقق من ظهور صندوق كتابة المحادثة (داخل الفوتر حصراً)
                msg_input = self._find_input_box()
                if msg_input is not None and msg_input.is_displayed():
                    break

                # إذا لم يبدأ التنقل الداخلي، استخدام driver.get كإجراء احتياطي
                if time.time() - wait_start > 6 and not msg_input:
                    try:
                        curr = self.driver.current_url or ""
                        if clean_phone not in curr:
                            self.driver.get(target_url)
                            time.sleep(2.0)
                    except Exception:
                        pass

                time.sleep(0.5)

            # معالجة الرقم غير المسجل
            if is_invalid_num:
                self._dismiss_modals()
                self.update_daily_stats(False, is_invalid_number=True)
                print(f"[{time.strftime('%H:%M:%S')}] ❌ رقم غير مسجل: {clean_phone}")
                return False, invalid_reason

            # فحص أخير إذا لم يتم العثور على صندوق الكتابة
            if not msg_input:
                msg_input = self._find_input_box()

            if not msg_input:
                self._dismiss_modals()
                self.update_daily_stats(False, is_invalid_number=False)
                return False, "فشل في فتح المحادثة أو العثور على صندوق الرسائل (يرجى التأكد من استقرار الإنترنت)"

            time.sleep(0.5)

            # 📊 قياس عدد الرسائل الصادرة في هذه المحادثة قبل الإرسال (Baseline)
            _baseline_xpath = '//div[contains(@data-testid, "msg-out")] | //div[contains(@class, "message-out")]'
            try:
                _baseline_count = len(self.driver.find_elements(By.XPATH, _baseline_xpath))
            except Exception:
                _baseline_count = -1

            # 📎 4. التعامل مع المرفقات (إذا تم تحديد مرفق)
            if attachment_path and os.path.exists(attachment_path):
                temp_dir = os.path.join(self.session_path, "temp_uploads")
                os.makedirs(temp_dir, exist_ok=True)

                original_ext = os.path.splitext(attachment_path)[1]
                random_filename = f"DOC_{datetime.now().strftime('%H%M%S')}_{random.randint(1000, 9999)}{original_ext}"
                obfuscated_path = os.path.join(temp_dir, random_filename)
                shutil.copy2(attachment_path, obfuscated_path)

                attach_btn_found = None
                attach_selectors = [
                    '//*[contains(@data-testid, "conversation-attach-button")]',
                    '//div[contains(@data-testid, "conversation-attach-button")]',
                    '//span[@data-icon="attach-menu-plus"]/parent::*',
                    '//span[@data-icon="attach-menu-plus"]',
                    '//span[@data-icon="plus"]/parent::*',
                    '//span[@data-icon="plus"]',
                    '//button[contains(@aria-label, "Attach")]',
                    '//button[contains(@aria-label, "إرفاق")]',
                    '//div[@title="Attach"]',
                    '//div[@title="إرفاق"]',
                ]
                for sel in attach_selectors:
                    try:
                        btns = self.driver.find_elements(By.XPATH, sel)
                        if btns and btns[0].is_displayed():
                            attach_btn_found = btns[0]
                            break
                    except Exception: continue

                if attach_btn_found is None:
                    self.update_daily_stats(False, is_invalid_number=False)
                    return False, "فشل العثور على زر الإرفاق"

                time.sleep(0.8)
                try:
                    ActionChains(self.driver).move_to_element(attach_btn_found).pause(0.2).click().perform()
                except Exception:
                    attach_btn_found.click()
                time.sleep(1.5)

                file_inputs = self.driver.find_elements(By.XPATH, '//input[@type="file"]')
                if not file_inputs:
                    self.update_daily_stats(False, is_invalid_number=False)
                    return False, "فشل العثور على حقل رفع الملف"
                file_inputs[-1].send_keys(obfuscated_path)
                time.sleep(3.0)

                wait = WebDriverWait(self.driver, 20)
                caption_input = wait.until(EC.presence_of_element_located((By.XPATH,
                    '//div[@contenteditable="true"][@data-tab="10"]'
                    ' | //div[@contenteditable="true" and contains(@class, "copyable-text")]'
                    ' | //div[@role="textbox"]'
                    ' | //div[contains(@data-testid, "media-caption-input-container")]//div[@contenteditable="true"]'
                )))

                if message:
                    self._inject_text_to_input(caption_input, message)
                    time.sleep(1.0)

                sent_ok = False
                media_send_btn = self._find_send_button()
                if media_send_btn:
                    try:
                        ActionChains(self.driver).move_to_element(media_send_btn).pause(0.3).click().perform()
                        sent_ok = True
                    except Exception: pass
                if not sent_ok:
                    try:
                        caption_input.send_keys(Keys.ENTER)
                        sent_ok = True
                    except Exception: pass

                if not sent_ok:
                    self.update_daily_stats(False, is_invalid_number=False)
                    return False, "فشل في الضغط على زر إرسال المرفق"

            else:
                # 💬 5. إرسال الرسالة النصية
                if not message:
                    return False, "الرسالة فارغة"

                # إدخال الرسالة في صندوق الكتابة المكتشف
                injected = self._inject_text_to_input(msg_input, message)
                if not injected:
                    print(f"[{time.strftime('%H:%M:%S')}] ⚠️ Retry injecting text...")
                    time.sleep(0.5)
                    self._inject_text_to_input(msg_input, message)

                time.sleep(random.uniform(0.6, 1.2))

                # إرسال الرسالة: النقر على زر الإرسال أو إرسال مفتاح ENTER
                sent_ok = False
                send_btn = self._find_send_button()
                if send_btn and send_btn.is_displayed():
                    try:
                        ActionChains(self.driver).move_to_element(send_btn).pause(0.2).click().perform()
                        sent_ok = True
                    except Exception:
                        try:
                            send_btn.click()
                            sent_ok = True
                        except Exception:
                            try:
                                self.driver.execute_script("arguments[0].click();", send_btn)
                                sent_ok = True
                            except Exception:
                                pass

                # الضغط على ENTER مباشرة في صندوق الرسائل (الطريقة الأساسية والمضمونة في واتساب)
                try:
                    msg_input.send_keys(Keys.ENTER)
                    sent_ok = True
                except Exception:
                    try:
                        ActionChains(self.driver).move_to_element(msg_input).click().send_keys(Keys.ENTER).perform()
                        sent_ok = True
                    except Exception:
                        pass

            # 🔍 6. حلقة التحقق الصارم من الإرسال الفعلي (تفريغ الصندوق + زيادة الرسائل)
            sent_verified = False
            verify_start = time.time()
            VERIFY_TIMEOUT = 18

            while time.time() - verify_start < VERIFY_TIMEOUT:
                # أ. فحص تفريغ صندوق الكتابة
                _input_empty = True
                try:
                    if msg_input:
                        _txt = self.driver.execute_script("return (arguments[0].innerText || arguments[0].textContent || '').trim();", msg_input)
                        _input_empty = (len(_txt or "") == 0)
                except Exception:
                    _input_empty = False

                # ب. فحص زيادة عدد الرسائل الصادرة
                _count_increased = False
                try:
                    _now_msgs = self.driver.find_elements(By.XPATH, _baseline_xpath)
                    if _baseline_count >= 0 and len(_now_msgs) > _baseline_count:
                        _count_increased = True
                except Exception:
                    _count_increased = False

                # ج. فحص وجود أيقونة الإرسال (الساعة أو الصح) في آخر رسالة
                _has_send_icon = False
                try:
                    _now_msgs = self.driver.find_elements(By.XPATH, _baseline_xpath)
                    if _now_msgs:
                        _last_m = _now_msgs[-1]
                        _icons = _last_m.find_elements(By.XPATH, './/*[contains(@data-icon, "msg-time") or contains(@data-icon, "msg-check") or contains(@data-icon, "msg-dblcheck")]')
                        if _icons:
                            _has_send_icon = True
                except Exception:
                    _has_send_icon = False

                # د. فحص اختفاء زر الإرسال (رجوعه لزر الميكروفون)
                _send_btn_gone = False
                try:
                    _sb = self._find_send_button()
                    _send_btn_gone = (_sb is None or not _sb.is_displayed())
                except Exception:
                    _send_btn_gone = True

                # المعايير الحاسمة للتحقق:
                # 1. تفريغ الصندوق وزيادة عدد الرسائل الصادرة
                if _input_empty and _count_increased:
                    sent_verified = True
                    break

                # 2. تفريغ الصندوق مع ظهور أيقونة الإرسال واختفاء زر الإرسال
                if _input_empty and _has_send_icon and _send_btn_gone:
                    sent_verified = True
                    break

                # محاولة إضافية للضغط على ENTER بعد 4 ثوانٍ إذا كان الحقل لا يزال يحتوي على نص
                if not _input_empty and (time.time() - verify_start > 4):
                    try:
                        msg_input.send_keys(Keys.ENTER)
                        time.sleep(0.5)
                    except Exception:
                        pass

                time.sleep(0.6)

            if sent_verified:
                self.update_daily_stats(True, is_invalid_number=False)
                print(f"[{time.strftime('%H:%M:%S')}] ✅ تم الإرسال بنجاح إلى: {clean_phone}")
                return True, "تم الإرسال بنجاح"
            else:
                self.update_daily_stats(False, is_invalid_number=False)
                print(f"[{time.strftime('%H:%M:%S')}] ❌ فشل الإرسال إلى: {clean_phone}")
                return False, "فشل الإرسال (لم يتم إرسال الرسالة من المتصفح)"

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"[send_message EXCEPTION] {e}")
            print(tb[:1000])
            short_err = str(e)[:120]
            self.last_error = f"send_message: {short_err}"
            self.update_daily_stats(False, is_invalid_number=False)
            return False, f"خطأ: {short_err}"

    def close(self):
        if self.driver:
            try: self.driver.quit()
            except: pass
            self.driver = None
