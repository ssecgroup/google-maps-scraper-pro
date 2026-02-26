from sqlalchemy import Column, String, Float, Integer, DateTime, JSON, Boolean, Text, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

# Association tables for many-to-many relationships
business_tags = Table(
    'business_tags',
    Base.metadata,
    Column('business_id', String(64), ForeignKey('businesses.id')),
    Column('tag_id', Integer, ForeignKey('tags.id'))
)

business_categories = Table(
    'business_categories',
    Base.metadata,
    Column('business_id', String(64), ForeignKey('businesses.id')),
    Column('category_id', Integer, ForeignKey('categories.id'))
)

class Business(Base):
    """Main business model with comprehensive fields"""
    __tablename__ = 'businesses'
    
    # Core fields
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    business_type = Column(String(100), index=True)
    
    # Ratings and reviews
    rating = Column(Float)
    reviews_count = Column(Integer, default=0)
    rating_distribution = Column(JSON)  # {5: 100, 4: 50, 3: 20, 2: 5, 1: 2}
    
    # Contact information
    phone_numbers = Column(JSON)  # List of phone numbers with types
    primary_phone = Column(String(50))
    phone_verified = Column(Boolean, default=False)
    
    emails = Column(JSON)  # List of emails with confidence scores
    primary_email = Column(String(255))
    email_verified = Column(Boolean, default=False)
    
    websites = Column(JSON)  # List of websites
    primary_website = Column(String(500))
    
    # Social media
    social_media = Column(JSON)  # {facebook: url, instagram: url, ...}
    social_media_presence = Column(JSON)  # Activity metrics if available
    
    # Location
    address = Column(Text)
    street_address = Column(String(255))
    city = Column(String(100), index=True)
    state = Column(String(50), index=True)
    country = Column(String(50), index=True)
    postal_code = Column(String(20), index=True)
    neighborhood = Column(String(100))
    
    # Geographic coordinates
    latitude = Column(Float)
    longitude = Column(Float)
    location_point = Column(String(100))  # WKT format for spatial queries
    
    # Google Maps data
    place_id = Column(String(255), unique=True, index=True)
    google_maps_url = Column(String(500))
    plus_code = Column(String(50))
    
    # Business details
    description = Column(Text)
    short_description = Column(String(500))
    category = Column(String(255), index=True)
    subcategories = Column(JSON)
    keywords = Column(JSON)
    
    # Operations
    opening_hours = Column(JSON)  # Structured hours data
    special_hours = Column(JSON)  # Holiday hours
    popular_times = Column(JSON)  # Busy times data
    timezone = Column(String(50))
    
    # Attributes
    price_range = Column(String(10))
    price_level = Column(Integer)  # 0-4 scale
    amenities = Column(JSON)
    payment_methods = Column(JSON)
    languages_spoken = Column(JSON)
    
    # Accessibility
    wheelchair_accessible = Column(Boolean)
    parking = Column(JSON)  # {free: true, valet: false, street: true}
    accessibility_features = Column(JSON)
    
    # Health and safety
    health_safety = Column(JSON)  # COVID-19 measures etc.
    certifications = Column(JSON)
    
    # Media
    photos_count = Column(Integer, default=0)
    photos = Column(JSON)  # URLs to photos
    videos = Column(JSON)
    logo_url = Column(String(500))
    
    # Reviews
    recent_reviews = Column(JSON)  # Last 5-10 reviews
    featured_review = Column(JSON)
    review_highlights = Column(JSON)  # Keywords from reviews
    
    # Verification
    verified = Column(Boolean, default=False)
    claimed = Column(Boolean, default=False)
    verification_date = Column(DateTime)
    claimed_by = Column(String(255))
    
    # Status
    is_active = Column(Boolean, default=True)
    permanently_closed = Column(Boolean, default=False)
    temporarily_closed = Column(Boolean, default=False)
    closed_date = Column(DateTime)
    
    # Business metadata
    year_established = Column(Integer)
    founder = Column(String(255))
    employee_count = Column(String(50))
    business_size = Column(String(50))  # Small, Medium, Large, Enterprise
    business_structure = Column(String(50))  # LLC, Corp, etc.
    
    # Online presence
    domain_authority = Column(Integer)
    seo_score = Column(Integer)
    google_ranking = Column(Integer)
    
    # Marketing
    marketing_emails = Column(JSON)  # Marketing contact emails
    newsletter = Column(Boolean, default=False)
    social_media_active = Column(Boolean, default=False)
    
    # Enrichment data
    enrichment_data = Column(JSON)  # Data from third-party APIs
    enrichment_sources = Column(JSON)  # Which sources were used
    enrichment_timestamp = Column(DateTime)
    
    # Quality metrics
    data_completeness = Column(Float)  # 0-100%
    confidence_score = Column(Float)  # 0-100%
    data_quality_grade = Column(String(1))  # A-F
    
    # Search context
    search_query = Column(String(255))
    search_location = Column(String(255))
    search_radius = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    last_scraped = Column(DateTime, index=True)
    last_verified = Column(DateTime)
    
    # Relationships
    tags = relationship("Tag", secondary=business_tags, back_populates="businesses")
    categories = relationship("Category", secondary=business_categories, back_populates="businesses")
    reviews = relationship("Review", back_populates="business", cascade="all, delete-orphan")
    competitors = relationship("Competitor", back_populates="business")
    history = relationship("BusinessHistory", back_populates="business")
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def update_from_scrape(self, data: Dict):
        """Update business from scraped data"""
        for key, value in data.items():
            if hasattr(self, key) and value is not None:
                setattr(self, key, value)
        self.last_scraped = datetime.utcnow()
    
    def calculate_quality_score(self):
        """Calculate data quality score"""
        score = 0
        total_fields = 20
        
        # Essential fields
        if self.name: score += 1
        if self.phone_numbers: score += 1
        if self.emails: score += 1
        if self.primary_website: score += 1
        if self.address: score += 1
        if self.latitude and self.longitude: score += 1
        
        # Important fields
        if self.opening_hours: score += 1
        if self.rating: score += 1
        if self.reviews_count > 10: score += 1
        if self.social_media: score += 1
        if self.price_range: score += 1
        
        # Verification
        if self.verified: score += 2
        if self.claimed: score += 1
        
        # Completeness
        if self.description: score += 1
        if self.photos_count > 5: score += 1
        if self.amenities: score += 1
        
        # Business details
        if self.year_established: score += 1
        if self.business_type: score += 1
        if self.payment_methods: score += 1
        
        self.data_completeness = (score / total_fields) * 100
        return self.data_completeness

