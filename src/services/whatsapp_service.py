import os
import time
import shutil
import base64
import io
import random
import subprocess
import re
from datetime import datetime

# Selenium imports are done lazily in methods to avoid blocking app startup

class WhatsAppService:
    def __init__(self, session_id="wa_pasha_stable"):
        # 2026 Persistent Session: Store in project root instead of temp dir
        self.base_session_dir = os.path.join(os.getcwd(), ".whatsapp_session")
        self.session_path = os.path.join(self.base_session_dir, session_id)
        self.driver = None
        self.last_error = ""

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
        
        # 2026 Advanced Stealth User Agent
        ver = self._get_chrome_version()
        ua = self._get_random_ua(ver)
        
        def apply_stealth_args(o, is_uc=False):
            if headless:
                # Optimized Headless for 2026/Chrome 146
                o.add_argument("--headless=new")
                o.add_argument("--disable-gpu")
                o.add_argument("--window-size=1920,1080")
            
            o.add_argument("--no-sandbox")
            o.add_argument("--disable-dev-shm-usage")
            o.add_argument(f"--user-data-dir={self.session_path}")
            o.add_argument(f"--user-agent={ua}")
            o.add_argument("--lang=ar,en-US,en;q=0.9") # Add Arabic to languages
            o.add_argument("--disable-blink-features=AutomationControlled")
            o.add_argument("--use-fake-ui-for-media-stream")
            o.add_argument("--disable-notifications")
            o.add_argument("--disable-extensions")
            o.add_argument("--profile-directory=Default")
            o.add_argument("--disable-infobars")
            o.add_argument("--ignore-certificate-errors")
            o.add_argument("--disable-browser-side-navigation")
            o.add_argument("--disable-features=IsolateOrigins,site-per-process")
            o.add_argument("--password-store=basic")

        # Find Chrome binary
        binary = self._find_chrome_binary()
        ver = self._get_chrome_version()
        
        # --- Launch Logic with Crash Recovery ---
        attempts = 2
        for attempt in range(attempts):
            try:
                print(f"[{time.strftime('%H:%M:%S')}] Launching WhatsApp Engine (Attempt {attempt+1}/{attempts})...")
                # Force taskkill of ghost processes on first attempt to ensure no locks
                if attempt == 0:
                    self._kill_zombies()

                import undetected_chromedriver as uc
                opts = uc.ChromeOptions()
                apply_stealth_args(opts, is_uc=True)
                
                print(f"[{time.strftime('%H:%M:%S')}] Initializing UC (Ver: {ver}, Binary: {binary})...")
                self.driver = uc.Chrome(
                    options=opts, 
                    browser_executable_path=binary,
                    use_subprocess=False, # Changed to False for better stability in restricted environments
                    headless=False, 
                    version_main=ver
                )
                
                print(f"[{time.strftime('%H:%M:%S')}] Navigating to WhatsApp Web...")
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                self.driver.get("https://web.whatsapp.com")
                print(f"[{time.strftime('%H:%M:%S')}] Ready!")
                return True, "Ready (Powered by UC Multi-Session)"
            except Exception as e:
                err_msg = str(e).lower()
                print(f"[{time.strftime('%H:%M:%S')}] Error: {str(e)[:150]}")
                self.last_error = f"UC Error: {str(e)[:120]}"
                
                if attempt == 0:
                    print(f"[{time.strftime('%H:%M:%S')}] Retrying with fresh session...")
                    self._kill_zombies()
                    try: shutil.rmtree(self.session_path, ignore_errors=True)
                    except: pass
                    time.sleep(2)
                    continue 

                # Final Fallback to standard Selenium with Stealth
                try:
                    print(f"[{time.strftime('%H:%M:%S')}] Final Fallback to Standard Selenium + Stealth...")
                    from selenium import webdriver
                    from selenium.webdriver.chrome.options import Options as StdOptions
                    from selenium_stealth import stealth
                    
                    std_opts = StdOptions()
                    apply_stealth_args(std_opts, is_uc=False)
                    self.driver = webdriver.Chrome(options=std_opts)
                    
                    # Apply manual stealth for 2026
                    stealth(self.driver,
                        languages=["en-US", "en"],
                        vendor="Google Inc.",
                        platform="Win32",
                        webgl_vendor="Intel Inc.",
                        renderer="Intel Iris OpenGL Engine",
                        fix_hairline=True,
                    )
                    
                    self.driver.get("https://web.whatsapp.com")
                    return True, "Ready (Safe Fallback + Stealth)"
                except Exception as e2:
                    print(f"[{time.strftime('%H:%M:%S')}] Critical Failure: {str(e2)[:100]}")
                    self.last_error += f" | Final Error: {str(e2)[:60]}"
                    return False, self.last_error

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
            # Common Linux Paths (for Streamlit Cloud/GitHub)
            linux_paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/chromium",
                "/usr/bin/chromium-browser",
                "/usr/bin/google-chrome-stable"
            ]
            for b in linux_paths:
                if os.path.exists(b): return b
            
            # Try to find from 'which' command
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
                # Kill only headless chromes that might be locking the profile
                os.system('taskkill /F /IM chrome.exe /FI "WINDOWTITLE eq chrome*" /FI "MEMUSAGE gt 1" >nul 2>&1')
            else:
                # Portable Linux cleanup
                os.system('pkill -f chromedriver > /dev/null 2>&1')
                os.system('pkill -f chrome > /dev/null 2>&1')
        except: pass


    def get_status(self):
        from selenium.webdriver.common.by import By
        if not self.driver: return "Disconnected"
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
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        if not self.driver: return False
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="side"]'))
            )
            return True
        except:
            return False

    def get_qr_hd(self):
        if not self.driver: return None
        try:
            from PIL import Image
            data_url = self.driver.execute_script(
                "return document.querySelector('canvas').toDataURL('image/png')"
            )
            if not data_url: return None
            header, b64data = data_url.split(",", 1)
            raw_bytes = base64.b64decode(b64data)
            img = Image.open(io.BytesIO(raw_bytes))
            
            # 2026 QR Enhancement: Higher contrast and sharper edges
            from PIL import ImageOps
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
        except:
            try:
                return self.driver.execute_script(
                    "return document.querySelector('canvas').toDataURL('image/png')"
                )
            except:
                return None

    def get_diagnostic_screenshot(self):
        if not self.driver: return None
        try: return self.driver.get_screenshot_as_base64()
        except: return None

    def _type_human_like(self, element, text):
        """يحاكي الطباعة البشرية مع فواصل زمنية عشوائية لتجنب الحظر"""
        for char in text:
            element.send_keys(char)
            if random.random() > 0.85:
                time.sleep(random.uniform(0.02, 0.15))
            elif random.random() > 0.98:
                time.sleep(random.uniform(0.5, 1.2))


    def send_message(self, phone, message, attachment_path=None):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.keys import Keys
        if not self.driver: return False, "Engine Offline"
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            
            clean_phone = "".join(filter(str.isdigit, str(phone)))
            
            # 1. Length Validation
            if len(clean_phone) < 8:
                return False, "رقم قصير جداً" 
            
            # Open the chat window with a brief random wait
            # محاكاة التفكير قبل الفتح
            time.sleep(random.uniform(2.0, 5.0))
            url = f"https://web.whatsapp.com/send?phone={clean_phone}"
            self.driver.get(url)
            
            # محاكاة حركة الماوس العشوائية والتمرير (Human Focus)
            try:
                actions = ActionChains(self.driver)
                for _ in range(random.randint(2, 4)):
                    actions.move_by_offset(random.randint(-50, 50), random.randint(-50, 50)).perform()
                    time.sleep(random.uniform(0.1, 0.3))
                # تمرير بسيط للأسفل والأعلى ليبدو كأن المستخدم يقرأ
                self.driver.execute_script(f"window.scrollBy(0, {random.randint(100, 300)})")
                time.sleep(random.uniform(0.5, 1.0))
                self.driver.execute_script(f"window.scrollBy(0, -{random.randint(50, 150)})")
            except: pass
            
            wait = WebDriverWait(self.driver, 45)
            
            # Wait for text box
            try:
                msg_input = wait.until(EC.presence_of_element_located(
                    (By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
                ))
            except:
                src = self.driver.page_source.lower()
                if "invalid" in src or "غير صحيح" in src:
                    return False, "رقم غير مسجل في الواتساب"
                return False, "فشل في التحميل"

            time.sleep(random.uniform(1.5, 3.0)) # Human-like pause after loading

            if attachment_path and os.path.exists(attachment_path):
                # 🛡️ تمويه اسم الملف: نسخ الملف لاسم عشوائي قبل الإرسال لتجنب البصمة المتكررة
                temp_dir = os.path.join(self.session_path, "temp_uploads")
                os.makedirs(temp_dir, exist_ok=True)
                
                original_ext = os.path.splitext(attachment_path)[1]
                random_filename = f"DOC_{datetime.now().strftime('%H%M%S')}_{random.randint(1000, 9999)}{original_ext}"
                obfuscated_path = os.path.join(temp_dir, random_filename)
                shutil.copy2(attachment_path, obfuscated_path)

                # Attach file
                attach_btn = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, '//div[@title="Attach"] | //span[@data-icon="plus"] | //span[@data-icon="attach-menu-plus"]')
                ))
                time.sleep(random.uniform(1.2, 2.5)) # تفكير قبل الضغط
                attach_btn.click()
                time.sleep(random.uniform(1.0, 2.0))

                file_input = self.driver.find_element(By.XPATH, '//input[@type="file"]')
                file_input.send_keys(obfuscated_path)
                
                caption_input = wait.until(EC.presence_of_element_located(
                    (By.XPATH, '//div[@contenteditable="true"][@data-tab="10"] | //div[@contenteditable="true" and contains(@class, "copyable-text")]')
                ))
                
                if message:
                    time.sleep(random.uniform(1.0, 2.5))
                    actions = ActionChains(self.driver)
                    actions.move_to_element(caption_input).click().perform()
                    
                    # استخدام دالة الكتابة البشرية لتجنب تكرار الكود
                    self._type_human_like(caption_input, message)
                    time.sleep(random.uniform(0.8, 1.5))
                
                # Natural pause before ENTER
                time.sleep(random.uniform(0.5, 1.2))
                caption_input.send_keys(Keys.ENTER)
            else:
                # Simple text message
                if message:
                    # استخدام دالة الكتابة البشرية لتجنب تكرار الكود
                    self._type_human_like(msg_input, message)
                    
                    time.sleep(random.uniform(1.2, 2.5))
                    # Natural pause before ENTER
                    time.sleep(random.uniform(0.5, 1.2))
                    msg_input.send_keys(Keys.ENTER)
            
            time.sleep(random.uniform(2.0, 4.0)) # Wait for send
            return True, "Done"
        except Exception as e:
            return False, f"Err: {str(e)[:40]}"


    def close(self):
        if self.driver:
            try: self.driver.quit()
            except: pass
            self.driver = None
