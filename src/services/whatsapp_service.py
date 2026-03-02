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
        if not os.path.exists(self.session_path): os.makedirs(self.session_path)
        self.driver = None
        self.is_connected = False

    def start_driver(self, headless=True):
        if self.driver: return True, "Running"
        shutil.rmtree(self.session_path, ignore_errors=True) # Clear old session to force fresh QR
        os.makedirs(self.session_path)
        
        opts = Options()
        if headless: opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1600,1200") # Larger window for better rendering
        opts.add_argument("--force-device-scale-factor=2.0") # Sharper Text/Images
        opts.add_argument("--high-dpi-support=1")
        opts.add_argument(f"user-data-dir={self.session_path}")
        opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")

        bin_path = shutil.which("chromium-browser") or shutil.which("chromium") or shutil.which("google-chrome")
        if bin_path: opts.binary_location = bin_path

        try:
            self.driver = webdriver.Chrome(options=opts)
            self.driver.get("https://web.whatsapp.com")
            return True, "Done"
        except Exception as e:
            try:
                srv = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=srv, options=opts)
                self.driver.get("https://web.whatsapp.com")
                return True, "Done"
            except: 
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
                self.driver.find_element(By.CSS_SELECTOR, "canvas")
                self.is_connected = False
                return "Awaiting Login"
            except: return "Loading..."

    def get_qr_hd(self):
        """Ultra-Sharp QR Capture using Javascript bridge."""
        if not self.driver: return None
        try:
            # Injecting JS to ensure canvas is at maximum contrast
            script = """
            var canvas = document.querySelector('canvas');
            if(canvas) {
                return canvas.toDataURL('image/png', 1.0);
            }
            return null;
            """
            return self.driver.execute_script(script)
        except: return None

    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
