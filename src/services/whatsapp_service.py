import os
import time
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
            return True, "Done"
        except:
            srv = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=srv, options=opts)
            self.driver.get("https://web.whatsapp.com")
            return True, "Done"

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

    def send_message(self, phone, message):
        """ULTRA ROBUST SEND FOR PASHA"""
        if not self.driver: return False, "No Driver"
        try:
            clean_phone = str(phone).replace('+', '').replace(' ', '').strip()
            # Direct link approach
            url = f"https://web.whatsapp.com/send?phone={clean_phone}&text={message}"
            self.driver.get(url)
            
            # Step 1: Wait for the app to load (checking for either send button or invalid number popup)
            wait = WebDriverWait(self.driver, 45)
            
            # XPaths for different versions of WhatsApp Web send button
            send_paths = [
                '//span[@data-icon="send"]',
                '//button[@aria-label="Send"]',
                '//button//span[@data-icon="send"]',
                '//*[@id="main"]/footer/div[1]/div/span[2]/div/div[2]/div[2]/button'
            ]
            
            send_btn = None
            for path in send_paths:
                try:
                    send_btn = wait.until(EC.element_to_be_clickable((By.XPATH, path)))
                    if send_btn: break
                except: continue
                
            if send_btn:
                # Direct click
                try: send_btn.click()
                except: 
                    # Force click via JS if obscured
                    self.driver.execute_script("arguments[0].click();", send_btn)
                
                time.sleep(3) # Wait to ensure it flies
                return True, "Success"
            else:
                # Check if "Phone number shared via url is invalid" popup exists
                if "invalid" in self.driver.page_source.lower():
                    return False, "Invalid Phone Number"
                return False, "Send Button Timeout (Page slow)"
                
        except Exception as e:
            return False, f"Error: {str(e)[:50]}"

    def close(self):
        if self.driver: self.driver.quit(); self.driver = None
