import os
import time
import shutil
import tempfile
import base64
import io
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

class WhatsAppService:
    def __init__(self, session_id="wa_pasha_fast_v12"):
        self.session_path = os.path.join(tempfile.gettempdir(), session_id)
        self.driver = None

    def start_driver(self, headless=True):
        """TURBO START - Optimized for speed"""
        if self.driver: 
            try:
                self.driver.current_url
                return True, "Active"
            except: 
                self.close()

        if os.path.exists(self.session_path):
            shutil.rmtree(self.session_path, ignore_errors=True)
        os.makedirs(self.session_path, exist_ok=True)
        
        opts = Options()
        if headless:
            opts.add_argument("--headless=new")
        
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument(f"user-data-dir={self.session_path}")
        opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        
        # SPEED OPTIMIZATIONS
        opts.add_argument("--disable-extensions")
        opts.add_argument("--disable-infobars")
        opts.add_argument("--disable-notifications")
        opts.add_argument("--disable-popup-blocking")
        opts.add_argument("--blink-settings=imagesEnabled=true")
        opts.page_load_strategy = "eager"  # Don't wait for full page load!
        
        possible_bins = ["/usr/bin/chromium", "/usr/bin/google-chrome", "/usr/bin/chromium-browser"]
        for b in possible_bins:
            if os.path.exists(b):
                opts.binary_location = b
                break

        try:
            self.driver = webdriver.Chrome(options=opts)
        except:
            try:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=opts)
            except Exception as e2:
                self.driver = None
                return False, f"Error: {str(e2)[:60]}"
        
        # Navigate and wait for QR canvas specifically
        self.driver.get("https://web.whatsapp.com")
        try:
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "canvas"))
            )
            return True, "QR Ready"
        except:
            return True, "Page Loaded"

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

    def get_qr_hd(self):
        """Pixel-Perfect QR with PIL upscale"""
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
            
            # 4X upscale with NEAREST (sharp pixels, no blur)
            new_size = (img.width * 4, img.height * 4)
            img_big = img.resize(new_size, Image.NEAREST)
            
            # White border
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

    def send_message(self, phone, message):
        if not self.driver: return False, "Engine Offline"
        try:
            clean_phone = "".join(filter(str.isdigit, str(phone)))
            url = f"https://web.whatsapp.com/send?phone={clean_phone}&text={message}"
            self.driver.get(url)
            wait = WebDriverWait(self.driver, 60)
            input_box = wait.until(EC.presence_of_element_located(
                (By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
            ))
            time.sleep(5)
            input_box.send_keys(Keys.ENTER)
            time.sleep(2)
            return True, "Done"
        except Exception as e:
            return False, f"Error: {str(e)[:40]}"

    def close(self):
        if self.driver:
            try: self.driver.quit()
            except: pass
            self.driver = None
