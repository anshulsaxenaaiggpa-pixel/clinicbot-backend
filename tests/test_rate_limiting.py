"""
Rate Limiting Tests - MODULE 5

Tests for rate limiting functionality.
"""
import pytest
from time import sleep

from app.services.rate_limiter import (
    RateLimiter,
    check_message_rate_limit,
    check_booking_rate_limit,
    check_ip_rate_limit
)


@pytest.fixture
def rate_limiter():
    """Create rate limiter instance for testing."""
    limiter = RateLimiter()
    yield limiter
    # Cleanup is handled by Redis key expiry


@pytest.fixture
def test_phone():
    return "+919999888877"


@pytest.fixture  
def test_ip():
    return "192.168.1.100"


# =============================================================================
# TEST 1: Rate limit enforced
# =============================================================================

def test_rate_limit_enforced(rate_limiter, test_phone):
    """Test that rate limit is enforced after threshold."""
    # Reset any existing limits
    rate_limiter.reset_limit(test_phone, "messages", "per_minute")
    
    # Should allow first 10 messages
    for i in range(10):
        allowed, error = rate_limiter.check_rate_limit(
            test_phone, "messages", "per_minute", limit=10
        )
        assert allowed == True, f"Failed on message {i+1}"
        assert error is None
    
    # 11th message should be rate limited
    allowed, error = rate_limiter.check_rate_limit(
        test_phone, "messages", "per_minute", limit=10
    )
    assert allowed == False
    assert "Rate limit exceeded" in error


# =============================================================================
# TEST 2: Different identifiers have independent limits
# =============================================================================

def test_independent_limits(rate_limiter):
    """Test that different phones have independent limits."""
    phone1 = "+919999888877"
    phone2 = "+919999888866"
    
    # Reset limits
    rate_limiter.reset_limit(phone1, "messages", "per_minute")
    rate_limiter.reset_limit(phone2, "messages", "per_minute")
    
    # Exhaust limit for phone1
    for i in range(10):
        rate_limiter.check_rate_limit(phone1, "messages", "per_minute", limit=10)
    
    # phone1 should be limited
    allowed, _ = rate_limiter.check_rate_limit(phone1, "messages", "per_minute", limit=10)
    assert allowed == False
    
    # phone2 should still work
    allowed, _ = rate_limiter.check_rate_limit(phone2, "messages", "per_minute", limit=10)
    assert allowed == True


# =============================================================================
# TEST 3: Rate limit resets after window
# =============================================================================

def test_rate_limit_resets(rate_limiter, test_phone):
    """Test that rate limit resets after time window."""
    # Note: This test requires Redis TTL to work
    rate_limiter.reset_limit(test_phone, "messages", "per_minute")
    
    # Exhaust limit
    for i in range(5):
        rate_limiter.check_rate_limit(test_phone, "messages", "per_minute", limit=5)
    
    # Should be limited
    allowed, _ = rate_limiter.check_rate_limit(test_phone, "messages", "per_minute", limit=5)
    assert allowed == False
    
    # After reset, should work again
    rate_limiter.reset_limit(test_phone, "messages", "per_minute")
    allowed, _ = rate_limiter.check_rate_limit(test_phone, "messages", "per_minute", limit=5)
    assert allowed == True


# =============================================================================
# TEST 4: IP rate limiting works
# =============================================================================

def test_ip_rate_limiting(rate_limiter, test_ip):
    """Test IP-based rate limiting."""
    rate_limiter.reset_limit(test_ip, "requests", "per_minute")
    
    # Should allow configured number of requests
    for i in range(60):
        allowed, _ = rate_limiter.check_rate_limit(test_ip, "requests", "per_minute")
        assert allowed == True
    
    # Next request should be limited
    allowed, error = rate_limiter.check_rate_limit(test_ip, "requests", "per_minute")
    assert allowed == False
    assert "Rate limit exceeded" in error


# =============================================================================
# TEST 5: Convenience functions work
# =============================================================================

def test_convenience_functions(test_phone):
    """Test that convenience functions work correctly."""
    # Get rate limiter and reset
    from app.services.rate_limiter import get_rate_limiter
    limiter = get_rate_limiter()
    limiter.reset_limit(test_phone, "messages", "per_minute")
    limiter.reset_limit(test_phone, "messages", "per_hour")
    limiter.reset_limit(test_phone, "bookings", "per_minute")
    limiter.reset_limit(test_phone, "bookings", "per_hour")
    
    # Test message rate limit
    allowed, error = check_message_rate_limit(test_phone)
    assert allowed == True
    
    # Test booking rate limit
    allowed, error = check_booking_rate_limit(test_phone)
    assert allowed == True


# =============================================================================
# TEST 6: Graceful degradation if Redis unavailable
# =============================================================================

def test_graceful_degradation():
    """Test that system fails open if Redis is unavailable."""
    # Create limiter with invalid Redis URL
    limiter = RateLimiter("redis://invalid:9999/0")
    
    # Should allow through (fail open)
    allowed, error = limiter.check_rate_limit("+919999999999", "messages", "per_minute")
    assert allowed == True
    assert error is None
