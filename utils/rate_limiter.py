import time
import threading
from collections import deque
from datetime import datetime, timedelta
import logging
import random

class RateLimiter:
    """Advanced rate limiter with multiple strategies"""
    
    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Rate limiting parameters
        self.requests_per_minute = config.get('requests_per_minute', 30)
        self.requests_per_ip = config.get('requests_per_ip', 100)
        self.cooldown_period = config.get('cooldown_period', 60)
        
        # Smart delay settings
        smart_delay = config.get('smart_delay', {})
        self.min_delay = smart_delay.get('min_delay', 1)
        self.max_delay = smart_delay.get('max_delay', 5)
        self.jitter = smart_delay.get('jitter', True)
        
        # Tracking
        self.request_times = deque(maxlen=100)
        self.ip_request_counts = {}
        self.lock = threading.Lock()
        self.last_request_time = 0
        self.consecutive_failures = 0
        
        # Adaptive rate limiting
        self.current_rate = self.requests_per_minute
        self.min_rate = 5
        self.max_rate = self.requests_per_minute
        self.rate_adjustment_factor = 0.9
        
    def wait_if_needed(self, ip_address: str = None):
        """Wait if rate limit would be exceeded"""
        with self.lock:
            now = time.time()
            
            # Clean old requests
            while self.request_times and self.request_times[0] < now - 60:
                self.request_times.popleft()
            
            # Check global rate limit
            if len(self.request_times) >= self.current_rate:
                sleep_time = self.request_times[0] + 60 - now
                if sleep_time > 0:
                    self.logger.debug(f"Rate limit reached, waiting {sleep_time:.2f}s")
                    time.sleep(sleep_time)
            
            # Check IP-based rate limit
            if ip_address and ip_address in self.ip_request_counts:
                if self.ip_request_counts[ip_address] >= self.requests_per_ip:
                    sleep_time = self.cooldown_period
                    self.logger.debug(f"IP {ip_address} rate limit reached, waiting {sleep_time}s")
                    time.sleep(sleep_time)
                    self.ip_request_counts[ip_address] = 0
            
            # Smart delay
            delay = self.calculate_delay()
            if delay > 0:
                time.sleep(delay)
            
            # Update tracking
            self.request_times.append(now)
            if ip_address:
                self.ip_request_counts[ip_address] = self.ip_request_counts.get(ip_address, 0) + 1
            
            self.last_request_time = now
    
    def calculate_delay(self) -> float:
        """Calculate smart delay based on various factors"""
        base_delay = self.min_delay
        
        # Increase delay if we've had failures
        if self.consecutive_failures > 0:
            base_delay *= min(2 ** self.consecutive_failures, 10)
        
        # Add jitter
        if self.jitter:
            jitter_amount = random.uniform(-0.3, 0.3) * base_delay
            base_delay += jitter_amount
        
        # Ensure within bounds
        return max(self.min_delay, min(base_delay, self.max_delay))
    
    def record_success(self):
        """Record a successful request"""
        with self.lock:
            self.consecutive_failures = 0
            # Gradually increase rate on success
            if self.current_rate < self.max_rate:
                self.current_rate = min(
                    self.current_rate * 1.05,
                    self.max_rate
                )
    
    def record_failure(self):
        """Record a failed request"""
        with self.lock:
            self.consecutive_failures += 1
            # Decrease rate on failure
            if self.current_rate > self.min_rate:
                self.current_rate = max(
                    self.current_rate * self.rate_adjustment_factor,
                    self.min_rate
                )
    
    def get_wait_time(self) -> float:
        """Get current wait time without actually waiting"""
        with self.lock:
            now = time.time()
            if len(self.request_times) >= self.current_rate:
                return max(0, self.request_times[0] + 60 - now)
            return 0
    
    def reset(self):
        """Reset rate limiter"""
        with self.lock:
            self.request_times.clear()
            self.ip_request_counts.clear()
            self.consecutive_failures = 0
            self.current_rate = self.max_rate
            self.logger.info("Rate limiter reset")
    
    def get_stats(self) -> dict:
        """Get rate limiter statistics"""
        with self.lock:
            now = time.time()
            requests_last_minute = len([t for t in self.request_times if t > now - 60])
            
            return {
                'requests_last_minute': requests_last_minute,
                'current_rate_limit': self.current_rate,
                'consecutive_failures': self.consecutive_failures,
                'active_ips': len(self.ip_request_counts),
                'wait_time': self.get_wait_time()
            }

class AdaptiveRateLimiter(RateLimiter):
    """Rate limiter that adapts based on response times"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.response_times = deque(maxlen=50)
        self.target_response_time = config.get('target_response_time', 2.0)
        
    def record_response_time(self, response_time: float):
        """Record response time for adaptive rate limiting"""
        with self.lock:
            self.response_times.append(response_time)
            
            # Adjust rate based on average response time
            if len(self.response_times) > 10:
                avg_response = sum(self.response_times) / len(self.response_times)
                
                if avg_response > self.target_response_time * 1.5:
                    # Too slow, decrease rate
                    self.current_rate = max(
                        self.current_rate * 0.8,
                        self.min_rate
                    )
                elif avg_response < self.target_response_time * 0.7:
                    # Fast responses, can increase rate
                    self.current_rate = min(
                        self.current_rate * 1.1,
                        self.max_rate
                    )
    
    def calculate_delay(self) -> float:
        """Calculate delay with adaptive component"""
        base_delay = super().calculate_delay()
        
        # Add adaptive component based on recent response times
        if len(self.response_times) > 5:
            avg_response = sum(self.response_times) / len(self.response_times)
            if avg_response > self.target_response_time:
                base_delay *= (avg_response / self.target_response_time)
        
        return base_delay

class DistributedRateLimiter:
    """Rate limiter for distributed scraping"""
    
    def __init__(self, redis_client, config: dict):
        self.redis = redis_client
        self.config = config
        self.key_prefix = "rate_limiter:"
        self.logger = logging.getLogger(__name__)
        
    def wait_if_needed(self, key: str = "global"):
        """Distributed rate limiting using Redis"""
        redis_key = f"{self.key_prefix}{key}"
        
        while True:
            current = self.redis.get(redis_key)
            if current is None:
                self.redis.setex(redis_key, 60, 1)
                break
            
            count = int(current)
            if count < self.config.get('requests_per_minute', 30):
                self.redis.incr(redis_key)
                break
            
            # Wait and retry
            time.sleep(1)
    
    def record_failure(self, key: str = "global"):
        """Record failure in distributed system"""
        redis_key = f"{self.key_prefix}failure:{key}"
        self.redis.incr(redis_key)
        self.redis.expire(redis_key, 3600)  # Expire after 1 hour
    
    def get_global_stats(self) -> dict:
        """Get global rate limiting stats"""
        stats = {}
        for key in self.redis.keys(f"{self.key_prefix}*"):
            count = self.redis.get(key)
            stats[key.decode()] = int(count) if count else 0
        return stats
