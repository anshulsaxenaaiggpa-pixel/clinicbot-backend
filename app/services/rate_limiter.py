"""
Rate Limiting Service - MODULE 5

Redis-based rate limiting per IP and phone number.
Prevents abuse and brute force attacks.
"""
from typing import Tuple, Optional
from datetime import datetime
import redis

from app.services.audit_service import log_rate_limit_block


# Rate limit configuration
RATE_LIMITS = {
    "per_phone_per_minute": {
        "messages": 10,  # Max 10 messages per minute per phone
        "bookings": 3,    # Max 3 booking attempts per minute
    },
    "per_phone_per_hour": {
        "messages": 100,  # Max 100 messages per hour
        "bookings": 10,   # Max 10 booking attempts per hour
    },
    "per_ip_per_minute": {
        "requests": 60,   # Max 60 requests per minute per IP
    }
}


class RateLimiter:
    """
    Redis-based rate limiter.
    
    Implements sliding window rate limiting for abuse prevention.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """Initialize rate limiter with Redis connection."""
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.redis_client.ping()
        except Exception as e:
            print(f"WARNING: Redis not available for rate limiting: {e}")
            self.redis_client = None
    
    def check_rate_limit(
        self,
        identifier: str,       # phone number or IP address
        action: str,           # messages/bookings/requests
        window: str,          # per_minute/per_hour
        limit: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if action is within rate limits.
        
        Args:
            identifier: Phone number or IP address
            action: Type of action (messages/bookings/requests)
            window: Time window (per_minute/per_hour)
            limit: Optional override limit
        
        Returns:
            (allowed: bool, error_message: Optional[str])
        """
        # If Redis unavailable, allow through (fail open for availability)
        if self.redis_client is None:
            return True, None
        
        try:
            # Determine limit configuration
            window_seconds = 60 if window == "per_minute" else 3600
            
            # Get configured limit
            if limit is None:
                # Determine rate limit key
                if identifier.startswith("+"):  # Phone number
                    limit_key = f"per_phone_{window.split('_')[1]}"
                else:  # IP address
                    limit_key = f"per_ip_{window.split('_')[1]}"
                
                limit = RATE_LIMITS.get(limit_key, {}).get(action, 100)
            
            # Create Redis key
            key = f"rate_limit:{window}:{action}:{identifier}"
            
            # Get current count
            current = self.redis_client.get(key)
            current_count = int(current) if current else 0
            
            # Check limit
            if current_count >= limit:
                ttl = self.redis_client.ttl(key)
                error_msg = f"Rate limit exceeded. Try again in {ttl} seconds."
                
                # Log rate limit block
                log_rate_limit_block(identifier, action)
                
                return False, error_msg
            
            # Increment counter
            pipe = self.redis_client.pipeline()
            pipe.incr(key)
            if current_count == 0:
                # Set expiry on first increment
                pipe.expire(key, window_seconds)
            pipe.execute()
            
            return True, None
        
        except Exception as e:
            # On error, fail open (allow request)
            print(f"Rate limit check error: {e}")
            return True, None
    
    def reset_limit(self, identifier: str, action: str, window: str):
        """Reset rate limit for testing or admin override."""
        if self.redis_client is None:
            return
        
        key = f"rate_limit:{window}:{action}:{identifier}"
        self.redis_client.delete(key)


# Global rate limiter instance
_rate_limiter = None


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        import os
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _rate_limiter = RateLimiter(redis_url)
    return _rate_limiter


# Convenience functions
def check_message_rate_limit(phone: str) -> Tuple[bool, Optional[str]]:
    """Check if phone can send more messages."""
    limiter = get_rate_limiter()
    
    # Check per-minute limit
    allowed, error = limiter.check_rate_limit(phone, "messages", "per_minute")
    if not allowed:
        return False, error
    
    # Check per-hour limit
    allowed, error = limiter.check_rate_limit(phone, "messages", "per_hour")
    return allowed, error


def check_booking_rate_limit(phone: str) -> Tuple[bool, Optional[str]]:
    """Check if phone can make more booking attempts."""
    limiter = get_rate_limiter()
    
    # Check per-minute limit
    allowed, error = limiter.check_rate_limit(phone, "bookings", "per_minute")
    if not allowed:
        return False, error
    
    # Check per-hour limit
    allowed, error = limiter.check_rate_limit(phone, "bookings", "per_hour")
    return allowed, error


def check_ip_rate_limit(ip_address: str) -> Tuple[bool, Optional[str]]:
    """Check if IP can make more requests."""
    limiter = get_rate_limiter()
    return limiter.check_rate_limit(ip_address, "requests", "per_minute")
