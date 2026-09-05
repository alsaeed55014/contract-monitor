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

# #region debug-point helper: wa-fake-send-bug logger (std lib only, env file based)
def __dbg_log(hypothesis_id, msg, data=None, run_id="pre-fix", location=""):
    """تسجيل أحداث التصحيح لسيرفر wa-fake-send-bug بدون أثر على الأداء."""
    try:
        import urllib.request
        _env_p = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".dbg", "wa-fake-send-bug.env")
        _u, _s = "http://127.0.0.1:7777/event", "wa-fake-send-bug"
        try:
            with open(_env_p, "r", encoding="utf-8") as __f:
                __c = __f.read()
            for __l in __c.split("\n"):
                if __l.startswith("DEBUG_SERVER_URL="): _u = __l.split("=",1)[1].strip()
                if __l.startswith("DEBUG_SESSION_ID="): _s = __l.split("=",1)[1].strip()
        except Exception:
            pass
        _payload = json.dumps({
            "sessionId": _s, "runId": run_id, "hypothesisId": hypothesis_id,
            "location": location or f"whatsapp_service.py",
            "msg": f"[DEBUG] {msg}",
            "data": data or {}, "ts": int(time.time()*1000)
        }).encode("utf-8")
        _req = urllib.request.Request(_u, data=_payload, headers={"Content-Type":"application/json"})
        try: urllib.request.urlopen(_req, timeout=1.5).read()
        except Exception: pass
    except Exception:
        pass
