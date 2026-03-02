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
    def __init__(self, session_path="wa_session_data"):
        # Use a consistent path but allow for easy clearing
        self.session_path = os.path.abspath(session_path)
        self.driver = None

    def start_driver(self, headless=True):
        """Ultra-Stable Cloud Starter for Pasha"""
        if self.driver: 
            try:
                self.driver.current_url
                return True, "Already Running"
            except: 
                self.close()

        # Step 1: Force clear old session to prevent "Profile in Use" error
        if os.path.exists(self.session_path):
            shutil.rmtree(self.session_path, ignore_errors=True)
        os.makedirs(self.session_path, exist_ok=True)
        
        opts = Options()
        if headless:
            opts.add_argument("--headless=new")
        
        # Essential flags for Streamlit Cloud (Linux)
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-extensions")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument(f"user-data-dir={self.session_path}")
        opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
        
        # Try to find system chromium first (Streamlit Cloud best practice)
        chrome_bin = shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
        if chrome_bin:
            opts.binary_location = chrome_bin

        try:
            # First attempt: Simple init
            self.driver = webdriver.Chrome(options=opts)
            self.driver.get("https://web.whatsapp.com")
            return True, "Engine Started"
        except Exception as e:
            # Second attempt: Using Service with auto-install
            try:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=opts)
                self.driver.get("https://web.whatsapp.com")
                return True, "Engine Started (Fallback)"
            except Exception as e2:
                self.driver = None
                return False, f"Pasha, Engine Failed: {str(e2)[:100]}"

    def get_status(self):
        if not self.driver: return "Disconnected"
        try:
            # Check for chat side bar
            self.driver.find_element(By.XPATH, '//*[@id="side"]')
            return "Connected"
        except:
            try:
                # Check for QR canvas
                self.driver.find_element(By.CSS_SELECTOR, "canvas")
                return "Awaiting Login"
            except:
                return "Loading..."

    def get_qr_hd(self):
        if not self.driver: return None
        try:
            return self.driver.execute_script("return document.querySelector('canvas').toDataURL()")
        except:
            return None

    def get_diagnostic_screenshot(self):
        if not self.driver: return None
        try: return self.driver.get_screenshot_as_base64()
        except: return None

    def send_message(self, phone, message):
        """The 'Enter Key' Strike for Pasha"""
        if not self.driver: return False, "Engine Offline"
        try:
            clean_phone = "".join(filter(str.isdigit, str(phone)))
            url = f"https://web.whatsapp.com/send?phone={clean_phone}&text={message}"
            self.driver.get(url)
            
            # Wait for content to load
            wait = WebDriverWait(self.driver, 45)
            # Find the message input box
            input_box = wait.until(EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')))
            
            if input_box:
                time.sleep(3) # Wait for page stability
                input_box.send_keys(Keys.ENTER)
                time.sleep(2)
                return True, "Sent Successfully"
            return False, "Input Box Hidden"
        except Exception as e:
            return False, f"Failed: {str(e)[:50]}"

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
