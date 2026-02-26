import requests
from typing import Dict, List, Optional
import time
from datetime import datetime
import json
import whois
from googlesearch import search
import re
import logging

class DataEnricher:
    """Enrich business data with additional information"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.api_keys = self.load_api_keys()
        
    def load_api_keys(self) -> Dict:
        """Load API keys from environment or config"""
        # In production, load from .env file
        return {
            'google_places': 'YOUR_API_KEY',
            'clearbit': 'YOUR_API_KEY',
            'hunter': 'YOUR_API_KEY',
            'linkedin': 'YOUR_API_KEY'
        }
    
    def enrich_with_google_places(self, business: Dict) -> Dict:
        """Enrich data using Google Places API"""
        if not self.api_keys.get('google_places'):
            return business
        
        try:
            place_id = business.get('place_id')
            if not place_id:
                return business
            
            url = f"https://maps.googleapis.com/maps/api/place/details/json"
            params = {
                'place_id': place_id,
                'fields': 'formatted_phone_number,website,opening_hours,price_level,rating,reviews,user_ratings_total,types,address_component,geometry',
                'key': self.api_keys['google_places']
            }
            
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json().get('result', {})
                
                # Update business data
                if data.get('formatted_phone_number') and not business.get('phone'):
                    business['phone'] = data['formatted_phone_number']
                
                if data.get('website') and not business.get('website'):
                    business['website'] = data['website']
                
                if data.get('opening_hours'):
                    business['opening_hours'] = data['opening_hours']['weekday_text']
                
                if data.get('price_level'):
                    business['price_level'] = data['price_level']
                
                # Add to enrichment history
                business['enrichment'] = business.get('enrichment', {})
                business['enrichment']['google_places'] = True
                
        except Exception as e:
            self.logger.error(f"Google Places enrichment failed: {str(e)}")
        
        return business
    
    def enrich_with_whois(self, business: Dict) -> Dict:
        """Get WHOIS information from business website"""
        website = business.get('website')
        if not website:
            return business
        
        try:
            domain = website.split('://')[-1].split('/')[0]
            whois_info = whois.whois(domain)
            
            business['enrichment'] = business.get('enrichment', {})
            business['enrichment']['whois'] = {
                'registrar': whois_info.registrar,
                'creation_date': str(whois_info.creation_date),
                'expiration_date': str(whois_info.expiration_date),
                'name_servers': whois_info.name_servers
            }
            
            # Extract email from WHOIS
            if whois_info.emails and not business.get('emails'):
                business['emails'] = business.get('emails', [])
                if isinstance(whois_info.emails, list):
                    business['emails'].extend(whois_info.emails)
                else:
                    business['emails'].append(whois_info.emails)
                    
        except Exception as e:
            self.logger.debug(f"WHOIS enrichment failed: {str(e)}")
        
        return business
    
    def enrich_with_clearbit(self, business: Dict) -> Dict:
        """Enrich with Clearbit company data"""
        if not self.api_keys.get('clearbit'):
            return business
        
        website = business.get('website')
        if not website:
            return business
        
        try:
            domain = website.split('://')[-1].split('/')[0]
            url = f"https://company.clearbit.com/v2/companies/find?domain={domain}"
            
            headers = {'Authorization': f"Bearer {self.api_keys['clearbit']}"}
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                business['enrichment'] = business.get('enrichment', {})
                business['enrichment']['clearbit'] = {
                    'name': data.get('name'),
                    'description': data.get('description'),
                    'industry': data.get('category', {}).get('industry'),
                    'employees': data.get('metrics', {}).get('employees'),
                    'market_cap': data.get('metrics', {}).get('marketCap'),
                    'founded_year': data.get('foundedYear'),
                    'phone': data.get('phone'),
                    'email_provider': data.get('site', {}).get('emailAddresses')
                }
                
        except Exception as e:
            self.logger.debug(f"Clearbit enrichment failed: {str(e)}")
        
        return business
    
    def enrich_with_hunter(self, business: Dict) -> Dict:
        """Find emails using Hunter.io"""
        if not self.api_keys.get('hunter'):
            return business
        
        website = business.get('website')
        if not website:
            return business
        
        try:
            domain = website.split('://')[-1].split('/')[0]
            url = f"https://api.hunter.io/v2/domain-search"
            params = {
                'domain': domain,
                'api_key': self.api_keys['hunter']
            }
            
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json().get('data', {})
                
                emails = []
                for email_data in data.get('emails', []):
                    emails.append({
                        'email': email_data['value'],
                        'type': email_data['type'],
                        'confidence': email_data['confidence']
                    })
                
                if emails:
                    business['emails'] = business.get('emails', [])
                    business['emails'].extend([e['email'] for e in emails])
                    
                    business['enrichment'] = business.get('enrichment', {})
                    business['enrichment']['hunter'] = emails
                    
        except Exception as e:
            self.logger.debug(f"Hunter enrichment failed: {str(e)}")
        
        return business
    
    def find_competitors(self, business: Dict) -> List[Dict]:
        """Find similar businesses in the area"""
        competitors = []
        
        try:
            # Use Google search to find competitors
            query = f"{business.get('category', '')} near {business.get('address', '')}"
            
            for url in search(query, num_results=10):
                if 'google.com/maps' in url:
                    # Extract business info from URL
                    competitors.append({
                        'url': url,
                        'source': 'google_search'
                    })
                    
        except Exception as e:
            self.logger.debug(f"Competitor search failed: {str(e)}")
        
        return competitors
    
    def verify_business_active(self, business: Dict) -> bool:
        """Verify if business is still active"""
        try:
            website = business.get('website')
            if website:
                response = requests.get(website, timeout=5)
                if response.status_code == 200:
                    return True
            
            # Check Google Maps for permanency
            place_id = business.get('place_id')
            if place_id:
                # Use Google Places API to check status
                url = f"https://maps.googleapis.com/maps/api/place/details/json"
                params = {
                    'place_id': place_id,
                    'fields': 'permanently_closed',
                    'key': self.api_keys.get('google_places', '')
                }
                
                response = requests.get(url, params=params)
                if response.status_code == 200:
                    data = response.json().get('result', {})
                    if data.get('permanently_closed'):
                        return False
            
            return True
            
        except Exception as e:
            self.logger.debug(f"Verification failed: {str(e)}")
            return False
