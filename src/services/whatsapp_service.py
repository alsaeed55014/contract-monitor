import os
import time
import shutil
import tempfile
import base64
import io
import glob
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

class WhatsAppService:
    def __init__(self, session_id="wa_pasha_stable"):
        self.session_path = os.path.join(tempfile.gettempdir(), session_id)
        self.driver = None
        self.last_error = ""


    def start_driver(self, headless=True, force_clean=False):
        if self.driver: 
            try:
                self.driver.current_url
                return True, "Active"
            except: 
                self.close()

        if force_clean and os.path.exists(self.session_path):
            shutil.rmtree(self.session_path, ignore_errors=True)
        
        os.makedirs(self.session_path, exist_ok=True)
        
        # Clean lock files
        for lf in ["SingletonLock", "SingletonSocket", "SingletonCookie", "lockfile"]:
            p = os.path.join(self.session_path, lf)
            try:
                if os.path.exists(p): os.remove(p)
            except: pass
        
        import undetected_chromedriver as uc
        
        opts = uc.ChromeOptions()
        if headless:
            opts.add_argument("--headless")
        
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument(f"--user-data-dir={self.session_path}")
        
        # 2026 Advanced Stealth User Agents (Updated for 125+)
        USER_AGENTS = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0"
        ]
        ua = random.choice(USER_AGENTS)
        opts.add_argument(f"--user-agent={ua}")
        opts.add_argument("--lang=en-US,en;q=0.9")
        
        # Bypassing Detection: Force Automation Controlled disable
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--use-fake-ui-for-media-stream")
        opts.add_argument("--disable-notifications")
        opts.add_argument("--remote-debugging-port=9222")
        
        # Find Chrome binary (Windows & Linux)
        binary = None
        if os.name == 'nt': # Windows
            win_paths = [
                os.environ.get("PROGRAMFILES", "C:\\Program Files") + "\\Google\\Chrome\\Application\\chrome.exe",
                os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)") + "\\Google\\Chrome\\Application\\chrome.exe",
                os.environ.get("LOCALAPPDATA", "") + "\\Google\\Chrome\\Application\\chrome.exe"
            ]
            for b in win_paths:
                if os.path.exists(b):
                    binary = b
                    break
        else: # Linux
            chrome_bins = [
                "/usr/bin/chromium", "/usr/bin/chromium-browser", 
                "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
                "/snap/bin/chromium"
            ]
            for b in chrome_bins:
                if os.path.exists(b):
                    binary = b
                    break
        
        try:
            # Use Undetected Chromedriver (UC)
            # UC manages its own driver, so we don't need Service() usually
            # Attempt to match modern version, but let uc auto-detect if possible
            self.driver = uc.Chrome(
                options=opts, 
                browser_executable_path=binary
            )
            self.driver.get("https://web.whatsapp.com")
            return True, "Ready (Powered by UC Stealth)"
        except Exception as e:
            self.last_error = f"UC Error: {str(e)[:100]}"
            # Fallback to standard if UC fails
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options as StdOptions
                std_opts = StdOptions()
                if headless: std_opts.add_argument("--headless")
                std_opts.add_argument(f"user-data-dir={self.session_path}")
                self.driver = webdriver.Chrome(options=std_opts)
                self.driver.get("https://web.whatsapp.com")
                return True, "Ready (Standard Fallback - Vulnerable)"
            except Exception as e2:
                self.last_error += f" | Standard Error: {str(e2)[:60]}"
                return False, self.last_error


    def get_status(self):
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
            new_size = (img.width * 4, img.height * 4)
            img_big = img.resize(new_size, Image.NEAREST)
            border = 40
            final = Image.new("RGB", (img_big.width + border*2, img_big.height + border*2), "white")
            final.paste(img_big, (border, border))
            buf = io.BytesIO()
            final.save(buf, format="PNG")
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


    def send_message(self, phone, message, attachment_path=None):
        if not self.driver: return False, "Engine Offline"
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            
            clean_phone = "".join(filter(str.isdigit, str(phone)))
            
            # 1. Length Validation
            if len(clean_phone) < 8:
                return False, "رقم قصير جداً" 
            
            # Open the chat window with a brief random wait
            time.sleep(random.uniform(1.0, 3.0))
            url = f"https://web.whatsapp.com/send?phone={clean_phone}"
            self.driver.get(url)
            
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
                # Attach file
                attach_btn = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, '//div[@title="Attach"] | //span[@data-icon="plus"] | //span[@data-icon="attach-menu-plus"]')
                ))
                time.sleep(random.uniform(0.5, 1.2))
                attach_btn.click()
                time.sleep(random.uniform(1.0, 2.0))

                file_input = self.driver.find_element(By.XPATH, '//input[@type="file"]')
                file_input.send_keys(attachment_path)
                
                caption_input = wait.until(EC.presence_of_element_located(
                    (By.XPATH, '//div[@contenteditable="true"][@data-tab="10"] | //div[@contenteditable="true" and contains(@class, "copyable-text")]')
                ))
                
                if message:
                    time.sleep(random.uniform(1.0, 2.5))
                    actions = ActionChains(self.driver)
                    actions.move_to_element(caption_input).click().perform()
                    
                    # Human-like typing with variable speed and occasional "mistakes" (simulated by pauses)
                    for char in message:
                        caption_input.send_keys(char)
                        # More natural typing rhythm
                        if random.random() > 0.85:
                            time.sleep(random.uniform(0.02, 0.15))
                        elif random.random() > 0.98:
                            time.sleep(random.uniform(0.5, 1.2)) # Thinking pause
                    time.sleep(random.uniform(0.8, 1.5))
                
                caption_input.send_keys(Keys.ENTER)
            else:
                # Simple text message
                if message:
                    # Slow/Natural typing simulation
                    for char in message:
                        msg_input.send_keys(char)
                        if random.random() > 0.90:
                            time.sleep(random.uniform(0.01, 0.12))
                        elif random.random() > 0.99:
                            time.sleep(random.uniform(0.4, 0.9))
                    
                    time.sleep(random.uniform(1.2, 2.5))
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
