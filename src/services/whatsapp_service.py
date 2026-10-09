import os
import time
import shutil
import base64
import io
import random
import subprocess
import re
import json
import logging
from datetime import datetime, date

# إعداد logging للكتابة إلى ملف
LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'whatsapp_debug.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()  # أيضاً يطبع في terminal
    ]
)
logger = logging.getLogger(__name__)

def log_debug(message):
    """دالة مساعدة للlogging - تكتب إلى الملف و terminal"""
    print(message)
    logger.info(message)



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
    """تحليل Spintax وتغيير صياغة الرسائل وتنظيفها لضمان نص طبيعي وبشري 100%"""
    if not text: return ""
    
    # 1. استخدام محرك تغيير الصياغة لتوليد رسالة فريدة بنفس المعنى
    try:
        from src.services.message_variation import MessageVariationEngine
        text = MessageVariationEngine.paraphrase(text)
    except Exception as e:
        print(f"[obfuscate_message] Warning: Could not use paraphrase engine: {e}")
    
    # 2. تحليل Spintax
    text = parse_spintax(text)
    
    # 3. تنظيف الرموز المخفية
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
                stats["invalid_numbers"] = stats.get("invalid_numbers", 0) + 1
                stats["invalid_sequential"] = stats.get("invalid_sequential", 0) + 1
            else:
                stats["technical_fail"] = stats.get("technical_fail", 0) + 1
                stats["invalid_sequential"] = 0
        self._save_json_file(self._daily_stats_file, stats)
        return stats

    def check_send_allowed(self) -> tuple[bool, str]:
        """🛡️ التحقق من إمكانية الإرسال اليوم. يُرجع (مسموح, السبب)."""
        stats = self.get_daily_stats()
        total = stats["sent_ok"] + stats["sent_fail"]
        ok_count = stats["sent_ok"]
        fail_count = stats["sent_fail"]
        invalid_count = stats.get("invalid_numbers", 0)
        seq_invalid = stats.get("invalid_sequential", 0)

        # 1) الحد اليومي الأقصى (للحسابات المستقرة)
        daily_limit = ANTIBAN["DAILY_HARD_LIMIT_ESTABLISHED"]
        if total >= daily_limit:
            return False, f"تم الوصول للحد اليومي ({daily_limit} رسالة). يُرجى الإرسال غداً."

        # 2) معدل الأرقام غير المسجلة فعلياً في واتساب (وليس الأخطاء التقنية للمتصفح)
        if total >= 8 and invalid_count >= 4:
            invalid_pct = (invalid_count / total) * 100
            if invalid_pct >= ANTIBAN["FAILURE_RATE_STOP_PCT"]:
                return (False,
                        f"معدل أرقام غير مسجلة حرج: {invalid_pct:.0f}٪ "
                        f"({invalid_count}/{total} رقم غير مسجل). قائمة الأرقام تحتوي أرقاماً غير صالحة كثيرة — خطر حظر الحساب. تم الإيقاف.")

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

    def reset_daily_stats(self):
        """🔄 إعادة ضبط إحصائيات اليوم وفك أي قفل أمان مؤقت ناتج عن أخطاء تجريبية أو تقنية"""
        try:
            today = _today_str()
            stats = {
                "date": today,
                "sent_ok": 0,
                "sent_fail": 0,
                "invalid_numbers": 0,
                "technical_fail": 0,
                "invalid_sequential": 0,
                "last_reset": datetime.now().isoformat()
            }
            self._save_json_file(self._daily_stats_file, stats)
            print(f"[{time.strftime('%H:%M:%S')}] 🔄 تم إعادة ضبط إحصائيات الإرسال اليومية وفك قفل الأمان بنجاح")
            return True
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] ⚠️ فشل إعادة ضبط الإحصائيات: {e}")
            return False

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

        # Single-instance guard: two concurrent launches race for the same
        # profile and BOTH exit instantly ("Chrome instance exited").
        try:
            _lock_path = os.path.join(self.base_session_dir, "wa_start.lock")
            if os.path.exists(_lock_path):
                if time.time() - os.path.getmtime(_lock_path) < 90:
                    return False, "Engine start already in progress (another launch is running). Wait a minute and retry."
            with open(_lock_path, "w") as _lf:
                _lf.write(str(os.getpid()))
        except Exception:
            pass

        # --- Clean Existing Locks (always: stale locks are the #1 cause of
        # "session not created: Chrome instance exited") ---
        # Only wipe the whole profile when explicitly forced: it holds the
        # WhatsApp login session (deleting it forces a QR re-scan).
        if force_clean and os.path.exists(self.session_path):
            shutil.rmtree(self.session_path, ignore_errors=True)

        os.makedirs(self.session_path, exist_ok=True)

        # Kill leftover chromes that hold OUR profile, then drop lock files.
        # (A zombie keeps the profile locked -> every new launch exits instantly.)
        self._kill_zombies()
        self._remove_chrome_locks()
        
        # --- Stealth & Environment Setup ---
        is_cloud = "/mount/" in __file__.replace("\\", "/") or os.path.exists("/mount")
        # Cloud containers have no X server/screen: headed Chrome dies instantly
        # ("Missing X server or $DISPLAY"). Force headless there; the QR is
        # shown from screenshots (get_qr_hd), so scanning still works.
        # Local runs keep a visible browser for debugging.
        use_headless = True if is_cloud else False
        ver = self._get_chrome_version()
        ua = self._get_random_ua(ver)
        binary = self._find_chrome_binary()

        def create_chrome_options(with_user_dir=True):
            from selenium.webdriver.chrome.options import Options as StdOptions
            o = StdOptions()
            if use_headless:
                o.add_argument("--headless=new")
                o.add_argument("--window-size=1366,768")
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
            o.add_argument("--password-store=basic")
            o.add_argument("--no-first-run")
            o.add_argument("--no-default-browser-check")
            o.add_argument("--disable-crash-reporter")
            o.add_argument("--disable-features=IsolateOrigins,site-per-process,VizDisplayCompositor")
            o.add_argument("--disable-background-timer-throttling")
            o.add_argument("--disable-backgrounding-occluded-windows")
            o.add_argument("--disable-renderer-backgrounding")
            o.add_argument("--memory-pressure-off")
            o.add_argument("--js-flags=--max-old-space-size=4096")
            # NOTE: no --remote-debugging-port on purpose. A fixed debug port
            # collides with zombie Chrome processes and makes every launch
            # exit instantly ("session not created"). Nothing connects to it.
            o.add_argument("--disable-software-rasterizer")
            o.add_experimental_option("excludeSwitches", ["enable-automation"])
            o.add_experimental_option('useAutomationExtension', False)
            if with_user_dir:
                o.add_argument(f"--user-data-dir={self.session_path}")
            if binary:
                o.binary_location = binary
            return o

        # 🚀 ATTEMPT 1: Standard Stealth Selenium (Fastest & 100% Reliable across Cloud & Local)
        _drv_log1 = ""
        try:
            print(f"[{time.strftime('%H:%M:%S')}] Launching Primary Stealth Engine (Headless: {use_headless})...")
            from selenium import webdriver
            from selenium_stealth import stealth
            from selenium.webdriver.chrome.service import Service
            
            std_opts = create_chrome_options(with_user_dir=True)

            # Service with verbose driver log (the log file reveals the real
            # cause when Chrome exits during session creation).
            service, _drv_log1 = self._new_service("attempt1")
            
            try:
                self.driver = webdriver.Chrome(service=service, options=std_opts)
            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] ⚠️ Service configuration failed: {e}, retrying without service")
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
            self.last_error = f"Primary Engine Err: {str(e1)[:500]}"
            _tail1 = self._driver_log_tail(_drv_log1)
            if _tail1:
                self.last_error += f" | driverlog: {_tail1}"

        # 🚀 ATTEMPT 2: Scoped zombie cleanup & retry (keeps the WhatsApp login)
        _drv_log2 = ""
        try:
            print(f"[{time.strftime('%H:%M:%S')}] Retrying with zombie cleanup (profile kept)...")
            self._kill_zombies()
            self._remove_chrome_locks()
            
            from selenium import webdriver
            from selenium_stealth import stealth
            from selenium.webdriver.chrome.service import Service
            
            std_opts = create_chrome_options(with_user_dir=True)

            service, _drv_log2 = self._new_service("attempt2")
            
            try:
                self.driver = webdriver.Chrome(service=service, options=std_opts)
            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] ⚠️ Service configuration failed in retry: {e}, retrying without service")
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
            self.last_error += f" | Attempt 2 Err: {str(e2)[:500]}"
            _tail2 = self._driver_log_tail(_drv_log2)
            if _tail2:
                self.last_error += f" | driverlog2: {_tail2}"

        # 🚀 ATTEMPT 3: Undetected Chromedriver (UC) Fallback
        # NOTE: uc's patched driver rejects selenium *experimental options*
        # ("unrecognized chrome option: excludeSwitches"), so UC gets an
        # args-only options object (uc injects its own stealth switches).
        try:
            import sys as _sys
            try:
                import distutils.version  # noqa: F401
            except ImportError:
                # Python 3.12+ without setuptools shim: uc 3.5.5 still does
                # `from distutils.version import LooseVersion`. Provide a
                # minimal compatible replacement so the import below works.
                import types as _types

                def _loose_parts(v):
                    return [int(x) if x.isdigit() else x
                            for x in re.split(r'(\d+)', str(v)) if x and x != '.']

                class _LooseVersion:
                    def __init__(self, vstring):
                        self.vstring = str(vstring)
                        self.version = _loose_parts(vstring)

                    def __hok(self, other, op):
                        o = other.version if isinstance(other, _LooseVersion) else _loose_parts(other)
                        return op(self.version, o)

                    def __eq__(self, o): return self.__hok(o, lambda a, b: a == b)
                    def __ne__(self, o): return self.__hok(o, lambda a, b: a != b)
                    def __lt__(self, o): return self.__hok(o, lambda a, b: a < b)
                    def __le__(self, o): return self.__hok(o, lambda a, b: a <= b)
                    def __gt__(self, o): return self.__hok(o, lambda a, b: a > b)
                    def __ge__(self, o): return self.__hok(o, lambda a, b: a >= b)
                    def __repr__(self): return f"LooseVersion('{self.vstring}')"

                _dv = _types.ModuleType("distutils.version")
                _dv.LooseVersion = _LooseVersion
                _du = _types.ModuleType("distutils")
                _du.version = _dv
                _sys.modules.setdefault("distutils", _du)
                _sys.modules.setdefault("distutils.version", _dv)
            import undetected_chromedriver as uc
            from selenium.webdriver.chrome.options import Options as _UCOpts
            print(f"[{time.strftime('%H:%M:%S')}] UC Fallback Engine...")
            uc_opts = _UCOpts()
            for _a in [
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                f"--user-agent={ua}",
                "--lang=ar,en-US,en;q=0.9",
                "--disable-blink-features=AutomationControlled",
                "--disable-notifications",
                "--disable-infobars",
                "--password-store=basic",
            ]:
                uc_opts.add_argument(_a)
            self.driver = uc.Chrome(
                options=uc_opts,
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
            self.last_error += f" | UC Err: {str(e3)[:500]}"

        # 🚀 ATTEMPT 4: Fresh temporary profile (diagnostic last resort).
        # Proves whether the saved profile itself is the blocker. WhatsApp
        # login will need a QR re-scan here, but the engine will run.
        try:
            import tempfile as _tf
            print(f"[{time.strftime('%H:%M:%S')}] Trying fresh temporary profile...")
            self._kill_zombies()
            _tmp_profile = _tf.mkdtemp(prefix="wa_fresh_")
            from selenium import webdriver as _wd
            from selenium.webdriver.chrome.service import Service as _Svc
            _fresh_opts = create_chrome_options(with_user_dir=False)
            _fresh_opts.add_argument(f"--user-data-dir={_tmp_profile}")
            if binary:
                _fresh_opts.binary_location = binary
            _svc4 = _Svc()
            if os.name == 'nt':
                _svc4.creation_flags = 0x08000000
            self.driver = _wd.Chrome(service=_svc4, options=_fresh_opts)
            self.driver.get("https://web.whatsapp.com")
            self._wait_for_qr_or_login(timeout=15)
            return True, "Ready (Fresh Temp Profile — rescan QR)"
        except Exception as e4:
            print(f"[{time.strftime('%H:%M:%S')}] Attempt 4 Error: {e4}")
            self.last_error += f" | TempProfile Err: {str(e4)[:500]}"
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

    def _new_service(self, tag="run"):
        """ChromeDriver Service with a verbose log file.

        When Chrome exits during session creation, the driver log reveals
        the real cause (the exception message alone rarely does).
        Returns (service, log_path).
        """
        from selenium.webdriver.chrome.service import Service
        log_path = os.path.join(self.session_path, f"chromedriver_{tag}.log")
        try:
            os.makedirs(self.session_path, exist_ok=True)
            service = Service(service_args=["--verbose"], log_output=log_path)
        except Exception:
            service = Service()
            log_path = ""
        if os.name == 'nt':
            try:
                service.creation_flags = 0x08000000  # CREATE_NO_WINDOW
            except Exception:
                pass
        return service, log_path

    def _driver_log_tail(self, log_path, n=12):
        """Returns the last lines of the chromedriver verbose log.

        Chrome's real crash reason (stderr) lives here, not in the
        selenium exception message.
        """
        try:
            if log_path and os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = [ln.strip() for ln in f.readlines() if ln.strip()]
                tail = " / ".join(lines[-n:])
                return tail[-800:]
        except Exception:
            pass
        return ""

    def _remove_chrome_locks(self):
        """Removes stale Chrome profile lock files (keeps login data intact)."""
        try:
            os.makedirs(self.session_path, exist_ok=True)
            for lf in ["SingletonLock", "SingletonSocket", "SingletonCookie",
                       "lockfile", "DevToolsActivePort"]:
                p = os.path.join(self.session_path, lf)
                try:
                    if os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass
            # Default/ sub-profile may hold its own locks
            for lf in ["SingletonLock", "SingletonSocket", "SingletonCookie",
                       "lockfile", "DevToolsActivePort"]:
                p = os.path.join(self.session_path, "Default", lf)
                try:
                    if os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass
        except Exception:
            pass

    def _kill_zombies(self):
        """Kills leftover chromedriver processes and ONLY the chrome.exe
        instances launched with OUR profile dir (never the user's browser)."""
        try:
            if os.name == 'nt':
                os.system('taskkill /F /IM chromedriver.exe /T >nul 2>&1')
                me = os.path.abspath(self.session_path).lower()
                killed = 0
                cmdlines = []
                try:
                    out = subprocess.check_output(
                        ['wmic', 'process', 'where', "name='chrome.exe'",
                         'get', 'ProcessId,CommandLine', '/format:csv'],
                        stderr=subprocess.DEVNULL, text=True, errors='ignore',
                        timeout=15)
                    cmdlines = out.splitlines()
                except Exception:
                    try:
                        out = subprocess.check_output(
                            ['powershell', '-NoProfile', '-Command',
                             "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
                             "ForEach-Object { \"$($_.ProcessId),$($_.CommandLine)\" }"],
                            stderr=subprocess.DEVNULL, text=True, errors='ignore',
                            timeout=20)
                        cmdlines = out.splitlines()
                    except Exception:
                        cmdlines = []
                for line in cmdlines:
                    ll = line.lower()
                    if 'chrome' not in ll or 'whatsapp_session' not in ll:
                        continue
                    if me not in ll and '--user-data-dir' not in ll:
                        continue
                    pid = line.strip().rsplit(',', 1)[-1].strip()
                    if pid.isdigit():
                        os.system(f'taskkill /F /PID {pid} /T >nul 2>&1')
                        killed += 1
                if killed:
                    time.sleep(3)
                else:
                    time.sleep(1)
            else:
                os.system('pkill -f chromedriver > /dev/null 2>&1')
                try:
                    import shlex
                    os.system(f'pkill -f {shlex.quote(os.path.basename(self.session_path))} > /dev/null 2>&1')
                except Exception:
                    pass
        except Exception:
            pass

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
            
            # تأخيرات واقعية أكثر تنوعاً لمحاكاة الكتابة البشرية
            base_delay = random.uniform(0.03, 0.12)
            
            # تأخير إضافي للرموز الخاصة
            if char in [" ", "\n", ".", ",", "!", "?", "،", "؛", ":", "؛", "؟", "،"]:
                base_delay += random.uniform(0.10, 0.35)
            # تأخير إضافي للأحرف الكبيرة
            elif char.isupper():
                base_delay += random.uniform(0.05, 0.18)
            # تأخير إضافي للأرقام
            elif char.isdigit():
                base_delay += random.uniform(0.04, 0.15)
                
            time.sleep(base_delay)
            
            # وقفات عشوائية أثناء الكتابة لمحاكاة التفكير
            if random.random() < 0.025:
                time.sleep(random.uniform(0.2, 0.8))
            # وقفات أطول نادرة جداً
            elif random.random() < 0.008:
                time.sleep(random.uniform(0.5, 1.2))

    def _find_attachment_send_button(self):
        """العثور على زر إرسال المرفق في شاشة المعاينة (media preview drawer)"""
        from selenium.webdriver.common.by import By
        if not self.driver:
            return None
        
        print(f"[{time.strftime('%H:%M:%S')}] 🔍 _find_attachment_send_button: Searching for attachment send button...")
        
        # أولاً، فحص جميع الأزرار في المعاينة
        try:
            all_buttons = self.driver.find_elements(By.XPATH, '//button')
            visible_buttons = []
            for btn in all_buttons:
                try:
                    if btn.is_displayed():
                        btn_text = btn.text
                        btn_aria = btn.get_attribute('aria-label')
                        btn_data = btn.get_attribute('data-testid')
                        btn_class = btn.get_attribute('class')
                        if btn_text or btn_aria or btn_data:
                            visible_buttons.append({
                                'text': btn_text,
                                'aria': btn_aria,
                                'data': btn_data,
                                'class': btn_class
                            })
                except Exception:
                    continue
            
            if visible_buttons:
                print(f"[{time.strftime('%H:%M:%S')}] 🔍 _find_attachment_send_button: Found {len(visible_buttons)} visible buttons")
                for i, btn_info in enumerate(visible_buttons[:10]):  # First 10 buttons
                    print(f"[{time.strftime('%H:%M:%S')}] 🔍 Button {i+1}: text='{btn_info['text']}', aria='{btn_info['aria']}', data='{btn_info['data']}', class='{btn_info['class']}'")
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] ⚠️ _find_attachment_send_button: Error scanning buttons: {e}")
        
        # Selectors الخاصة بزر إرسال المرفق في شاشة المعاينة
        selectors = [
            # زر الإرسال في شاشة معاينة الوسائط
            '//div[contains(@data-testid, "media-send-button")]',
            '//div[contains(@data-testid, "drawer")]//button[contains(@data-testid, "send")]',
            '//div[contains(@data-testid, "media-preview")]//button[contains(@data-testid, "send")]',
            '//div[contains(@class, "media-send")]//button',
            '//button[@data-icon="send"]/ancestor::div[contains(@class, "drawer")]',
            '//button[@data-icon="send"]/ancestor::div[contains(@data-testid, "media-preview")]',
            # أزرار الإرسال العامة في footer (بديل)
            '//footer//button[@data-testid="compose-btn-send"]',
            '//footer//button[contains(@data-testid, "send")]',
            '//span[@data-icon="send"]/parent::button',
        ]
        
        for i, sel in enumerate(selectors):
            try:
                elems = self.driver.find_elements(By.XPATH, sel)
                for e in elems:
                    try:
                        if e.is_displayed():
                            print(f"[{time.strftime('%H:%M:%S')}] ✅ _find_attachment_send_button: Found button with selector {i+1}: {sel}")
                            return e
                    except Exception:
                        continue
            except Exception:
                continue
        
        print(f"[{time.strftime('%H:%M:%S')}] ❌ _find_attachment_send_button: No attachment send button found")
        return None

    def _find_send_button(self):
        """العثور على زر إرسال المرفق في شاشة المعاينة (media preview drawer)"""
        from selenium.webdriver.common.by import By
        if not self.driver:
            return None
        
        # Selectors الخاصة بزر إرسال المرفق في شاشة المعاينة
        selectors = [
            # زر الإرسال في شاشة معاينة الوسائط
            '//div[contains(@data-testid, "media-send-button")]',
            '//div[contains(@data-testid, "drawer")]//button[contains(@data-testid, "send")]',
            '//div[contains(@data-testid, "media-preview")]//button[contains(@data-testid, "send")]',
            '//div[contains(@class, "media-send")]//button',
            '//button[@data-icon="send"]/ancestor::div[contains(@class, "drawer")]',
            '//button[@data-icon="send"]/ancestor::div[contains(@data-testid, "media-preview")]',
            # أزرار الإرسال العامة في footer (بديل)
            '//footer//button[@data-testid="compose-btn-send"]',
            '//footer//button[contains(@data-testid, "send")]',
            '//span[@data-icon="send"]/parent::button',
        ]
        
        for sel in selectors:
            try:
                elems = self.driver.find_elements(By.XPATH, sel)
                for e in elems:
                    try:
                        if e.is_displayed():
                            return e
                    except Exception:
                        continue
            except Exception:
                continue
        return None
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
        """إدخال النص في صندوق الرسالة بطرق متعددة ومضمونة وسريعة تدعم العربية والإيموجي بالكامل"""
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

        # الطريقة الأولى (الأكثر كفاءة وموثوقية للعربية والأسطر المتعددة): Clipboard Paste (Ctrl+V)
        try:
            copied = _copy_text_to_clipboard(text)
            if copied:
                ActionChains(self.driver).move_to_element(msg_input).click().key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                time.sleep(0.5)
                curr_text = self.driver.execute_script("return (arguments[0].innerText || arguments[0].textContent || '').trim();", msg_input)
                if len(curr_text) > 0:
                    return True
        except Exception as e:
            print(f"[inject_text] Clipboard attempt note: {e}")

        # الطريقة الثانية: JS insertText مع أحداث React InputEvent (Lexical/DraftJS)
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
            if len(curr_text) > 0:
                return True
        except Exception:
            pass

        # الطريقة الثالثة: send_keys سطر بسطر مع Shift+Enter
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

        # الطريقة الرابعة: الكتابة الحرفية
        try:
            self._type_human_like(msg_input, text)
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

        print(f"[{time.strftime('%H:%M:%S')}] ========== STARTING SEND MESSAGE ==========")
        print(f"[{time.strftime('%H:%M:%S')}] Phone: {phone}")
        print(f"[{time.strftime('%H:%M:%S')}] Has attachment: {attachment_path is not None}")
        print(f"[{time.strftime('%H:%M:%S')}] Message length: {len(message) if message else 0}")

        if not self.driver:
            print(f"[{time.strftime('%H:%M:%S')}] ❌ FAILED: Engine Offline (المحرك غير متصل)")
            return False, "Engine Offline (المحرك غير متصل)"
        try:
            _ = self.driver.window_handles
            print(f"[{time.strftime('%H:%M:%S')}] ✅ OPEN_CHAT: Driver is connected")
        except Exception as e:
            self.driver = None
            print(f"[{time.strftime('%H:%M:%S')}] ❌ FAILED: Engine Disconnected - {e}")
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
                print(f"[{time.strftime('%H:%M:%S')}] ❌ FAILED: Invalid phone number ({phone})")
                return False, f"رقم غير صالح ({phone})"

            # إغلاق أي نوافذ منبثقة سابقة
            self._auto_handle_popups()
            self._dismiss_modals()
            time.sleep(0.4)

            # 🌐 2. التنقل المباشر لرابط المحادثة مع دعم التعبئة التلقائية (URL Prefill)
            if message and not attachment_path:
                encoded_msg = urllib.parse.quote(message)
                target_url = f"https://web.whatsapp.com/send/?phone={clean_phone}&text={encoded_msg}"
            else:
                target_url = f"https://web.whatsapp.com/send/?phone={clean_phone}"
            print(f"[{time.strftime('%H:%M:%S')}] 🚀 OPEN_CHAT: Navigating to: {clean_phone}...")

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
                    print(f"[{time.strftime('%H:%M:%S')}] ✅ OPEN_CHAT: Navigated via JS link")
            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] ⚠️ OPEN_CHAT: JS navigation failed: {e}")
                navigated = False

            if not navigated:
                try:
                    self.driver.get(target_url)
                    print(f"[{time.strftime('%H:%M:%S')}] ✅ OPEN_CHAT: Navigated via driver.get()")
                except Exception as e_nav:
                    print(f"[{time.strftime('%H:%M:%S')}] ⚠️ OPEN_CHAT: Navigation retry via JS: {e_nav}")
                    self.driver.execute_script(f"window.location.href = '{target_url}';")

            # فترة انتظار أولية لتهيئة واجهة المحادثة
            time.sleep(random.uniform(2.5, 4.0))
            print(f"[{time.strftime('%H:%M:%S')}] ✅ OPEN_CHAT: Navigation completed, waiting for chat to load")

            # ⏳ 3. حلقة انتظار ظهور صندوق الكتابة أو نافذة خطأ الرقم غير المسجل (حتى 35 ثانية)
            wait_start = time.time()
            msg_input = None
            is_invalid_num = False
            invalid_reason = "رقم غير مسجل في الواتساب"
            invalid_detection_count = 0  # عداد للتحقق المتعدد من الرقم غير الصالح

            while time.time() - wait_start < 35:
                self._auto_handle_popups()

                # A. التحقق من ظهور نافذة رقم غير مسجل (مع تحقق متعدد لتجنب الأخطاء)
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
                                invalid_detection_count += 1
                                # نحتاج للتحقق مرتين متتاليتين لتجنب الأخطاء المؤقتة
                                if invalid_detection_count >= 2:
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
                    # إذا وجد صندوق الكتابة، الرقم صالح - إلغاء أي اكتشاف خاطئ للرقم غير الصالح
                    is_invalid_num = False
                    invalid_detection_count = 0
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
                print(f"[{time.strftime('%H:%M:%S')}] ❌ FAILED: Could not find message input box")
                return False, "فشل في فتح المحادثة أو العثور على صندوق الرسائل (يرجى التأكد من استقرار الإنترنت)"
            
            print(f"[{time.strftime('%H:%M:%S')}] ✅ MESSAGE_BOX_FOUND: Message input box found and ready")

            time.sleep(0.5)

            # 📊 قياس عدد الرسائل الصادرة في هذه المحادثة قبل الإرسال (Baseline)
            _baseline_xpath = '//div[contains(@data-testid, "msg-out")] | //div[contains(@class, "message-out")] | //div[contains(@class, "message-sent")] | //div[contains(@class, "outgoing")]'
            try:
                _baseline_count = len(self.driver.find_elements(By.XPATH, _baseline_xpath))
                print(f"[{time.strftime('%H:%M:%S')}] 📊 Baseline message count: {_baseline_count}")
            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] ⚠️ Error getting baseline count: {e}")
                _baseline_count = -1

            # 📎 4. التعامل مع المرفقات (سواء ملف واحد أو قائمة ملفات PDF، فيديو، صور)
            raw_attachments = []
            if attachment_path:
                print(f"[{time.strftime('%H:%M:%S')}] 📎 ATTACHMENT_STARTED: Processing attachments...")
                if isinstance(attachment_path, (list, tuple, set)):
                    raw_attachments = [str(p) for p in attachment_path if p and os.path.exists(str(p))]
                elif isinstance(attachment_path, str) and os.path.exists(attachment_path):
                    raw_attachments = [attachment_path]
                print(f"[{time.strftime('%H:%M:%S')}] 📎 ATTACHMENT_STARTED: Found {len(raw_attachments)} attachments")

            if raw_attachments:
                temp_dir = os.path.join(self.session_path, "temp_uploads")
                os.makedirs(temp_dir, exist_ok=True)

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

                def _open_attach_menu():
                    for sel in attach_selectors:
                        try:
                            btns = self.driver.find_elements(By.XPATH, sel)
                            if btns and btns[0].is_displayed():
                                try:
                                    ActionChains(self.driver).move_to_element(btns[0]).pause(0.2).click().perform()
                                except Exception:
                                    btns[0].click()
                                return True
                        except Exception:
                            continue
                    return False

                def _select_document_option():
                    """اختيار 'مستند' من قائمة الإرفاق للمستندات"""
                    document_selectors = [
                        '//span[contains(text(), "مستند")]/parent::button',
                        '//span[contains(text(), "Document")]/parent::button',
                        '//div[@title="Document"]',
                        '//div[@title="مستند"]',
                        '//button[contains(@aria-label, "Document")]',
                        '//button[contains(@aria-label, "مستند")]',
                    ]
                    for sel in document_selectors:
                        try:
                            btns = self.driver.find_elements(By.XPATH, sel)
                            if btns and btns[0].is_displayed():
                                try:
                                    ActionChains(self.driver).move_to_element(btns[0]).pause(0.2).click().perform()
                                except Exception:
                                    btns[0].click()
                                print(f"[{time.strftime('%H:%M:%S')}] ✅ ATTACHMENT_SELECTED: Document option selected")
                                return True
                        except Exception:
                            continue
                    print(f"[{time.strftime('%H:%M:%S')}] ⚠️ ATTACHMENT_SELECTED: Document option not found, may use general file input")
                    return False

                media_exts = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.mp4', '.mov', '.avi', '.mkv', '.3gp'}
                document_exts = {'.pdf', '.doc', '.docx', '.txt', '.xls', '.xlsx', '.ppt', '.pptx', '.rtf', '.odt', '.ods', '.odp', '.csv', '.zip', '.rar', '.7z'}

                def _get_target_file_input(ext):
                    ext_lower = ext.lower()
                    is_media = ext_lower in media_exts
                    is_document = ext_lower in document_exts
                    file_inputs = self.driver.find_elements(By.XPATH, '//input[@type="file"]')
                    if not file_inputs:
                        return None
                    
                    msg = f"🔍 _get_target_file_input: Found {len(file_inputs)} file inputs"
                    print(f"[{time.strftime('%H:%M:%S')}] {msg}")
                    logger.info(msg)
                    
                    for i, finp in enumerate(file_inputs):
                        try:
                            acc = (finp.get_attribute("accept") or "").lower()
                            msg = f"🔍 File input {i+1}: accept='{acc}'"
                            print(f"[{time.strftime('%H:%M:%S')}] {msg}")
                            logger.info(msg)
                        except Exception as e:
                            msg = f"⚠️ Error getting accept attribute: {e}"
                            print(f"[{time.strftime('%H:%M:%S')}] {msg}")
                            logger.info(msg)
                    
                    # للمستندات: جرب جميع inputs من الأخير إلى الأول
                    if is_document:
                        msg = f"🔍 _get_target_file_input: Document file, trying inputs from last to first"
                        print(f"[{time.strftime('%H:%M:%S')}] {msg}")
                        logger.info(msg)
                        # عكس القائمة لنجرب من الأخير إلى الأول
                        for finp in reversed(file_inputs):
                            acc = (finp.get_attribute("accept") or "").lower()
                            # تجنب inputs للصور فقط أو الفيديو فقط
                            if "image" in acc and "video" not in acc and "document" not in acc and "*" not in acc:
                                continue
                            if "video" in acc and "image" not in acc and "document" not in acc and "*" not in acc:
                                continue
                            msg = f"✅ _get_target_file_input: Selected document input with accept='{acc}'"
                            print(f"[{time.strftime('%H:%M:%S')}] {msg}")
                            logger.info(msg)
                            return finp
                        # Fallback: آخر input
                        msg = f"⚠️ _get_target_file_input: No suitable document input, using last input"
                        print(f"[{time.strftime('%H:%M:%S')}] {msg}")
                        logger.info(msg)
                        return file_inputs[-1]
                    
                    # للصور/الفيديو: ابحث عن input للصور/الفيديو
                    if is_media:
                        for finp in file_inputs:
                            acc = (finp.get_attribute("accept") or "").lower()
                            if "image" in acc or "video" in acc:
                                msg = f"✅ _get_target_file_input: Selected media input with accept='{acc}'"
                                print(f"[{time.strftime('%H:%M:%S')}] {msg}")
                                logger.info(msg)
                                return finp
                        msg = f"⚠️ _get_target_file_input: No media input, using first input"
                        print(f"[{time.strftime('%H:%M:%S')}] {msg}")
                        logger.info(msg)
                        return file_inputs[0]
                    
                    # للملفات الأخرى: استخدام last input
                    msg = f"⚠️ _get_target_file_input: Unknown file type, using last input"
                    print(f"[{time.strftime('%H:%M:%S')}] {msg}")
                    logger.info(msg)
                    return file_inputs[-1]

                caption_injected = False
                created_temp_subfolders = []

                try:
                    for att_idx, single_att in enumerate(raw_attachments):
                        print(f"[{time.strftime('%H:%M:%S')}] 📎 ATTACHMENT_SELECTED: Processing attachment {att_idx + 1}/{len(raw_attachments)}: {os.path.basename(single_att)}")
                        ext = os.path.splitext(single_att)[1].lower()

                        # وقفة طبيعية لمحاكاة السلوك البشري إذا كان هناك أكثر من مرفق
                        if att_idx > 0:
                            time.sleep(random.uniform(2.5, 4.0))

                        # فتح قائمة الإرفاق وجعل file inputs تظهر
                        print(f"[{time.strftime('%H:%M:%S')}] 📎 ATTACHMENT_SELECTED: Opening attach menu to reveal file inputs...")
                        opened = _open_attach_menu()
                        if not opened:
                            print(f"[{time.strftime('%H:%M:%S')}] ⚠️ ATTACHMENT_SELECTED: First attempt failed, retrying...")
                            time.sleep(0.8)
                            opened = _open_attach_menu()
                        if not opened:
                            print(f"[{time.strftime('%H:%M:%S')}] ❌ ATTACHMENT_SELECTED: Failed to find attach button")
                            self.update_daily_stats(False, is_invalid_number=False)
                            return False, "فشل العثور على زر الإرفاق"
                        print(f"[{time.strftime('%H:%M:%S')}] ✅ ATTACHMENT_SELECTED: Attach menu opened")

                        # للمستندات: تغيير accept attribute لـ file input لقبول المستندات
                        if ext.lower() in document_exts:
                            print(f"[{time.strftime('%H:%M:%S')}] 📎 ATTACHMENT_SELECTED: Document detected, modifying file input to accept documents...")
                            target_input = _get_target_file_input(ext)
                            if target_input:
                                try:
                                    # تغيير accept attribute باستخدام JavaScript
                                    modify_accept_script = """
                                    (function() {
                                        var inputs = document.querySelectorAll('input[type="file"]');
                                        for (var i = 0; i < inputs.length; i++) {
                                            inputs[i].setAttribute('accept', '*/*');
                                        }
                                        return 'Modified ' + inputs.length + ' inputs';
                                    })();
                                    """
                                    result = self.driver.execute_script(modify_accept_script)
                                    print(f"[{time.strftime('%H:%M:%S')}] ✅ ATTACHMENT_SELECTED: Modified file input accept: {result}")
                                    time.sleep(0.5)
                                except Exception as e:
                                    print(f"[{time.strftime('%H:%M:%S')}] ⚠️ ATTACHMENT_SELECTED: Failed to modify accept: {e}")
                            else:
                                print(f"[{time.strftime('%H:%M:%S')}] ❌ ATTACHMENT_SELECTED: No file input found")
                        else:
                            time.sleep(0.5)
                            target_input = _get_target_file_input(ext)
                        
                        target_input = _get_target_file_input(ext)
                        if not target_input:
                            print(f"[{time.strftime('%H:%M:%S')}] ❌ ATTACHMENT_SELECTED: Failed to find file input for ext: {ext}")
                            self.update_daily_stats(False, is_invalid_number=False)
                            return False, "فشل العثور على حقل رفع الملف"
                        print(f"[{time.strftime('%H:%M:%S')}] ✅ ATTACHMENT_SELECTED: File input found for ext: {ext}")

                        # الحفاظ على الاسم الأصلي للملف داخل مجلد مؤقت فريد
                        orig_name = os.path.basename(single_att)
                        send_subfolder = os.path.join(temp_dir, f"send_{int(time.time()*1000)}_{random.randint(100, 999)}")
                        os.makedirs(send_subfolder, exist_ok=True)
                        created_temp_subfolders.append(send_subfolder)
                        ready_path = os.path.join(send_subfolder, orig_name)
                        shutil.copy2(single_att, ready_path)
                        print(f"[{time.strftime('%H:%M:%S')}] ✅ ATTACHMENT_UPLOAD_STARTED: File copied to temp: {ready_path}")

                        # رفع الملف
                        try:
                            target_input.send_keys(ready_path)
                            print(f"[{time.strftime('%H:%M:%S')}] ✅ PDF_UPLOAD_STARTED: File path sent to input successfully")
                        except Exception as e:
                            print(f"[{time.strftime('%H:%M:%S')}] ❌ PDF_UPLOAD_STARTED: Failed to send file path: {e}")
                            self.update_daily_stats(False, is_invalid_number=False)
                            return False, f"فشل رفع المرفق ({orig_name})"

                        time.sleep(2.5)
                        print(f"[{time.strftime('%H:%M:%S')}] ⏳ PDF_UPLOAD_STARTED: Waiting for preview to appear...")
                        
                        # فحص رسالة خطأ "الملف غير مدعوم"
                        try:
                            error_msg = self.driver.find_elements(By.XPATH, '//*[contains(text(), "غير مدعوم") or contains(text(), "not supported")]')
                            if error_msg:
                                print(f"[{time.strftime('%H:%M:%S')}] ❌ PDF_UPLOAD_STARTED: WhatsApp shows 'file not supported' error")
                                print(f"[{time.strftime('%H:%M:%S')}] ❌ PDF_UPLOAD_STARTED: Wrong file input was selected - file treated as image instead of document")
                                logger.info("❌ PDF_UPLOAD_STARTED: WhatsApp shows 'file not supported' error")
                                # حاول استخدام file input آخر
                                print(f"[{time.strftime('%H:%M:%S')}] 🔧 PDF_UPLOAD_STARTED: Trying alternative file input...")
                                try:
                                    file_inputs = self.driver.find_elements(By.XPATH, '//input[@type="file"]')
                                    if len(file_inputs) > 1:
                                        # استخدم file input مختلف
                                        for alt_input in reversed(file_inputs):
                                            if alt_input != target_input:
                                                try:
                                                    alt_input.send_keys(ready_path)
                                                    print(f"[{time.strftime('%H:%M:%S')}] ✅ PDF_UPLOAD_STARTED: Retried with alternative file input")
                                                    logger.info("✅ PDF_UPLOAD_STARTED: Retried with alternative file input")
                                                    time.sleep(2.5)
                                                    # فحص مرة أخرى
                                                    error_msg = self.driver.find_elements(By.XPATH, '//*[contains(text(), "غير مدعوم") or contains(text(), "not supported")]')
                                                    if not error_msg:
                                                        print(f"[{time.strftime('%H:%M:%S')}] ✅ PDF_UPLOAD_STARTED: Alternative input worked!")
                                                        logger.info("✅ PDF_UPLOAD_STARTED: Alternative input worked!")
                                                        break
                                                except Exception as e:
                                                    print(f"[{time.strftime('%H:%M:%S')}] ⚠️ PDF_UPLOAD_STARTED: Alternative input failed: {e}")
                                                    continue
                                except Exception as e:
                                    print(f"[{time.strftime('%H:%M:%S')}] ⚠️ PDF_UPLOAD_STARTED: Failed to try alternative: {e}")
                                
                                # فحص نهائي
                                error_msg = self.driver.find_elements(By.XPATH, '//*[contains(text(), "غير مدعوم") or contains(text(), "not supported")]')
                                if error_msg:
                                    print(f"[{time.strftime('%H:%M:%S')}] ❌ PDF_UPLOAD_STARTED: Still showing error after retry")
                                    logger.info("❌ PDF_UPLOAD_STARTED: Still showing error after retry")
                                    self.update_daily_stats(False, is_invalid_number=False)
                                    return False, "الملف غير مدعوم من WhatsApp (تم تجربة جميع file inputs)"
                        except Exception as e:
                            print(f"[{time.strftime('%H:%M:%S')}] ⚠️ PDF_UPLOAD_STARTED: Error checking for error message: {e}")
                            logger.info(f"⚠️ PDF_UPLOAD_STARTED: Error checking for error message: {e}")

                        # فحص شاشة المعاينة وصندوق النص المرفق
                        caption_input = None
                        try:
                            wait = WebDriverWait(self.driver, 15)
                            caption_input = wait.until(EC.presence_of_element_located((By.XPATH,
                                '//div[@contenteditable="true"][@data-tab="10"]'
                                ' | //div[@contenteditable="true" and contains(@class, "copyable-text")]'
                                ' | //div[@role="textbox"]'
                                ' | //div[contains(@data-testid, "media-caption-input-container")]//div[@contenteditable="true"]'
                            )))
                            print(f"[{time.strftime('%H:%M:%S')}] ✅ PDF_UPLOAD_COMPLETED: Caption input found")
                        except Exception as e:
                            print(f"[{time.strftime('%H:%M:%S')}] ⚠️ PDF_UPLOAD_COMPLETED: Caption input not found (may be document without caption): {e}")
                            caption_input = None

                        # لا نحقن الرسالة كـ Caption مع المرفق لمنع المشاكل
                        # سنرسل الرسالة في صندوق المحادثة بعد اختفاء المعاينة
                        caption_injected = False
                        print(f"[{time.strftime('%H:%M:%S')}] ℹ️ PDF_UPLOAD_COMPLETED: Skipping caption injection to avoid issues, will send in chat box after attachment")

                        # التحقق من ظهور معاينة المرفق قبل البحث عن زر الإرسال
                        print(f"[{time.strftime('%H:%M:%S')}] 🔍 PDF_PREVIEW_VISIBLE: Checking for attachment preview...")
                        preview_visible = False
                        try:
                            previews = self.driver.find_elements(By.XPATH,
                                '//div[contains(@data-testid, "media-preview")] | '
                                '//div[contains(@data-testid, "media-caption-input-container")] | '
                                '//div[contains(@data-testid, "drawer-middle")]'
                            )
                            if previews and any(p.is_displayed() for p in previews):
                                preview_visible = True
                                print(f"[{time.strftime('%H:%M:%S')}] ✅ PDF_PREVIEW_VISIBLE: Attachment preview is visible")
                            else:
                                print(f"[{time.strftime('%H:%M:%S')}] ⚠️ PDF_PREVIEW_VISIBLE: Attachment preview not visible, waiting more...")
                                time.sleep(5.0)  # زيادة من 3.0 إلى 5.0 ثانية
                                # Check again
                                previews = self.driver.find_elements(By.XPATH,
                                    '//div[contains(@data-testid, "media-preview")] | '
                                    '//div[contains(@data-testid, "media-caption-input-container")] | '
                                    '//div[contains(@data-testid, "drawer-middle")]'
                                )
                                if previews and any(p.is_displayed() for p in previews):
                                    preview_visible = True
                                    print(f"[{time.strftime('%H:%M:%S')}] ✅ PDF_PREVIEW_VISIBLE: Attachment preview visible after retry")
                        except Exception as e:
                            print(f"[{time.strftime('%H:%M:%S')}] ⚠️ PDF_PREVIEW_VISIBLE: Error checking preview: {e}")

                        if not preview_visible:
                            print(f"[{time.strftime('%H:%M:%S')}] ❌ PDF_SEND_FAILED: Attachment preview not visible, cannot send")
                            self.update_daily_stats(False, is_invalid_number=False)
                            return False, "فشل ظهور معاينة المرفق، لا يمكن الإرسال"

                        # مهلة أمان إضافية بحسب حجم الملف ونوعه (فيديوهات / مستندات PDF) لضمان تسليمه لخوادم واتساب
                        try:
                            file_size_mb = os.path.getsize(ready_path) / (1024 * 1024)
                        except Exception:
                            file_size_mb = 1.0

                        if ext in ['.mp4', '.mov', '.avi', '.mkv'] or file_size_mb > 5:
                            print(f"[{time.strftime('%H:%M:%S')}] ⏳ PDF_UPLOAD_COMPLETED: Video/large file, waiting {min(10.0, 4.0 + file_size_mb * 0.5):.1f}s")
                            time.sleep(min(10.0, 4.0 + file_size_mb * 0.5))
                        elif ext in ['.pdf', '.doc', '.docx']:
                            print(f"[{time.strftime('%H:%M:%S')}] ⏳ PDF_UPLOAD_COMPLETED: Document, waiting {min(7.0, 3.0 + file_size_mb * 0.4):.1f}s")
                            time.sleep(min(7.0, 3.0 + file_size_mb * 0.4))
                        else:
                            print(f"[{time.strftime('%H:%M:%S')}] ⏳ PDF_UPLOAD_COMPLETED: Other file, waiting 3.0s")
                            time.sleep(3.0)
                        
                        # تأخير إضافي لضمان استقرار WhatsApp قبل الإرسال
                        print(f"[{time.strftime('%H:%M:%S')}] ⏳ PDF_UPLOAD_COMPLETED: Waiting for WhatsApp to stabilize before send...")
                        time.sleep(2.0)

                        # مهلة أمان إضافية بحسب حجم الملف ونوعه (فيديوهات / مستندات PDF) لضمان تسليمه لخوادم واتساب
                        try:
                            file_size_mb = os.path.getsize(ready_path) / (1024 * 1024)
                        except Exception:
                            file_size_mb = 1.0

                        if ext in ['.mp4', '.mov', '.avi', '.mkv'] or file_size_mb > 5:
                            print(f"[{time.strftime('%H:%M:%S')}] ⏳ PDF_UPLOAD_COMPLETED: Video/large file, waiting {min(10.0, 4.0 + file_size_mb * 0.5):.1f}s")
                            time.sleep(min(10.0, 4.0 + file_size_mb * 0.5))
                        elif ext in ['.pdf', '.doc', '.docx']:
                            print(f"[{time.strftime('%H:%M:%S')}] ⏳ PDF_UPLOAD_COMPLETED: Document, waiting {min(7.0, 3.0 + file_size_mb * 0.4):.1f}s")
                            time.sleep(min(7.0, 3.0 + file_size_mb * 0.4))
                        else:
                            print(f"[{time.strftime('%H:%M:%S')}] ⏳ PDF_UPLOAD_COMPLETED: Other file, waiting 3.0s")
                            time.sleep(3.0)
                        
                        # تأخير إضافي لضمان استقرار WhatsApp قبل الإرسال
                        print(f"[{time.strftime('%H:%M:%S')}] ⏳ PDF_UPLOAD_COMPLETED: Waiting for WhatsApp to stabilize before send...")
                        time.sleep(2.0)

                        # النقر على زر إرسال المرفق
                        sent_att_ok = False
                        media_send_btn = self._find_attachment_send_button()  # استخدام الدالة الجديدة
                        print(f"[{time.strftime('%H:%M:%S')}] 🔘 ATTACHMENT_SEND_BUTTON_FOUND: Attachment send button found: {media_send_btn is not None}")
                        if media_send_btn:
                            try:
                                ActionChains(self.driver).move_to_element(media_send_btn).pause(0.5).click().perform()
                                sent_att_ok = True
                                print(f"[{time.strftime('%H:%M:%S')}] ✅ ATTACHMENT_SEND_BUTTON_CLICKED: Clicked attachment send button")
                                time.sleep(1.0)  # Wait after click
                                
                                # فحص فوري: هل المعاينة ما زالت ظاهرة؟
                                try:
                                    previews_after_click = self.driver.find_elements(By.XPATH,
                                        '//div[contains(@data-testid, "media-preview")] | '
                                        '//div[contains(@data-testid, "media-caption-input-container")] | '
                                        '//div[contains(@data-testid, "drawer-middle")]'
                                    )
                                    preview_visible_after = previews_after_click and any(p.is_displayed() for p in previews_after_click)
                                    print(f"[{time.strftime('%H:%M:%S')}] 🔍 ATTACHMENT_SEND_BUTTON_CLICKED: Preview visible after click: {preview_visible_after}")
                                except Exception as e:
                                    print(f"[{time.strftime('%H:%M:%S')}] ⚠️ ATTACHMENT_SEND_BUTTON_CLICKED: Error checking preview after click: {e}")
                            except Exception as e:
                                print(f"[{time.strftime('%H:%M:%S')}] ⚠️ ATTACHMENT_SEND_BUTTON_CLICKED: ActionChains click failed: {e}")
                                try:
                                    media_send_btn.click()
                                    sent_att_ok = True
                                    print(f"[{time.strftime('%H:%M:%S')}] ✅ ATTACHMENT_SEND_BUTTON_CLICKED: Clicked directly")
                                    time.sleep(1.0)
                                except Exception as e2:
                                    print(f"[{time.strftime('%H:%M:%S')}] ⚠️ ATTACHMENT_SEND_BUTTON_CLICKED: Direct click failed: {e2}")
                        else:
                            print(f"[{time.strftime('%H:%M:%S')}] ❌ ATTACHMENT_SEND_BUTTON_FOUND: Could not find attachment send button, trying regular send button")
                            # Fallback to regular send button
                            media_send_btn = self._find_send_button()
                            if media_send_btn:
                                try:
                                    ActionChains(self.driver).move_to_element(media_send_btn).pause(0.5).click().perform()
                                    sent_att_ok = True
                                    print(f"[{time.strftime('%H:%M:%S')}] ✅ ATTACHMENT_SEND_BUTTON_CLICKED: Clicked regular send button as fallback")
                                    time.sleep(1.0)
                                except Exception as e:
                                    print(f"[{time.strftime('%H:%M:%S')}] ⚠️ ATTACHMENT_SEND_BUTTON_CLICKED: Fallback click failed: {e}")
                        
                        if not sent_att_ok and caption_input:
                            try:
                                caption_input.send_keys(Keys.ENTER)
                                sent_att_ok = True
                                print(f"[{time.strftime('%H:%M:%S')}] ✅ ATTACHMENT_SEND_BUTTON_CLICKED: Pressed ENTER on caption input")
                            except Exception as e:
                                print(f"[{time.strftime('%H:%M:%S')}] ⚠️ ATTACHMENT_SEND_BUTTON_CLICKED: ENTER on caption failed: {e}")
                        if not sent_att_ok:
                            try:
                                alt_btns = self.driver.find_elements(By.XPATH, '//span[@data-icon="send"]/parent::* | //button[@aria-label="Send" or @aria-label="إرسال"]')
                                if alt_btns and alt_btns[-1].is_displayed():
                                    alt_btns[-1].click()
                                    sent_att_ok = True
                                    print(f"[{time.strftime('%H:%M:%S')}] ✅ ATTACHMENT_SEND_BUTTON_CLICKED: Clicked alternative send button")
                            except Exception as e:
                                print(f"[{time.strftime('%H:%M:%S')}] ⚠️ ATTACHMENT_SEND_BUTTON_CLICKED: Alternative button failed: {e}")

                        if not sent_att_ok:
                            self.update_daily_stats(False, is_invalid_number=False)
                            print(f"[{time.strftime('%H:%M:%S')}] ❌ PDF_SEND_FAILED: فشل في الضغط على زر إرسال المرفق ({orig_name})")
                            return False, f"فشل في الضغط على زر إرسال المرفق ({orig_name})"

                        # ⏳ الانتظار حتى اكتمال رفع الوسائط وإغلاق شاشة المعاينة بعد الإرسال
                        up_start = time.time()
                        print(f"[{time.strftime('%H:%M:%S')}] ⏳ PDF_SEND_CONFIRMED: Waiting for attachment preview to close (message sent)...")
                        preview_closed = False
                        while time.time() - up_start < 45:  # زيادة من 30 إلى 45 ثانية
                            previews = self.driver.find_elements(By.XPATH,
                                '//div[contains(@data-testid, "media-preview")] | '
                                '//div[contains(@data-testid, "media-caption-input-container")] | '
                                '//div[contains(@data-testid, "drawer-middle")]'
                            )
                            if not previews or not any(p.is_displayed() for p in previews):
                                print(f"[{time.strftime('%H:%M:%S')}] ✅ PDF_SEND_CONFIRMED: Attachment preview closed, PDF sent successfully")
                                preview_closed = True
                                break
                            time.sleep(1.0)  # زيادة من 0.5 إلى 1.0 ثانية
                        else:
                            print(f"[{time.strftime('%H:%M:%S')}] ⚠️ PDF_SEND_CONFIRMED: Preview still visible after timeout, but assuming sent")
                            # Consider it sent anyway to avoid blocking
                        
                        # فحص إضافي: التأكد من أن المرفق تم إرساله (عنصر message)
                        if preview_closed:
                            try:
                                # البحث عن رسالة المرفق في المحادثة
                                time.sleep(2.0)
                                attachment_msgs = self.driver.find_elements(By.XPATH,
                                    '//div[contains(@data-testid, "msg-out")]//div[contains(@class, "message-document")] | '
                                    '//div[contains(@data-testid, "msg-out")]//div[contains(@class, "message-image")] | '
                                    '//div[contains(@data-testid, "msg-out")]//div[contains(@class, "message-video")]'
                                )
                                if attachment_msgs:
                                    print(f"[{time.strftime('%H:%M:%S')}] ✅ PDF_SEND_CONFIRMED: Found {len(attachment_msgs)} attachment messages in chat")
                                else:
                                    print(f"[{time.strftime('%H:%M:%S')}] ⚠️ PDF_SEND_CONFIRMED: No attachment message found in chat (attachment may not have been sent)")
                            except Exception as e:
                                print(f"[{time.strftime('%H:%M:%S')}] ⚠️ PDF_SEND_CONFIRMED: Error checking attachment messages: {e}")

                    # لا نرسل الرسالة مرة أخرى في صندوق المحادثة إذا تم إرسالها كـ Caption مع المرفق
                    # لأن الضغط على زر الإرسال في شاشة المعاينة يرسل الرسالة + المرفق معاً
                    if message and not caption_injected:
                        print(f"[{time.strftime('%H:%M:%S')}] 📝 MESSAGE_TYPED: Message not injected as caption, sending in chat box...")
                        time.sleep(3.0)  # Wait for preview to close fully - زيادة من 2.0 إلى 3.0
                        chat_box = self._find_input_box()
                        if chat_box:
                            print(f"[{time.strftime('%H:%M:%S')}] ✅ MESSAGE_TYPED: Chat box found after preview closed")
                            if self._inject_text_to_input(chat_box, message):
                                print(f"[{time.strftime('%H:%M:%S')}] ✅ MESSAGE_TYPED: Message injected into chat box")
                                time.sleep(1.5)  # زيادة من 0.8 إلى 1.5
                                snd = self._find_send_button()
                                if snd:
                                    print(f"[{time.strftime('%H:%M:%S')}] 🔘 SEND_CLICKED: Clicking send button in chat box...")
                                    try: 
                                        snd.click()
                                        print(f"[{time.strftime('%H:%M:%S')}] ✅ SEND_CLICKED: Send button clicked")
                                        # Wait for send to complete
                                        time.sleep(3.0)  # زيادة من 2.0 إلى 3.0
                                    except Exception as e:
                                        print(f"[{time.strftime('%H:%M:%S')}] ⚠️ SEND_CLICKED: Click failed: {e}, trying ENTER...")
                                        chat_box.send_keys(Keys.ENTER)
                                        print(f"[{time.strftime('%H:%M:%S')}] ✅ SEND_CLICKED: ENTER pressed")
                                        time.sleep(3.0)  # زيادة من 2.0 إلى 3.0
                                else:
                                    print(f"[{time.strftime('%H:%M:%S')}] ⚠️ SEND_CLICKED: Send button not found, trying ENTER...")
                                    chat_box.send_keys(Keys.ENTER)
                                    print(f"[{time.strftime('%H:%M:%S')}] ✅ SEND_CLICKED: ENTER pressed")
                                    time.sleep(3.0)  # زيادة من 2.0 إلى 3.0
                            else:
                                print(f"[{time.strftime('%H:%M:%S')}] ❌ MESSAGE_TYPED: Failed to inject message into chat box")
                        else:
                            print(f"[{time.strftime('%H:%M:%S')}] ❌ MESSAGE_TYPED: Chat box not found after preview closed")
                    else:
                        print(f"[{time.strftime('%H:%M:%S')}] ℹ️ MESSAGE_TYPED: No message to send or already sent separately")
                        # Wait a bit to ensure attachment processing is complete
                        time.sleep(2.0)
                    
                    print(f"[{time.strftime('%H:%M:%S')}] ✅ ATTACHMENT_SEND_COMPLETED: All attachments processed successfully")
                    
                    # 🔍 التحقق من الإرسال بعد معالجة المرفقات
                    print(f"[{time.strftime('%H:%M:%S')}] 🔍 SEND_CONFIRMED: Verifying message send after attachments...")
                    verify_start = time.time()
                    VERIFY_TIMEOUT = 30
                    sent_verified = False
                    
                    # Wait a bit first for the message to appear
                    time.sleep(2.0)
                    
                    while time.time() - verify_start < VERIFY_TIMEOUT:
                        _count_increased = False
                        try:
                            _now_msgs = self.driver.find_elements(By.XPATH, _baseline_xpath)
                            if _baseline_count >= 0 and len(_now_msgs) > _baseline_count:
                                _count_increased = True
                                print(f"[{time.strftime('%H:%M:%S')}] ✅ SEND_CONFIRMED: Message count increased from {_baseline_count} to {len(_now_msgs)}")
                            else:
                                print(f"[{time.strftime('%H:%M:%S')}] ⏳ SEND_CONFIRMED: Current count: {len(_now_msgs)}, Baseline: {_baseline_count}")
                        except Exception as e:
                            print(f"[{time.strftime('%H:%M:%S')}] ⚠️ SEND_CONFIRMED: Error checking message count: {e}")
                            _count_increased = False
                        
                        if _count_increased:
                            sent_verified = True
                            print(f"[{time.strftime('%H:%M:%S')}] ✅ SEND_CONFIRMED: Message count increased, send verified")
                            break
                        
                        time.sleep(1.0)
                    
                    if not sent_verified:
                        print(f"[{time.strftime('%H:%M:%S')}] ❌ SEND_CONFIRMED: Could not verify send after {VERIFY_TIMEOUT}s, message not confirmed sent")
                        self.update_daily_stats(False, is_invalid_number=False)
                        return False, "فشل التحقق من الإرسال، الرسالة لم تُرسل"
                    
                    # Return success after attachments
                    self.update_daily_stats(True, is_invalid_number=False)
                    print(f"[{time.strftime('%H:%M:%S')}] ✅ SEND_CONFIRMED: تم الإرسال بنجاح إلى: {clean_phone}")
                    return True, "تم الإرسال بنجاح"
                finally:
                    # تنظيف المجلدات المؤقتة المنشأة لهذا الإرسال
                    for sub in created_temp_subfolders:
                        try: shutil.rmtree(sub, ignore_errors=True)
                        except Exception: pass

            else:
                # 💬 5. إرسال الرسالة النصية
                if not message:
                    return False, "الرسالة فارغة"

                print(f"[{time.strftime('%H:%M:%S')}] 📝 Checking message in input box (length: {len(message)} chars)...")

                # التحقق هل الرسالة موجودة مسبقاً عبر الرابط (URL Prefill)
                curr_text = ""
                try:
                    curr_text = self.driver.execute_script("return (arguments[0].innerText || arguments[0].textContent || '').trim();", msg_input)
                except Exception:
                    pass

                injected = (len(curr_text) > 0)
                if injected:
                    print(f"[{time.strftime('%H:%M:%S')}] ✅ Message already in input box (prefilled via URL)")
                else:
                    injected = self._inject_text_to_input(msg_input, message)
                    if not injected:
                        print(f"[{time.strftime('%H:%M:%S')}] ⚠️ First injection failed, retrying...")
                        time.sleep(0.5)
                        injected = self._inject_text_to_input(msg_input, message)

                if not injected:
                    print(f"[{time.strftime('%H:%M:%S')}] ❌ FAILED: All injection methods failed")
                    return False, "فشل في إدخال الرسالة في صندوق الكتابة"

                print(f"[{time.strftime('%H:%M:%S')}] ✅ MESSAGE_TYPED: Message ready in input box")
                time.sleep(random.uniform(0.6, 1.2))

                # إرسال الرسالة: النقر على زر الإرسال المكتشف بدقة
                sent_ok = False
                send_btn = self._find_send_button()
                print(f"[{time.strftime('%H:%M:%S')}] 🔘 SEND_CLICKED: Send button found: {send_btn is not None}")

                if send_btn and send_btn.is_displayed():
                    try:
                        ActionChains(self.driver).move_to_element(send_btn).pause(0.2).click().perform()
                        sent_ok = True
                        print(f"[{time.strftime('%H:%M:%S')}] ✅ SEND_CLICKED: Clicked send button via ActionChains")
                    except Exception as e:
                        print(f"[{time.strftime('%H:%M:%S')}] ⚠️ SEND_CLICKED: ActionChains click failed: {e}")
                        try:
                            send_btn.click()
                            sent_ok = True
                            print(f"[{time.strftime('%H:%M:%S')}] ✅ SEND_CLICKED: Clicked send button directly")
                        except Exception as e2:
                            print(f"[{time.strftime('%H:%M:%S')}] ⚠️ SEND_CLICKED: Direct click failed: {e2}")
                            try:
                                self.driver.execute_script("""
                                    var btn = arguments[0];
                                    btn.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, cancelable: true}));
                                    btn.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, cancelable: true}));
                                    btn.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
                                """, send_btn)
                                sent_ok = True
                                print(f"[{time.strftime('%H:%M:%S')}] ✅ SEND_CLICKED: Clicked send button via JS")
                            except Exception as e3:
                                print(f"[{time.strftime('%H:%M:%S')}] ❌ SEND_CLICKED: JS click failed: {e3}")
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] ⚠️ SEND_CLICKED: Send button not found or not visible")

                # إذا لم يكن زر الإرسال متاحاً أو فشل النقر عليه، نستخدم ENTER كبديل وحيد
                if not sent_ok:
                    print(f"[{time.strftime('%H:%M:%S')}] 🔑 SEND_CLICKED: Trying ENTER key as fallback...")
                    try:
                        self.driver.execute_script("arguments[0].focus();", msg_input)
                        msg_input.click()
                        time.sleep(0.2)
                        msg_input.send_keys(Keys.ENTER)
                        sent_ok = True
                        print(f"[{time.strftime('%H:%M:%S')}] ✅ SEND_CLICKED: Pressed ENTER key on input box")
                    except Exception as e:
                        print(f"[{time.strftime('%H:%M:%S')}] ⚠️ SEND_CLICKED: ENTER key failed: {e}")
                        try:
                            ActionChains(self.driver).move_to_element(msg_input).click().send_keys(Keys.ENTER).perform()
                            sent_ok = True
                            print(f"[{time.strftime('%H:%M:%S')}] ✅ SEND_CLICKED: Pressed ENTER via ActionChains")
                        except Exception as e2:
                            print(f"[{time.strftime('%H:%M:%S')}] ❌ SEND_CLICKED: ENTER via ActionChains failed: {e2}")

                print(f"[{time.strftime('%H:%M:%S')}] 📊 SEND_CLICKED: Send operation completed: {sent_ok}")

            # 🔍 6. حلقة التحقق المحسّن من الإرسال الفعلي (أكثر تساهلاً ودقة)
            sent_verified = False
            verify_start = time.time()
            VERIFY_TIMEOUT = 30  # زيادة وقت التحقق إلى 30 ثانية
            
            print(f"[{time.strftime('%H:%M:%S')}] 🔍 SEND_CONFIRMED: Starting verification loop (text message path)...")

            while time.time() - verify_start < VERIFY_TIMEOUT:
                # أ. فحص تفريغ صندوق الكتابة
                _input_empty = True
                _current_input_text = ""
                try:
                    if msg_input:
                        _current_input_text = self.driver.execute_script("return (arguments[0].innerText || arguments[0].textContent || '').trim();", msg_input)
                        _input_empty = (len(_current_input_text or "") == 0)
                except Exception:
                    _input_empty = False

                # ب. فحص زيادة عدد الرسائل الصادرة
                _count_increased = False
                try:
                    _now_msgs = self.driver.find_elements(By.XPATH, _baseline_xpath)
                    if _baseline_count >= 0 and len(_now_msgs) > _baseline_count:
                        _count_increased = True
                        print(f"[{time.strftime('%H:%M:%S')}] ✅ SEND_CONFIRMED: Message count increased from {_baseline_count} to {len(_now_msgs)}")
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

                # هـ. فحص وجود رسالة صادرة جديدة في الـ DOM
                _has_new_msgout = False
                try:
                    _now_msgs = self.driver.find_elements(By.XPATH, _baseline_xpath)
                    if _now_msgs and _baseline_count >= 0:
                        if len(_now_msgs) > _baseline_count:
                            _has_new_msgout = True
                        elif len(_now_msgs) > 0:
                            _has_new_msgout = True
                except Exception:
                    _has_new_msgout = False

                # المعايير الحاسمة للتحقق (أكثر تساهلاً ودقة):
                # 1. زيادة عدد الرسائل الصادرة (أقوى دليل)
                if _count_increased:
                    sent_verified = True
                    break

                # 2. اختفاء زر الإرسال (تحول إلى ميكروفون) بعد إرسال الرسالة
                if _send_btn_gone and (_input_empty or (time.time() - verify_start > 2)):
                    sent_verified = True
                    break

                # 3. تفريغ الصندوق مع وجود رسالة صادرة أو أيقونة إرسال
                if _input_empty and (_has_new_msgout or _has_send_icon):
                    sent_verified = True
                    break

                # 4. تفريغ الصندوق فقط بعد ثانيتين
                if _input_empty and (time.time() - verify_start > 2):
                    sent_verified = True
                    break

                # 5. وجود أيقونة الإرسال في آخر رسالة
                if _has_send_icon and (time.time() - verify_start > 2):
                    sent_verified = True
                    break

                # 6. إذا فرغ معظم الصندوق (أقل من 5 أحرف)
                if len(_current_input_text or "") < 5 and (time.time() - verify_start > 5):
                    sent_verified = True
                    break

                time.sleep(0.8)

            if sent_verified:
                self.update_daily_stats(True, is_invalid_number=False)
                print(f"[{time.strftime('%H:%M:%S')}] ✅ SEND_CONFIRMED: تم الإرسال بنجاح إلى: {clean_phone}")
                return True, "تم الإرسال بنجاح"
            else:
                self.update_daily_stats(False, is_invalid_number=False)
                print(f"[{time.strftime('%H:%M:%S')}] ❌ FAILED: فشل التحقق من الإرسال إلى: {clean_phone}")
                print(f"[{time.strftime('%H:%M:%S')}] 🔍 Debug: sent_ok={sent_ok}, _count_increased={_count_increased}, _send_btn_gone={_send_btn_gone}, _has_new_msgout={_has_new_msgout}, _has_send_icon={_has_send_icon}")
                return False, "فشل الإرسال (لم يتم إرسال الرسالة من المتصفح)"

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"[{time.strftime('%H:%M:%S')}] ❌ EXCEPTION in send_message: {e}")
            print(f"[{time.strftime('%H:%M:%S')}] Traceback: {tb}")
            short_err = str(e)[:120]
            self.last_error = f"send_message: {short_err}"
            self.update_daily_stats(False, is_invalid_number=False)
            return False, f"خطأ: {short_err}"

    def close(self):
        if self.driver:
            try: self.driver.quit()
            except: pass
            self.driver = None
        try:
            _lp = os.path.join(self.base_session_dir, "wa_start.lock")
            if os.path.exists(_lp):
                os.remove(_lp)
        except Exception:
            pass
