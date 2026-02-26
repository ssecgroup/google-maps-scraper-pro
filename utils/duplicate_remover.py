import hashlib
from typing import List, Dict, Set, Tuple
from fuzzywuzzy import fuzz
import logging
from collections import defaultdict
import json

class DuplicateRemover:
    """Advanced duplicate detection and removal"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Thresholds
        self.name_threshold = self.config.get('name_threshold', 85)  # Fuzzy match threshold
        self.phone_threshold = self.config.get('phone_threshold', 100)  # Exact match for phones
        self.address_threshold = self.config.get('address_threshold', 90)
        
        # Strategies
        self.strategies = [
            self.detect_by_place_id,
            self.detect_by_phone,
            self.detect_by_name_address,
            self.detect_by_website,
            self.detect_by_coordinates
        ]
        
    def remove_duplicates(self, businesses: List[Dict]) -> List[Dict]:
        """Remove duplicate businesses"""
        if not businesses:
            return []
        
        original_count = len(businesses)
        self.logger.info(f"Checking {original_count} businesses for duplicates")
        
        # Track unique businesses
        unique_businesses = []
        seen_hashes = set()
        duplicate_groups = defaultdict(list)
        
        for business in businesses:
            # Generate multiple hashes for different matching strategies
            business_id = self.generate_business_id(business)
            
            if business_id not in seen_hashes:
                seen_hashes.add(business_id)
                unique_businesses.append(business)
            else:
                # Track duplicate for analysis
                duplicate_groups[business_id].append(business)
        
        # Merge data from duplicates
        enhanced_businesses = self.merge_duplicate_data(unique_businesses, duplicate_groups)
        
        removed = original_count - len(enhanced_businesses)
        if removed > 0:
            self.logger.info(f"Removed {removed} duplicates, kept {len(enhanced_businesses)} unique businesses")
        
        return enhanced_businesses
    
    def generate_business_id(self, business: Dict) -> str:
        """Generate unique ID for business using multiple strategies"""
        
        # Try each strategy in order
        for strategy in self.strategies:
            biz_id = strategy(business)
            if biz_id:
                return biz_id
        
        # Fallback: hash of name + address
        name = business.get('name', '').strip().lower()
        address = business.get('address', '').strip().lower()
        
        # Clean strings
        name = self.clean_string(name)
        address = self.clean_string(address)
        
        unique_string = f"{name}|{address}"
        return hashlib.md5(unique_string.encode()).hexdigest()
    
    def detect_by_place_id(self, business: Dict) -> str:
        """Detect duplicates using Google Place ID"""
        place_id = business.get('place_id')
        if place_id:
            return f"place_id:{place_id}"
        return None
    
    def detect_by_phone(self, business: Dict) -> str:
        """Detect duplicates using phone numbers"""
        phones = business.get('phone_numbers', [])
        if phones:
            # Clean and use primary phone
            primary_phone = self.clean_phone(phones[0] if isinstance(phones, list) else phones)
            if primary_phone:
                return f"phone:{primary_phone}"
        return None
    
    def detect_by_name_address(self, business: Dict) -> str:
        """Detect duplicates using name and address combination"""
        name = business.get('name', '').strip().lower()
        address = business.get('address', '').strip().lower()
        
        if name and address:
            name = self.clean_string(name)
            address = self.clean_string(address)
            return f"name_addr:{hashlib.md5(f'{name}|{address}'.encode()).hexdigest()}"
        
        return None
    
    def detect_by_website(self, business: Dict) -> str:
        """Detect duplicates using website domain"""
        website = business.get('website', '')
        if website:
            # Extract domain
            domain = self.extract_domain(website)
            if domain:
                return f"domain:{domain}"
        return None
    
    def detect_by_coordinates(self, business: Dict) -> str:
        """Detect duplicates using coordinates"""
        coords = business.get('coordinates', {})
        if coords:
            lat = coords.get('lat')
            lng = coords.get('lng')
            if lat and lng:
                # Round to 4 decimal places (~11 meters accuracy)
                rounded_coords = f"{round(lat, 4)},{round(lng, 4)}"
                return f"coords:{rounded_coords}"
        return None
    
    def clean_phone(self, phone: str) -> str:
        """Clean phone number for comparison"""
        if not phone:
            return None
        
        # Remove all non-digit characters
        cleaned = re.sub(r'\D', '', phone)
        
        # Standardize to 10 digits if possible
        if len(cleaned) == 11 and cleaned.startswith('1'):
            cleaned = cleaned[1:]
        
        return cleaned if len(cleaned) >= 10 else None
    
    def clean_string(self, text: str) -> str:
        """Clean string for comparison"""
        if not text:
            return ""
        
        # Remove extra whitespace and punctuation
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except:
            return None
    
    def merge_duplicate_data(self, unique_businesses: List[Dict], 
                            duplicate_groups: Dict) -> List[Dict]:
        """Merge data from duplicates to enhance unique entries"""
        
        for business in unique_businesses:
            biz_id = self.generate_business_id(business)
            duplicates = duplicate_groups.get(biz_id, [])
            
            if duplicates:
                # Merge data from duplicates
                merged = self.merge_business_data(business, duplicates)
                business.update(merged)
        
        return unique_businesses
    
    def merge_business_data(self, primary: Dict, duplicates: List[Dict]) -> Dict:
        """Merge data from duplicates into primary business"""
        merged = {}
        
        # Fields that can be merged (combine multiple values)
        mergeable_fields = {
            'phone_numbers': set,
            'emails': set,
            'social_media': dict,
            'amenities': set,
            'photos': list,
            'recent_reviews': list
        }
        
        for field, merge_type in mergeable_fields.items():
            values = set()
            
            # Add from primary
            primary_val = primary.get(field)
            if primary_val:
                if isinstance(primary_val, list):
                    values.update(primary_val)
                elif isinstance(primary_val, dict):
                    values = primary_val
                else:
                    values.add(primary_val)
            
            # Add from duplicates
            for dup in duplicates:
                dup_val = dup.get(field)
                if dup_val:
                    if isinstance(dup_val, list):
                        values.update(dup_val)
                    elif isinstance(dup_val, dict):
                        if isinstance(values, dict):
                            values.update(dup_val)
                    else:
                        values.add(dup_val)
            
            # Convert back to appropriate type
            if merge_type == set:
                merged[field] = list(values)[:10]  # Limit to 10 items
            elif merge_type == dict:
                merged[field] = values
            else:
                merged[field] = values
        
        # Fields that should be the best version
        best_fields = ['rating', 'description', 'website', 'price_range']
        for field in best_fields:
            best_value = self.get_best_value(primary, duplicates, field)
            if best_value:
                merged[field] = best_value
        
        return merged
    
    def get_best_value(self, primary: Dict, duplicates: List[Dict], field: str):
        """Get the best value for a field from all available data"""
        candidates = []
        
        # Add primary
        if primary.get(field):
            candidates.append(primary[field])
        
        # Add from duplicates
        for dup in duplicates:
            if dup.get(field):
                candidates.append(dup[field])
        
        if not candidates:
            return None
        
        # For rating, take the highest
        if field == 'rating':
            return max(candidates)
        
        # For description, take the longest
        if field == 'description':
            return max(candidates, key=len)
        
        # For others, take the most common
        from collections import Counter
        counter = Counter(candidates)
        return counter.most_common(1)[0][0]
    
    def find_similar_businesses(self, businesses: List[Dict], 
                               threshold: float = 80) -> List[Tuple]:
        """Find similar businesses using fuzzy matching"""
        similar_pairs = []
        
        for i in range(len(businesses)):
            for j in range(i + 1, len(businesses)):
                similarity = self.calculate_similarity(businesses[i], businesses[j])
                if similarity >= threshold:
                    similar_pairs.append((i, j, similarity))
        
        return similar_pairs
    
    def calculate_similarity(self, biz1: Dict, biz2: Dict) -> float:
        """Calculate similarity score between two businesses"""
        scores = []
        weights = {
            'name': 0.4,
            'address': 0.3,
            'phone': 0.2,
            'category': 0.1
        }
        
        # Name similarity
        name1 = biz1.get('name', '')
        name2 = biz2.get('name', '')
        if name1 and name2:
            name_score = fuzz.ratio(name1.lower(), name2.lower())
            scores.append(name_score * weights['name'])
        
        # Address similarity
        addr1 = biz1.get('address', '')
        addr2 = biz2.get('address', '')
        if addr1 and addr2:
            addr_score = fuzz.ratio(self.clean_string(addr1), self.clean_string(addr2))
            scores.append(addr_score * weights['address'])
        
        # Phone similarity
        phone1 = biz1.get('primary_phone', '')
        phone2 = biz2.get('primary_phone', '')
        if phone1 and phone2:
            clean1 = self.clean_phone(phone1)
            clean2 = self.clean_phone(phone2)
            if clean1 and clean2:
                phone_score = 100 if clean1 == clean2 else 0
                scores.append(phone_score * weights['phone'])
        
        # Category similarity
        cat1 = biz1.get('category', '')
        cat2 = biz2.get('category', '')
        if cat1 and cat2:
            cat_score = fuzz.ratio(cat1.lower(), cat2.lower())
            scores.append(cat_score * weights['category'])
        
        return sum(scores) if scores else 0
    
    def group_by_cluster(self, businesses: List[Dict], threshold: float = 80) -> List[List]:
        """Group businesses into clusters of similar businesses"""
        from sklearn.cluster import DBSCAN
        import numpy as np
        
        # Create feature matrix
        features = []
        for biz in businesses:
            feature_vector = self.create_feature_vector(biz)
            features.append(feature_vector)
        
        if len(features) < 2:
            return [businesses]
        
        # Perform clustering
        clustering = DBSCAN(eps=0.3, min_samples=2, metric='cosine')
        labels = clustering.fit_predict(features)
        
        # Group by cluster
        clusters = defaultdict(list)
        for i, label in enumerate(labels):
            clusters[label].append(businesses[i])
        
        return list(clusters.values())
    
    def create_feature_vector(self, business: Dict) -> List[float]:
        """Create feature vector for clustering"""
        import numpy as np
        from sentence_transformers import SentenceTransformer
        
        # Use pre-trained model for text embeddings
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Combine relevant text fields
        text = f"{business.get('name', '')} {business.get('category', '')} {business.get('description', '')}"
        
        # Generate embedding
        embedding = model.encode(text)
        
        return embedding
