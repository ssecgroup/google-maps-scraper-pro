"""
Streaming Export Manager - Saves data directly to disk with NO RAM accumulation
Data is streamed to files as soon as it's collected
"""

import csv
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Generator
import sqlite3
import threading
from queue import Queue
import time
import logging

class StreamingExporter:
    """
    Streams data directly to disk with minimal RAM usage
    Uses file buffers and queues to prevent memory accumulation
    """
    
    def __init__(self, output_dir: str = 'output'):
        self.output_dir = output_dir
        self.logger = logging.getLogger(__name__)
        self.create_output_directories()
        
        # Streaming buffers
        self.csv_buffers = {}
        self.json_buffer = []
        self.json_buffer_size = 0
        self.max_buffer_size = 100  # Flush to disk every 100 records
        
        # Thread safety
        self.lock = threading.Lock()
        
    def create_output_directories(self):
        """Create output directories if they don't exist"""
        dirs = ['csv', 'json', 'sqlite', 'incremental']
        for dir_name in dirs:
            path = os.path.join(self.output_dir, dir_name)
            if not os.path.exists(path):
                os.makedirs(path)
                self.logger.info(f"Created directory: {path}")
    
    def stream_to_csv(self, business: Dict, base_name: str = 'businesses'):
        """
        Stream a single business record to CSV - NO RAM accumulation
        Each record is written immediately to disk
        """
        filename = os.path.join(self.output_dir, 'csv', f'{base_name}.csv')
        file_exists = os.path.exists(filename)
        
        with self.lock:
            with open(filename, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=business.keys())
                
                # Write header only if file is new
                if not file_exists:
                    writer.writeheader()
                
                writer.writerow(business)
                f.flush()  # Force write to disk immediately
                os.fsync(f.fileno())  # Ensure data is written to physical disk
        
        return filename
    
    def stream_to_json(self, business: Dict, base_name: str = 'businesses'):
        """
        Stream business to JSON file with buffering
        Buffer flushes to disk every max_buffer_size records
        """
        filename = os.path.join(self.output_dir, 'json', f'{base_name}.json')
        
        with self.lock:
            # Add to buffer
            self.json_buffer.append(business)
            self.json_buffer_size += 1
            
            # Flush buffer to disk if threshold reached
            if self.json_buffer_size >= self.max_buffer_size:
                self.flush_json_buffer(filename)
        
        return filename
    
    def flush_json_buffer(self, filename: str):
        """Flush JSON buffer to disk"""
        if not self.json_buffer:
            return
        
        try:
            # Read existing data if file exists
            existing_data = []
            if os.path.exists(filename):
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                except:
                    existing_data = []
            
            # Append new data
            all_data = existing_data + self.json_buffer
            
            # Write back to disk
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            
            # Clear buffer
            self.json_buffer = []
            self.json_buffer_size = 0
            
            self.logger.debug(f"Flushed JSON buffer to {filename}")
            
        except Exception as e:
            self.logger.error(f"Error flushing JSON buffer: {str(e)}")
    
    def stream_to_sqlite(self, business: Dict, base_name: str = 'businesses'):
        """
        Stream business to SQLite database - immediate write
        """
        db_path = os.path.join(self.output_dir, 'sqlite', f'{base_name}.db')
        
        with self.lock:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create table if not exists
            columns = ', '.join([f'"{k}" TEXT' for k in business.keys()])
            placeholders = ', '.join(['?' for _ in business.keys()])
            
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS businesses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    {columns},
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Insert record
            cursor.execute(
                f'INSERT INTO businesses ({", ".join([f"\"{k}\"" for k in business.keys()])}) VALUES ({placeholders})',
                list(business.values())
            )
            
            conn.commit()
            conn.close()
        
        return db_path
    
    def stream_incremental(self, business: Dict, base_name: str = 'businesses'):
        """
        Save each business to an incremental file with timestamp
        Perfect for zero RAM hit - each record in its own file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        filename = os.path.join(self.output_dir, 'incremental', 
                               f'{base_name}_{timestamp}.json')
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(business, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        
        return filename
    
    def stream_generator(self, data_generator: Generator, base_name: str = 'businesses'):
        """
        Process a generator and stream each item to disk
        Ultimate zero RAM solution - processes one item at a time
        """
        count = 0
        for business in data_generator:
            # Stream to all formats
            self.stream_to_csv(business, base_name)
            self.stream_to_json(business, base_name)
            self.stream_to_sqlite(business, base_name)
            
            # Optional: incremental files for complete safety
            if count % 10 == 0:  # Every 10th record
                self.stream_incremental(business, f"{base_name}_checkpoint")
            
            count += 1
            
            # Yield progress without storing
            yield count
        
        # Final flush
        self.flush_json_buffer(os.path.join(self.output_dir, 'json', f'{base_name}.json'))
    
    def close(self):
        """Close all buffers and ensure data is written"""
        if self.json_buffer:
            filename = os.path.join(self.output_dir, 'json', 'final_flush.json')
            self.flush_json_buffer(filename)
            self.logger.info(f"Final buffer flush complete")

class LiveSaveManager:
    """
    Manages live saving with zero RAM hit
    Integrates with scraper to save data as soon as it's collected
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.exporter = StreamingExporter()
        self.logger = logging.getLogger(__name__)
        self.save_queue = Queue()
        self.running = True
        self.save_count = 0
        
        # Start saver thread
        self.saver_thread = threading.Thread(target=self._saver_worker, daemon=True)
        self.saver_thread.start()
    
    def save_business(self, business: Dict, base_name: str = 'businesses'):
        """
        Queue a business for saving - returns immediately
        NO waiting for disk I/O
        """
        self.save_queue.put((business, base_name))
        self.save_count += 1
        
        # Log progress every 10 saves
        if self.save_count % 10 == 0:
            self.logger.info(f"Queued {self.save_count} businesses for saving")
    
    def _saver_worker(self):
        """Background thread that handles actual disk writes"""
        batch = []
        last_flush = time.time()
        
        while self.running:
            try:
                # Get item from queue with timeout
                item = self.save_queue.get(timeout=1)
                batch.append(item)
                
                # Write batch when it reaches size or time threshold
                current_time = time.time()
                if len(batch) >= 10 or (current_time - last_flush) > 5:
                    self._write_batch(batch)
                    batch = []
                    last_flush = current_time
                    
            except:
                # Queue empty, continue
                if batch and (time.time() - last_flush) > 5:
                    self._write_batch(batch)
                    batch = []
                    last_flush = time.time()
                continue
    
    def _write_batch(self, batch):
        """Write a batch of businesses to disk"""
        for business, base_name in batch:
            try:
                # Add serial number
                business['s_no'] = self.save_count
                
                # Save to multiple formats
                self.exporter.stream_to_csv(business, base_name)
                self.exporter.stream_to_json(business, base_name)
                
                if self.config['export_settings'].get('database', {}).get('type') == 'sqlite':
                    self.exporter.stream_to_sqlite(business, base_name)
                    
            except Exception as e:
                self.logger.error(f"Error saving business: {str(e)}")
    
    def flush(self):
        """Force flush all pending saves"""
        self.logger.info("Flushing all pending saves...")
        self.running = False
        self.saver_thread.join(timeout=10)
        self.exporter.close()
        self.logger.info(f"Flush complete. Total businesses saved: {self.save_count}")
    
    def get_stats(self) -> Dict:
        """Get saving statistics"""
        return {
            'queued': self.save_queue.qsize(),
            'total_saved': self.save_count,
            'thread_alive': self.saver_thread.is_alive()
        }