# #endregion

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
        """🛡️ العثور على زر الإرسال بأحدث الـ selectors لواتساب 2026 (نسخة 2.24.x+)"""
        from selenium.webdriver.common.by import By
        selectors = [
            # === الـ selectors الرسمية لواتساب ويب 2024-2026 ===
            '//button[contains(@data-testid, "compose-btn-send")]',
            '//div[contains(@data-testid, "compose-btn-send")]',
            # Span داخل زر الإرسال
            '//span[@data-icon="send"]/parent::button',
            '//span[@data-icon="send"]/ancestor::button',
            '//span[@data-icon="send"]/ancestor::div[contains(@role,"button")]',
            '//span[@data-icon="send"]/parent::*',
            # بالعربية
            '//button[@aria-label="إرسال"]',
            '//button[@aria-label="ارسل"]',
            # بالإنجليزية (حسابات EN)
            '//button[@aria-label="Send"]',
            # SVG بأيقونة الإرسال
            '//*[name()="svg" and contains(@data-icon, "send")]/ancestor::*[self::button or self::div][1]',
            # fallback: أي زر داخل footer له tabindex
            '//footer//button[@tabindex]',
            # fallback: أي عنصر role=button في footer له بادئة send
            '//footer//*[@role="button"][contains(translate(@aria-label,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz"),"send") or contains(translate(@aria-label,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz"),"ارسل") or contains(translate(@aria-label,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz"),"إرسال")]',
        ]
        for sel in selectors:
            try:
                elems = self.driver.find_elements(By.XPATH, sel)
                for e in elems:
                    try:
                        if e.is_displayed() and e.is_enabled():
                            # تحقق إضافي: العنصر له حجم حقيقي
                            size = e.size
                            if size.get("width", 0) < 5 or size.get("height", 0) < 5:
                                continue
                            return e
                    except: continue
            except: continue
        return None

    def _dismiss_modals(self):
        """إغلاق أي نوافذ منبثقة أو تنبيهات أرقام غير صالحة تلقائياً (واتساب 2026)"""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        try:
            # 1. الأزرار النصية (OK / موافق / Close / إغلاق / No / لا)
            ok_btn_selectors = [
                '//div[@role="button"][contains(normalize-space(.), "OK") or contains(normalize-space(.), "موافق") or contains(normalize-space(.), "Close") or contains(normalize-space(.), "إغلاق") or contains(normalize-space(.), "حسناً") or contains(normalize-space(.), "حسنا") or contains(normalize-space(.), "No") or contains(normalize-space(.), "لا")]',
                '//button[contains(normalize-space(.), "OK") or contains(normalize-space(.), "موافق") or contains(normalize-space(.), "Close") or contains(normalize-space(.), "إغلاق") or contains(normalize-space(.), "حسناً") or contains(normalize-space(.), "حسنا") or contains(normalize-space(.), "No") or contains(normalize-space(.), "لا")]',
                # 2026: الـ data-testid الجديد
                '//*[contains(@data-testid, "popup-modal")]//button',
                '//*[contains(@data-testid, "dialog-close")]',
                # أيقونة X
                '//span[@data-icon="x"]/parent::*',
                '//span[@data-icon="X"]/parent::*',
                '//*[@aria-label="Close"]',
                '//*[@aria-label="إغلاق"]',
            ]
            for sel in ok_btn_selectors:
                ok_btns = self.driver.find_elements(By.XPATH, sel)
                for btn in ok_btns:
                    try:
                        if btn.is_displayed():
                            try:
                                btn.click()
                            except:
                                try:
                                    self.driver.execute_script("arguments[0].click();", btn)
                                except:
                                    pass
                            time.sleep(0.5)
                    except: pass
            # 2. الضغط على ESC كطريقة احتياطية لإغلاق المودالات
            try:
                body = self.driver.find_element(By.TAG_NAME, "body")
                body.send_keys(Keys.ESCAPE)
                time.sleep(0.3)
            except:
                pass
        except: pass

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
                # Pop-up عام جلسة مفتوحة في مكان آخر
                '//*[contains(@data-testid, "content-host")]//button[1]',
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

        # #region debug-point H4+H5: pre-send state capture
        try:
            _dbg_pre = {"phone": phone, "msg_len": len(message or ""), "has_attachment": bool(attachment_path and os.path.exists(attachment_path))}
            try:
                _dbg_pre["driver_url"] = (self.driver.current_url[:120] if self.driver and self.driver.current_url else "NO_URL")
                _dbg_pre["driver_title"] = (self.driver.title[:80] if self.driver else "NO_DRIVER")
            except Exception as _e:
                _dbg_pre["driver_url_err"] = str(_e)[:80]
            try:
                _qr = self.driver.find_elements(By.XPATH, '//canvas | //*[@data-ref] | //*[contains(@data-testid, "qr")] | //*[contains(@aria-label, "QR")] | //*[contains(@aria-label, "Scan")]') if self.driver else []
                _dbg_pre["qr_elements_found"] = len(_qr)
                _main = self.driver.find_elements(By.XPATH, '//*[@id="main"] | //div[@id="main"]') if self.driver else []
                _dbg_pre["main_div_found"] = len(_main)
                _side = self.driver.find_elements(By.XPATH, '//*[@id="side"]') if self.driver else []
                _dbg_pre["side_panel_found"] = len(_side)
                _out_msgs = self.driver.find_elements(By.XPATH, '//*[contains(@data-testid, "msg-out")] | //div[contains(@class, "message-out")]') if self.driver else []
                _dbg_pre["existing_msgout_count_initial"] = len(_out_msgs)
            except Exception as _e:
                _dbg_pre["dom_check_err"] = str(_e)[:100]
            try:
                _dbg_pre["wa_status"] = self.get_status()
            except Exception as _e:
                _dbg_pre["status_err"] = str(_e)[:80]
            __dbg_log("H5", "pre-send state (login check + url + qr check + initial msg-out)", _dbg_pre, location="send_message:start (H4+H5)")
        except Exception:
            pass
        # #endregion
        
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

            # 🛡️ 2026: زيادة وقت التحميل الأولي لـ React hydration (مهم جداً للنسخ الجديدة)
            time.sleep(random.uniform(4.0, 7.0))

            # #region debug-point H4: post-navigation state (did we really reach the chat?)
            try:
                _dbg_postnav = {"clean_phone": clean_phone, "target_url": target_url[:120]}
                try:
                    _dbg_postnav["actual_url"] = (self.driver.current_url[:150] if self.driver else "NO_DRIVER")
                    _dbg_postnav["title"] = (self.driver.title[:80] if self.driver else "")
                    _dbg_postnav["match_send"] = "send?phone" in (_dbg_postnav.get("actual_url","").lower())
                except Exception as _e:
                    _dbg_postnav["nav_url_err"] = str(_e)[:80]
                try:
                    _main = self.driver.find_elements(By.XPATH, '//*[@id="main"] | //div[@id="main"]') if self.driver else []
                    _footer = self.driver.find_elements(By.XPATH, '//footer | //*[@role="region"][contains(@data-testid,"conversation-panel")]') if self.driver else []
                    _qr2 = self.driver.find_elements(By.XPATH, '//canvas | //*[@data-ref] | //*[contains(@data-testid, "qr")]') if self.driver else []
                    _dbg_postnav["main_count"] = len(_main)
                    _dbg_postnav["footer_count"] = len(_footer)
                    _dbg_postnav["qr_count_postnav"] = len(_qr2)
                except Exception as _e:
                    _dbg_postnav["postnav_dom_err"] = str(_e)[:80]
                __dbg_log("H4", "post navigation: real URL match chat URL? + main/footer present?", _dbg_postnav, location="send_message:post-navigate (H4)")
            except Exception:
                pass
            # #endregion

            # ⏳ 3. Wait for chat input / send button OR invalid number dialog
            #    — 2026: زيادة المهلة إلى 60 ثانية بسبب بطء بعض أجهزة واتساب الجديدة
            wait_start = time.time()
            msg_input = None
            send_btn = None
            is_invalid_num = False

            while time.time() - wait_start < 60:
                self._auto_handle_popups()
                self._dismiss_modals()

                # A. Check for invalid number dialog (أحدث التحكم 2026)
                try:
                    invalid_selectors = [
                        '//div[@data-animate-modal-popup="true"]',
                        '//div[contains(@class, "modal")]',
                        '//div[@role="dialog"]',
                        '//div[@role="alert"]',
                        '//*[contains(@data-testid, "popup")]',
                        '//*[contains(@data-testid, "dialog")]',
                    ]
                    bad_keywords = [
                        "invalid", "phone number shared via url is invalid",
                        "غير صالح", "غير صحيح", "not on whatsapp", "ليس مسجلاً",
                        "number is invalid", "this phone number", "check the number",
                        "رقم هاتف", "رقم غير صالح", "رقم الهاتف غير مسجل",
                        "shared url is invalid",
                    ]
                    for sel in invalid_selectors:
                        try:
                            invalid_elements = self.driver.find_elements(By.XPATH, sel)
                            for elem in invalid_elements:
                                try:
                                    txt = elem.text.lower()
                                    if any(k in txt for k in bad_keywords):
                                        is_invalid_num = True
                                        break
                                except:
                                    pass
                        except: pass
                    if not is_invalid_num:
                        # فحص page_source مباشرة (backup plan)
                        src_lower = self.driver.page_source.lower()
                        if any(k in src_lower for k in bad_keywords):
                            is_invalid_num = True
                except Exception:
                    pass

                if is_invalid_num:
                    break

                # B. Check for active send button (when pre-filled via URL)
                send_btn = self._find_send_button()
                if send_btn and send_btn.is_displayed():
                    break

                # C. Check for compose box — أحدث الـ selectors لـ 2024-2026
                try:
                    input_selectors = [
                        # الأصلي الرسمي لواتساب الجديد
                        '//*[@data-testid="conversation-compose-box-input"]',
                        # نسخة div contenteditable عادية
                        '//footer//div[@contenteditable="true"][@data-tab="10"]',
                        # fallback عام للنسخ القديمة
                        '//footer//div[@contenteditable="true"][contains(@class, "copyable-text")]',
                        '//div[@role="textbox"][@contenteditable="true"]',
                        # fallback بحد أوسع
                        '//footer//*[@contenteditable="true"]',
                        # من خلال الهامش الأيمن للـ compose
                        '//div[contains(@data-testid,"conversation")]//div[@contenteditable="true"]',
                    ]
                    found = False
                    for sel in input_selectors:
                        try:
                            inputs = self.driver.find_elements(By.XPATH, sel)
                            for inp in inputs:
                                try:
                                    if inp.is_displayed():
                                        size = inp.size
                                        if size.get("width", 0) > 20 or size.get("height", 0) > 10:
                                            msg_input = inp
                                            found = True
                                            break
                                except:
                                    pass
                            if found:
                                break
                        except Exception:
                            continue
                    if found:
                        break
                except Exception: pass

                time.sleep(0.5)

            # #region debug-point H1+H2+H3: state after wait, BEFORE send click
            try:
                _dbg_presend = {"is_invalid_num": is_invalid_num, "wait_secs_elapsed": round(time.time()-wait_start, 1)}
                # H1: COUNT OF EXISTING msg-out ELEMENTS BEFORE SENDING (the gold baseline for H1)
                try:
                    _out_before = self.driver.find_elements(By.XPATH, '//div[contains(@data-testid, "msg-out")] | //div[contains(@class, "message-out")] | //div[contains(@data-testid, "message-out")]') if self.driver else []
                    _dbg_presend["msgout_count_before_send"] = len(_out_before)
                    # Also capture text contents of LAST 2 msg-out items (if any) to compare later
                    try:
                        _dbg_presend["last_msgout_texts_pre"] = [((elem.text[:100] if elem.text else "") + f"|visible={elem.is_displayed()}") for elem in _out_before[-2:]]
                    except Exception:
                        pass
                except Exception as _e:
                    _dbg_presend["msgout_count_err"] = str(_e)[:100]
                # H3: send_btn details
                try:
                    if send_btn is not None:
                        _dbg_presend["send_btn_found"] = True
                        _s = send_btn
                        try:
                            _dbg_presend["send_btn_tag"] = _s.tag_name
                            _dbg_presend["send_btn_displayed"] = _s.is_displayed()
                            _dbg_presend["send_btn_enabled"] = _s.is_enabled()
                            _sz = _s.size
                            _dbg_presend["send_btn_size_w"] = _sz.get("width", -1)
                            _dbg_presend["send_btn_size_h"] = _sz.get("height", -1)
                            for _a in ["aria-label","data-testid","data-icon","class","title","role"]:
                                try:
                                    _v = _s.get_attribute(_a)
                                    if _v: _dbg_presend[f"send_btn_{_a.replace('-','_')}"] = str(_v)[:80]
                                except Exception: pass
                        except Exception as _es:
                            _dbg_presend["send_btn_props_err"] = str(_es)[:100]
                    else:
                        _dbg_presend["send_btn_found"] = False
                except Exception as _e:
                    _dbg_presend["send_btn_check_err"] = str(_e)[:100]
                # H2: msg_input details (is it really there? does it have actual text content from URL prefill?)
                try:
                    if msg_input is not None:
                        _dbg_presend["msg_input_found"] = True
                        _mi = msg_input
                        try:
                            _mi_sz = _mi.size
                            _dbg_presend["msg_input_size_w"] = _mi_sz.get("width",-1)
                            _dbg_presend["msg_input_size_h"] = _mi_sz.get("height",-1)
                            _dbg_presend["msg_input_displayed"] = _mi.is_displayed()
                            _dbg_presend["msg_input_enabled"] = _mi.is_enabled()
                            # CRITICAL: capture actual DOM text of the input box (is the pre-filled URL text really visible in it?)
                            try:
                                _input_text = _mi.text if hasattr(_mi, "text") else ""
                                _dbg_presend["msg_input_actual_text_len"] = len(_input_text or "")
                                _dbg_presend["msg_input_actual_text_preview"] = str(_input_text or "")[:150]
                                # Alternative: check innerText via JS
                                try:
                                    _js_text = self.driver.execute_script("return (arguments[0] && (arguments[0].innerText || arguments[0].textContent || '')).toString();", _mi)
                                    _dbg_presend["msg_input_js_innertext_len"] = len(_js_text or "")
                                    _dbg_presend["msg_input_js_innertext_preview"] = str(_js_text or "")[:150]
                                except Exception:
                                    pass
                            except Exception as _ei:
                                _dbg_presend["msg_input_text_err"] = str(_ei)[:100]
                            # Capture attributes for class name match for search field vs chat field
                            for _a in ["data-tab","data-testid","role","contenteditable","class","aria-label","title","placeholder"]:
                                try:
                                    _v = _mi.get_attribute(_a)
                                    if _v: _dbg_presend[f"msg_input_{_a.replace('-','_')}"] = str(_v)[:120]
                                except Exception: pass
                        except Exception as _em:
                            _dbg_presend["msg_input_props_err"] = str(_em)[:100]
                        # Also check: is this search box or real chat box? search box has data-tab="3"
                        try:
                            _dt = _mi.get_attribute("data-tab") or ""
                            if _dt == "3":
                                _dbg_presend["msg_input_DANGER_search_box"] = True  # DANGER: This is SEARCH not CHAT!
                            elif _dt == "10" or (_mi.get_attribute("data-testid") or "").find("compose") > -1:
                                _dbg_presend["msg_input_OK_chat_box"] = True  # OK: real chat compose
                        except Exception:
                            pass
                    else:
                        _dbg_presend["msg_input_found"] = False
                except Exception as _e:
                    _dbg_presend["msg_input_check_err"] = str(_e)[:100]
                __dbg_log("H2", "after wait loop: msg-out baseline count + send_btn validity + msg_input real content (H1+H2+H3)", _dbg_presend, location="send_message:after-wait (H1+H2+H3)")
            except Exception:
                pass
            # #endregion

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

            # ╔══════════════════════════════════════════════════════════════╗
            # ║ 🛡️ STRICT SEND BASELINE (لإيقاف النتائج الوهمية نهائياً)      ║
            # ╠══════════════════════════════════════════════════════════════╣
            # ║ 1. عدّ كل رسائل صادرة (msg-out) الموجودة قبل محاولة الإرسال  ║
            # ║ 2. احفظ نص آخر رسالة صادرة حتى نقارنها بعد الإرسال           ║
            # ║ 3. احفظ مقطع النص المتوقع للبحث عنه بعد الإرسال              ║
            # ╚══════════════════════════════════════════════════════════════╝
            from selenium.webdriver.common.by import By as _By
            _msgout_count_baseline = -1
            _last_msgout_text_baseline = ""
            _expected_msg_fragment = ""
            try:
                _baseline_xpath = '//div[contains(@data-testid, "msg-out")] | //div[contains(@class, "message-out")] | //div[contains(@data-testid, "message-out")]'
                _prev = self.driver.find_elements(_By.XPATH, _baseline_xpath)
                _msgout_count_baseline = len(_prev)
                if _prev:
                    try:
                        _last_e = _prev[-1]
                        _t = self.driver.execute_script(
                            "return (arguments[0].innerText || arguments[0].textContent || '').toString().replace(/\\s+/g, ' ').trim();",
                            _last_e
                        )
                        _last_msgout_text_baseline = (_t or "").strip()
                    except Exception:
                        _last_msgout_text_baseline = getattr(_prev[-1], "text", "").strip()
            except Exception:
                _msgout_count_baseline = -1
            if message:
                # إزالة الرموز المخفية من المقطع المقارن لتفادي الفشل بسبب الـ obfuscation
                _norm = re.sub(r'[\u200B-\u200F\u202A-\u202E\u00AD\u2060\uFEFF\s]', '', message).lower()
                if len(_norm) > 55:
                    _norm = _norm[:55]
                _expected_msg_fragment = _norm
            # ══════════════════════════════════════════════════════════════

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
                    # 2026: أحدث الأيقونات والإرفاقات
                    '//*[contains(@data-testid, "conversation-attach-button")]',
                    '//div[contains(@data-testid, "conversation-attach-button")]',
                    # أيقونة +/attach-menu-plus (الأصلية)
                    '//span[@data-icon="attach-menu-plus"]/parent::*',
                    '//span[@data-icon="attach-menu-plus"]',
                    '//span[@data-icon="plus"]/parent::*',
                    '//span[@data-icon="plus"]',
                    # بالعربية والإنجليزية
                    '//button[contains(@aria-label, "Attach")]',
                    '//button[contains(@aria-label, "إرفاق")]',
                    '//*[@role="button"][contains(translate(@aria-label,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz"),"attach") or contains(translate(@aria-label,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz"),"إرفاق")]',
                    # عنوان الشريط
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
                        # 🛡️ 2026: التأكيد أولاً على Focus فعلي للعنصر قبل أي إجراء
                        self.driver.execute_script("""
                            var el = arguments[0];
                            el.scrollIntoView({behavior: 'smooth', block: 'center'});
                            el.focus();
                            el.setSelectionRange(el.innerText.length, el.innerText.length);
                        """, msg_input)
                    except:
                        pass
                    time.sleep(random.uniform(0.5, 1.0))

                    try:
                        ActionChains(self.driver).move_to_element(msg_input).pause(0.2).click().perform()
                    except Exception:
                        try: msg_input.click()
                        except Exception: pass
                    time.sleep(random.uniform(0.6, 1.0))

                    # 🛡️ 2026: حقن النص بطريقة تشغل أحداث React بشكل كامل
                    # الطريقة 1: insertText مع أحداث input كاملة
                    try:
                        encoded_msg = json.dumps(message)
                        self.driver.execute_script(f"""
                            (function() {{
                                var el = arguments[0];
                                var text = {encoded_msg};
                                el.focus();
                                document.execCommand('selectAll', false, null);
                                document.execCommand('insertText', false, text);
                                // أحداث متعددة لتفعيل React state
                                el.dispatchEvent(new InputEvent('beforeinput', {{ bubbles: true, cancelable: true, data: text, inputType: 'insertText' }}));
                                el.dispatchEvent(new InputEvent('input', {{ bubbles: true, cancelable: true, data: text, inputType: 'insertText' }}));
                                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                el.dispatchEvent(new KeyboardEvent('keydown', {{ bubbles: true, key: 'Enter' }}));
                            }}).call(null, arguments[0]);
                        """, msg_input)
                    except Exception as js_err:
                        print(f"[DEBUG] JS inject error: {js_err}")
                        # الطريقة الاحتياطية: محاكاة الكتابة البشرية
                        try:
                            self._type_human_like(msg_input, message)
                        except Exception as ty_err:
                            print(f"[DEBUG] _type_human_like error: {ty_err}")
                    time.sleep(random.uniform(1.0, 1.8))

                    # 🛡️ 2026: إعادة محاولة تفعيل زر الإرسال بعد حقن النص
                    time.sleep(random.uniform(0.5, 1.0))
                    send_btn = self._find_send_button()
                    if not send_btn:
                        # زيادة فترة الانتظار قليلاً لظهور الزر
                        for _retry in range(3):
                            time.sleep(1.0)
                            send_btn = self._find_send_button()
                            if send_btn:
                                break

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
                            try:
                                self.driver.execute_script("arguments[0].click();", send_btn)
                                sent_ok = True
                            except Exception:
                                pass

                if not sent_ok and msg_input:
                    try:
                        # التركيز على صندوق الكتابة ثم ENTER
                        try:
                            msg_input.click()
                            time.sleep(0.3)
                        except:
                            pass
                        msg_input.send_keys(Keys.ENTER)
                        sent_ok = True
                    except Exception as k_err:
                        print(f"[DEBUG] Keys.ENTER send error: {k_err}")

                if not sent_ok:
                    try:
                        # 2026: أحدث query للزر من داخل الـ JS
                        self.driver.execute_script("""
                            var btn = null;
                            var all = document.querySelectorAll('[data-testid*="compose-btn-send"], [data-icon="send"], button[aria-label="Send"], button[aria-label="إرسال"], button[aria-label="ارسل"]');
                            for (var b of all) {
                                var rect = b.getBoundingClientRect();
                                if (rect.width > 0 && rect.height > 0) { btn = b; break; }
                            }
                            if (!btn) {
                                var ancestor = document.querySelector('footer span[data-icon="send"]');
                                if (ancestor) btn = ancestor.closest('button, div[role="button"]');
                            }
                            if (btn) {
                                var rect0 = btn.getBoundingClientRect();
                                function clickAt(el, x, y) {
                                    el.dispatchEvent(new MouseEvent('pointerdown', {bubbles:true,cancelable:true,clientX:x,clientY:y,view:window,button:0}));
                                    el.dispatchEvent(new MouseEvent('pointerup',   {bubbles:true,cancelable:true,clientX:x,clientY:y,view:window,button:0}));
                                    el.dispatchEvent(new MouseEvent('click',      {bubbles:true,cancelable:true,clientX:x,clientY:y,view:window,button:0}));
                                }
                                clickAt(btn, rect0.left+rect0.width/2, rect0.top+rect0.height/2);
                            }
                        """)
                        sent_ok = True
                    except Exception:
                        pass

            # #region debug-point H1+H3: post-click, PRE-verification. Count msg-out and compare with baseline
            try:
                _dbg_postclick = {"sent_ok_click_flag": sent_ok, "clean_phone": clean_phone, "message_expected_len": len(message or "")}
                try:
                    _out_after = self.driver.find_elements(By.XPATH, '//div[contains(@data-testid, "msg-out")] | //div[contains(@class, "message-out")] | //div[contains(@data-testid, "message-out")]') if self.driver else []
                    _dbg_postclick["msgout_count_after_click"] = len(_out_after)
                    # last 3 message texts
                    try:
                        _dbg_postclick["last_msgout_texts_postclick"] = [((elem.text[:120] if elem.text else "") + f"|display={elem.is_displayed()}") for elem in _out_after[-3:]]
                    except Exception:
                        pass
                except Exception as _e:
                    _dbg_postclick["msgout_postclick_count_err"] = str(_e)[:80]
                # check msg_input now empty or not
                try:
                    if msg_input is not None:
                        _it = msg_input.text if hasattr(msg_input, "text") else ""
                        _dbg_postclick["msg_input_text_after_click_len"] = len(_it or "")
                        _dbg_postclick["msg_input_text_after_click_preview"] = str(_it or "")[:100]
                        try:
                            _it2 = self.driver.execute_script("return (arguments[0] && (arguments[0].innerText || arguments[0].textContent || '')).toString();", msg_input)
                            _dbg_postclick["msg_input_js_text_after_click_len"] = len(_it2 or "")
                            _dbg_postclick["msg_input_js_text_after_click_preview"] = str(_it2 or "")[:100]
                        except Exception:
                            pass
                except Exception:
                    pass
                __dbg_log("H1", "IMMEDIATELY AFTER SEND CLICK: new msgout count + input empty check (H1 H3)", _dbg_postclick, location="send_message:post-click pre-verify (H1+H3)")
            except Exception:
                pass
            # #endregion

            # 🔍 6. STRICT VERIFICATION LOOP (محسوب بدقة BASELINE COUNT + TEXT MATCH)
            sent_verified = False
            verify_start = time.time()
            VERIFY_TIMEOUT = 30  # صارمة: 30 ثانية كحد أقصى مع فحوصات حقيقية
            _input_was_empty_js = False
            _msgout_increased = False

            while time.time() - verify_start < VERIFY_TIMEOUT:
                # ───────── A. فحص فارغية صندوق الكتابة بواسطة JS (موثوق) ─────────
                if msg_input is not None:
                    try:
                        _curr_input_text_js = self.driver.execute_script("""
                            (function(el){
                                if (!el) return '';
                                var t = (el.innerText || el.textContent || '').toString();
                                t = t.replace(/[\\u200B-\\u200F\\u202A-\\u202E\\u00AD\\u2060\\uFEFF]/g, '');
                                return t.replace(/\\s+/g, ' ').trim();
                            })(arguments[0]);
                        """, msg_input)
                        _input_was_empty_js = (len(_curr_input_text_js or "") == 0)
                    except Exception:
                        _input_was_empty_js = False
                else:
                    _input_was_empty_js = False

                # ───────── B. فحص الزيادة في عدد الرسائل الصادرة عن BASELINE ─────────
                try:
                    _check_xpath = '//div[contains(@data-testid, "msg-out")] | //div[contains(@class, "message-out")] | //div[contains(@data-testid, "message-out")]'
                    _now_count = self.driver.find_elements(By.XPATH, _check_xpath)
                    _msgout_increased = (_msgout_count_baseline >= 0 and len(_now_count) > _msgout_count_baseline)
                except Exception:
                    _msgout_increased = False

                # ───────── C. استدعاء دالة التحقق الصارمة مع كل المعاملات ─────────
                _strict_ok = self._verify_message_sent(
                    baseline_msgout_count=_msgout_count_baseline,
                    prev_last_msgout_text=_last_msgout_text_baseline,
                    expected_msg_fragment=_expected_msg_fragment,
                    is_attachment=(attachment_path and os.path.exists(attachment_path)),
                )
                if _strict_ok:
                    sent_verified = True
                    break

                # شروط ترقية إضافية فقط في حالة اجتماع 2 شرطين معاً (وليس أحدهما فقط!)
                if _msgout_increased and _input_was_empty_js:
                    sent_verified = True
                    break
                if _msgout_increased and message and len(_expected_msg_fragment) < 4:
                    # رسالة قصيرة جداً فشل المطابقة النصية لكن العدد زاد + الرسالة قصيرة
                    sent_verified = True
                    break
                if _input_was_empty_js and (attachment_path and os.path.exists(attachment_path)):
                    # مرفق: فارغ الحقل + العدد زاد (تحقق C بالفعل سيعيد True غالباً)
                    if _msgout_increased or (attachment_path and self._verify_message_sent(
                        baseline_msgout_count=_msgout_count_baseline,
                        prev_last_msgout_text=_last_msgout_text_baseline,
                        expected_msg_fragment="", is_attachment=True)):
                        sent_verified = True
                        break

                time.sleep(0.7)

            # 🛡️ محاولة أخيرة: ENTER + إعادة التحقق مرة واحدة فقط بعد 4 ثوانٍ
            if not sent_verified and msg_input is not None:
                try:
                    time.sleep(1.0)
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'}); arguments[0].focus();", msg_input)
                        time.sleep(0.3)
                        msg_input.click()
                        time.sleep(0.3)
                    except Exception:
                        pass
                    try:
                        msg_input.send_keys(Keys.ENTER)
                    except Exception:
                        # fallback JS Enter
                        self.driver.execute_script("""
                            var el = arguments[0]; if (el && el.dispatchEvent) {
                                el.dispatchEvent(new KeyboardEvent('keydown', {bubbles:true,cancelable:true,key:'Enter',code:'Enter'}));
                                el.dispatchEvent(new KeyboardEvent('keypress',{bubbles:true,cancelable:true,key:'Enter',code:'Enter'}));
                                el.dispatchEvent(new KeyboardEvent('keyup',   {bubbles:true,cancelable:true,key:'Enter',code:'Enter'}));
                            }
                        """, msg_input)
                    time.sleep(4.0)
                    # إعادة تشغيل فحص صارم واحد أخير بعد الـ ENTER
                    if self._verify_message_sent(
                        baseline_msgout_count=_msgout_count_baseline,
                        prev_last_msgout_text=_last_msgout_text_baseline,
                        expected_msg_fragment=_expected_msg_fragment,
                        is_attachment=(attachment_path and os.path.exists(attachment_path)),
                    ):
                        sent_verified = True
                except Exception:
                    pass

            # #region debug-point H1+H2+H3: FINAL VERDICT EVIDENCE CAPTURE (critical for distinguishing real vs fake success)
            try:
                _dbg_final = {"clean_phone": clean_phone, "sent_ok_flag": sent_ok, "sent_verified": sent_verified,
                              "verify_elapsed_sec": round(time.time() - verify_start, 1), "verify_timeout": VERIFY_TIMEOUT}
                # H1: FINAL COUNT OF msg-out + actual text of LAST msg-out (SMOKING GUN)
                try:
                    _out_final = self.driver.find_elements(By.XPATH, '//div[contains(@data-testid, "msg-out")] | //div[contains(@class, "message-out")] | //div[contains(@data-testid, "message-out")]') if self.driver else []
                    _dbg_final["msgout_count_final"] = len(_out_final)
                    # Check the actual TEXT of the LAST (most recent) message-out - does it really contain our message?
                    if _out_final:
                        try:
                            last_out = _out_final[-1]
                            _last_txt = (last_out.text or "").strip()[:300]
                            _dbg_final["last_msgout_final_text_len"] = len(_last_txt)
                            _dbg_final["last_msgout_final_text"] = _last_txt
                            # Check if expected message (first 80 chars) is actually PRESENT in last msg-out (real success indicator)
                            if message:
                                _expected_fragment = (message.strip()[:80]).lower()
                                _found_in_last = _expected_fragment and (_expected_fragment in _last_txt.lower())
                                _dbg_final["EXPECTED_MESSAGE_IN_LAST_MSGOUT_MATCH"] = _found_in_last
                                # Also check 2nd-to-last if needed
                                if not _found_in_last and len(_out_final) >= 2:
                                    _prev_txt = ((_out_final[-2].text or "").strip()[:300]).lower()
                                    _dbg_final["EXPECTED_MESSAGE_IN_2NDLAST_MSGOUT_MATCH"] = _expected_fragment in _prev_txt
                        except Exception as _e:
                            _dbg_final["last_msgout_capture_err"] = str(_e)[:100]
                except Exception as _e:
                    _dbg_final["msgout_final_count_err"] = str(_e)[:80]
                # H2: Final check of input field
                try:
                    if msg_input is not None:
                        _fi_final = msg_input.text if hasattr(msg_input, "text") else ""
                        _dbg_final["msg_input_final_empty"] = len((_fi_final or "").strip()) == 0
                        try:
                            _fi_final_js = self.driver.execute_script("return (arguments[0] && (arguments[0].innerText || arguments[0].textContent || '')).toString();", msg_input)
                            _dbg_final["msg_input_final_js_empty"] = len((_fi_final_js or "").strip()) == 0
                        except Exception:
                            pass
                except Exception:
                    pass
                # H3: What did _verify_message_sent actually return?
                try:
                    _vms = self._verify_message_sent()
                    _dbg_final["verify_message_sent_result"] = _vms
                except Exception as _e:
                    _dbg_final["verify_message_sent_error"] = str(_e)[:80]
                # FINAL: The return value we are about to give (exposes the fake positive claim)
                _ok = bool(sent_verified)
                _dbg_final["FUNCTION_CLAIMS_OK"] = _ok
                _dbg_final["IS_PROBABLE_FAKE_SUCCESS"] = _ok and (not _dbg_final.get("EXPECTED_MESSAGE_IN_LAST_MSGOUT_MATCH", False)
                                                                and not _dbg_final.get("EXPECTED_MESSAGE_IN_2NDLAST_MSGOUT_MATCH", False)
                                                                and len(_out_final if _out_final else []) == _dbg_presend.get("msgout_count_before_send", -1))
                __dbg_log("H1", "SMOKING GUN: FINAL VERDICT Evidence (message text in DOM + count delta + claim comparison)",
                          _dbg_final, location="send_message:final-verdict (ALL H)")
            except Exception:
                pass
            # #endregion

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
