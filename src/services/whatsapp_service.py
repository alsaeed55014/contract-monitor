import os
import time
import shutil
import tempfile
import base64
import io
import glob
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

from src.config import BASE_DIR

# ─── Stealth JS patches injected after page load ─────────────────────────────
# These make the browser look like a real user, not an automation bot.
_STEALTH_JS = """
// 1. Remove webdriver flag
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// 2. Fake plugins (real browsers have plugins)
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});

// 3. Fake language
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en'],
});

// 4. Hide chrome automation flags
window.chrome = { runtime: {} };

// 5. Override permissions query to not reveal automation
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
    Promise.resolve({ state: Notification.permission }) :
    originalQuery(parameters)
);
"""

class WhatsAppService:
    def __init__(self, session_id="wa_pasha_stable"):
        # Store session permanently in BASE_DIR to prevent logging out
        self.session_path = os.path.join(BASE_DIR, ".whatsapp_session", session_id)
        self.driver = None
        self.last_error = ""

    def _apply_stealth(self):
        """Inject stealth JavaScript to hide automation fingerprints."""
        try:
            if self.driver:
                self.driver.execute_cdp_cmd(
                    "Page.addScriptToEvaluateOnNewDocument",
                    {"source": _STEALTH_JS}
                )
        except Exception:
            # Fallback: execute directly (less effective but better than nothing)
            try:
                self.driver.execute_script(_STEALTH_JS)
            except Exception:
                pass

    def start_driver(self, headless=False, force_clean=False):
        """
        Starts the Chrome driver using undetected-chromedriver first (best),
        then falls back to regular selenium with stealth patches.
        headless=False by default on desktop — WhatsApp Web REQUIRES a visible
        browser window to show and scan the QR code reliably.
        """
        if self.driver:
            try:
                self.driver.current_url
                return True, "Active"
            except:
                self.close()

        if force_clean and os.path.exists(self.session_path):
            shutil.rmtree(self.session_path, ignore_errors=True)

        os.makedirs(self.session_path, exist_ok=True)

        # Clean lock files from previous crashed sessions
        for lf in ["SingletonLock", "SingletonSocket", "SingletonCookie", "lockfile"]:
            p = os.path.join(self.session_path, lf)
            try:
                if os.path.exists(p):
                    os.remove(p)
            except:
                pass

        # ── Attempt 1: undetected-chromedriver (BEST — bypasses WA bot detection) ──
        try:
            import undetected_chromedriver as uc

            options = uc.ChromeOptions()
            options.add_argument(f"--user-data-dir={self.session_path}")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-notifications")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--lang=en-US")

            if headless:
                # headless=2 is the new Chrome headless mode, less detectable
                options.add_argument("--headless=new")

            self.driver = uc.Chrome(
                options=options,
                user_data_dir=self.session_path,
                headless=headless,
                use_subprocess=True,   # Keeps browser alive if Python restarts
                version_main=None,     # Auto-detect Chrome version
            )

            self._apply_stealth()
            self.driver.get("https://web.whatsapp.com")
            return True, "Ready (Stealth Engine)"

        except ImportError:
            pass  # Fall through to selenium
        except Exception as e:
            self.last_error = f"UC: {str(e)[:80]}"
            self.close()

        # ── Attempt 2: Regular selenium + manual stealth patches (FALLBACK) ──
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service

            opts = Options()
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--disable-setuid-sandbox")
            opts.add_argument("--disable-software-rasterizer")
            opts.add_argument("--disable-infobars")
            opts.add_argument("--disable-notifications")
            opts.add_argument("--window-size=1920,1080")
            opts.add_argument("--lang=en-US")
            opts.add_argument(f"--user-data-dir={self.session_path}")

            # Critical stealth flags
            opts.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            opts.add_experimental_option("useAutomationExtension", False)
            opts.add_argument("--disable-blink-features=AutomationControlled")

            if headless:
                opts.add_argument("--headless=new")
                opts.add_argument(
                    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                )

            # Keep browser open if Streamlit restarts
            opts.add_experimental_option("detach", True)
            opts.page_load_strategy = "eager"

            # Find Chrome binary
            if os.name == 'nt':
                for b in [
                    os.environ.get("PROGRAMFILES", "C:\\Program Files") + "\\Google\\Chrome\\Application\\chrome.exe",
                    os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)") + "\\Google\\Chrome\\Application\\chrome.exe",
                    os.environ.get("LOCALAPPDATA", "") + "\\Google\\Chrome\\Application\\chrome.exe",
                ]:
                    if os.path.exists(b):
                        opts.binary_location = b
                        break
            else:
                for b in ["/usr/bin/chromium", "/usr/bin/chromium-browser",
                          "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
                          "/snap/bin/chromium"]:
                    if os.path.exists(b):
                        opts.binary_location = b
                        break

            # Try webdriver-manager
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
            except Exception:
                service = None

            if service:
                self.driver = webdriver.Chrome(service=service, options=opts)
            else:
                self.driver = webdriver.Chrome(options=opts)

            self._apply_stealth()
            self.driver.get("https://web.whatsapp.com")
            return True, "Ready (Standard Engine)"

        except Exception as e:
            self.last_error = f"Selenium: {str(e)[:80]}"
            self.close()
            return False, self.last_error

    def get_status(self):
        if not self.driver:
            return "Disconnected"
        try:
            self.driver.find_element(By.XPATH, '//*[@id="side"]')
            return "Connected"
        except:
            try:
                self.driver.find_element(By.CSS_SELECTOR, "canvas")
                return "Awaiting Login"
            except:
                return "Loading..."

    def wait_for_connection(self, timeout=30):
        if not self.driver:
            return False
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="side"]'))
            )
            return True
        except:
            return False

    def get_qr_hd(self):
        """Captures and upscales the QR code canvas for easier scanning."""
        if not self.driver:
            return None
        try:
            from PIL import Image
            data_url = self.driver.execute_script(
                "return document.querySelector('canvas') ? document.querySelector('canvas').toDataURL('image/png') : null"
            )
            if not data_url:
                return None
            header, b64data = data_url.split(",", 1)
            raw_bytes = base64.b64decode(b64data)
            img = Image.open(io.BytesIO(raw_bytes))
            # 4x upscale with nearest-neighbour for crisp QR pixels
            new_size = (img.width * 4, img.height * 4)
            img_big = img.resize(new_size, Image.NEAREST)
            border = 40
            final = Image.new("RGB", (img_big.width + border * 2, img_big.height + border * 2), "white")
            final.paste(img_big, (border, border))
            buf = io.BytesIO()
            final.save(buf, format="PNG")
            buf.seek(0)
            return base64.b64encode(buf.read()).decode()
        except:
            try:
                return self.driver.execute_script(
                    "return document.querySelector('canvas') ? document.querySelector('canvas').toDataURL('image/png') : null"
                )
            except:
                return None

    def get_diagnostic_screenshot(self):
        if not self.driver:
            return None
        try:
            return self.driver.get_screenshot_as_base64()
        except:
            return None

    def send_message(self, phone, message, attachment_path=None):
        if not self.driver:
            return False, "Engine Offline"
        try:
            from selenium.webdriver.common.action_chains import ActionChains

            clean_phone = "".join(filter(str.isdigit, str(phone)))

            if len(clean_phone) < 8:
                return False, "رقم قصير جداً"
            if len(clean_phone) > 15:
                return False, "رقم طويل جداً"

            url = f"https://web.whatsapp.com/send?phone={clean_phone}"
            self.driver.get(url)

            wait = WebDriverWait(self.driver, 45)

            try:
                msg_input = wait.until(EC.presence_of_element_located(
                    (By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
                ))
            except:
                src = self.driver.page_source.lower()
                if "invalid" in src or "غير صحيح" in src:
                    return False, "لا يوجد حساب واتساب"
                return False, "فشل التحميل (تحقق من الاتصال)"

            time.sleep(2)

            if attachment_path and os.path.exists(attachment_path):
                attach_btn = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, '//div[@title="Attach"] | //span[@data-icon="plus"] | //span[@data-icon="attach-menu-plus"]')
                ))
                attach_btn.click()
                time.sleep(1)

                file_input = self.driver.find_element(By.XPATH, '//input[@type="file"]')
                file_input.send_keys(attachment_path)

                caption_input = wait.until(EC.presence_of_element_located(
                    (By.XPATH, '//div[@contenteditable="true"][@data-tab="10"] | //div[@contenteditable="true" and contains(@class, "copyable-text")]')
                ))

                if message:
                    actions = ActionChains(self.driver)
                    actions.move_to_element(caption_input).click().send_keys(message).perform()
                    time.sleep(1)

                caption_input.send_keys(Keys.ENTER)
            else:
                if message:
                    msg_input.send_keys(message)
                    time.sleep(1)
                    msg_input.send_keys(Keys.ENTER)

            time.sleep(3)
            return True, "Done"
        except Exception as e:
            return False, f"Error: {str(e)[:50]}"

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