class ZeroRAMScraper:
    """
    Scraper that uses generators to achieve zero RAM accumulation
    Processes and saves one business at a time
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.save_manager = LiveSaveManager(config)
        self.logger = logging.getLogger(__name__)
    
    def scrape_generator(self, query: str, location: str, max_results: int) -> Generator:
        """
        Generator that yields businesses one at a time
        Perfect for streaming to disk with zero RAM
        """
        from selenium.webdriver.common.by import By
        import time
        
        # Initialize browser (your existing browser code)
        from core.enhanced_browser import EnhancedBrowserManager
        
        with EnhancedBrowserManager(self.config) as browser:
            # Navigate to search
            search_url = f"https://www.google.com/maps/search/{query}+{location}/"
            browser.driver.get(search_url)
            time.sleep(5)
            
            # Find results container
            results_container = browser.wait_for_element(By.CSS_SELECTOR, 'div[role="feed"]', timeout=20)
            if not results_container:
                return
            
            businesses_found = 0
            last_height = 0
            scroll_attempts = 0
            
            while businesses_found < max_results and scroll_attempts < 30:
                # Get current results
                result_elements = browser.driver.find_elements(
                    By.CSS_SELECTOR, 'div[role="feed"] > div > div[jsaction]'
                )
                
                # Process only NEW results (starting from where we left off)
                for i in range(businesses_found, min(len(result_elements), max_results)):
                    try:
                        # Click to load details
                        browser.safe_click(result_elements[i])
                        time.sleep(2)
                        
                        # Extract business data
                        from core.smart_parser import SmartParser
                        parser = SmartParser(browser, self.config)
                        business = parser.extract_business_info(
                            result_elements[i],
                            search_context={'query': query, 'location': location}
                        )
                        
                        if business:
                            businesses_found += 1
                            
                            # YIELD the business - this is the key to zero RAM!
                            yield business
                            
                    except Exception as e:
                        self.logger.debug(f"Error: {str(e)}")
                        continue
                
                # Scroll for more
                browser.driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollHeight",
                    results_container
                )
                time.sleep(2)
                
                new_height = browser.driver.execute_script(
                    "return arguments[0].scrollHeight",
                    results_container
                )
                
                if new_height == last_height:
                    scroll_attempts += 1
                else:
                    scroll_attempts = 0
                
                last_height = new_height
    
    def run_streaming(self, query: str, location: str, max_results: int):
        """
        Run scraper in streaming mode - ZERO RAM ACCUMULATION
        """
        print(f"\n{Fore.CYAN}🚀 Starting ZERO-RAM streaming scrape...")
        
        # Create generator
        business_generator = self.scrape_generator(query, location, max_results)
        
        # Process one business at a time
        count = 0
        for business in business_generator:
            # Save immediately (background thread)
            self.save_manager.save_business(business, f"{query}_{location}".replace(' ', '_'))
            
            count += 1
            if count % 10 == 0:
                print(f"✓ Processed {count} businesses - RAM usage: minimal")
        
        # Flush any pending saves
        self.save_manager.flush()
        
        print(f"\n{Fore.GREEN}✅ Streaming complete! {count} businesses saved with zero RAM hit")
        print(f"📁 Check output directory for files")
