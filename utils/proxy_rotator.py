"""
Proxy Rotator - Rotates proxies to avoid detection
"""

import random
import logging
import os
import time
from typing import Optional, List
from colorama import Fore, Style

class ProxyRotator:
    """Rotates proxies for each browser session"""
    
    def __init__(self, proxy_file: str = 'proxies.txt'):
        self.logger = logging.getLogger(__name__)
        self.proxy_file = proxy_file
        self.proxies = self.load_proxies()
        self.current_index = 0
        self.failed_proxies = set()
        
    def load_proxies(self) -> List[str]:
        """Load proxies from file"""
        proxies = []
        try:
            if os.path.exists(self.proxy_file):
                with open(self.proxy_file, 'r') as f:
                    for line in f:
                        proxy = line.strip()
                        if proxy and not proxy.startswith('#'):
                            proxies.append(proxy)
                self.logger.info(f"{Fore.GREEN}✓ Loaded {len(proxies)} proxies from {self.proxy_file}")
            else:
                self.logger.warning(f"{Fore.YELLOW}⚠ No proxy file found: {self.proxy_file}")
                # Create sample proxy file
                self.create_sample_proxy_file()
        except Exception as e:
            self.logger.error(f"Error loading proxies: {e}")
        
        return proxies
    
    def create_sample_proxy_file(self):
        """Create a sample proxy file"""
        try:
            with open(self.proxy_file, 'w') as f:
                f.write("# Proxy format: protocol://user:pass@host:port\n")
                f.write("# Examples:\n")
                f.write("# http://user:pass@proxy1.example.com:8080\n")
                f.write("# socks5://user:pass@proxy2.example.com:1080\n")
                f.write("# http://proxy3.example.com:8080\n")
            self.logger.info(f"{Fore.GREEN}✓ Created sample proxy file: {self.proxy_file}")
        except:
            pass
    
    def get_proxy(self) -> Optional[str]:
        """Get next proxy from the list"""
        if not self.proxies:
            return None
        
        # Try to get a working proxy
        attempts = 0
        max_attempts = len(self.proxies) * 2
        
        while attempts < max_attempts:
            proxy = random.choice(self.proxies)
            if proxy not in self.failed_proxies:
                self.current_index = (self.current_index + 1) % len(self.proxies)
                return proxy
            attempts += 1
        
        # If all proxies failed, reset and try any
        self.logger.warning("All proxies have failed, resetting failed list")
        self.failed_proxies.clear()
        return random.choice(self.proxies) if self.proxies else None
    
    def mark_failed(self, proxy: str):
        """Mark a proxy as failed"""
        if proxy:
            self.failed_proxies.add(proxy)
            self.logger.warning(f"Proxy marked as failed: {proxy}")
    
    def has_proxies(self) -> bool:
        """Check if any proxies are available"""
        return len(self.proxies) > 0
