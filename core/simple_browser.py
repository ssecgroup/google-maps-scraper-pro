"""
Simple browser manager as fallback
"""

import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent
from colorama import Fore, Style
from typing import Optional, Dict, Any

class SimpleBrowserManager:
    """Simple browser manager as fallback"""
    
    def __init__(self, config: Dict[str, Any], proxy_rotator=None):
        self.config = config
        self.driver = None
        self.setup_logging()
        
    def setup_logging(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def start_browser(self):
        """Start simple browser"""
        try:
            self.logger.info(f"{Fore.GREEN}Starting simple browser...")
            
            options = Options()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-notifications')
            options.add_argument('--ignore-certificate-errors')
            
            # Random user agent
            options.add_argument(f'user-agent={UserAgent().random}')
            
            # Headless mode
            if self.config['advanced_settings'].get('headless', False):
                options.add_argument('--headless=new')
            
            # Use webdriver-manager
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            
            self.logger.info(f"{Fore.GREEN}✓ Simple browser started")
            return self.driver
            
        except Exception as e:
            self.logger.error(f"{Fore.RED}Failed to start browser: {str(e)}")
            raise
    
    def handle_captcha(self) -> bool:
        """Simple captcha check"""
        try:
            captcha_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'captcha')]")
            if captcha_elements:
                self.logger.warning("Captcha detected!")
                time.sleep(10)
            return True
        except:
            return True
    
    def close_browser(self):
        """Close browser"""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info(f"{Fore.GREEN}Browser closed")
            except:
                pass
    
    def __enter__(self):
        self.start_browser()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_browser()
