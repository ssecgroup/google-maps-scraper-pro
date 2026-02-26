"""
Advanced Captcha Detector and Solver Module
Supports multiple captcha types and solving services
"""

import re
import time
import logging
import base64
import json
import requests
from typing import Optional, Dict, List, Tuple, Any
from io import BytesIO
from PIL import Image
import numpy as np
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import cv2
import pytesseract
from urllib.parse import urlparse, parse_qs
import hashlib
from datetime import datetime
import os

class CaptchaDetector:
    """Detects various types of captchas on web pages"""
    
    def __init__(self, driver=None):
        self.driver = driver
        self.logger = logging.getLogger(__name__)
        
        # Captcha patterns
        self.captcha_patterns = {
            'recaptcha_v2': [
                'google.com/recaptcha/api2',
                'recaptcha',
                'g-recaptcha',
                'data-sitekey',
                'recaptcha-token'
            ],
            'recaptcha_v3': [
                'recaptcha/api.js',
                'render=explicit',
                'recaptcha-v3'
            ],
            'hcaptcha': [
                'hcaptcha.com',
                'h-captcha',
                'data-hcaptcha',
                'hcaptcha-token'
            ],
            'image_captcha': [
                'captcha.png',
                'captcha.jpg',
                'captcha-image',
                'security-code',
                'verification-code'
            ],
            'text_captcha': [
                'enter the text',
                'type the characters',
                'security question',
                'verification question'
            ],
            'funcaptcha': [
                'funcaptcha',
                'arkoselabs',
                'arkose labs'
            ],
            'geetest': [
                'geetest',
                'gt.js',
                'slide-captcha'
            ],
            'turnstile': [
                'turnstile',
                'cf-turnstile',
                'cloudflare turnstile'
            ],
            'simple_math': [
                'what is',
                'solve the',
                'math problem',
                'calculate'
            ]
        }
        
        # CSS selectors for captcha elements
        self.captcha_selectors = {
            'recaptcha_v2': [
                'iframe[src*="recaptcha"]',
                '.g-recaptcha',
                'div[data-sitekey]',
                '#recaptcha'
            ],
            'recaptcha_v3': [
                'script[src*="recaptcha"][src*="render="]',
                '.grecaptcha-badge'
            ],
            'hcaptcha': [
                'iframe[src*="hcaptcha"]',
                '.h-captcha',
                'div[data-hcaptcha]'
            ],
            'image_captcha': [
                'img[src*="captcha"]',
                '#captcha-image',
                '.captcha-image',
                'img[alt*="captcha"]'
            ],
            'text_captcha': [
                'input[name*="captcha"]',
                'input[id*="captcha"]',
                '.captcha-input'
            ],
            'funcaptcha': [
                'iframe[src*="funcaptcha"]',
                'iframe[src*="arkoselabs"]'
            ],
            'geetest': [
                '.geetest',
                'div[class*="geetest"]',
                'script[src*="gt.js"]'
            ],
            'turnstile': [
                '.cf-turnstile',
                'div[class*="turnstile"]',
                'iframe[src*="turnstile"]'
            ]
        }
        
    def detect(self, page_source: str = None, driver=None) -> Dict[str, Any]:
        """Detect captcha type and details from page"""
        if driver:
            self.driver = driver
            
        result = {
            'detected': False,
            'captcha_type': None,
            'site_key': None,
            'url': None,
            'element': None,
            'confidence': 0,
            'details': {}
        }
        
        # Get page source if not provided
        if not page_source and self.driver:
            page_source = self.driver.page_source
        elif not page_source:
            return result
        
        # Check each captcha type
        for captcha_type, patterns in self.captcha_patterns.items():
            confidence = 0
            matched_patterns = []
            
            for pattern in patterns:
                if re.search(pattern, page_source, re.IGNORECASE):
                    confidence += 1
                    matched_patterns.append(pattern)
            
            if confidence > 0:
                confidence_score = (confidence / len(patterns)) * 100
                
                if confidence_score > result['confidence']:
                    result['detected'] = True
                    result['captcha_type'] = captcha_type
                    result['confidence'] = confidence_score
                    result['details']['patterns'] = matched_patterns
                    
                    # Extract site key if available
                    site_key = self.extract_site_key(page_source, captcha_type)
                    if site_key:
                        result['site_key'] = site_key
        
        # Try to find the actual element
        if result['detected'] and self.driver:
            element = self.find_captcha_element(result['captcha_type'])
            if element:
                result['element'] = element
                result['url'] = self.driver.current_url
        
        return result
    
    def extract_site_key(self, page_source: str, captcha_type: str) -> Optional[str]:
        """Extract site key from page source"""
        
        patterns = {
            'recaptcha_v2': [
                r'data-sitekey=["\']([^"\']+)["\']',
                r'?k=([^&"\']+)',
                r'sitekey=([^&\s"\']+)'
            ],
            'recaptcha_v3': [
                r'render=["\']([^"\']+)["\']',
                r'sitekey=([^&\s"\']+)'
            ],
            'hcaptcha': [
                r'data-sitekey=["\']([^"\']+)["\']',
                r'sitekey=([^&\s"\']+)'
            ],
            'funcaptcha': [
                r'data-pkey=["\']([^"\']+)["\']',
                r'public_key=([^&\s"\']+)'
            ],
            'geetest': [
                r'gt=([^&\s"\']+)',
                r'challenge=([^&\s"\']+)'
            ],
            'turnstile': [
                r'data-sitekey=["\']([^"\']+)["\']',
                r'sitekey=([^&\s"\']+)'
            ]
        }
        
        type_patterns = patterns.get(captcha_type, [])
        
        for pattern in type_patterns:
            match = re.search(pattern, page_source)
            if match:
                return match.group(1)
        
        return None
    
    def find_captcha_element(self, captcha_type: str) -> Optional[WebElement]:
        """Find the captcha element on the page"""
        if not self.driver:
            return None
        
        selectors = self.captcha_selectors.get(captcha_type, [])
        
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    return elements[0]
            except:
                continue
        
        return None
    
    def is_captcha_present(self) -> bool:
        """Quick check if any captcha is present"""
        result = self.detect()
        return result['detected']
    
    def get_captcha_image(self, element: WebElement = None) -> Optional[bytes]:
        """Get captcha image as bytes"""
        if not element and self.driver:
            # Try to find image captcha
            result = self.detect()
            if result['captcha_type'] == 'image_captcha' and result['element']:
                element = result['element']
        
        if not element:
            return None
        
        try:
            # Get image URL or take screenshot
            if element.tag_name == 'img':
                img_url = element.get_attribute('src')
                if img_url:
                    response = requests.get(img_url, timeout=10)
                    if response.status_code == 200:
                        return response.content
            
            # Fallback: take screenshot of element
            screenshot = element.screenshot_as_png
            return screenshot
            
        except Exception as e:
            self.logger.error(f"Error getting captcha image: {str(e)}")
            return None

