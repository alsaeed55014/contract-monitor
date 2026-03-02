import os
import time
import base64
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class WhatsAppService:
    def __init__(self, session_path="wd_session"):
        self.session_path = os.path.abspath(session_path)
        if not os.path.exists(self.session_path):
            os.makedirs(self.session_path)
        self.driver = None
        self.is_connected = False

    def start_driver(self, headless=True):
        if self.driver:
            return True, "Running"
            
        options = Options()
        if headless:
            options.add_argument("--headless=new")
        
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--remote-allow-origins=*")
        options.add_argument(f"user-data-dir={self.session_path}")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")

        # Cloud Binary Finder
        bin_path = shutil.which("chromium-browser") or shutil.which("chromium") or shutil.which("google-chrome")
        if bin_path: options.binary_location = bin_path

        try:
            # Try Default System Driver
            self.driver = webdriver.Chrome(options=options)
            self.driver.get("https://web.whatsapp.com")
            return True, "Success"
        except:
            try:
                # Fallback to Manager
                srv = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=srv, options=options)
                self.driver.get("https://web.whatsapp.com")
                return True, "Success"
            except Exception as e:
                self.driver = None
                return False, str(e)

    def get_status(self):
        if not self.driver: return "Disconnected"
        try:
            self.driver.find_element(By.XPATH, '//*[@id="side"]')
            self.is_connected = True
            return "Connected"
        except:
            try:
                WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "canvas")))
                self.is_connected = False
                return "Awaiting Login"
            except: return "Loading..."

    def get_qr_base64(self):
        if not self.driver: return None
        try:
            canvas = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "canvas")))
            return canvas.screenshot_as_base64
        except: return None

    def send_message(self, phone, message):
        if not self.is_connected or not self.driver: return False, "No Connection"
        try:
            self.driver.get(f"https://web.whatsapp.com/send?phone={phone.lstrip('+')}&text={message}")
            btn = WebDriverWait(self.driver, 35).until(EC.element_to_be_clickable((By.XPATH, '//span[@data-icon="send"]')))
            btn.click()
            time.sleep(2)
            return True, "Sent"
        except Exception as e: return False, str(e)

    def close(self):
        if self.driver:
            try: self.driver.quit()
            except: pass
            self.driver = None
