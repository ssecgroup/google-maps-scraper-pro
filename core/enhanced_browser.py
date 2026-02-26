"""
Enhanced Browser Driver for Google Maps Scraper Pro 4.4
ULTIMATE EDITION - Anti-detection, Auto-recovery, Page Load Verification
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, SessionNotCreatedException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from fake_useragent import UserAgent
from colorama import Fore, Style
import time
import random
import logging
import os
import subprocess
import re
from typing import Optional, Dict, Any, List
import requests
import zipfile
import shutil
from collections import Counter

class EnhancedBrowserManager:
    """
    Professional browser manager with automatic version detection
    """
    
    def __init__(self, config: Dict[str, Any], proxy_rotator=None):
        self.config = config
        self.proxy_rotator = proxy_rotator
        self.driver = None
        self.setup_logging()
        self.browser_path = self.find_chromium_path()
        self.browser_version = self.get_browser_version()
        self.driver_path = self.setup_chromedriver()
        self.current_proxy = None
        
    def setup_logging(self):
        """Setup logging"""
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
    
    def find_chromium_path(self) -> Optional[str]:
        """Find Chromium browser path"""
        possible_paths = [
            '/usr/lib/chromium/chromium',
            '/usr/bin/chromium',
            '/usr/bin/chromium-browser',
            '/usr/bin/google-chrome',
            '/usr/bin/google-chrome-stable',
            '/snap/bin/chromium',
            '/snap/bin/chromium-browser',
            '/usr/local/bin/chromium',
            '/opt/google/chrome/chrome'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                self.logger.info(f"✓ Found browser at: {path}")
                return path
        
        # Try to find with 'which' command
        try:
            result = subprocess.run(['which', 'chromium'], capture_output=True, text=True)
            if result.returncode == 0:
                path = result.stdout.strip()
                if os.path.exists(path):
                    self.logger.info(f"✓ Found browser at: {path}")
                    return path
        except:
            pass
        
        self.logger.error("✗ Could not find Chromium browser")
        return None
    
    def get_browser_version(self) -> Optional[str]:
        """Get browser version"""
        if not self.browser_path:
            return None
        
        try:
            result = subprocess.run([self.browser_path, '--version'], capture_output=True, text=True)
            version_output = result.stdout.strip()
            
            # Extract version number
            match = re.search(r'(\d+\.\d+\.\d+\.\d+)', version_output)
            if match:
                version = match.group(1)
                self.logger.info(f"✓ Browser version: {version}")
                return version
            
            # Alternative format
            match = re.search(r'(\d+\.\d+\.\d+)', version_output)
            if match:
                version = match.group(1)
                self.logger.info(f"✓ Browser version: {version}")
                return version
                
        except Exception as e:
            self.logger.error(f"Could not get browser version: {e}")
        
        return None
    
    def get_major_version(self) -> int:
        """Get major version number"""
        if not self.browser_version:
            return 114  # Default fallback
        
        try:
            return int(self.browser_version.split('.')[0])
        except:
            return 114
    
    def setup_chromedriver(self) -> Optional[str]:
        """Setup correct ChromeDriver version"""
        major_version = self.get_major_version()
        self.logger.info(f"Setting up ChromeDriver for Chromium {major_version}")
        
        # Method 1: Try webdriver-manager with ChromeType.CHROMIUM
        try:
            self.logger.info("Method 1: Using webdriver-manager with ChromeType.CHROMIUM")
            driver_path = ChromeDriverManager(
                chrome_type=ChromeType.CHROMIUM
            ).install()
            self.logger.info(f"✓ ChromeDriver installed at: {driver_path}")
            return driver_path
        except Exception as e:
            self.logger.warning(f"Method 1 failed: {e}")
        
        # Method 2: Try with specific version
        try:
            self.logger.info(f"Method 2: Trying to get ChromeDriver {major_version}")
            
            # Try to get latest patch version for this major version
            response = requests.get(
                f"https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"
            )
            
            if response.status_code == 200:
                versions = response.json()['versions']
                # Find versions matching our major version
                matching = [v for v in versions if v['version'].startswith(f"{major_version}.")]
                
                if matching:
                    # Get the latest matching version
                    latest = matching[-1]
                    download_url = None
                    
                    # Find Linux64 download
                    for download in latest['downloads'].get('chromedriver', []):
                        if download['platform'] == 'linux64':
                            download_url = download['url']
                            break
                    
                    if download_url:
                        self.logger.info(f"Downloading ChromeDriver from: {download_url}")
                        
                        # Download and extract
                        zip_response = requests.get(download_url)
                        zip_path = '/tmp/chromedriver.zip'
                        
                        with open(zip_path, 'wb') as f:
                            f.write(zip_response.content)
                        
                        # Extract
                        extract_dir = f'/tmp/chromedriver_{major_version}'
                        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                            zip_ref.extractall(extract_dir)
                        
                        # Find chromedriver binary
                        for root, dirs, files in os.walk(extract_dir):
                            if 'chromedriver' in files:
                                driver_path = os.path.join(root, 'chromedriver')
                                os.chmod(driver_path, 0o755)
                                
                                # Copy to /usr/local/bin
                                dest_path = '/usr/local/bin/chromedriver'
                                shutil.copy2(driver_path, dest_path)
                                os.chmod(dest_path, 0o755)
                                
                                self.logger.info(f"✓ ChromeDriver {major_version} installed at: {dest_path}")
                                return dest_path
        except Exception as e:
            self.logger.warning(f"Method 2 failed: {e}")
        
        # Method 3: Use system chromedriver if available
        try:
            self.logger.info("Method 3: Checking system chromedriver")
            result = subprocess.run(['which', 'chromedriver'], capture_output=True, text=True)
            if result.returncode == 0:
                driver_path = result.stdout.strip()
                self.logger.info(f"✓ Found system chromedriver at: {driver_path}")
                return driver_path
        except:
            pass
        
        # Method 4: Fallback to webdriver-manager default
        try:
            self.logger.info("Method 4: Using webdriver-manager default")
            driver_path = ChromeDriverManager().install()
            self.logger.info(f"✓ ChromeDriver installed at: {driver_path}")
            return driver_path
        except Exception as e:
            self.logger.error(f"All methods failed: {e}")
        
        return None
    
    def get_options(self) -> Options:
        """Get Chrome options with proxy support"""
        options = Options()
        
        # Set browser binary path
        if self.browser_path:
            options.binary_location = self.browser_path
            self.logger.info(f"Using browser: {self.browser_path}")
        
        # Get proxy from rotator if available
        if self.proxy_rotator:
            self.current_proxy = self.proxy_rotator.get_proxy()
            if self.current_proxy:
                options.add_argument(f'--proxy-server={self.current_proxy}')
                self.logger.info(f"Using proxy: {self.current_proxy}")
        
        # Essential arguments
        essential_args = [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-extensions',
            '--disable-notifications',
            '--disable-popup-blocking',
            '--ignore-certificate-errors',
            '--disable-blink-features=AutomationControlled',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor',
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-logging',
            '--log-level=3',
            '--silent',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
        ]
        
        for arg in essential_args:
            options.add_argument(arg)
        
        # Random user agent
        try:
            ua = UserAgent()
            options.add_argument(f'user-agent={ua.random}')
        except:
            options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')
        
        # Window size
        options.add_argument('--window-size=1920,1080')
        
        # Language
        options.add_argument('--lang=en-US,en;q=0.9')
        
        # Headless mode
        if self.config.get('advanced_settings', {}).get('headless', False):
            options.add_argument('--headless=new')
        
        # Anti-detection preferences
        prefs = {
            'credentials_enable_service': False,
            'profile.password_manager_enabled': False,
            'profile.default_content_setting_values.notifications': 2,
            'profile.default_content_setting_values.images': 1,  # Load images
            'profile.default_content_setting_values.javascript': 1,  # Enable JS
        }
        options.add_experimental_option('prefs', prefs)
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        
        return options
    
    def start_browser(self) -> webdriver.Chrome:
        """Start browser with retry logic"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                self.logger.info(f"{Fore.GREEN}Starting browser (attempt {retry_count + 1}/{max_retries})...")
                
                options = self.get_options()
                
                if not self.driver_path:
                    raise Exception("No ChromeDriver path available")
                
                service = Service(self.driver_path)
                self.driver = webdriver.Chrome(service=service, options=options)
                
                self.driver.implicitly_wait(10)
                self.execute_stealth_scripts()
                
                self.logger.info(f"{Fore.GREEN}✓ Browser started successfully")
                return self.driver
                
            except SessionNotCreatedException as e:
                self.logger.error(f"{Fore.RED}Session not created: {str(e)}")
                self.logger.info("Attempting to fix ChromeDriver version...")
                
                # Clear cache and try to reinstall
                import shutil
                wdm_cache = os.path.expanduser('~/.wdm')
                if os.path.exists(wdm_cache):
                    shutil.rmtree(wdm_cache)
                
                # Try to reinstall driver
                self.driver_path = self.setup_chromedriver()
                retry_count += 1
                
            except Exception as e:
                self.logger.error(f"{Fore.RED}Failed to start browser: {str(e)}")
                retry_count += 1
                time.sleep(2)
        
        raise Exception(f"Failed to start browser after {max_retries} attempts")
    
    def execute_stealth_scripts(self):
        """Execute JavaScript to hide automation"""
        scripts = [
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            """,
            """
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            """,
            """
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            """,
            """
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            """,
            """
            // Override navigator properties
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });
            """,
            """
            // Add Chrome runtime
            window.chrome = {
                runtime: {}
            };
            """
        ]
        
        for script in scripts:
            try:
                self.driver.execute_script(script)
            except:
                pass
    
    def check_page_loaded(self) -> bool:
        """Check if page actually loaded (not showing data:,)"""
        try:
            # Check current URL
            current_url = self.driver.current_url
            if current_url == "data:," or not current_url:
                self.logger.error("❌ Page failed to load (data:,)")
                return False
            
            # Check if page has any content
            body = self.driver.find_element(By.TAG_NAME, 'body')
            if not body.text and len(self.driver.page_source) < 1000:
                self.logger.error("❌ Page loaded but has no content")
                return False
            
            # Check for captcha or blocked page
            page_source = self.driver.page_source.lower()
            if 'captcha' in page_source or 'unusual traffic' in page_source:
                self.logger.error("❌ Captcha or block detected")
                return False
            
            return True
        except Exception as e:
            self.logger.error(f"Error checking page load: {e}")
            return False
    
    def wait_for_element(self, by: str, value: str, timeout: int = 10) -> Optional[Any]:
        """Wait for element"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            return None
    
    def find_elements_safe(self, by: str, value: str) -> List[Any]:
        """Safely find elements"""
        try:
            return self.driver.find_elements(by, value)
        except:
            return []
    
    def safe_click(self, element, retries: int = 3) -> bool:
        """Safely click element"""
        for attempt in range(retries):
            try:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", 
                    element
                )
                time.sleep(0.5)
                element.click()
                return True
            except:
                if attempt == retries - 1:
                    try:
                        self.driver.execute_script("arguments[0].click();", element)
                        return True
                    except:
                        return False
                time.sleep(1)
        return False
    
    def handle_captcha(self) -> bool:
        """Check for captcha"""
        try:
            captcha_selectors = [
                "//iframe[contains(@src, 'recaptcha')]",
                "//div[contains(@class, 'g-recaptcha')]",
                "//*[contains(text(), 'captcha')]",
                "//*[contains(text(), 'CAPTCHA')]"
            ]
            
            for selector in captcha_selectors:
                elements = self.driver.find_elements(By.XPATH, selector)
                if elements:
                    self.logger.warning(f"{Fore.YELLOW}⚠ Captcha detected!")
                    print(f"{Fore.YELLOW}Please solve captcha manually. Waiting 30 seconds...")
                    time.sleep(30)
                    return False
            return True
        except:
            return True
    
    def wait_for_results_container(self, timeout: int = 20) -> Optional[Any]:
        """Wait for results container with multiple selectors"""
        
        # Try multiple container selectors
        container_selectors = [
            (By.CSS_SELECTOR, 'div[role="feed"]'),
            (By.CSS_SELECTOR, 'div[role="main"]'),
            (By.CSS_SELECTOR, '.m6QErb'),
            (By.XPATH, '//div[contains(@aria-label, "results")]'),
            (By.CSS_SELECTOR, '[class*="section-list"]'),
            (By.CSS_SELECTOR, '.Nv2PK'),
            (By.CSS_SELECTOR, 'div[jsaction*="mouseover"]'),
            (By.CSS_SELECTOR, '.hfpxzc'),
            (By.CSS_SELECTOR, '.THOPZb'),
        ]
        
        for by, selector in container_selectors:
            try:
                self.logger.debug(f"Trying container selector: {selector}")
                element = WebDriverWait(self.driver, timeout/2).until(
                    EC.presence_of_element_located((by, selector))
                )
                self.logger.info(f"✓ Found results container with: {selector}")
                return element
            except TimeoutException:
                continue
            except Exception as e:
                self.logger.debug(f"Error with selector {selector}: {str(e)}")
                continue
        
        self.logger.error("Could not find any results container")
        return None
    
    def get_business_cards(self) -> List[Any]:
        """Get business cards using multiple selectors"""
        selectors = [
            (By.CSS_SELECTOR, 'div[role="article"]'),
            (By.CSS_SELECTOR, 'a[href*="maps/place"]'),
            (By.CSS_SELECTOR, '[data-place-id]'),
            (By.CSS_SELECTOR, '.hfpxzc'),
            (By.CSS_SELECTOR, '.Nv2PK'),
            (By.CSS_SELECTOR, '.THOPZb'),
            (By.CSS_SELECTOR, 'div[role="feed"] > div > div'),
            (By.XPATH, '//a[contains(@href, "maps/place")]'),
            (By.CSS_SELECTOR, '.m6QErb .NrDZNb'),
            (By.CSS_SELECTOR, '.qBF1Pd'),
            (By.CSS_SELECTOR, '.lI9IFe'),
        ]
        
        all_elements = []
        
        for by, selector in selectors:
            try:
                elements = self.driver.find_elements(by, selector)
                if elements:
                    valid_elements = []
                    for elem in elements:
                        try:
                            if elem.is_displayed() and elem.text and len(elem.text.strip()) > 3:
                                valid_elements.append(elem)
                        except:
                            continue
                    
                    if valid_elements:
                        self.logger.debug(f"Found {len(valid_elements)} cards with: {selector}")
                        all_elements.extend(valid_elements)
            except:
                continue
        
        # Remove duplicates
        seen = set()
        unique_elements = []
        for elem in all_elements:
            try:
                elem_id = elem.id if hasattr(elem, 'id') else str(hash(elem.text[:50]))
                if elem_id not in seen:
                    seen.add(elem_id)
                    unique_elements.append(elem)
            except:
                unique_elements.append(elem)
        
        return unique_elements[:50]
    
    def extract_business_details(self) -> Dict[str, Any]:
        """Extract ALL business details including premium fields"""
        details = {
            'name': None,
            'phone': None,
            'website': None,
            'address': None,
            'category': None,
            'rating': None,
            'reviews': None,
            'featured_review': None,
            'keywords': [],
            'popular_dishes': [],
            'atmosphere_keywords': [],
            'owner_response': None,
            'sentiment_score': None,
            'plus_code': None,
            'place_id': None,
            'latitude': None,
            'longitude': None,
            'description': None,
            'hours': None,
            'hours_table': [],
            'services': [],
            'payment_methods': [],
            'price_range': None,
            'parking': None,
            'wheelchair_accessible': None,
            'wifi': None,
            'outdoor_seating': None,
            'takeaway': None,
            'delivery': None,
            'scraped_at': time.time()
        }
        
        current_url = self.driver.current_url
        
        # Check if we're on a place page
        if '/maps/place/' not in current_url:
            return details
        
        # Name extraction
        name_selectors = [
            'h1.DUwDvf', 'h1.lfPIob', '.DUwDvf', '.lfPIob',
            'h1.fontHeadlineLarge', '.fontHeadlineLarge',
            'div[role="main"] h1',
        ]
        
        for selector in name_selectors:
            try:
                if selector.startswith('//'):
                    elems = self.driver.find_elements(By.XPATH, selector)
                else:
                    elems = self.driver.find_elements(By.CSS_SELECTOR, selector)
                
                for elem in elems:
                    if elem and elem.text.strip():
                        name_text = elem.text.strip()
                        if name_text and name_text not in ["Results", "Search", "Google Maps"] and len(name_text) > 2:
                            details['name'] = name_text
                            break
                if details['name']:
                    break
            except:
                continue
        
        # Phone extraction
        phone_selectors = [
            'button[data-item-id*="phone"]',
            'a[href^="tel:"]',
            '//button[contains(@aria-label, "phone")]',
        ]
        
        for selector in phone_selectors:
            try:
                if selector.startswith('//'):
                    elems = self.driver.find_elements(By.XPATH, selector)
                else:
                    elems = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elems:
                    text = elems[0].text.strip()
                    href = elems[0].get_attribute('href') or ''
                    
                    if text and any(c.isdigit() for c in text):
                        details['phone'] = text
                    elif 'tel:' in href:
                        details['phone'] = href.replace('tel:', '').split('?')[0]
                    break
            except:
                continue
        
        # Website extraction
        website_selectors = [
            'a[data-item-id*="authority"]',
            'a[href^="http"]:not([href*="google"])',
            '//a[contains(@href, "http") and not(contains(@href, "google"))]',
        ]
        
        for selector in website_selectors:
            try:
                if selector.startswith('//'):
                    elems = self.driver.find_elements(By.XPATH, selector)
                else:
                    elems = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elems:
                    href = elems[0].get_attribute('href')
                    if href and not href.startswith('https://www.google.com'):
                        details['website'] = href
                        break
            except:
                continue
        
        # Address extraction
        address_selectors = [
            'button[data-item-id*="address"]',
            '//button[contains(@aria-label, "address")]',
            'div[class*="rogA2c"]',
        ]
        
        for selector in address_selectors:
            try:
                if selector.startswith('//'):
                    elems = self.driver.find_elements(By.XPATH, selector)
                else:
                    elems = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elems:
                    text = elems[0].text.strip() or ''
                    if text and len(text) > 5:
                        details['address'] = text
                        break
            except:
                continue
        
        # Rating extraction
        rating_selectors = [
            'div[class*="fontBodyMedium"] span[aria-hidden="true"]',
            '[role="img"][aria-label*="stars"]',
        ]
        
        for selector in rating_selectors:
            try:
                if selector.startswith('//'):
                    elems = self.driver.find_elements(By.XPATH, selector)
                else:
                    elems = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elems:
                    text = elems[0].text.strip() or ''
                    numbers = re.findall(r'(\d+\.?\d*)', text)
                    if numbers:
                        details['rating'] = float(numbers[0])
                        break
            except:
                continue
        
        # Reviews count extraction
        reviews_selectors = [
            'button[aria-label*="reviews"]',
            '//button[contains(@aria-label, "review")]',
        ]
        
        for selector in reviews_selectors:
            try:
                if selector.startswith('//'):
                    elems = self.driver.find_elements(By.XPATH, selector)
                else:
                    elems = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elems:
                    text = elems[0].text.strip() or ''
                    numbers = re.findall(r'(\d+)', text.replace(',', ''))
                    if numbers:
                        details['reviews'] = int(numbers[0])
                        break
            except:
                continue
        
        # Category extraction
        category_selectors = [
            'button[jsaction*="category"]',
            '//button[contains(@class, "category")]',
        ]
        
        for selector in category_selectors:
            try:
                if selector.startswith('//'):
                    elems = self.driver.find_elements(By.XPATH, selector)
                else:
                    elems = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elems and elems[0].text.strip():
                    details['category'] = elems[0].text.strip()
                    break
            except:
                continue
        
        # Price range extraction
        try:
            price_selectors = [
                'span[class*="price"]',
                '[aria-label*="price"]',
                '//span[contains(text(), "₹")]'
            ]
            for selector in price_selectors:
                if selector.startswith('//'):
                    elems = self.driver.find_elements(By.XPATH, selector)
                else:
                    elems = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elems and elems[0].text.strip():
                    details['price_range'] = elems[0].text.strip()
                    break
        except:
            pass
        
        # Wheelchair accessible
        try:
            accessible_selectors = [
                '[aria-label*="wheelchair"]',
                '[class*="accessible"]',
                '//div[contains(text(), "wheelchair")]'
            ]
            for selector in accessible_selectors:
                if selector.startswith('//'):
                    elems = self.driver.find_elements(By.XPATH, selector)
                else:
                    elems = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elems:
                    details['wheelchair_accessible'] = True
                    break
        except:
            pass
        
        # Place ID extraction
        try:
            if 'place/' in current_url:
                match = re.search(r'place/([^/]+)', current_url)
                if match:
                    details['place_id'] = match.group(1)
        except:
            pass
        
        # Coordinates extraction
        try:
            if '@' in current_url:
                coords_match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', current_url)
                if coords_match:
                    details['latitude'] = float(coords_match.group(1))
                    details['longitude'] = float(coords_match.group(2))
        except:
            pass
        
        return details
    
    def scroll_feed(self, feed_element) -> bool:
        """Scroll feed and return True if new content loaded"""
        try:
            old_height = self.driver.execute_script(
                "return arguments[0].scrollHeight", 
                feed_element
            )
            
            scroll_amount = random.randint(300, 700)
            self.driver.execute_script(
                "arguments[0].scrollTop += arguments[1];",
                feed_element, scroll_amount
            )
            
            time.sleep(random.uniform(1.5, 3.5))
            
            new_height = self.driver.execute_script(
                "return arguments[0].scrollHeight", 
                feed_element
            )
            
            return new_height > old_height
        except:
            return False
    
    def close_browser(self):
        """Close browser"""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info(f"{Fore.GREEN}✓ Browser closed")
            except:
                pass
    
    def __enter__(self):
        self.start_browser()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_browser()
