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
from selenium.webdriver.common.keys import Keys

class WhatsAppService:
    def __init__(self, session_path="wd_session"):
        self.session_path = os.path.abspath(session_path)
        if not os.path.exists(self.session_path): os.makedirs(self.session_path)
        self.driver = None

    def start_driver(self, headless=True):
        if self.driver: return True, "Running"
        opts = Options()
        if headless: opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument(f"user-data-dir={self.session_path}")
        opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
        try:
            self.driver = webdriver.Chrome(options=opts)
            self.driver.get("https://web.whatsapp.com")
            return True, "Success"
        except:
            srv = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=srv, options=opts)
            self.driver.get("https://web.whatsapp.com")
            return True, "Success"

    def get_status(self):
        if not self.driver: return "Disconnected"
        try:
            self.driver.find_element(By.XPATH, '//*[@id="side"]')
            return "Connected"
        except:
            try:
                self.driver.find_element(By.CSS_SELECTOR, "canvas")
                return "Awaiting Login"
            except: return "Loading..."

    def get_qr_hd(self):
        try: return self.driver.execute_script("return document.querySelector('canvas').toDataURL()")
        except: return None

    def get_diagnostic_screenshot(self):
        """Hidden tool for Pasha to see what browser sees"""
        if not self.driver: return None
        try: return self.driver.get_screenshot_as_base64()
        except: return None

    def send_message(self, phone, message):
        """KEYBOARD EMULATION SEND - FOR PASHA"""
        if not self.driver: return False, "Driver Offline"
        try:
            clean_phone = str(phone).replace('+', '').replace(' ', '').replace('-', '').strip()
            # Navigate to direct link
            url = f"https://web.whatsapp.com/send?phone={clean_phone}&text={message}"
            self.driver.get(url)
            
            # Technique: Wait for EITHER the send button OR the input box
            wait = WebDriverWait(self.driver, 40)
            
            # Look for the footer/input area which means chat loaded
            input_box = wait.until(EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')))
            
            if input_box:
                time.sleep(2) # Stabilize
                # Final Strike: Send the ENTER key to the message box
                input_box.send_keys(Keys.ENTER)
                time.sleep(3) # Wait for flight
                return True, "Message Sent (via Enter)"
            
            return False, "Chat Box Not Found"
        except Exception as e:
            return False, f"Timeout: {str(e)[:20]}"

    def close(self):
        if self.driver: self.driver.quit(); self.driver = None
