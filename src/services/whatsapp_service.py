import os
import time
import shutil
import tempfile
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

class WhatsAppService:
    def __init__(self, session_id="wa_pasha_session_v3"):
        self.session_path = os.path.join(tempfile.gettempdir(), session_id)
        self.driver = None

    def start_driver(self, headless=True):
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
        opts.add_argument("--window-size=1920,1080")
        # Boost Pixel Ratio for Ultra-HD QR for Pasha
        opts.add_argument("--force-device-scale-factor=2") 
        opts.add_argument(f"user-data-dir={self.session_path}")
        opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        
        possible_bins = ["/usr/bin/chromium", "/usr/bin/google-chrome", "/usr/bin/chromium-browser"]
        for b in possible_bins:
            if os.path.exists(b):
                opts.binary_location = b
                break

        try:
            self.driver = webdriver.Chrome(options=opts)
            self.driver.get("https://web.whatsapp.com")
            return True, "Done"
        except Exception as e:
            try:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=opts)
                self.driver.get("https://web.whatsapp.com")
                return True, "Done Fallback"
            except Exception as e2:
                self.driver = None
                return False, f"Error: {str(e2)}"

    def get_status(self):
        if not self.driver: return "Disconnected"
        try:
            # Check for main side panel
            self.driver.find_element(By.XPATH, '//*[@id="side"]')
            return "Connected"
        except:
            try:
                # Check for QR canvas
                canvas = self.driver.find_element(By.CSS_SELECTOR, "canvas")
                # Auto-click reload if QR expired (Blurred)
                try:
                    reload_btn = self.driver.find_element(By.XPATH, "//span[@data-icon='refresh-l-light']")
                    reload_btn.click()
                    time.sleep(1)
                except: pass
                return "Awaiting Login"
            except:
                return "Loading..."

    def get_qr_hd(self):
        """Pasha's Ultra-Clear QR Capture"""
        if not self.driver: return None
        try:
            # Inject white background JS for better contrast
            script = """
            var canvas = document.querySelector('canvas');
            if(canvas) {
                var newCanvas = document.createElement('canvas');
                var context = newCanvas.getContext('2d');
                newCanvas.width = canvas.width + 40;
                newCanvas.height = canvas.height + 40;
                context.fillStyle = "white";
                context.fillRect(0,0,newCanvas.width,newCanvas.height);
                context.drawImage(canvas, 20, 20);
                return newCanvas.toDataURL("image/png");
            }
            return null;
            """
            return self.driver.execute_script(script)
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
            wait = WebDriverWait(self.driver, 45)
            input_box = wait.until(EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')))
            time.sleep(5)
            input_box.send_keys(Keys.ENTER)
            time.sleep(2)
            return True, "Success"
        except Exception as e:
            return False, str(e)[:50]

    def close(self):
        if self.driver:
            try: self.driver.quit()
            except: pass
            self.driver = None