class Review(Base):
    """Business reviews model"""
    __tablename__ = 'reviews'
    
    id = Column(Integer, primary_key=True)
    business_id = Column(String(64), ForeignKey('businesses.id'), index=True)
    author_name = Column(String(255))
    author_id = Column(String(255))
    rating = Column(Integer)
    text = Column(Text)
    review_date = Column(DateTime)
    response_date = Column(DateTime)
    response_text = Column(Text)
    language = Column(String(10))
    likes_count = Column(Integer, default=0)
    photos = Column(JSON)
    verified = Column(Boolean, default=False)
    source = Column(String(50))  # Google, Yelp, Facebook, etc.
    scraped_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    business = relationship("Business", back_populates="reviews")

class Tag(Base):
    """Tags for categorizing businesses"""
    __tablename__ = 'tags'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, index=True)
    category = Column(String(50))
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    businesses = relationship("Business", secondary=business_tags, back_populates="tags")

class Category(Base):
    """Business categories"""
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, index=True)
    parent_id = Column(Integer, ForeignKey('categories.id'))
    level = Column(Integer, default=0)
    path = Column(String(500))
    description = Column(Text)
    icon = Column(String(255))
    usage_count = Column(Integer, default=0)
    
    # Relationships
    businesses = relationship("Business", secondary=business_categories, back_populates="categories")
    children = relationship("Category", backref=db.backref('parent', remote_side=[id]))

class Competitor(Base):
    """Competitor analysis"""
    __tablename__ = 'competitors'
    
    id = Column(Integer, primary_key=True)
    business_id = Column(String(64), ForeignKey('businesses.id'), index=True)
    competitor_name = Column(String(255))
    competitor_place_id = Column(String(255))
    competitor_rating = Column(Float)
    competitor_reviews = Column(Integer)
    similarity_score = Column(Float)  # How similar they are (0-1)
    distance_meters = Column(Float)  # Distance from original business
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    business = relationship("Business", back_populates="competitors")

class BusinessHistory(Base):
    """Track changes to businesses over time"""
    __tablename__ = 'business_history'
    
    id = Column(Integer, primary_key=True)
    business_id = Column(String(64), ForeignKey('businesses.id'), index=True)
    field_name = Column(String(100))
    old_value = Column(Text)
    new_value = Column(Text)
    change_type = Column(String(50))  # update, delete, create
    changed_at = Column(DateTime, default=datetime.utcnow)
    changed_by = Column(String(255))  # scraper, manual, api
    
    # Relationships
    business = relationship("Business", back_populates="history")

class ScrapeJob(Base):
    """Track scraping jobs"""
    __tablename__ = 'scrape_jobs'
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String(64), unique=True, index=True)
    query = Column(String(255))
    location = Column(String(255))
    max_results = Column(Integer)
    businesses_found = Column(Integer)
    businesses_new = Column(Integer)
    businesses_updated = Column(Integer)
    status = Column(String(50))  # running, completed, failed
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    duration_seconds = Column(Float)
    error_message = Column(Text)
    config_used = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class ProxyLog(Base):
    """Track proxy usage and performance"""
    __tablename__ = 'proxy_logs'
    
    id = Column(Integer, primary_key=True)
    proxy = Column(String(255))
    success_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    last_used = Column(DateTime)
    response_time_avg = Column(Float)
    banned = Column(Boolean, default=False)
    ban_time = Column(DateTime)
    notes = Column(Text)

class EmailTemplate(Base):
    """Email templates for outreach"""
    __tablename__ = 'email_templates'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    subject = Column(String(255))
    body_html = Column(Text)
    body_text = Column(Text)
    category = Column(String(50))
    variables = Column(JSON)  # Available template variables
    usage_count = Column(Integer, default=0)
    success_rate = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class OutreachCampaign(Base):
    """Track email outreach campaigns"""
    __tablename__ = 'outreach_campaigns'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    template_id = Column(Integer, ForeignKey('email_templates.id'))
    target_businesses = Column(JSON)  # List of business IDs or filters
    emails_sent = Column(Integer, default=0)
    emails_opened = Column(Integer, default=0)
    emails_replied = Column(Integer, default=0)
    status = Column(String(50))
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
