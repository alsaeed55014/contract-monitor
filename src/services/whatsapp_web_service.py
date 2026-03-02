import os
import time
import logging
import threading
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
import io
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WhatsAppWebService")

class WhatsAppWebService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(WhatsAppWebService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized: return
        self.driver = None
        self.qr_code_base64 = None
        self.is_connected = False
        self.last_error = None
        # Move session to a location without non-ASCII characters to avoid Chrome issues
        self.session_path = "C:\\whatsapp_automation_session"
        if not os.path.exists(self.session_path):
            os.makedirs(self.session_path)
        self._initialized = True

    def start_driver(self):
        """Starts the Selenium driver."""
        if self.driver:
            return

        chrome_options = Options()
        chrome_options.add_argument(f"--user-data-dir={self.session_path}")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        # Try headless to support servers, with window size
        chrome_options.add_argument("--headless=new") 
        chrome_options.add_argument("--window-size=1920,1080")
        # Add a real user agent to prevent "unsupported browser"
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            # Check for Streamlit Cloud (Linux) Environment
            if os.path.exists("/usr/bin/chromium"):
                chrome_options.binary_location = "/usr/bin/chromium"
                service = Service("/usr/bin/chromedriver")
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            elif os.path.exists("/usr/bin/google-chrome"):
                chrome_options.binary_location = "/usr/bin/google-chrome"
                service = Service("/usr/bin/chromedriver")
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                # Windows / Local Dev
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            self.driver.get("https://web.whatsapp.com")
            logger.info("WhatsApp Web engine started.")
            self.last_error = None
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Failed to start Chrome: {e}")
            self.driver = None

    def get_qr_status(self):
        """Checks the status of the connection and captures QR if needed."""
        if not self.driver:
            self.start_driver()
            if not self.driver: return "error", None

        try:
            # 1. Check if we are already logged in (look for chat list or search bar)
            search_bar = self.driver.find_elements(By.CSS_SELECTOR, "div[contenteditable='true']")
            chat_list = self.driver.find_elements(By.CSS_SELECTOR, "div[data-testid='chat-list']")
            if chat_list or search_bar:
                self.is_connected = True
                self.qr_code_base64 = None
                return "connected", None

            # 2. Look for QR code container
            qr_container = self.driver.find_elements(By.CSS_SELECTOR, "div[data-testid='qrcode']")
            if qr_container:
                # Capture the precise QR element
                qr_element = qr_container[0]
                qr_base64 = qr_element.screenshot_as_base64
                self.qr_code_base64 = qr_base64
                return "qr_ready", qr_base64
            
            # 3. Check for "Click to reload QR" button which often blocks progress
            reload_btn = self.driver.find_elements(By.XPATH, "//button[contains(., 'Click to reload QR')]")
            if reload_btn:
                reload_btn[0].click()
                time.sleep(1)
            
            return "loading", None
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Error checking QR status: {e}")
            return "loading", None

    def get_diagnostic_screenshot(self):
        """Captures a full-page screenshot for debugging purposes."""
        if not self.driver:
            return None
        try:
            return self.driver.screenshot_as_base64
        except Exception as e:
            logger.error(f"Failed to take diagnostic screenshot: {e}")
            return None

    def get_page_source(self):
        """Returns the current page HTML for deep debugging."""
        if not self.driver:
            return "Driver not started"
        return self.driver.page_source

    def send_message(self, phone, message):
        """Sends a message using the active WhatsApp Web session."""
        if not self.is_connected:
            return False, "WhatsApp not connected"

        try:
            # Format phone number
            clean_phone = "".join(filter(str.isdigit, str(phone)))
            url = f"https://web.whatsapp.com/send?phone={clean_phone}&text={message}"
            self.driver.get(url)
            
            # Wait for send button
            wait = WebDriverWait(self.driver, 20)
            send_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "span[data-testid='send']")))
            send_btn.click()
            
            # Wait a bit to ensure it's sent
            time.sleep(2)
            return True, "Message sent"
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False, str(e)

    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.is_connected = False
