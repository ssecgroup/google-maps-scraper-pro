#!/usr/bin/env python3
"""
Google Maps Business Scraper Pro 5.0
ULTIMATE EDITION - Manual + Auto Mode, Zero RAM, Checkpoint Handling
Author: sssecgroup
Version: 5.0.0
"""

import json
import time
import logging
import argparse
import random
import signal
import sys
import os
import re
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Generator, Set
from colorama import Fore, Style, init
from tqdm import tqdm
from dotenv import load_dotenv
import warnings
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from queue import Queue
import csv
import sqlite3
import pandas as pd
import hashlib
import glob
import shutil

# Import enhanced browser
from core.enhanced_browser import EnhancedBrowserManager
from core.smart_parser import SmartParser

# Suppress warnings
warnings.filterwarnings("ignore")

# Load environment variables
load_dotenv()

# Initialize colorama
init(autoreset=True)

# ============================================================================
# CHECKPOINT MANAGER ❤ https://github/ssecgroup
# ============================================================================

class CheckpointManager:
    """Manages checkpoints for auto-resume and final conversion"""
    
    def __init__(self, base_name: str, checkpoint_dir: str = 'output1/checkpoints', 
                 final_dir: str = 'output1/final'):
        self.base_name = base_name
        self.checkpoint_dir = checkpoint_dir
        self.final_dir = final_dir
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.checkpoint_file = None
        self.processed_ids: Set[str] = set()
        self.last_checkpoint_count = 0
        self.checkpoint_interval = 100
        self.shutdown_requested = False
        self.shutdown_count = 0
        
        # Create directories
        os.makedirs(checkpoint_dir, exist_ok=True)
        os.makedirs(final_dir, exist_ok=True)
        os.makedirs(os.path.join(final_dir, 'csv'), exist_ok=True)
        os.makedirs(os.path.join(final_dir, 'excel'), exist_ok=True)
        os.makedirs(os.path.join(final_dir, 'json'), exist_ok=True)
        os.makedirs(os.path.join(final_dir, 'html'), exist_ok=True)
        os.makedirs(os.path.join(final_dir, 'summary'), exist_ok=True)
        os.makedirs('output1/logs', exist_ok=True)
        
        # Setup logging
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging to file"""
        log_file = os.path.join('output1/logs', f'scraper_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def generate_business_id(self, business: Dict) -> str:
        """Generate unique ID for business"""
        name = business.get('name', '')
        phone = business.get('phone', '')
        address = business.get('address', '')
        # Use first 50 chars of name + phone + address hash
        unique_str = f"{name[:50]}|{phone}|{address}"
        return hashlib.md5(unique_str.encode()).hexdigest()
    
    def is_processed(self, business: Dict) -> bool:
        """Check if business was already processed"""
        business_id = business.get('_id') or self.generate_business_id(business)
        return business_id in self.processed_ids
    
    def save_checkpoint(self, businesses: List[Dict], count: int):
        """Save checkpoint file"""
        checkpoint_file = os.path.join(
            self.checkpoint_dir, 
            f"{self.base_name}_checkpoint_{count}.jsonl"
        )
        
        try:
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                for business in businesses:
                    # Add ID if not present
                    if '_id' not in business:
                        business['_id'] = self.generate_business_id(business)
                    
                    f.write(json.dumps(business, ensure_ascii=False) + '\n')
                    self.processed_ids.add(business['_id'])
            
            self.last_checkpoint_count = count
            self.checkpoint_file = checkpoint_file
            self.logger.info(f"{Fore.GREEN}   Checkpoint saved: {os.path.basename(checkpoint_file)}")
            
        except Exception as e:
            self.logger.error(f"{Fore.RED}  ✗ Failed to save checkpoint: {e}")
    
    def convert_to_final(self):
        """Convert checkpoint to final formats"""
        if not self.checkpoint_file or not os.path.exists(self.checkpoint_file):
            self.logger.warning("No checkpoint file to convert")
            return
        
        self.logger.info(f"\n{Fore.CYAN} Converting to final formats...")
        
        # Read all businesses from checkpoint
        businesses = []
        try:
            with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        businesses.append(json.loads(line))
        except Exception as e:
            self.logger.error(f"Failed to read checkpoint: {e}")
            return
        
        if not businesses:
            self.logger.warning("No businesses in checkpoint")
            return
        
        self.logger.info(f"Loaded {len(businesses)} businesses from checkpoint")
        
        # Save to final formats
        self.save_to_csv(businesses)
        self.save_to_excel(businesses)
        self.save_to_json(businesses)
        self.generate_html_report(businesses)
        self.generate_summary(businesses)
    
    def save_to_csv(self, businesses: List[Dict]):
        """Save to CSV"""
        filename = os.path.join(self.final_dir, 'csv', f'{self.base_name}_{self.timestamp}.csv')
        
        try:
            if businesses:
                # Flatten nested structures for CSV
                flat_businesses = []
                for b in businesses:
                    flat_b = {}
                    for key, value in b.items():
                        if isinstance(value, (dict, list)):
                            flat_b[key] = json.dumps(value, ensure_ascii=False)
                        else:
                            flat_b[key] = value
                    flat_businesses.append(flat_b)
                
                df = pd.DataFrame(flat_businesses)
                df.to_csv(filename, index=False, encoding='utf-8-sig')
                self.logger.info(f"{Fore.GREEN}  ✓ CSV: {os.path.basename(filename)}")
        except Exception as e:
            self.logger.error(f"CSV export failed: {e}")
    
    def save_to_excel(self, businesses: List[Dict]):
        """Save to Excel"""
        filename = os.path.join(self.final_dir, 'excel', f'{self.base_name}_{self.timestamp}.xlsx')
        
        try:
            if businesses:
                df = pd.DataFrame(businesses)
                df.to_excel(filename, index=False)
                self.logger.info(f"{Fore.GREEN}  ✓ Excel: {os.path.basename(filename)}")
        except Exception as e:
            self.logger.error(f"Excel export failed: {e}")
    
    def save_to_json(self, businesses: List[Dict]):
        """Save to JSON"""
        filename = os.path.join(self.final_dir, 'json', f'{self.base_name}_{self.timestamp}.json')
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(businesses, f, indent=2, ensure_ascii=False, default=str)
            self.logger.info(f"{Fore.GREEN}  ✓ JSON: {os.path.basename(filename)}")
        except Exception as e:
            self.logger.error(f"JSON export failed: {e}")
    
    def generate_html_report(self, businesses: List[Dict]):
        """Generate HTML report"""
        filename = os.path.join(self.final_dir, 'html', f'report_{self.base_name}_{self.timestamp}.html')
        
        try:
            total = len(businesses)
            with_phone = sum(1 for b in businesses if b.get('phone'))
            with_website = sum(1 for b in businesses if b.get('website'))
            with_address = sum(1 for b in businesses if b.get('address'))
            
            html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Business Scraping Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        h1 {{ color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }}
        .stat-card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .stat-value {{ font-size: 32px; font-weight: bold; color: #4CAF50; }}
        table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; }}
        th {{ background: #4CAF50; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid #eee; }}
        tr:hover {{ background: #f5f5f5; }}
    </style>
</head>
<body>
    <h1> Business Scraping Report</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-value">{total}</div>
            <div>Total Businesses</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{with_phone}</div>
            <div>With Phone</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{with_website}</div>
            <div>With Website</div>
        </div>
    </div>
    
    <h2> Business Details</h2>
    <table>
        <tr>
            <th>#</th>
            <th>Name</th>
            <th>Phone</th>
            <th>Website</th>
            <th>Address</th>
            <th>Rating</th>
        </tr>"""
            
            for i, b in enumerate(businesses[:100]):
                html += f"""
        <tr>
            <td>{i+1}</td>
            <td>{b.get('name', 'N/A')}</td>
            <td>{b.get('phone', 'N/A')}</td>
            <td><a href="{b.get('website', '#')}">Link</a></td>
            <td>{b.get('address', 'N/A')}</td>
            <td>{b.get('rating', 'N/A')}</td>
        </tr>"""
            
            html += """
    </table>
</body>
</html>"""
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html)
            
            self.logger.info(f"{Fore.GREEN}  ✓ HTML: {os.path.basename(filename)}")
        except Exception as e:
            self.logger.error(f"HTML export failed: {e}")
    
    def generate_summary(self, businesses: List[Dict]):
        """Generate text summary"""
        filename = os.path.join(self.final_dir, 'summary', f'summary_{self.base_name}_{self.timestamp}.txt')
        
        try:
            total = len(businesses)
            with_phone = sum(1 for b in businesses if b.get('phone'))
            with_website = sum(1 for b in businesses if b.get('website'))
            
            summary = f"""
{'='*60}
BUSINESS SCRAPING SUMMARY
{'='*60}

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Base Name: {self.base_name}
Total Businesses: {total}

{'='*60}
STATISTICS
{'='*60}
With Phone: {with_phone} ({with_phone/total*100:.1f}%)
With Website: {with_website} ({with_website/total*100:.1f}%)

{'='*60}
FIRST 10 BUSINESSES
{'='*60}
"""
            
            for i, b in enumerate(businesses[:10]):
                summary += f"""
{i+1}. {b.get('name', 'N/A')}
   Phone: {b.get('phone', 'N/A')}
   Website: {b.get('website', 'N/A')}
   Address: {b.get('address', 'N/A')}
"""
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(summary)
            
            self.logger.info(f"{Fore.GREEN}  ✓ Summary: {os.path.basename(filename)}")
        except Exception as e:
            self.logger.error(f"Summary export failed: {e}")


