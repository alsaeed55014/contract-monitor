import os
import time
import shutil
import tempfile
import base64
import io
import glob
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
        for lf in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
            p = os.path.join(self.session_path, lf)
            try:
                if os.path.exists(p): os.remove(p)
            except: pass
        
        opts = Options()
        if headless:
            opts.add_argument("--headless=new")
        
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument(f"user-data-dir={self.session_path}")
        opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        opts.add_argument("--disable-extensions")
        opts.page_load_strategy = "eager"
        
        # Find Chrome/Chromium binary
        chrome_bins = [
            "/usr/bin/chromium", "/usr/bin/chromium-browser", 
            "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
            "/snap/bin/chromium"
        ]
        for b in chrome_bins:
            if os.path.exists(b):
                opts.binary_location = b
                break
        
        # Find chromedriver
        driver_paths = [
            "/usr/bin/chromedriver",
            "/usr/lib/chromium/chromedriver",
            "/usr/lib/chromium-browser/chromedriver",
            "/snap/bin/chromium.chromedriver"
        ]
        
        found_driver = None
        for dp in driver_paths:
            if os.path.exists(dp):
                found_driver = dp
                break
        
        # Attempt 1: Direct with found driver path
        errors = []
        if found_driver:
            try:
                service = Service(executable_path=found_driver)
                self.driver = webdriver.Chrome(service=service, options=opts)
                self.driver.get("https://web.whatsapp.com")
                try:
                    WebDriverWait(self.driver, 25).until(
                        lambda d: d.find_elements(By.CSS_SELECTOR, "canvas") or d.find_elements(By.XPATH, '//*[@id="side"]')
                    )
                except: pass
                return True, "Ready"
            except Exception as e:
                errors.append(f"Direct({found_driver}): {str(e)[:80]}")
                self.driver = None
        
        # Attempt 2: Let Selenium auto-detect
        try:
            self.driver = webdriver.Chrome(options=opts)
            self.driver.get("https://web.whatsapp.com")
            try:
                WebDriverWait(self.driver, 25).until(
                    lambda d: d.find_elements(By.CSS_SELECTOR, "canvas") or d.find_elements(By.XPATH, '//*[@id="side"]')
                )
            except: pass
            return True, "Ready (Auto)"
        except Exception as e:
            errors.append(f"Auto: {str(e)[:80]}")
            self.driver = None
        
        # Attempt 3: webdriver-manager fallback
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=opts)
            self.driver.get("https://web.whatsapp.com")
            try:
                WebDriverWait(self.driver, 25).until(
                    lambda d: d.find_elements(By.CSS_SELECTOR, "canvas") or d.find_elements(By.XPATH, '//*[@id="side"]')
                )
            except: pass
            return True, "Ready (WDM)"
        except Exception as e:
            errors.append(f"WDM: {str(e)[:80]}")
            self.driver = None
        
        self.last_error = " | ".join(errors)
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
            # Open the chat window first
            url = f"https://web.whatsapp.com/send?phone={clean_phone}"
            self.driver.get(url)
            
            wait = WebDriverWait(self.driver, 45)
            
            # Wait for either the text box (connected) or the error popup (invalid number)
            try:
                msg_input = wait.until(EC.presence_of_element_located(
                    (By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
                ))
            except:
                # Check for "Phone number shared via url is invalid" popup
                if "invalid" in self.driver.page_source.lower() or "غير صحيح" in self.driver.page_source:
                    return False, "Invalid Number"
                return False, "Load Timeout"

            time.sleep(2) # Stability

            if attachment_path and os.path.exists(attachment_path):
                # 1. Click Attach button (the '+' or paperclip)
                attach_btn = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, '//div[@title="Attach"] | //span[@data-icon="plus"] | //span[@data-icon="attach-menu-plus"]')
                ))
                attach_btn.click()
                time.sleep(1)

                # 2. Find the hidden input for documents/images
                # We target the common hidden input for all files
                file_input = self.driver.find_element(By.XPATH, '//input[@type="file"]')
                file_input.send_keys(attachment_path)
                
                # 3. Wait for preview/caption box to appear
                # The input box in the preview screen
                caption_input = wait.until(EC.presence_of_element_located(
                    (By.XPATH, '//div[@contenteditable="true"][@data-tab="10"] | //div[@contenteditable="true" and contains(@class, "copyable-text")]')
                ))
                
                # Some versions of WA scroll or autofocus differently. 
                # Let's clear and type the message as a caption
                if message:
                    # Using ActionChains to ensure the text is typed into the caption
                    actions = ActionChains(self.driver)
                    actions.move_to_element(caption_input).click().send_keys(message).perform()
                    time.sleep(1)
                
                caption_input.send_keys(Keys.ENTER)
            else:
                # Simple text message
                if message:
                    msg_input.send_keys(message)
                    time.sleep(1)
                    msg_input.send_keys(Keys.ENTER)
            
            time.sleep(3) # Wait for send to complete
            return True, "Done"
        except Exception as e:
            return False, f"Error: {str(e)[:50]}"

    def close(self):
        if self.driver:
            try: self.driver.quit()
            except: pass
            self.driver = None
