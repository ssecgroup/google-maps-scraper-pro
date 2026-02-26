import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import time
import logging
from typing import List, Set, Dict, Optional
import dns.resolver
import smtplib
from email_validator import validate_email, EmailNotValidError
import aiohttp
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json

class EmailFinder:
    """Advanced email extraction from websites"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Patterns
        self.email_patterns = [
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            r'[a-zA-Z0-9._%+-]+\[at\][a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            r'[a-zA-Z0-9._%+-]+\(at\)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            r'[a-zA-Z0-9._%+-]+ @ [a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        ]
        
        # Common email contact pages
        self.contact_paths = [
            '/contact', '/contact-us', '/contactus', '/about', '/about-us',
            '/support', '/help', '/feedback', '/team', '/staff', '/company',
            '/contact.php', '/contact.html', '/about.php', '/about.html'
        ]
        
        # Cache
        self.cache = {}
        
    def find_emails(self, website: str, max_pages: int = 5) -> List[Dict]:
        """Find emails from a website"""
        if not website:
            return []
        
        # Check cache
        if website in self.cache:
            return self.cache[website]
        
        emails = []
        visited = set()
        
        try:
            # Start with main page
            main_emails = self.extract_from_url(website)
            emails.extend(main_emails)
            visited.add(website)
            
            # Check contact pages
            for path in self.contact_paths[:max_pages]:
                contact_url = urljoin(website, path)
                if contact_url not in visited:
                    contact_emails = self.extract_from_url(contact_url)
                    emails.extend(contact_emails)
                    visited.add(contact_url)
                    
                    if len(emails) >= 10:  # Limit total emails
                        break
                    
                    time.sleep(1)  # Be respectful
            
            # Deduplicate and validate
            emails = self.deduplicate_emails(emails)
            
            # Verify emails
            for email in emails:
                email['verified'] = self.verify_email(email['address'])
            
            # Cache results
            self.cache[website] = emails
            
        except Exception as e:
            self.logger.debug(f"Error finding emails for {website}: {str(e)}")
        
        return emails
    
    def extract_from_url(self, url: str) -> List[Dict]:
        """Extract emails from a single URL"""
        emails = []
        
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Method 1: mailto links
                for link in soup.find_all('a', href=re.compile(r'^mailto:')):
                    email = link['href'].replace('mailto:', '').split('?')[0].strip()
                    if self.validate_email_format(email):
                        emails.append({
                            'address': email,
                            'source': 'mailto_link',
                            'context': link.get_text(strip=True)[:200],
                            'page': url
                        })
                
                # Method 2: email patterns in text
                text = soup.get_text()
                for pattern in self.email_patterns:
                    for match in re.finditer(pattern, text):
                        email = match.group()
                        # Clean obfuscated emails
                        email = email.replace('[at]', '@').replace('(at)', '@').replace(' @ ', '@')
                        if self.validate_email_format(email):
                            # Get surrounding context
                            start = max(0, match.start() - 50)
                            end = min(len(text), match.end() + 50)
                            context = text[start:end]
                            
                            emails.append({
                                'address': email,
                                'source': 'text_pattern',
                                'context': context,
                                'page': url
                            })
                
                # Method 3: check for email in meta tags
                for meta in soup.find_all('meta', attrs={'name': 'email'}):
                    email = meta.get('content', '')
                    if self.validate_email_format(email):
                        emails.append({
                            'address': email,
                            'source': 'meta_tag',
                            'context': 'meta tag',
                            'page': url
                        })
                
                # Method 4: check for contact forms
                forms = soup.find_all('form')
                for form in forms:
                    action = form.get('action', '')
                    if any(word in action.lower() for word in ['contact', 'email', 'send']):
                        # This indicates a contact form exists
                        emails.append({
                            'address': 'CONTACT_FORM_FOUND',
                            'source': 'contact_form',
                            'context': f'Form action: {action}',
                            'page': url
                        })
                        
        except Exception as e:
            self.logger.debug(f"Error extracting from {url}: {str(e)}")
        
        return emails
    
    def find_emails_async(self, websites: List[str]) -> Dict[str, List[Dict]]:
        """Find emails from multiple websites asynchronously"""
        
        async def fetch(session, url):
            try:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        text = await response.text()
                        return url, self.extract_emails_from_html(text, url)
            except:
                pass
            return url, []
        
        async def main():
            async with aiohttp.ClientSession() as session:
                tasks = []
                for website in websites:
                    tasks.append(fetch(session, website))
                
                results = await asyncio.gather(*tasks)
                return dict(results)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(main())
        loop.close()
        
        return results
    
    def extract_emails_from_html(self, html: str, url: str) -> List[Dict]:
        """Extract emails from HTML content"""
        emails = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # mailto links
        for link in soup.find_all('a', href=re.compile(r'^mailto:')):
            email = link['href'].replace('mailto:', '').split('?')[0].strip()
            if self.validate_email_format(email):
                emails.append({
                    'address': email,
                    'source': 'mailto_link',
                    'page': url
                })
        
        # text patterns
        text = soup.get_text()
        for pattern in self.email_patterns:
            for match in re.finditer(pattern, text):
                email = match.group().replace('[at]', '@').replace('(at)', '@')
                if self.validate_email_format(email):
                    emails.append({
                        'address': email,
                        'source': 'text_pattern',
                        'page': url
                    })
        
        return emails
    
    def validate_email_format(self, email: str) -> bool:
        """Validate email format"""
        try:
            valid = validate_email(email, check_deliverability=False)
            
            # Exclude common spam/tracker emails
            exclude_patterns = [
                'noreply', 'no-reply', 'donotreply', 'info@', 'support@',
                'admin@', 'webmaster@', 'contact@', 'hello@', 'care@',
                'marketing@', 'sales@', 'enquiries@', 'query@'
            ]
            
            email_lower = email.lower()
            for pattern in exclude_patterns:
                if pattern in email_lower:
                    return False
            
            # Exclude disposable domains
            disposable_domains = self.load_disposable_domains()
            domain = email_lower.split('@')[1]
            if domain in disposable_domains:
                return False
            
            return True
            
        except EmailNotValidError:
            return False
    
    def load_disposable_domains(self) -> Set:
        """Load list of disposable email domains"""
        # Common disposable domains
        disposable = {
            'tempmail.com', 'throwaway.com', 'mailinator.com', 'guerrillamail.com',
            'sharklasers.com', 'grr.la', 'mailnesia.com', '10minutemail.com',
            'yopmail.com', 'temp-mail.org', 'fakeinbox.com', 'maildrop.cc',
            'getnada.com', 'tempemail.net', 'spambox.us', 'trashmail.com'
        }
        
        # Try to load from remote source
        try:
            response = requests.get(
                'https://raw.githubusercontent.com/disposable-email-domains/disposable-email-domains/master/disposable_email_blocklist.conf',
                timeout=5
            )
            if response.status_code == 200:
                remote_domains = set(response.text.strip().split('\n'))
                disposable.update(remote_domains)
        except:
            pass
        
        return disposable
    
    def verify_email(self, email: str, check_mx: bool = True, 
                    check_smtp: bool = False) -> bool:
        """Verify if email exists"""
        try:
            # Format validation
            valid = validate_email(email, check_deliverability=False)
            email = valid.email
            
            # Check MX records
            if check_mx:
                domain = email.split('@')[1]
                try:
                    mx_records = dns.resolver.resolve(domain, 'MX')
                    if not mx_records:
                        return False
                except:
                    return False
            
            # Check SMTP (optional, may be blocked)
            if check_smtp:
                # This can be unreliable and may get you blocked
                domain = email.split('@')[1]
                try:
                    # Get MX server
                    mx_records = dns.resolver.resolve(domain, 'MX')
                    mx_server = str(mx_records[0].exchange)
                    
                    # SMTP check
                    server = smtplib.SMTP(timeout=10)
                    server.connect(mx_server)
                    server.helo(server.local_hostname)
                    server.mail('test@example.com')
                    code, message = server.rcpt(email)
                    server.quit()
                    
                    return code == 250
                except:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.debug(f"Email verification failed: {str(e)}")
            return False
    
    def deduplicate_emails(self, emails: List[Dict]) -> List[Dict]:
        """Remove duplicate emails"""
        seen = set()
        unique_emails = []
        
        for email in emails:
            addr = email.get('address', '').lower()
            if addr and addr not in seen and addr != 'contact_form_found':
                seen.add(addr)
                unique_emails.append(email)
        
        return unique_emails
    
    def prioritize_emails(self, emails: List[Dict]) -> List[Dict]:
        """Prioritize emails based on quality signals"""
        for email in emails:
            score = 0
            addr = email.get('address', '').lower()
            
            # Higher score for personal emails
            if any(x in addr for x in ['@gmail', '@yahoo', '@hotmail', '@outlook']):
                score += 10
            
            # Lower score for generic addresses
            if any(x in addr for x in ['info@', 'contact@', 'support@']):
                score -= 5
            
            # Higher score for verified emails
            if email.get('verified'):
                score += 20
            
            # Higher score for mailto links (more intentional)
            if email.get('source') == 'mailto_link':
                score += 15
            
            email['priority_score'] = score
        
        # Sort by priority score
        return sorted(emails, key=lambda x: x.get('priority_score', 0), reverse=True)
    
    def find_patterns(self, businesses: List[Dict]) -> Dict:
        """Find email patterns across businesses"""
        patterns = {
            'common_domains': {},
            'naming_patterns': {},
            'email_formats': {}
        }
        
        for business in businesses:
            website = business.get('website')
            if not website:
                continue
            
            domain = self.extract_domain(website)
            emails = business.get('emails', [])
            
            for email in emails:
                if isinstance(email, dict):
                    addr = email.get('address')
                else:
                    addr = email
                
                if addr and '@' in addr:
                    # Track domain frequency
                    email_domain = addr.split('@')[1]
                    patterns['common_domains'][email_domain] = \
                        patterns['common_domains'].get(email_domain, 0) + 1
                    
                    # Track email format
                    if domain and email_domain == domain:
                        local_part = addr.split('@')[0]
                        format_type = self.identify_email_format(local_part)
                        patterns['email_formats'][format_type] = \
                            patterns['email_formats'].get(format_type, 0) + 1
        
        return patterns
    
    def extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain.split('/')[0]
        except:
            return None
    
    def identify_email_format(self, local_part: str) -> str:
        """Identify the format of an email local part"""
        if '.' in local_part:
            parts = local_part.split('.')
            if len(parts) == 2 and all(p.isalpha() for p in parts):
                return 'first.last'
        if '_' in local_part:
            return 'first_last'
        if local_part.isalpha():
            return 'single_name'
        if local_part.isdigit():
            return 'numeric'
        if re.match(r'^[a-z]+\d+$', local_part):
            return 'name_number'
        return 'custom'