# ============================================================================
# MAIN SCRAPER
# ============================================================================

class GoogleMapsScraperPro:
    """Main scraper class with manual and auto modes"""
    
    def __init__(self, config_file: str = 'config_pro.json'):
        self.config_file = config_file
        self.load_config()
        self.setup_logging()
        self.checkpoint = None
        self.start_time = None
        self.businesses = []
        self.interrupted = False
        self.interrupt_count = 0
        self.setup_signal_handlers()
        
    def load_config(self):
        """Load configuration"""
        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
            print(f"{Fore.GREEN}✓ Configuration loaded")
        except:
            self.config = {
                "advanced_settings": {
                    "headless": False,
                    "rate_limiting": {"smart_delay": {"min_delay": 1, "max_delay": 2}}
                }
            }
    
    def setup_logging(self):
        """Setup logging"""
        log_file = os.path.join('output1/logs', f'scraper_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(f" Logging to: {log_file}")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful Ctrl+C behavior"""
        def signal_handler(signum, frame):
            self.interrupt_count += 1
            
            if self.interrupt_count == 1:
                # First Ctrl+C - Skip current item and continue
                print(f"\n{Fore.YELLOW}⚠ First Ctrl+C detected: Skipping current item and continuing...")
                print(f"{Fore.YELLOW}   Press Ctrl+C again within 2 seconds to force exit")
                self.interrupted = True
                
                # Set a timer for second Ctrl+C
                def reset_interrupt():
                    time.sleep(2)
                    self.interrupt_count = 0
                    self.interrupted = False
                
                threading.Thread(target=reset_interrupt, daemon=True).start()
                
            elif self.interrupt_count == 2:
                # Second Ctrl+C within 2 seconds - Force exit
                print(f"\n{Fore.RED}⚠ Second Ctrl+C detected: Forcing immediate exit!")
                
                # Save final checkpoint
                if self.checkpoint and self.businesses:
                    print(f"\n{Fore.CYAN} Saving final checkpoint before exit...")
                    self.checkpoint.save_checkpoint(self.businesses, len(self.businesses))
                    self.checkpoint.convert_to_final()
                
                sys.exit(1)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def extract_phone_from_text(self, text: str) -> Optional[str]:
        """Extract phone number from text"""
        # Common phone patterns
        patterns = [
            r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'(\+?\d{1,3}[-.\s]?)?\d{10}',
            r'(\+?\d{1,3}[-.\s]?)?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return None
    
    def extract_rating_from_text(self, text: str) -> Optional[float]:
        """Extract rating from text"""
        # Look for patterns like "4.5" or "4,5"
        patterns = [
            r'(\d+\.\d+)',
            r'(\d+,\d+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                # Usually the first number is the rating
                try:
                    return float(matches[0].replace(',', '.'))
                except:
                    pass
        return None
    
    def manual_mode(self, max_results: int = 500):
        """
        Manual mode - user performs search, script scrapes results
        """
        print(f"\n{Fore.MAGENTA}{'='*60}")
        print(f"{Fore.MAGENTA} MANUAL SEARCH MODE")
        print(f"{Fore.MAGENTA}{'='*60}")
        print(f"{Fore.CYAN}1. Browser will open to Google Maps")
        print(f"{Fore.CYAN}2. Type your search (e.g., 'restaurants in Tiruppur')")
        print(f"{Fore.CYAN}3. Wait for results to load")
        print(f"{Fore.CYAN}4. Return here and press Enter")
        print(f"{Fore.MAGENTA}{'='*60}\n")
        
        # Initialize browser
        browser = EnhancedBrowserManager(self.config)
        
        try:
            browser.start_browser()
            
            # Navigate to Google Maps
            browser.driver.get("https://www.google.com/maps")
            self.logger.info(" Browser opened to Google Maps")
            
            # Wait for user to perform search
            input(f"{Fore.YELLOW} Press Enter AFTER you've performed your search and results are loaded...")
            
            # Give a moment for results to settle
            time.sleep(2)
            
            # Check for business cards
            cards = browser.get_business_cards()
            self.logger.info(f" Found {len(cards)} business cards")
            
            if len(cards) == 0:
                self.logger.error(" No business cards found! Make sure you're on a search results page.")
                return
            
            # Let user decide how many to scrape
            print(f"\n{Fore.CYAN}Found {len(cards)} businesses")
            print(f"{Fore.CYAN}Will scrape up to {max_results} businesses")
            confirm = input(f"{Fore.YELLOW}Start scraping? (y/n): ").lower()
            
            if confirm != 'y':
                self.logger.info("Scraping cancelled by user")
                return
            
            # Initialize checkpoint
            base_name = f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.checkpoint = CheckpointManager(base_name)
            
            self.start_time = time.time()
            self.businesses = []
            
            print(f"\n{Fore.MAGENTA}{'='*60}")
            print(f"{Fore.MAGENTA} STARTING SCRAPE")
            print(f"{Fore.MAGENTA}{'='*60}")
            
            # Create parser with driver
            parser = SmartParser(browser.driver)
            self.logger.info(" SmartParser initialized with driver")
            
            # Progress bar
            pbar = tqdm(total=max_results, desc="Scraping", unit="businesses")
            
            # Track processed indices
            processed_indices = set()
            failed_cards = set()
            stagnant_count = 0
            
            while len(self.businesses) < max_results and stagnant_count < 10:
                # Check for interrupt (skip current item)
                if self.interrupted:
                    self.interrupted = False
                    self.logger.info("Skipping current item due to interrupt")
                    continue
                
                # Get current cards (refresh to avoid stale)
                try:
                    current_cards = browser.get_business_cards()
                except Exception as e:
                    self.logger.error(f"Error getting cards: {e}")
                    time.sleep(2)
                    continue
                
                if len(current_cards) == 0:
                    self.logger.info("No more cards available")
                    break
                
                # Find new cards to process (skip already processed AND failed)
                new_indices = []
                for i in range(min(len(current_cards), max_results)):
                    if i not in processed_indices and i not in failed_cards:
                        new_indices.append(i)
                
                if not new_indices:
                    stagnant_count += 1
                    time.sleep(1)
                    continue
                
                stagnant_count = 0
                
                # Process new cards
                for idx in new_indices:
                    if len(self.businesses) >= max_results:
                        break
                    
                    # Check for interrupt (skip current item)
                    if self.interrupted:
                        self.interrupted = False
                        self.logger.info("Skipping current item due to interrupt")
                        continue
                    
                    try:
                        card = current_cards[idx]
                        
                        # Scroll into view
                        try:
                            browser.driver.execute_script(
                                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                                card
                            )
                            time.sleep(0.5)
                        except:
                            pass
                        
                        # Click on card
                        if not browser.safe_click(card):
                            failed_cards.add(idx)
                            continue
                        
                        time.sleep(1)
                        
                        # Get card text for extraction
                        card_text = card.text
                        
                        # Extract name using SmartParser
                        try:
                            name = parser.extract_name(card)
                        except:
                            # Fallback: try to extract from card text
                            lines = card_text.split('\n')
                            name = lines[0] if lines else None
                        
                        if name:
                            # Create business dict
                            business = {
                                'name': name,
                                'phone': self.extract_phone_from_text(card_text),
                                'website': None,
                                'address': None,
                                'rating': self.extract_rating_from_text(card_text),
                                'reviews': None,
                                'category': None,
                                'scraped_at': time.time(),
                                'mode': 'manual'
                            }
                            
                            # Try to get more details from the page after click
                            try:
                                # Look for phone in the detail view
                                phone_elements = browser.driver.find_elements(By.CSS_SELECTOR, 'button[data-item-id*="phone"], a[href^="tel:"]')
                                if phone_elements:
                                    business['phone'] = phone_elements[0].text or phone_elements[0].get_attribute('href', '').replace('tel:', '')
                                
                                # Look for website
                                website_elements = browser.driver.find_elements(By.CSS_SELECTOR, 'a[data-item-id*="authority"], a[href^="http"]')
                                for elem in website_elements:
                                    href = elem.get_attribute('href')
                                    if href and 'google.com' not in href and href.startswith('http'):
                                        business['website'] = href
                                        break
                                
                                # Look for address
                                address_elements = browser.driver.find_elements(By.CSS_SELECTOR, 'button[data-item-id*="address"]')
                                if address_elements:
                                    business['address'] = address_elements[0].text
                                
                                # Look for category
                                category_elements = browser.driver.find_elements(By.CSS_SELECTOR, 'button[jsaction*="category"]')
                                if category_elements:
                                    business['category'] = category_elements[0].text
                                    
                            except:
                                pass
                            
                            # Check for duplicate
                            if not self.checkpoint.is_processed(business):
                                self.businesses.append(business)
                                processed_indices.add(idx)
                                pbar.update(1)
                                
                                # Show success
                                name_short = business['name'][:40] + "..." if len(business['name']) > 40 else business['name']
                                icons = []
                                if business.get('phone'): icons.append("📞")
                                if business.get('website'): icons.append("🌐")
                                if business.get('address'): icons.append("📍")
                                if business.get('rating'): icons.append("⭐")
                                print(f"\n{Fore.GREEN}    #{len(self.businesses)}: {name_short} {' '.join(icons)}")
                                
                                # Save checkpoint every 10 businesses
                                if len(self.businesses) % 10 == 0:
                                    self.checkpoint.save_checkpoint(
                                        self.businesses[-10:],
                                        len(self.businesses)
                                    )
                                    print(f"{Fore.CYAN} Progress: {len(self.businesses)} businesses scraped")
                            else:
                                # Duplicate - mark as processed
                                processed_indices.add(idx)
                        else:
                            # No valid business data
                            failed_cards.add(idx)
                            
                    except StaleElementReferenceException:
                        self.logger.debug(f"Stale element at index {idx}, skipping...")
                        failed_cards.add(idx)
                        continue
                    except Exception as e:
                        self.logger.debug(f"Error at index {idx}: {e}")
                        failed_cards.add(idx)
                        continue
                    
                    # Small pause between cards
                    time.sleep(0.5)
            
            pbar.close()
            
            # Save final checkpoint
            if self.businesses:
                self.checkpoint.save_checkpoint(self.businesses, len(self.businesses))
                self.checkpoint.convert_to_final()
            
            # Show summary
            self.show_summary()
            
        except Exception as e:
            self.logger.error(f"Error in manual mode: {e}")
            import traceback
            traceback.print_exc()
        finally:
            browser.close_browser()
    
    def show_summary(self):
        """Show summary of scraping"""
        if not self.start_time or not self.businesses:
            return
        
        elapsed = time.time() - self.start_time
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        
        print(f"\n{Fore.GREEN}{'='*60}")
        print(f"{Fore.GREEN} MANUAL SCRAPE COMPLETE!")
        print(f"{Fore.GREEN}{'='*60}")
        print(f"   Businesses scraped: {len(self.businesses)}")
        print(f"   Master file: {self.checkpoint.base_name}")
        print(f"{Fore.GREEN}{'='*60}\n")
        
        # Log to file
        self.logger.info(f"Scraping complete: {len(self.businesses)} businesses in {elapsed:.1f}s")
        self.logger.info(f"Master file: {self.checkpoint.base_name}")
        
        # Print summary
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN} SCRAPING SUMMARY")
        print(f"{Fore.CYAN}{'='*60}")
        print(f"   Time elapsed:     {hours:02d}:{minutes:02d}:{seconds:02d}")
        print(f"   Businesses found: {len(self.businesses)}")
        print(f"   Rate:             {len(self.businesses)/elapsed:.2f}/sec")
        print(f"{Fore.CYAN}{'='*60}\n")
    
    def run(self):
        """Main entry point"""
        print(f"\n{Fore.MAGENTA}{'='*60}")
        print(f"{Fore.MAGENTA} GOOGLE MAPS SCRAPER PRO 5.0")
        print(f"{Fore.MAGENTA}{'='*60}\n")


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Google Maps Scraper Pro 5.0')
    
    # Mode selection
    parser.add_argument('--manual', action='store_true', 
                       help='Manual mode - you control the search')
    parser.add_argument('--auto', action='store_true',
                       help='Auto mode - script performs search')
    
    # Search options
    parser.add_argument('--query', '-q', help='Business type (for auto mode)')
    parser.add_argument('--location', '-l', help='Location (for auto mode)')
    parser.add_argument('--max', '-m', type=int, default=500, help='Max results')
    parser.add_argument('--headless', action='store_true', help='Run headless')
    
    args = parser.parse_args()
    
    # Create directories
    os.makedirs('output1/checkpoints', exist_ok=True)
    os.makedirs('output1/final', exist_ok=True)
    os.makedirs('output1/logs', exist_ok=True)
    
    # Update config
    config = {
        "advanced_settings": {
            "headless": args.headless,
            "rate_limiting": {"smart_delay": {"min_delay": 1, "max_delay": 2}}
        }
    }
    
    # Save temp config
    temp_config = 'temp_config.json'
    with open(temp_config, 'w') as f:
        json.dump(config, f)
    
    # Run scraper
    scraper = GoogleMapsScraperPro(temp_config)
    
    if args.manual:
        # Manual mode
        print(f"\n{Fore.MAGENTA}{'='*60}")
        print(f"{Fore.MAGENTA} ❤ GOOGLE MAPS SCRAPER PRO 5.0 by ssecgroup_shiyanthan k")
        print(f"{Fore.MAGENTA}{'='*60}")
        print(f"   Mode:          {Fore.CYAN}MANUAL")
        print(f"   Headless:      {Fore.CYAN}{args.headless}")
        print(f"   Max results:   {Fore.CYAN}{args.max}")
        print(f"   Log file:      {Fore.CYAN}output1/logs/")
        print(f"{Fore.MAGENTA}{'='*60}\n")
        
        scraper.manual_mode(args.max)
    
    elif args.auto:
        # Auto mode (to be implemented)
        if not args.query or not args.location:
            print(f"{Fore.RED}✗ Auto mode requires --query and --location")
            return
        
        print(f"{Fore.RED}Auto mode coming soon...")
        # scraper.auto_mode(args.query, args.location, args.max)
    
    else:
        parser.print_help()
    
    # Clean up
    try:
        os.remove(temp_config)
    except:
        pass

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⚠ Scraping interrupted by user")
        sys.exit(0)
