import sqlite3
import psycopg2
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, JSON, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from datetime import datetime
import json
import logging
import os
from typing import List, Dict, Optional, Any
from contextlib import contextmanager

Base = declarative_base()

class Business(Base):
    """SQLAlchemy Business Model"""
    __tablename__ = 'businesses'
    
    id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    rating = Column(Float)
    reviews = Column(Integer)
    category = Column(String(255))
    description = Column(Text)
    phone_numbers = Column(JSON)
    primary_phone = Column(String(50))
    emails = Column(JSON)
    primary_email = Column(String(255))
    website = Column(String(500))
    social_media = Column(JSON)
    address = Column(Text)
    coordinates = Column(JSON)
    place_id = Column(String(255))
    zip_code = Column(String(20))
    opening_hours = Column(JSON)
    price_range = Column(String(10))
    amenities = Column(JSON)
    verified = Column(Boolean, default=False)
    claimed = Column(Boolean, default=False)
    data_completeness = Column(Float)
    confidence_score = Column(Float)
    search_query = Column(String(255))
    search_location = Column(String(255))
    scraped_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    enrichment_data = Column(JSON)
    tags = Column(JSON)

class DatabaseManager:
    """Manages database operations for multiple database types"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.db_type = config.get('export_settings', {}).get('database', {}).get('type', 'sqlite')
        self.connection_string = config.get('export_settings', {}).get('database', {}).get('connection_string', 'sqlite:///business_data.db')
        self.setup_logging()
        self.engine = None
        self.Session = None
        self.connect()
        
    def setup_logging(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def connect(self):
        """Establish database connection"""
        try:
            if self.db_type == 'sqlite':
                self.engine = create_engine(
                    self.connection_string,
                    poolclass=QueuePool,
                    pool_size=10,
                    max_overflow=20,
                    pool_pre_ping=True
                )
            elif self.db_type == 'postgresql':
                self.engine = create_engine(
                    self.connection_string,
                    pool_size=10,
                    max_overflow=20,
                    pool_pre_ping=True
                )
            elif self.db_type == 'mysql':
                self.engine = create_engine(
                    self.connection_string,
                    pool_size=10,
                    max_overflow=20,
                    pool_pre_ping=True
                )
            
            # Create tables
            Base.metadata.create_all(self.engine)
            self.Session = sessionmaker(bind=self.engine)
            
            self.logger.info(f"✅ Connected to {self.db_type} database")
            
        except Exception as e:
            self.logger.error(f"❌ Database connection failed: {str(e)}")
            raise
    
    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations"""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            self.logger.error(f"Session error: {str(e)}")
            raise
        finally:
            session.close()
    
    def insert_business(self, business_data: Dict) -> bool:
        """Insert or update a business record"""
        try:
            with self.session_scope() as session:
                # Check if exists
                existing = session.query(Business).filter_by(id=business_data.get('id')).first()
                
                if existing:
                    # Update
                    for key, value in business_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                    existing.updated_at = datetime.utcnow()
                    self.logger.debug(f"Updated business: {business_data.get('name')}")
                else:
                    # Insert
                    business = Business(**business_data)
                    session.add(business)
                    self.logger.debug(f"Inserted business: {business_data.get('name')}")
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to insert business: {str(e)}")
            return False
    
    def insert_many(self, businesses: List[Dict]) -> int:
        """Insert multiple businesses efficiently"""
        inserted = 0
        
        try:
            with self.session_scope() as session:
                for business_data in businesses:
                    try:
                        existing = session.query(Business).filter_by(id=business_data.get('id')).first()
                        
                        if existing:
                            for key, value in business_data.items():
                                if hasattr(existing, key):
                                    setattr(existing, key, value)
                            existing.updated_at = datetime.utcnow()
                        else:
                            business = Business(**business_data)
                            session.add(business)
                        
                        inserted += 1
                        
                        # Commit in batches
                        if inserted % 100 == 0:
                            session.flush()
                            self.logger.info(f"Processed {inserted} records")
                            
                    except Exception as e:
                        self.logger.error(f"Error processing business: {str(e)}")
                        continue
                        
        except Exception as e:
            self.logger.error(f"Batch insert failed: {str(e)}")
        
        return inserted
    
    def query_businesses(self, filters: Dict = None, limit: int = 100) -> List[Business]:
        """Query businesses with filters"""
        try:
            with self.session_scope() as session:
                query = session.query(Business)
                
                if filters:
                    for key, value in filters.items():
                        if hasattr(Business, key):
                            query = query.filter(getattr(Business, key) == value)
                
                return query.limit(limit).all()
                
        except Exception as e:
            self.logger.error(f"Query failed: {str(e)}")
            return []
    
    def export_to_csv(self, filename: str, query=None):
        """Export query results to CSV"""
        import pandas as pd
        
        try:
            with self.session_scope() as session:
                if query is None:
                    query = session.query(Business)
                
                # Convert to DataFrame
                df = pd.read_sql(query.statement, session.bind)
                df.to_csv(filename, index=False)
                self.logger.info(f"Exported to CSV: {filename}")
                
        except Exception as e:
            self.logger.error(f"CSV export failed: {str(e)}")
    
    def get_statistics(self) -> Dict:
        """Get database statistics"""
        try:
            with self.session_scope() as session:
                total = session.query(Business).count()
                with_phone = session.query(Business).filter(Business.phone_numbers != '[]').count()
                with_email = session.query(Business).filter(Business.emails != '[]').count()
                with_website = session.query(Business).filter(Business.website.isnot(None)).count()
                
                avg_rating = session.query(Business).with_entities(
                    func.avg(Business.rating)
                ).scalar() or 0
                
                return {
                    'total_businesses': total,
                    'with_phone': with_phone,
                    'with_email': with_email,
                    'with_website': with_website,
                    'avg_rating': round(avg_rating, 2),
                    'last_updated': datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {str(e)}")
            return {}
    
    def backup_database(self, backup_path: str = None):
        """Create database backup"""
        if not backup_path:
            backup_path = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        
        try:
            if self.db_type == 'sqlite':
                # SQLite backup
                import shutil
                db_path = self.connection_string.replace('sqlite:///', '')
                shutil.copy2(db_path, backup_path)
                self.logger.info(f"Database backed up to: {backup_path}")
            else:
                # For PostgreSQL/MySQL, use dump commands
                self.logger.info(f"Backup functionality for {self.db_type} requires external tools")
                
        except Exception as e:
            self.logger.error(f"Backup failed: {str(e)}")
    
    def close(self):
        """Close database connection"""
        if self.engine:
            self.engine.dispose()
            self.logger.info("Database connection closed")
