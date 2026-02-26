import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import logging
from typing import Dict, List, Optional
import json
import time

class SocialMediaFinder:
    """Find and validate social media profiles"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Social media patterns
        self.patterns = {
            'facebook': [
                r'(?:https?:)?\/\/(?:www\.)?facebook\.com\/([a-zA-Z0-9.]+)',
                r'(?:https?:)?\/\/(?:www\.)?fb\.com\/([a-zA-Z0-9.]+)'
            ],
            'instagram': [
                r'(?:https?:)?\/\/(?:www\.)?instagram\.com\/([a-zA-Z0-9._]+)',
                r'(?:https?:)?\/\/(?:www\.)?instagr\.am\/([a-zA-Z0-9._]+)'
            ],
            'twitter': [
                r'(?:https?:)?\/\/(?:www\.)?twitter\.com\/([a-zA-Z0-9_]+)',
                r'(?:https?:)?\/\/(?:www\.)?x\.com\/([a-zA-Z0-9_]+)'
            ],
            'linkedin': [
                r'(?:https?:)?\/\/(?:www\.)?linkedin\.com\/(?:company|in)\/([a-zA-Z0-9-]+)',
                r'(?:https?:)?\/\/(?:www\.)?linkedin\.com\/school\/([a-zA-Z0-9-]+)'
            ],
            'youtube': [
                r'(?:https?:)?\/\/(?:www\.)?youtube\.com\/(?:c|channel|user)\/([a-zA-Z0-9-]+)',
                r'(?:https?:)?\/\/(?:www\.)?youtu\.be\/([a-zA-Z0-9-]+)'
            ],
            'yelp': [
                r'(?:https?:)?\/\/(?:www\.)?yelp\.com\/biz\/([a-zA-Z0-9-]+)',
                r'(?:https?:)?\/\/(?:www\.)?yelp\.ca\/biz\/([a-zA-Z0-9-]+)'
            ],
            'pinterest': [
                r'(?:https?:)?\/\/(?:www\.)?pinterest\.com\/([a-zA-Z0-9_]+)',
                r'(?:https?:)?\/\/(?:www\.)?pin\.it\/([a-zA-Z0-9_]+)'
            ],
            'tiktok': [
                r'(?:https?:)?\/\/(?:www\.)?tiktok\.com\/@([a-zA-Z0-9_.]+)',
                r'(?:https?:)?\/\/(?:www\.)?tiktok\.com\/([a-zA-Z0-9_.]+)'
            ],
            'snapchat': [
                r'(?:https?:)?\/\/(?:www\.)?snapchat\.com\/add\/([a-zA-Z0-9_.]+)'
            ],
            'reddit': [
                r'(?:https?:)?\/\/(?:www\.)?reddit\.com\/(?:r|user)\/([a-zA-Z0-9_]+)'
            ],
            'medium': [
                r'(?:https?:)?\/\/(?:www\.)?medium\.com\/@([a-zA-Z0-9.]+)'
            ]
        }
        
        # Platform icons/fonts
        self.icon_classes = {
            'facebook': ['fa-facebook', 'fab fa-facebook', 'icon-facebook'],
            'twitter': ['fa-twitter', 'fab fa-twitter', 'icon-twitter'],
            'instagram': ['fa-instagram', 'fab fa-instagram', 'icon-instagram'],
            'linkedin': ['fa-linkedin', 'fab fa-linkedin', 'icon-linkedin'],
            'youtube': ['fa-youtube', 'fab fa-youtube', 'icon-youtube'],
            'pinterest': ['fa-pinterest', 'fab fa-pinterest', 'icon-pinterest'],
            'tiktok': ['fa-tiktok', 'fab fa-tiktok'],
            'snapchat': ['fa-snapchat', 'fab fa-snapchat'],
            'yelp': ['fa-yelp', 'fab fa-yelp']
        }
    
    def find_social_media(self, website: str, business_name: str = None) -> Dict[str, str]:
        """Find all social media profiles for a business"""
        if not website:
            return {}
        
        social_media = {}
        
        try:
            # Method 1: Extract from website
            social_from_website = self.extract_from_website(website)
            social_media.update(social_from_website)
            
            # Method 2: Search by business name
            if business_name and not social_media:
                social_from_search = self.search_by_name(business_name)
                social_media.update(social_from_search)
            
            # Method 3: Check common patterns
            if not social_media:
                social_from_patterns = self.check_common_patterns(website, business_name)
                social_media.update(social_from_patterns)
            
            # Validate profiles
            for platform, url in list(social_media.items()):
                if not self.validate_profile(platform, url):
                    del social_media[platform]
            
        except Exception as e:
            self.logger.debug(f"Error finding social media: {str(e)}")
        
        return social_media
    
    def extract_from_website(self, website: str) -> Dict[str, str]:
        """Extract social media links from website"""
        social_media = {}
        
        try:
            response = self.session.get(website, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Method 1: Look for social media links
                for platform, patterns in self.patterns.items():
                    for pattern in patterns:
                        # Find all links that match
                        links = soup.find_all('a', href=re.compile(pattern))
                        if links:
                            social_media[platform] = links[0]['href']
                            break
                
                # Method 2: Look for icon classes
                if not social_media:
                    for platform, classes in self.icon_classes.items():
                        for icon_class in classes:
                            icons = soup.find_all(class_=re.compile(icon_class))
                            if icons:
                                # Find parent link
                                parent_link = icons[0].find_parent('a')
                                if parent_link and parent_link.get('href'):
                                    social_media[platform] = urljoin(website, parent_link['href'])
                                    break
                
                # Method 3: Check meta tags
                if not social_media:
                    for platform in self.patterns.keys():
                        meta = soup.find('meta', property=f'al:{platform}:url')
                        if meta:
                            social_media[platform] = meta.get('content', '')
                            break
                        
        except Exception as e:
            self.logger.debug(f"Error extracting from website: {str(e)}")
        
        return social_media
    
    def search_by_name(self, business_name: str) -> Dict[str, str]:
        """Search for social media profiles by business name"""
        social_media = {}
        
        try:
            # Clean business name for search
            search_name = re.sub(r'[^\w\s]', '', business_name)
            search_name = search_name.replace(' ', '+')
            
            for platform, patterns in self.patterns.items():
                # Construct search URL
                search_url = f"https://www.google.com/search?q={search_name}+{platform}"
                
                response = self.session.get(search_url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Look for platform URLs in search results
                    for pattern in patterns:
                        # Find links that match platform pattern
                        links = soup.find_all('a', href=re.compile(pattern))
                        if links:
                            # Get first result
                            href = links[0]['href']
                            # Extract actual URL from Google redirect
                            if '/url?q=' in href:
                                url = href.split('/url?q=')[1].split('&')[0]
                                social_media[platform] = url
                                break
                
                time.sleep(1)  # Be respectful
                
        except Exception as e:
            self.logger.debug(f"Error searching by name: {str(e)}")
        
        return social_media
    
    def check_common_patterns(self, website: str, business_name: str) -> Dict[str, str]:
        """Check common URL patterns for social media"""
        social_media = {}
        
        if not website or not business_name:
            return social_media
        
        try:
            domain = self.extract_domain(website)
            clean_name = self.clean_business_name(business_name)
            
            # Common patterns
            patterns = {
                'facebook': [
                    f"https://facebook.com/{clean_name}",
                    f"https://facebook.com/{domain}",
                    f"https://fb.com/{clean_name}"
                ],
                'instagram': [
                    f"https://instagram.com/{clean_name}",
                    f"https://instagram.com/{domain}"
                ],
                'twitter': [
                    f"https://twitter.com/{clean_name}",
                    f"https://twitter.com/{domain}",
                    f"https://x.com/{clean_name}"
                ],
                'linkedin': [
                    f"https://linkedin.com/company/{clean_name}",
                    f"https://linkedin.com/company/{domain}"
                ],
                'youtube': [
                    f"https://youtube.com/c/{clean_name}",
                    f"https://youtube.com/channel/{clean_name}"
                ]
            }
            
            for platform, urls in patterns.items():
                for url in urls:
                    if self.validate_profile(platform, url):
                        social_media[platform] = url
                        break
                        
        except Exception as e:
            self.logger.debug(f"Error checking patterns: {str(e)}")
        
        return social_media
    
    def validate_profile(self, platform: str, url: str) -> bool:
        """Validate if social media profile exists and is accessible"""
        try:
            response = self.session.get(url, timeout=10, allow_redirects=True)
            
            if response.status_code == 200:
                # Check for platform-specific indicators
                if platform == 'facebook':
                    return 'Facebook' in response.text and 'not found' not in response.text.lower()
                elif platform == 'instagram':
                    return 'Instagram' in response.text and 'Page Not Found' not in response.text
                elif platform == 'twitter':
                    return 'Twitter' in response.text and 'This account doesn’t exist' not in response.text
                elif platform == 'linkedin':
                    return 'LinkedIn' in response.text and 'Page not found' not in response.text
                elif platform == 'youtube':
                    return 'YouTube' in response.text and 'This channel does not exist' not in response.text
                
                return True
                
        except Exception as e:
            self.logger.debug(f"Profile validation failed: {str(e)}")
        
        return False
    
    def get_profile_metrics(self, platform: str, url: str) -> Dict:
        """Get basic metrics from social media profile"""
        metrics = {
            'platform': platform,
            'url': url,
            'followers': None,
            'posts': None,
            'verified': False,
            'last_active': None
        }
        
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                if platform == 'instagram':
                    # Extract follower count from meta
                    meta = soup.find('meta', property='og:description')
                    if meta:
                        content = meta.get('content', '')
                        # Parse "X Followers, Y Following, Z Posts"
                        numbers = re.findall(r'([\d,]+)', content)
                        if len(numbers) >= 1:
                            metrics['followers'] = numbers[0].replace(',', '')
                    
                elif platform == 'twitter':
                    # Look for follower count
                    follower_elem = soup.find('a', href=re.compile(r'/followers'))
                    if follower_elem:
                        metrics['followers'] = follower_elem.text.strip()
                    
                elif platform == 'youtube':
                    # Extract subscriber count
                    sub_elem = soup.find('span', id='subscriber-count')
                    if sub_elem:
                        metrics['followers'] = sub_elem.text.strip()
                
                # Check for verification badge
                verified_indicators = ['verified', 'Verified', '✓']
                for indicator in verified_indicators:
                    if indicator in response.text:
                        metrics['verified'] = True
                        break
                        
        except Exception as e:
            self.logger.debug(f"Error getting metrics: {str(e)}")
        
        return metrics
    
    def extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain.split('.')[0]
        except:
            return None
    
    def clean_business_name(self, name: str) -> str:
        """Clean business name for URL use"""
        if not name:
            return None
        
        # Convert to lowercase
        name = name.lower()
        
        # Remove special characters
        name = re.sub(r'[^\w\s-]', '', name)
        
        # Replace spaces with hyphens or remove them
        name = re.sub(r'\s+', '-', name)
        
        # Remove common suffixes
        suffixes = ['llc', 'inc', 'corp', 'ltd', 'co', 'company']
        for suffix in suffixes:
            if name.endswith(f'-{suffix}'):
                name = name[:-len(f'-{suffix}')]
        
        return name.strip('-')
    
    def find_influencers(self, category: str, location: str, limit: int = 10) -> List[Dict]:
        """Find social media influencers in a category"""
        influencers = []
        
        try:
            # Search for influencers on different platforms
            platforms = ['instagram', 'youtube', 'tiktok']
            
            for platform in platforms:
                search_query = f"{category} {location} influencer"
                search_url = f"https://www.google.com/search?q={search_query}+{platform}"
                
                response = self.session.get(search_url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Find platform profiles in results
                    for pattern in self.patterns.get(platform, []):
                        links = soup.find_all('a', href=re.compile(pattern))
                        for link in links[:limit]:
                            href = link['href']
                            if '/url?q=' in href:
                                url = href.split('/url?q=')[1].split('&')[0]
                                
                                # Get profile info
                                profile = {
                                    'platform': platform,
                                    'url': url,
                                    'name': link.get_text(strip=True),
                                    'found_at': time.time()
                                }
                                
                                # Get metrics
                                metrics = self.get_profile_metrics(platform, url)
                                profile.update(metrics)
                                
                                influencers.append(profile)
                    
                    time.sleep(2)
            
        except Exception as e:
            self.logger.error(f"Error finding influencers: {str(e)}")
        
        return influencers[:limit]
    
    def analyze_social_presence(self, social_media: Dict) -> Dict:
        """Analyze overall social media presence"""
        analysis = {
            'platforms_count': len(social_media),
            'platforms': list(social_media.keys()),
            'engagement_score': 0,
            'recommendations': []
        }
        
        # Calculate engagement score
        platform_weights = {
            'instagram': 10,
            'facebook': 8,
            'twitter': 7,
            'linkedin': 6,
            'youtube': 9,
            'tiktok': 9,
            'pinterest': 5,
            'yelp': 4
        }
        
        total_weight = 0
        for platform in social_media.keys():
            total_weight += platform_weights.get(platform, 5)
        
        analysis['engagement_score'] = min(100, total_weight * 3)
        
        # Generate recommendations
        if 'instagram' not in social_media:
            analysis['recommendations'].append('Consider creating an Instagram account for visual marketing')
        if 'facebook' not in social_media:
            analysis['recommendations'].append('Facebook presence would help with local community engagement')
        if 'linkedin' not in social_media and 'B2B' in str(social_media):
            analysis['recommendations'].append('LinkedIn is crucial for B2B networking')
        if 'youtube' not in social_media:
            analysis['recommendations'].append('Video content on YouTube could showcase products/services')
        
        return analysis
