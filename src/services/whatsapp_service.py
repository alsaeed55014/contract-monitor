import os
import time
import shutil
import tempfile
import base64
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

class WhatsAppService:
    def __init__(self, session_id="wa_pasha_engine_v9"):
        # We use a completely new session ID to clear all old corruption
        self.session_path = os.path.join(tempfile.gettempdir(), session_id)
        self.driver = None

    def start_driver(self, headless=True):
        """Pasha's Ultra-High-Performance Driver Initialization"""
        if self.driver: 
            try:
                self.driver.current_url
                return True, "Active"
            except: 
                self.close()

        # Step 1: Force Cleanup for a clean QR scan
        if os.path.exists(self.session_path):
            shutil.rmtree(self.session_path, ignore_errors=True)
        os.makedirs(self.session_path, exist_ok=True)
        
        opts = Options()
        if headless:
            opts.add_argument("--headless=new")
        
        # ELITE FLAGS for QR Scanning on Cloud
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--force-device-scale-factor=2") # 2X Zoom for Ultra-Clear QR
        opts.add_argument("--high-dpi-support=1")
        opts.add_argument(f"user-data-dir={self.session_path}")
        # Use a more modern user agent
        opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        
        # Binary Discovery
        possible_bins = ["/usr/bin/chromium", "/usr/bin/google-chrome", "/usr/bin/chromium-browser"]
        for b in possible_bins:
            if os.path.exists(b):
                opts.binary_location = b
                break

        try:
            self.driver = webdriver.Chrome(options=opts)
            self.driver.get("https://web.whatsapp.com")
            # Wait for any content to appear
            WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            return True, "Ready"
        except Exception as e:
            try:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=opts)
                self.driver.get("https://web.whatsapp.com")
                return True, "Ready (Fallback)"
            except Exception as e2:
                self.driver = None
                return False, f"Launch Failed: {str(e2)[:60]}"

    def get_status(self):
        if not self.driver: return "Disconnected"
        try:
            # Check for side panel (Login OK)
            self.driver.find_element(By.XPATH, '//*[@id="side"]')
            return "Connected"
        except:
            try:
                # Check for canvas (Waiting for scan)
                canvas = self.driver.find_element(By.CSS_SELECTOR, "canvas")
                
                # AUTO-FIX: Click refresh button if it appears on QR
                try:
                    refresh_area = self.driver.find_element(By.XPATH, "//div[contains(@class, 'reload')]")
                    refresh_area.click()
                    time.sleep(1)
                except: pass
                
                return "Awaiting Login"
            except:
                return "Loading..."

    def get_qr_hd(self):
        """Pasha's Perfect QR Capturer - High Resolution Fragment"""
        if not self.driver: return None
        try:
            # 1. First, wait for canvas to appear
            wait = WebDriverWait(self.driver, 5)
            canvas = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "canvas")))
            
            # 2. Inject JS to make QR isolated and bright white
            pasha_js = """
            var canvas = document.querySelector('canvas');
            if(canvas) {
                canvas.parentElement.style.padding = '30px';
                canvas.parentElement.style.background = 'white';
                canvas.parentElement.style.borderRadius = '20px';
                canvas.style.transform = 'scale(1.2)'; // Enlarge for Pasha
            }
            """
            self.driver.execute_script(pasha_js)
            
            # 3. Take a direct element screenshot for maximum precision
            return canvas.screenshot_as_base64
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
            input_box = wait.until(EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')))
            time.sleep(5) # Network latency stabilizer
            input_box.send_keys(Keys.ENTER)
            time.sleep(2)
            return True, "Done"
        except Exception as e:
            return False, f"Send Error: {str(e)[:40]}"

    def close(self):
        if self.driver:
            try: self.driver.quit()
            except: pass
            self.driver = None
