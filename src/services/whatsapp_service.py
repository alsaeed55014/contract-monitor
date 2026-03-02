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
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class WhatsAppService:
    def __init__(self, session_path="wd_session"):
        self.session_path = os.path.abspath(session_path)
        if not os.path.exists(self.session_path):
            os.makedirs(self.session_path)
        
        self.driver = None
        self.is_connected = False
        self.last_qr = None

    def start_driver(self, headless=True):
        if self.driver:
            return True, "Driver already running"
            
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless=new")
        
        # Robust Cloud Compatibility Settings
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--remote-allow-origins=*")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(f"user-data-dir={self.session_path}")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")

        # Automatically find chromium path on Streamlit Cloud
        chrome_path = shutil.which("chromium-browser") or shutil.which("chromium") or shutil.which("google-chrome")
        if chrome_path:
            chrome_options.binary_location = chrome_path

        try:
            # Try to start using standard manager
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.get("https://web.whatsapp.com")
            return True, "Success"
        except Exception as e:
            # Fallback if manager fails (Common on Linux/Cloud)
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
                self.driver.get("https://web.whatsapp.com")
                return True, "Success"
            except Exception as e2:
                print(f"FAILED TO START DRIVER: {str(e2)}")
                return False, f"Could not find Chrome/Chromium. Please add 'packages.txt'. Error: {str(e2)}"

    def get_status(self):
        if not self.driver:
            return "Disconnected"
        try:
            self.driver.find_element(By.XPATH, '//*[@id="side"]')
            self.is_connected = True
            return "Connected"
        except:
            try:
                WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "canvas")))
                self.is_connected = False
                return "Awaiting Login"
            except:
                return "Loading..."

    def get_qr_base64(self):
        if not self.driver: return None
        try:
            qr_canvas = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "canvas")))
            return qr_canvas.screenshot_as_base64
        except: return None

    def send_message(self, phone, message):
        if not self.is_connected or not self.driver:
            return False, "Not connected"
        try:
            clean_phone = phone.lstrip('+')
            url = f"https://web.whatsapp.com/send?phone={clean_phone}&text={message}"
            self.driver.get(url)
            send_btn = WebDriverWait(self.driver, 35).until(EC.element_to_be_clickable((By.XPATH, '//span[@data-icon="send"]')))
            send_btn.click()
            time.sleep(3)
            return True, "Success"
        except Exception as e:
            return False, str(e)

    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
