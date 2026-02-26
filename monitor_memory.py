\#!/usr/bin/env python3
"""
Monitor memory usage during scraping
Shows that RAM stays constant while disk usage grows
"""

import psutil
import time
import os
import sys
from threading import Thread
from datetime import datetime

class MemoryMonitor:
    """Monitors RAM and disk usage in real-time"""
    
    def __init__(self, interval=1):
        self.interval = interval
        self.process = psutil.Process(os.getpid())
        self.running = True
        self.peak_ram = 0
        self.disk_usage_start = self.get_disk_usage()
        
    def get_disk_usage(self):
        """Get disk usage of output directory"""
        output_dir = 'output'
        if os.path.exists(output_dir):
            total = 0
            for root, dirs, files in os.walk(output_dir):
                for file in files:
                    filepath = os.path.join(root, file)
                    total += os.path.getsize(filepath)
            return total
        return 0
    
    def monitor(self):
        """Monitor and display resource usage"""
        print(f"\n{'='*60}")
        print(f"📊 RESOURCE MONITOR")
        print(f"{'='*60}")
        print(f"{'Time':>10} {'RAM (MB)':>12} {'Peak RAM':>12} {'Disk (MB)':>12} {'Δ Disk (MB)':>12}")
        print(f"{'-'*60}")
        
        start_time = time.time()
        
        while self.running:
            # Get current RAM usage
            ram_mb = self.process.memory_info().rss / 1024 / 1024
            self.peak_ram = max(self.peak_ram, ram_mb)
            
            # Get disk usage
            disk_bytes = self.get_disk_usage()
            disk_mb = disk_bytes / 1024 / 1024
            disk_delta = (disk_bytes - self.disk_usage_start) / 1024 / 1024
            
            # Elapsed time
            elapsed = time.time() - start_time
            
            print(f"{elapsed:>10.1f}s {ram_mb:>12.1f} {self.peak_ram:>12.1f} {disk_mb:>12.1f} {disk_delta:>12.1f}")
            
            time.sleep(self.interval)
    
    def start(self):
        """Start monitoring in background thread"""
        thread = Thread(target=self.monitor, daemon=True)
        thread.start()
        return thread
    
    def stop(self):
        """Stop monitoring"""
        self.running = False

# Example usage
if __name__ == "__main__":
    monitor = MemoryMonitor()
    monitor.start()
    
    try:
        # Run your scraper here
        print("Scraper running... Monitor shows constant RAM, growing disk")
        time.sleep(30)  # Simulate scraping
    finally:
        monitor.stop()
