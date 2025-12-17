"""Rate limiting using Redis"""
from fastapi import Request
from typing import Optional
import redis
from datetime import datetime, timedelta

from app.config import settings
from app.utils.errors import RateLimitError

# Redis client
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

# Rate limit configuration
RATE_LIMIT_REQUESTS = 200  # requests per window
RATE_LIMIT_WINDOW = 60      # window in seconds


async def check_rate_limit(clinic_id: str) -> bool:
    """
    Check if clinic has exceeded rate limit
    
    Args:
        clinic_id: Clinic UUID as string
        
    Returns:
        True if within limit, raises RateLimitError otherwise
    """
    key = f"ratelimit:{clinic_id}"
    
    try:
        # Get current count
        current = redis_client.get(key)
        
        if current is None:
            # First request in window
            redis_client.setex(key, RATE_LIMIT_WINDOW, 1)
            return True
        
        current = int(current)
        
        if current >= RATE_LIMIT_REQUESTS:
            # Exceeded limit
            ttl = redis_client.ttl(key)
            raise RateLimitError(retry_after=ttl if ttl > 0 else RATE_LIMIT_WINDOW)
        
        # Increment counter
        redis_client.incr(key)
        return True
        
    except redis.RedisError:
        # If Redis is down, allow request (fail open)
        return True


async def get_rate_limit_status(clinic_id: str) -> dict:
    """
    Get current rate limit status for clinic
    
    Returns:
        {
            "requests_made": int,
            "requests_remaining": int,
            "reset_in_seconds": int
        }
    """
    key = f"ratelimit:{clinic_id}"
    
    try:
        current = redis_client.get(key)
        ttl = redis_client.ttl(key)
        
        if current is None:
            return {
                "requests_made": 0,
                "requests_remaining": RATE_LIMIT_REQUESTS,
                "reset_in_seconds": RATE_LIMIT_WINDOW
            }
        
        current = int(current)
        
        return {
            "requests_made": current,
            "requests_remaining": max(0, RATE_LIMIT_REQUESTS - current),
            "reset_in_seconds": ttl if ttl > 0 else RATE_LIMIT_WINDOW
        }
        
    except redis.RedisError:
        # Default response if Redis is down
        return {
            "requests_made": 0,
            "requests_remaining": RATE_LIMIT_REQUESTS,
            "reset_in_seconds": RATE_LIMIT_WINDOW
        }