class CaptchaSolver:
    """Solves various types of captchas using multiple services"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.detector = CaptchaDetector()
        
        # API keys
        self.twocaptcha_key = self.config.get('twocaptcha_key') or os.getenv('TWOCAPTCHA_API_KEY')
        self.anti_captcha_key = self.config.get('anti_captcha_key') or os.getenv('ANTI_CAPTCHA_API_KEY')
        self.capsolver_key = self.config.get('capsolver_key') or os.getenv('CAPSOLVER_API_KEY')
        
        # Settings
        self.default_timeout = self.config.get('solver_timeout', 120)
        self.polling_interval = self.config.get('polling_interval', 5)
        self.use_ocr = self.config.get('use_ocr', True)
        
        # Initialize OCR if available
        if self.use_ocr:
            try:
                pytesseract.get_tesseract_version()
                self.ocr_available = True
            except:
                self.ocr_available = False
                self.logger.warning("Tesseract OCR not installed. OCR captcha solving disabled.")
        
        # Cache for solved captchas (avoid re-solving)
        self.solution_cache = {}
        self.cache_ttl = 3600  # 1 hour
        
    def solve(self, driver=None, captcha_type: str = None, **kwargs) -> Optional[str]:
        """Solve captcha - main entry point"""
        
        # Detect captcha if not specified
        if not captcha_type and driver:
            detection = self.detector.detect(driver=driver)
            if not detection['detected']:
                self.logger.warning("No captcha detected")
                return None
            captcha_type = detection['captcha_type']
            kwargs['site_key'] = detection.get('site_key')
            kwargs['url'] = detection.get('url') or driver.current_url
            kwargs['element'] = detection.get('element')
        
        self.logger.info(f"Solving {captcha_type} captcha...")
        
        # Check cache
        cache_key = self.get_cache_key(captcha_type, kwargs)
        if cache_key in self.solution_cache:
            cache_time, solution = self.solution_cache[cache_key]
            if time.time() - cache_time < self.cache_ttl:
                self.logger.info("Using cached captcha solution")
                return solution
        
        # Route to appropriate solver
        solvers = {
            'recaptcha_v2': self.solve_recaptcha_v2,
            'recaptcha_v3': self.solve_recaptcha_v3,
            'hcaptcha': self.solve_hcaptcha,
            'image_captcha': self.solve_image_captcha,
            'text_captcha': self.solve_text_captcha,
            'funcaptcha': self.solve_funcaptcha,
            'geetest': self.solve_geetest,
            'turnstile': self.solve_turnstile,
            'simple_math': self.solve_math_captcha
        }
        
        solver = solvers.get(captcha_type)
        if not solver:
            self.logger.error(f"Unsupported captcha type: {captcha_type}")
            return None
        
        try:
            solution = solver(**kwargs)
            
            # Cache solution
            if solution:
                self.solution_cache[cache_key] = (time.time(), solution)
            
            return solution
            
        except Exception as e:
            self.logger.error(f"Captcha solving failed: {str(e)}")
            return None
    
    def solve_recaptcha_v2(self, site_key: str, url: str, **kwargs) -> Optional[str]:
        """Solve reCAPTCHA v2"""
        
        # Try 2captcha first
        if self.twocaptcha_key:
            try:
                # Create task
                response = requests.post('https://2captcha.com/in.php', data={
                    'key': self.twocaptcha_key,
                    'method': 'userrecaptcha',
                    'googlekey': site_key,
                    'pageurl': url,
                    'json': 1
                })
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 1:
                        captcha_id = data['request']
                        
                        # Wait for solution
                        for _ in range(self.default_timeout // self.polling_interval):
                            time.sleep(self.polling_interval)
                            
                            result = requests.get('https://2captcha.com/res.php', params={
                                'key': self.twocaptcha_key,
                                'action': 'get',
                                'id': captcha_id,
                                'json': 1
                            })
                            
                            if result.status_code == 200:
                                data = result.json()
                                if data.get('status') == 1:
                                    self.logger.info("reCAPTCHA v2 solved with 2captcha")
                                    return data['request']
                                elif data.get('request') == 'CAPCHA_NOT_READY':
                                    continue
                                else:
                                    break
                                    
            except Exception as e:
                self.logger.error(f"2captcha error: {str(e)}")
        
        # Try capsolver
        if self.capsolver_key:
            return self.solve_with_capsolver('ReCaptchaV2Task', {
                'websiteURL': url,
                'websiteKey': site_key
            })
        
        # Try anti-captcha
        if self.anti_captcha_key:
            return self.solve_with_anticaptcha('NoCaptchaTaskProxyless', {
                'websiteURL': url,
                'websiteKey': site_key
            })
        
        return None
    
    def solve_recaptcha_v3(self, site_key: str, url: str, action: str = 'verify', 
                          min_score: float = 0.3, **kwargs) -> Optional[str]:
        """Solve reCAPTCHA v3"""
        
        if self.capsolver_key:
            return self.solve_with_capsolver('ReCaptchaV3Task', {
                'websiteURL': url,
                'websiteKey': site_key,
                'pageAction': action,
                'minScore': min_score
            })
        
        if self.twocaptcha_key:
            # 2captcha v3 support
            response = requests.post('https://2captcha.com/in.php', data={
                'key': self.twocaptcha_key,
                'method': 'userrecaptcha',
                'version': 'v3',
                'googlekey': site_key,
                'pageurl': url,
                'action': action,
                'min_score': min_score,
                'json': 1
            })
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 1:
                    captcha_id = data['request']
                    
                    for _ in range(self.default_timeout // self.polling_interval):
                        time.sleep(self.polling_interval)
                        
                        result = requests.get('https://2captcha.com/res.php', params={
                            'key': self.twocaptcha_key,
                            'action': 'get',
                            'id': captcha_id,
                            'json': 1
                        })
                        
                        if result.status_code == 200:
                            data = result.json()
                            if data.get('status') == 1:
                                return data['request']
        
        return None
    
    def solve_hcaptcha(self, site_key: str, url: str, **kwargs) -> Optional[str]:
        """Solve hCaptcha"""
        
        if self.capsolver_key:
            return self.solve_with_capsolver('HCaptchaTask', {
                'websiteURL': url,
                'websiteKey': site_key
            })
        
        if self.twocaptcha_key:
            response = requests.post('https://2captcha.com/in.php', data={
                'key': self.twocaptcha_key,
                'method': 'hcaptcha',
                'sitekey': site_key,
                'pageurl': url,
                'json': 1
            })
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 1:
                    captcha_id = data['request']
                    
                    for _ in range(self.default_timeout // self.polling_interval):
                        time.sleep(self.polling_interval)
                        
                        result = requests.get('https://2captcha.com/res.php', params={
                            'key': self.twocaptcha_key,
                            'action': 'get',
                            'id': captcha_id,
                            'json': 1
                        })
                        
                        if result.status_code == 200:
                            data = result.json()
                            if data.get('status') == 1:
                                return data['request']
        
        return None
    
    def solve_image_captcha(self, image_data: bytes = None, element: WebElement = None, 
                           **kwargs) -> Optional[str]:
        """Solve image-based captcha"""
        
        # Get image data if not provided
        if not image_data and element:
            image_data = self.detector.get_captcha_image(element)
        
        if not image_data:
            return None
        
        # Try OCR first
        if self.use_ocr and self.ocr_available:
            try:
                # Preprocess image
                image = Image.open(BytesIO(image_data))
                
                # Convert to OpenCV format
                cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                
                # Preprocessing pipeline
                processed = self.preprocess_image(cv_image)
                
                # Perform OCR with multiple configs
                configs = [
                    '--psm 8 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                    '--psm 8 -c tessedit_char_whitelist=0123456789abcdefghijklmnopqrstuvwxyz',
                    '--psm 8'
                ]
                
                for config in configs:
                    text = pytesseract.image_to_string(processed, config=config)
                    text = text.strip().replace(' ', '').upper()
                    
                    if text and len(text) >= 4 and len(text) <= 8:
                        self.logger.info(f"OCR solved captcha: {text}")
                        return text
                        
            except Exception as e:
                self.logger.debug(f"OCR failed: {str(e)}")
        
        # Try 2captcha
        if self.twocaptcha_key:
            try:
                # Encode image
                encoded = base64.b64encode(image_data).decode('utf-8')
                
                response = requests.post('https://2captcha.com/in.php', data={
                    'key': self.twocaptcha_key,
                    'method': 'base64',
                    'body': encoded,
                    'json': 1
                })
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 1:
                        captcha_id = data['request']
                        
                        for _ in range(self.default_timeout // self.polling_interval):
                            time.sleep(self.polling_interval)
                            
                            result = requests.get('https://2captcha.com/res.php', params={
                                'key': self.twocaptcha_key,
                                'action': 'get',
                                'id': captcha_id,
                                'json': 1
                            })
                            
                            if result.status_code == 200:
                                data = result.json()
                                if data.get('status') == 1:
                                    return data['request']
                                    
            except Exception as e:
                self.logger.error(f"2captcha image solve failed: {str(e)}")
        
        return None
    
    def solve_text_captcha(self, question: str = None, element: WebElement = None, 
                          **kwargs) -> Optional[str]:
        """Solve text-based captcha questions"""
        
        # Get question from element if not provided
        if not question and element:
            question = element.text
        elif not question:
            return None
        
        # Common math patterns
        math_patterns = [
            (r'what is (\d+)\s*\+\s*(\d+)', lambda m: str(int(m.group(1)) + int(m.group(2)))),
            (r'what is (\d+)\s*\-\s*(\d+)', lambda m: str(int(m.group(1)) - int(m.group(2)))),
            (r'what is (\d+)\s*\*\s*(\d+)', lambda m: str(int(m.group(1)) * int(m.group(2)))),
            (r'what is (\d+)\s*\/\s*(\d+)', lambda m: str(int(m.group(1)) // int(m.group(2)))),
            (r'(\d+)\s*\+\s*(\d+)\s*=', lambda m: str(int(m.group(1)) + int(m.group(2)))),
            (r'(\d+)\s*\-\s*(\d+)\s*=', lambda m: str(int(m.group(1)) - int(m.group(2)))),
        ]
        
        for pattern, calculator in math_patterns:
            match = re.search(pattern, question, re.IGNORECASE)
            if match:
                return calculator(match)
        
        # Word patterns
        word_patterns = {
            r'type the word ["\']?(\w+)["\']?': lambda m: m.group(1),
            r'enter the text:?\s*["\']?(\w+)["\']?': lambda m: m.group(1),
            r'what color is the sky': lambda m: 'blue',
            r'what color is grass': lambda m: 'green',
            r'what is the capital of france': lambda m: 'paris',
            r'what is the capital of usa': lambda m: 'washington',
        }
        
        for pattern, answer_func in word_patterns.items():
            if re.search(pattern, question, re.IGNORECASE):
                return answer_func(None)
        
        return None
    
    def solve_math_captcha(self, question: str = None, **kwargs) -> Optional[str]:
        """Simple math captcha solver"""
        return self.solve_text_captcha(question, **kwargs)
    
    def solve_funcaptcha(self, public_key: str, url: str, **kwargs) -> Optional[str]:
        """Solve FunCaptcha (Arkose Labs)"""
        
        if self.capsolver_key:
            return self.solve_with_capsolver('FunCaptchaTask', {
                'websiteURL': url,
                'websitePublicKey': public_key
            })
        
        if self.twocaptcha_key:
            response = requests.post('https://2captcha.com/in.php', data={
                'key': self.twocaptcha_key,
                'method': 'funcaptcha',
                'publickey': public_key,
                'pageurl': url,
                'json': 1
            })
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 1:
                    captcha_id = data['request']
                    
                    for _ in range(self.default_timeout // self.polling_interval):
                        time.sleep(self.polling_interval)
                        
                        result = requests.get('https://2captcha.com/res.php', params={
                            'key': self.twocaptcha_key,
                            'action': 'get',
                            'id': captcha_id,
                            'json': 1
                        })
                        
                        if result.status_code == 200:
                            data = result.json()
                            if data.get('status') == 1:
                                return data['request']
        
        return None
    
    def solve_geetest(self, gt: str, challenge: str, url: str, **kwargs) -> Optional[Dict]:
        """Solve Geetest captcha"""
        
        if self.capsolver_key:
            result = self.solve_with_capsolver('GeeTestTask', {
                'websiteURL': url,
                'gt': gt,
                'challenge': challenge
            })
            
            if result and isinstance(result, str):
                try:
                    return json.loads(result)
                except:
                    pass
        
        if self.twocaptcha_key:
            response = requests.post('https://2captcha.com/in.php', data={
                'key': self.twocaptcha_key,
                'method': 'geetest',
                'gt': gt,
                'challenge': challenge,
                'pageurl': url,
                'json': 1
            })
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 1:
                    captcha_id = data['request']
                    
                    for _ in range(self.default_timeout // self.polling_interval):
                        time.sleep(self.polling_interval)
                        
                        result = requests.get('https://2captcha.com/res.php', params={
                            'key': self.twocaptcha_key,
                            'action': 'get',
                            'id': captcha_id,
                            'json': 1
                        })
                        
                        if result.status_code == 200:
                            data = result.json()
                            if data.get('status') == 1:
                                return data['request']
        
        return None
    
    def solve_turnstile(self, site_key: str, url: str, **kwargs) -> Optional[str]:
        """Solve Cloudflare Turnstile captcha"""
        
        if self.capsolver_key:
            return self.solve_with_capsolver('TurnstileTask', {
                'websiteURL': url,
                'websiteKey': site_key
            })
        
        return None
    
    def solve_with_capsolver(self, task_type: str, task_data: Dict) -> Optional[str]:
        """Solve captcha using capsolver.com"""
        
        if not self.capsolver_key:
            return None
        
        try:
            # Create task
            response = requests.post('https://api.capsolver.com/createTask', json={
                'clientKey': self.capsolver_key,
                'task': {
                    'type': task_type,
                    **task_data
                }
            })
            
            if response.status_code == 200:
                data = response.json()
                if data.get('errorId') == 0:
                    task_id = data['taskId']
                    
                    # Wait for solution
                    for _ in range(self.default_timeout // 3):
                        time.sleep(3)
                        
                        result = requests.post('https://api.capsolver.com/getTaskResult', json={
                            'clientKey': self.capsolver_key,
                            'taskId': task_id
                        })
                        
                        if result.status_code == 200:
                            data = result.json()
                            if data.get('errorId') == 0:
                                if data.get('status') == 'ready':
                                    solution = data['solution']
                                    
                                    # Extract token from solution
                                    if 'gRecaptchaResponse' in solution:
                                        return solution['gRecaptchaResponse']
                                    elif 'token' in solution:
                                        return solution['token']
                                    elif 'answer' in solution:
                                        return solution['answer']
                                    elif 'validate' in solution:
                                        return solution['validate']
                                    else:
                                        return json.dumps(solution)
        
        except Exception as e:
            self.logger.error(f"Capsolver error: {str(e)}")
        
        return None
    
    def solve_with_anticaptcha(self, task_type: str, task_data: Dict) -> Optional[str]:
        """Solve captcha using anti-captcha.com"""
        
        if not self.anti_captcha_key:
            return None
        
        try:
            # Create task
            response = requests.post('https://api.anti-captcha.com/createTask', json={
                'clientKey': self.anti_captcha_key,
                'task': {
                    'type': task_type,
                    **task_data
                }
            })
            
            if response.status_code == 200:
                data = response.json()
                if data.get('errorId') == 0:
                    task_id = data['taskId']
                    
                    # Wait for solution
                    for _ in range(self.default_timeout // 3):
                        time.sleep(3)
                        
                        result = requests.post('https://api.anti-captcha.com/getTaskResult', json={
                            'clientKey': self.anti_captcha_key,
                            'taskId': task_id
                        })
                        
                        if result.status_code == 200:
                            data = result.json()
                            if data.get('errorId') == 0:
                                if data.get('status') == 'ready':
                                    solution = data['solution']
                                    if 'gRecaptchaResponse' in solution:
                                        return solution['gRecaptchaResponse']
                                    elif 'token' in solution:
                                        return solution['token']
        
        except Exception as e:
            self.logger.error(f"Anti-captcha error: {str(e)}")
        
        return None
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for better OCR"""
        
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        
        # Adaptive thresholding
        thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY_INV, 11, 2)
        
        # Remove noise
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
        
        return cleaned
    
    def get_cache_key(self, captcha_type: str, kwargs: Dict) -> str:
        """Generate cache key for captcha solution"""
        # Create deterministic string from parameters
        param_str = f"{captcha_type}:"
        for key in sorted(kwargs.keys()):
            if key not in ['element', 'driver']:  # Exclude non-serializable objects
                param_str += f"{key}={kwargs.get(key)}|"
        
        return hashlib.md5(param_str.encode()).hexdigest()
    
    def inject_solution(self, driver, token: str, captcha_type: str = 'recaptcha_v2'):
        """Inject solved captcha token into page"""
        
        if captcha_type in ['recaptcha_v2', 'recaptcha_v3']:
            # Inject reCAPTCHA response
            script = f"""
                document.getElementById('g-recaptcha-response').innerHTML = '{token}';
                document.getElementById('g-recaptcha-response').style.display = 'block';
                
                // Trigger callback if exists
                if (typeof ___grecaptcha_cfg !== 'undefined') {{
                    for (let i = 0; i < ___grecaptcha_cfg.clients.length; i++) {{
                        if (___grecaptcha_cfg.clients[i] && 
                            typeof ___grecaptcha_cfg.clients[i].callback === 'function') {{
                            ___grecaptcha_cfg.clients[i].callback('{token}');
                        }}
                    }}
                }}
            """
            driver.execute_script(script)
            
        elif captcha_type == 'hcaptcha':
            script = f"""
                document.querySelector('[name="h-captcha-response"]').innerHTML = '{token}';
                if (typeof hcaptcha !== 'undefined') {{
                    hcaptcha.setResponse(token);
                }}
            """
            driver.execute_script(script)
        
        # Try to submit form
        try:
            submit_button = driver.find_element(By.CSS_SELECTOR, 'input[type="submit"], button[type="submit"]')
            submit_button.click()
        except:
            pass
        
        time.sleep(2)

