# core/smart_parser.py

import re
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class SmartParser:
    def __init__(self, driver=None):
        self.driver = driver
        self.name_patterns = self._get_name_patterns()
    
    def _get_name_patterns(self):
        """Return prioritized list of name selectors (current as of March 2026)"""
        return [
            # Primary patterns - Most reliable
            {'type': 'css', 'selector': 'a[href*="maps/place"] h3'},
            {'type': 'css', 'selector': '.fontHeadlineSmall'},
            {'type': 'css', 'selector': '.qBF1Pd'},
            {'type': 'css', 'selector': 'h3.fontHeadlineSmall'},
            
            # Container-based patterns
            {'type': 'css', 'selector': 'div[role="article"] h3'},
            {'type': 'css', 'selector': '.Nv2PK h3'},
            {'type': 'css', 'selector': '[data-place-id] h3'},
            
            # Class-based patterns (Google's dynamic classes)
            {'type': 'css', 'selector': '[class*="headline"]'},
            {'type': 'css', 'selector': '[class*="fontHeadline"]'},
            {'type': 'css', 'selector': '[class*="businessName"]'},
            
            # XPath patterns for tricky cases
            {'type': 'xpath', 'selector': './/h3[ancestor::a[contains(@href, "maps/place")]]'},
            {'type': 'xpath', 'selector': './/*[contains(@class, "headline")]//h3'},
            {'type': 'xpath', 'selector': './/a[contains(@href, "maps/place")]//h3'},
            
            # Aggressive XPath - any h3 with text
            {'type': 'xpath', 'selector': './/h3[string-length(text()) > 2]'},
            
            # Ultimate fallback - any element with reasonable text
            {'type': 'xpath', 'selector': './/*[string-length(text()) > 2 and string-length(text()) < 100 and not(contains(text(), "·")) and not(contains(text(), "★"))]'}
        ]
    
    def extract_name(self, element, use_selenium=True):
        """
        Extract business name from element using multiple strategies
        Returns: (name_string, confidence_score)
        """
        if not element:
            return None, 0
        
        # Try all patterns in order
        for pattern in self.name_patterns:
            try:
                if pattern['type'] == 'css':
                    found_element = element.find_element(By.CSS_SELECTOR, pattern['selector'])
                else:  # xpath
                    found_element = element.find_element(By.XPATH, pattern['selector'])
                
                if found_element:
                    text = found_element.text.strip()
                    
                    # Validate the text looks like a business name
                    if self._is_valid_business_name(text):
                        # Calculate confidence
                        confidence = self._calculate_confidence(text, pattern)
                        return text, confidence
                        
            except NoSuchElementException:
                continue
            except Exception as e:
                print(f"Error with pattern {pattern}: {str(e)}")
                continue
        
        # If all patterns fail, try getting text directly
        direct_text = element.text.strip()
        if direct_text and self._is_valid_business_name(direct_text):
            return direct_text.split('\n')[0], 50  # Lower confidence
        
        # Last resort: parse from HTML
        return self._extract_from_html(element), 30
    
    def _is_valid_business_name(self, text):
        """Validate if text looks like a business name"""
        if not text or len(text) < 2 or len(text) > 100:
            return False
        
        # Common patterns that indicate NOT a business name
        invalid_patterns = [
            r'^[0-9+\-*/().]+$',  # Just numbers/symbols
            r'^[0-9]+\s*(min|hr|hour|mile|km|ft)$',  # Distance/duration
            r'^[★☆★]',  # Star ratings
            r'(open|closed|closes|opens) now',  # Status
            r'^[0-9]+$',  # Just numbers
            r'^[•·●]',  # Bullet points
        ]
        
        for pattern in invalid_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return False
        
        # Should contain at least one letter
        if not re.search(r'[a-zA-Z]', text):
            return False
        
        return True
    
    def _calculate_confidence(self, text, pattern):
        """Calculate confidence score for extracted name"""
        score = 80  # Base score for successful extraction
        
        # Boost based on pattern position
        pattern_index = self.name_patterns.index(pattern)
        if pattern_index < 5:
            score += 15  # High confidence for primary patterns
        elif pattern_index < 10:
            score += 10  # Medium confidence
        else:
            score += 5   # Low confidence patterns
        
        # Boost for certain characteristics
        if text.isupper() and len(text) > 3:
            score += 5   # All caps often indicates business name
        
        if any(char in text for char in ['&', '-', "'", '.']):
            score += 3   # Special chars common in business names
        
        if text[0].isupper() and text[-1].isalpha():
            score += 2   # Starts with capital, ends with letter
        
        return min(score, 100)  # Cap at 100
    
    def _extract_from_html(self, element):
        """Last resort: extract from HTML attributes"""
        try:
            html = element.get_attribute('outerHTML')
            
            # Look for aria-label (often contains business name)
            aria = element.get_attribute('aria-label')
            if aria and self._is_valid_business_name(aria):
                return aria
            
            # Look in data attributes
            for attr in ['data-name', 'data-business-name', 'data-place-name']:
                val = element.get_attribute(attr)
                if val and self._is_valid_business_name(val):
                    return val
            
            # Regex pattern for name in HTML
            patterns = [
                r'aria-label="([^"]+)"',
                r'data-name="([^"]+)"',
                r'>([^<]{3,50})</h3>',
                r'<div[^>]*>([^<]{3,50})</div>'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, html)
                if match and self._is_valid_business_name(match.group(1)):
                    return match.group(1)
                    
        except:
            pass
        
        return "Unknown"
    
    def extract_batch_names(self, elements, timeout=5):
        """Extract names from multiple elements with retry"""
        results = []
        
        for element in elements:
            name, confidence = self.extract_name(element)
            
            # If confidence is low, try waiting and retry
            if confidence < 60 and timeout > 0:
                try:
                    WebDriverWait(self.driver, 2).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'h3'))
                    )
                    name, confidence = self.extract_name(element)
                except:
                    pass
            
            results.append({
                'name': name,
                'confidence': confidence,
                'extracted_at': 'smart_parser_v2'
            })
        
        return results
