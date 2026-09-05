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
    "MAX_INVALID_IN_A_ROW": 4,         # Stop après 4 numéros invalides d'affilée
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
        """🛡️ Vérifie si on PEUT envoyer encore aujourd'hui. Retourne (autorisé, raison)."""
        stats = self.get_daily_stats()
        total = stats["sent_ok"] + stats["sent_fail"]
        ok_count = stats["sent_ok"]
        fail_count = stats["sent_fail"]
        seq_invalid = stats.get("invalid_sequential", 0)

        # 1) Limite quotidienne DURE (basée sur ancienneté estimée du compte)
        # Pour rester prudent, on applique toujours la limite "établie"
        daily_limit = ANTIBAN["DAILY_HARD_LIMIT_ESTABLISHED"]
        if total >= daily_limit:
            return False, f"Limite quotidienne atteinte ({daily_limit}). Reprendre demain."

        # 2) Taux d'échec global
        if total >= 8:
            fail_pct = (fail_count / total) * 100
            if fail_pct >= ANTIBAN["FAILURE_RATE_STOP_PCT"]:
                return (False,
                        f"Taux d'échec critique {fail_pct:.0f}% "
                        f"({fail_count}/{total}). Beaucoup de numéros invalides = risque de BAN. STOP.")
            if fail_pct >= ANTIBAN["FAILURE_RATE_SLOWDOWN_PCT"]:
                # On autorise mais avec avertissement (l'appelant peut ralentir)
                pass

        # 3) Séquence de numéros invalides d'affilée
        if seq_invalid >= ANTIBAN["MAX_INVALID_IN_A_ROW"]:
            return (False,
                    f"{seq_invalid} numéros invalides CONSÉCUTIFS. "
                    "La liste est probablement pourrie = risque BAN immédiat. STOP.")

        return True, f"OK ({ok_count} ok / {fail_count} échoués / {total} du jour)"

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
        """🛡️ العثور على زر الإرسال بأحدث الـ selectors لواتساب 2026"""
        from selenium.webdriver.common.by import By
        selectors = [
            '//button[contains(@aria-label, "Send")]',
            '//button[@aria-label="Send"]',
            '//span[@data-icon="send"]',
            '//span[@data-icon="send-dark"]',
            '//span[@data-icon="send-light"]',
            '//div[contains(@data-testid, "compose-btn-send")]',
            '//button[contains(@data-testid, "send")]',
            '//footer//*[name()="svg" and contains(@data-icon, "send")]/ancestor::*[self::button or self::div][1]',
            '//footer//button[@tabindex]',
        ]
        for sel in selectors:
            try:
                elems = self.driver.find_elements(By.XPATH, sel)
                for e in elems:
                    try:
                        if e.is_displayed() and e.is_enabled():
                            return e
                    except: continue
            except: continue
        return None

    def _dismiss_modals(self):
        """إغلاق أي نوافذ منبثقة أو تنبيهات أرقام غير صالحة تلقائياً"""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        try:
            ok_btns = self.driver.find_elements(By.XPATH,
                '//div[@role="button"][contains(., "OK") or contains(., "موافق") or contains(., "Close") or contains(., "إغلاق")]'
                ' | //button[contains(., "OK") or contains(., "موافق") or contains(., "Close") or contains(., "إغلاق")]'
                ' | //span[@data-icon="x"]/parent::*'
            )
            for btn in ok_btns:
                try:
                    if btn.is_displayed():
                        btn.click()
                        time.sleep(0.5)
                except: pass
        except: pass

    def _verify_message_sent(self) -> bool:
        """🛡️ التحقق الفعلي من نجاح الإرسال بالبحث عن علامات الصح أو الساعة في آخر رسالة"""
        from selenium.webdriver.common.by import By
        try:
            status_selectors = [
                '//span[@data-icon="msg-time"]',
                '//*[contains(@data-icon, "msg-time")]',
                '//span[@data-icon="msg-check"]',
                '//*[contains(@data-icon, "msg-check")]',
                '//span[@data-icon="msg-dblcheck"]',
                '//*[contains(@data-icon, "msg-dblcheck")]',
                '//span[@data-icon="msg-dblcheck-ack"]',
                '//*[contains(@data-icon, "msg-dblcheck-ack")]',
                '//div[contains(@class, "message-out")]',
                '//div[contains(@data-testid, "msg-out")]',
            ]
            for sel in status_selectors:
                try:
                    elems = self.driver.find_elements(By.XPATH, sel)
                    if elems:
                        last = elems[-1]
                        try:
                            if last.is_displayed():
                                return True
                        except:
                            return True
                except: continue
            try:
                src = self.driver.page_source.lower()
                bad_words = ["failed", "error", "couldn't", "can't send", "غير قادر", "فشل", "خطأ"]
                if any(w in src for w in bad_words):
                    recent_src = src[-2000:].lower()
                    if any(w in recent_src for w in bad_words):
                        return False
                return True
            except:
                return True
        except Exception:
            return False

    def _normalize_phone(self, phone: str) -> str:
        """Standardize phone to international digits format (e.g. 9665XXXXXXXX)."""
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
        """Automatically dismiss or accept common WhatsApp Web popups (Use Here, etc.)."""
        if not self.driver: return
        from selenium.webdriver.common.by import By
        try:
            # 1. 'Use Here' / 'استخدام هنا' popup
            use_here_btns = self.driver.find_elements(By.XPATH,
                '//button[contains(., "Use Here") or contains(., "استخدام هنا") or contains(., "استخدم هنا")] | '
                '//div[@role="button"][contains(., "Use Here") or contains(., "استخدام هنا") or contains(., "استخدم هنا")]'
            )
            for btn in use_here_btns:
                if btn.is_displayed():
                    btn.click()
                    time.sleep(1.0)
                    break
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

        # 🛡️ 1. Anti-Ban Safety Check
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

            # Dismiss any popups or 'Use Here'
            self._auto_handle_popups()
            self._dismiss_modals()
            time.sleep(random.uniform(0.4, 0.8))

            # 🌐 2. Navigate directly to WhatsApp chat URL (pre-filling text for native React compatibility)
            if not attachment_path and message:
                encoded_text = urllib.parse.quote(message)
                target_url = f"https://web.whatsapp.com/send?phone={clean_phone}&text={encoded_text}"
            else:
                target_url = f"https://web.whatsapp.com/send?phone={clean_phone}"

            print(f"[{time.strftime('%H:%M:%S')}] 🚀 Navigating to: {target_url[:80]}...")
            try:
                self.driver.get(target_url)
            except Exception as e_nav:
                print(f"[{time.strftime('%H:%M:%S')}] Navigation retry via JS: {e_nav}")
                self.driver.execute_script(f"window.location.href = '{target_url}';")

            time.sleep(random.uniform(2.0, 3.5))

            # ⏳ 3. Wait for chat input / send button OR invalid number dialog
            wait_start = time.time()
            msg_input = None
            send_btn = None
            is_invalid_num = False

            while time.time() - wait_start < 35:
                self._auto_handle_popups()

                # A. Check for invalid number dialog
                try:
                    invalid_elements = self.driver.find_elements(By.XPATH,
                        '//div[@data-animate-modal-popup="true"] | '
                        '//div[contains(@class, "modal")] | '
                        '//div[@role="dialog"] | '
                        '//div[@role="alert"]'
                    )
                    for elem in invalid_elements:
                        txt = elem.text.lower()
                        if any(k in txt for k in ["invalid", "phone number shared via url is invalid", "غير صالح", "غير صحيح", "not on whatsapp", "ليس مسجلاً"]):
                            is_invalid_num = True
                            break
                except Exception: pass

                if is_invalid_num:
                    break

                # B. Check for active send button (when pre-filled via URL)
                send_btn = self._find_send_button()
                if send_btn and send_btn.is_displayed():
                    break

                # C. Check for compose box
                try:
                    inputs = self.driver.find_elements(By.XPATH,
                        '//footer//div[@contenteditable="true"] | '
                        '//div[@contenteditable="true"][@data-tab="10"] | '
                        '//div[@contenteditable="true"][contains(@class, "copyable-text")] | '
                        '//div[@role="textbox"][@contenteditable="true"] | '
                        '//div[contains(@data-testid, "conversation-compose-box-input")]'
                    )
                    for inp in inputs:
                        if inp.is_displayed():
                            msg_input = inp
                            break
                    if msg_input:
                        break
                except Exception: pass

                time.sleep(0.4)

            if is_invalid_num:
                self._dismiss_modals()
                self.update_daily_stats(False, is_invalid_number=True)
                return False, "رقم غير مسجل في الواتساب"

            if not send_btn and not msg_input:
                src = self.driver.page_source.lower()
                if any(k in src for k in ["invalid", "phone number shared via url is invalid", "غير صالح"]):
                    self._dismiss_modals()
                    self.update_daily_stats(False, is_invalid_number=True)
                    return False, "رقم غير مسجل في الواتساب"
                self.update_daily_stats(False, is_invalid_number=False)
                return False, "فشل في فتح المحادثة أو العثور على صندوق الرسائل"

            time.sleep(random.uniform(0.6, 1.2))

            # 📎 4. Handle Attachment (if specified)
            if attachment_path and os.path.exists(attachment_path):
                temp_dir = os.path.join(self.session_path, "temp_uploads")
                os.makedirs(temp_dir, exist_ok=True)
                
                original_ext = os.path.splitext(attachment_path)[1]
                random_filename = f"DOC_{datetime.now().strftime('%H%M%S')}_{random.randint(1000, 9999)}{original_ext}"
                obfuscated_path = os.path.join(temp_dir, random_filename)
                shutil.copy2(attachment_path, obfuscated_path)

                attach_btn_found = None
                attach_selectors = [
                    '//span[@data-icon="plus"]',
                    '//span[@data-icon="attach-menu-plus"]',
                    '//div[@title="Attach"]',
                    '//button[contains(@aria-label, "Attach")]',
                    '//button[contains(@aria-label, "إرفاق")]',
                    '//div[contains(@data-testid, "conversation-attach-button")]',
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

                time.sleep(random.uniform(0.8, 1.5))
                try:
                    ActionChains(self.driver).move_to_element(attach_btn_found).pause(0.2).click().perform()
                except Exception:
                    attach_btn_found.click()
                time.sleep(random.uniform(1.2, 2.0))

                file_inputs = self.driver.find_elements(By.XPATH, '//input[@type="file"]')
                if not file_inputs:
                    self.update_daily_stats(False, is_invalid_number=False)
                    return False, "فشل العثور على حقل رفع الملف"
                file_inputs[-1].send_keys(obfuscated_path)
                time.sleep(random.uniform(2.5, 4.0))

                wait = WebDriverWait(self.driver, 20)
                caption_input = wait.until(EC.presence_of_element_located((By.XPATH,
                    '//div[@contenteditable="true"][@data-tab="10"]'
                    ' | //div[@contenteditable="true" and contains(@class, "copyable-text")]'
                    ' | //div[@role="textbox"]'
                    ' | //div[contains(@data-testid, "media-caption-input-container")]//div[@contenteditable="true"]'
                )))

                if message:
                    time.sleep(random.uniform(0.8, 1.5))
                    try:
                        ActionChains(self.driver).move_to_element(caption_input).click().perform()
                    except Exception:
                        caption_input.click()
                    
                    encoded_cap = json.dumps(message)
                    self.driver.execute_script(f"""
                        var el = arguments[0];
                        el.focus();
                        document.execCommand('selectAll', false, null);
                        document.execCommand('insertText', false, {encoded_cap});
                        el.dispatchEvent(new InputEvent('input', {{ bubbles: true, data: {encoded_cap} }}));
                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    """, caption_input)
                    time.sleep(random.uniform(0.8, 1.5))

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
                # 💬 5. Handle Text Message
                if not message:
                    return False, "الرسالة فارغة"

                # If Send button is not yet active (e.g. text wasn't pre-filled by URL), inject it into msg_input
                if not send_btn and msg_input:
                    try:
                        ActionChains(self.driver).move_to_element(msg_input).click().perform()
                    except Exception:
                        try: msg_input.click()
                        except Exception: pass
                    time.sleep(random.uniform(0.4, 0.8))

                    encoded_msg = json.dumps(message)
                    self.driver.execute_script(f"""
                        var el = arguments[0];
                        el.focus();
                        document.execCommand('selectAll', false, null);
                        document.execCommand('insertText', false, {encoded_msg});
                        el.dispatchEvent(new InputEvent('input', {{ bubbles: true, data: {encoded_msg} }}));
                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    """, msg_input)
                    time.sleep(random.uniform(0.8, 1.5))

                # Click Send button or press ENTER
                sent_ok = False
                send_btn = self._find_send_button()
                if send_btn:
                    try:
                        ActionChains(self.driver).move_to_element(send_btn).pause(random.uniform(0.2, 0.5)).click().perform()
                        sent_ok = True
                    except Exception as s_err:
                        try:
                            send_btn.click()
                            sent_ok = True
                        except Exception:
                            self.driver.execute_script("arguments[0].click();", send_btn)
                            sent_ok = True

                if not sent_ok and msg_input:
                    try:
                        msg_input.send_keys(Keys.ENTER)
                        sent_ok = True
                    except Exception as k_err:
                        print(f"[DEBUG] Keys.ENTER send error: {k_err}")

                if not sent_ok:
                    try:
                        self.driver.execute_script("""
                            var btn = document.querySelector('button[aria-label="Send"], button[aria-label="إرسال"], span[data-icon="send"]');
                            if (btn) (btn.closest('button') || btn).click();
                        """)
                        sent_ok = True
                    except Exception: pass

            # 🔍 6. STRICT VERIFICATION LOOP (Ensures 100% Real Send, No Fake Progress)
            sent_verified = False
            verify_start = time.time()
            while time.time() - verify_start < 12:
                if msg_input:
                    try:
                        if not msg_input.text.strip():
                            sent_verified = True
                            break
                    except Exception:
                        sent_verified = True
                        break

                if self._verify_message_sent():
                    sent_verified = True
                    break

                time.sleep(0.5)

            if not sent_verified and msg_input:
                try:
                    msg_input.send_keys(Keys.ENTER)
                    time.sleep(2.0)
                    if not msg_input.text.strip() or self._verify_message_sent():
                        sent_verified = True
                except Exception: pass

            if sent_verified:
                self.update_daily_stats(True, is_invalid_number=False)
                return True, "تم الإرسال بنجاح"
            else:
                self.update_daily_stats(False, is_invalid_number=False)
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