class CaptchaHandler:
    """High-level captcha handler that combines detection and solving"""
    
    def __init__(self, driver=None, config: Dict = None):
        self.driver = driver
        self.config = config or {}
        self.detector = CaptchaDetector(driver)
        self.solver = CaptchaSolver(config)
        self.logger = logging.getLogger(__name__)
        
    def handle(self, driver=None) -> bool:
        """Handle any captcha on the current page"""
        
        if driver:
            self.driver = driver
            self.detector.driver = driver
        
        # Detect captcha
        detection = self.detector.detect(driver=self.driver)
        
        if not detection['detected']:
            return True  # No captcha to handle
        
        self.logger.info(f"Captcha detected: {detection['captcha_type']} (confidence: {detection['confidence']:.1f}%)")
        
        # Solve captcha
        solution = self.solver.solve(
            driver=self.driver,
            captcha_type=detection['captcha_type'],
            site_key=detection.get('site_key'),
            url=detection.get('url') or self.driver.current_url,
            element=detection.get('element')
        )
        
        if solution:
            self.logger.info("Captcha solved successfully")
            
            # Inject solution
            self.solver.inject_solution(self.driver, solution, detection['captcha_type'])
            
            # Verify if captcha is gone
            time.sleep(3)
            if not self.detector.is_captcha_present():
                return True
            
        self.logger.warning("Failed to solve captcha")
        return False
    
    def wait_for_captcha_solve(self, timeout: int = 120) -> bool:
        """Wait for captcha to be solved (useful for manual solving)"""
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if not self.detector.is_captcha_present():
                return True
            time.sleep(2)
        
        return False
    
    def bypass_captcha(self, url: str, site_key: str, captcha_type: str = 'recaptcha_v2') -> Optional[str]:
        """Bypass captcha without browser (direct API)"""
        
        return self.solver.solve(
            captcha_type=captcha_type,
            site_key=site_key,
            url=url
        )

# Example usage
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Example: Solve captcha using API
    solver = CaptchaSolver({
        'twocaptcha_key': 'YOUR_API_KEY',
        'capsolver_key': 'YOUR_API_KEY'
    })
    
    # Solve reCAPTCHA v2
    token = solver.solve_recaptcha_v2(
        site_key='6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-',
        url='https://www.google.com/recaptcha/api2/demo'
    )
    
    if token:
        print(f"Solved captcha: {token[:50]}...")
    else:
        print("Failed to solve captcha")
