import os
import time
import base64
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
            print("Driver already running.")
            return True, "Driver already running"
            
        print(f"Starting driver (Headless: {headless})...")
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless=new")
        
        chrome_options.add_argument(f"user-data-dir={self.session_path}")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--remote-allow-origins=*")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")

        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.get("https://web.whatsapp.com")
            print("Driver started successfully.")
            return True, "Success"
        except Exception as e:
            print(f"CRITICAL ERROR starting driver: {str(e)}")
            self.driver = None
            return False, str(e)

    def get_status(self):
        if not self.driver:
            return "Disconnected"
        
        try:
            # Check if chat list is visible (Logged in)
            self.driver.find_element(By.XPATH, '//*[@id="side"]')
            self.is_connected = True
            return "Connected"
        except (NoSuchElementException, Exception):
            # Check if QR is visible (Not logged in)
            try:
                # Give it a short wait for the canvas to render
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "canvas"))
                )
                self.is_connected = False
                return "Awaiting Login"
            except:
                # Might be still loading or error
                return "Loading..."

    def get_qr_base64(self):
        if not self.driver:
            return None
        
        try:
            # Wait for canvas to appear
            qr_canvas = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "canvas"))
            )
            # Take screenshot of the canvas
            return qr_canvas.screenshot_as_base64
        except:
            return None

    def send_message(self, phone, message, file_path=None):
        if not self.is_connected or not self.driver:
            return False, "Not connected"
            
        try:
            # WhatsApp URL for direct message
            # Remove + and lead with phone number
            clean_phone = phone.lstrip('+')
            url = f"https://web.whatsapp.com/send?phone={clean_phone}&text={message}"
            self.driver.get(url)
            
            # Wait for send button
            send_btn = WebDriverWait(self.driver, 30).until(
                EC.element_to_be_clickable((By.XPATH, '//span[@data-icon="send"]'))
            )
            
            # If there's a file, we need to handle attachment logic (complex)
            # For now, let's focus on text
            
            send_btn.click()
            time.sleep(2) # Wait for message to actually send
            return True, "Success"
        except Exception as e:
            return False, str(e)

    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
