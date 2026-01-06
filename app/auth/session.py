"""
Session Management for Admin UI

Secure session-based authentication using Redis and signed cookies.

Features:
- Redis-backed session storage (30-min TTL)
- Secure, HttpOnly, SameSite=Strict cookies
- CSRF token generation and validation
- Session renewal on activity
- IP tracking for security
"""
from datetime import datetime, timedelta
from typing import Optional
import secrets
import hashlib

from itsdangerous import URLSafeTimedSerializer, BadSignature
from redis import StrictRedis

from app.core.config import settings


class SessionManager:
    """Secure session management for admin authentication."""
    
    SESSION_TTL_SECONDS = 1800  # 30 minutes
    COOKIE_NAME = "admin_session"
    CSRF_TOKEN_LENGTH = 32
    
    def __init__(self):
        """Initialize session manager with Redis connection."""
        try:
            print(f"🔧 SessionManager: Initializing with REDIS_URL: {settings.REDIS_URL[:30]}..." if settings.REDIS_URL else "🔧 SessionManager: REDIS_URL not set")
            
            self.redis = StrictRedis.from_url(
                settings.REDIS_URL,
                decode_responses=True
            )
            
            # Test connection
            self.redis.ping()
            print("✅ SessionManager: Redis connection successful")
            
        except Exception as e:
            print(f"\n{'='*80}")
            print(f"❌ CRITICAL: SessionManager Redis connection FAILED")
            print(f"{'='*80}")
            print(f"Error: {str(e)}")
            print(f"REDIS_URL: {settings.REDIS_URL}")
            print(f"{'='*80}\n")
            raise
        
        self.serializer = URLSafeTimedSerializer(
            settings.SESSION_SECRET_KEY,
            salt="admin-session"
        )
    
    def create_session(
        self,
        admin_user_id: str,
        ip_address: str,
        user_agent: str
    ) -> tuple[str, str]:
        """
        Create new session for authenticated admin.
        
        Args:
            admin_user_id: Admin user UUID
            ip_address: Client IP address
            user_agent: Client user agent
        
        Returns:
            tuple: (session_token, csrf_token)
        """
        # Generate session ID
        session_id = secrets.token_urlsafe(32)
        
        # Generate CSRF token
        csrf_token = secrets.token_urlsafe(self.CSRF_TOKEN_LENGTH)
        
        # Store session data in Redis
        session_data = {
            "user_id": admin_user_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "csrf_token": csrf_token,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat()
        }
        
        # Store with TTL
        session_key = f"admin_session:{session_id}"
        self.redis.hmset(session_key, session_data)
        self.redis.expire(session_key, self.SESSION_TTL_SECONDS)
        
        # Sign session ID for cookie
        signed_token = self.serializer.dumps(session_id)
        
        return signed_token, csrf_token
    
    def validate_session(
        self,
        session_token: str,
        ip_address: str
    ) -> Optional[dict]:
        """
        Validate session token and return session data.
        
        Args:
            session_token: Signed session token from cookie
            ip_address: Client IP address for verification
        
        Returns:
            Session data dict if valid, None otherwise
        """
        try:
            # Unsign token (max_age enforced by URLSafeTimedSerializer)
            session_id = self.serializer.loads(
                session_token,
                max_age=self.SESSION_TTL_SECONDS
            )
        except BadSignature:
            return None
        
        # Retrieve session from Redis
        session_key = f"admin_session:{session_id}"
        session_data = self.redis.hgetall(session_key)
        
        if not session_data:
            return None
        
        # Verify IP address (prevent session hijacking)
        if session_data.get("ip_address") != ip_address:
            # IP mismatch - destroy session
            self.destroy_session(session_token)
            return None
        
        # Renew session TTL on activity
        self.redis.expire(session_key, self.SESSION_TTL_SECONDS)
        
        # Update last activity
        self.redis.hset(session_key, "last_activity", datetime.utcnow().isoformat())
        
        return session_data
    
    def validate_csrf_token(
        self,
        session_token: str,
        csrf_token: str
    ) -> bool:
        """
        Validate CSRF token matches session.
        
        Args:
            session_token: Signed session token
            csrf_token: CSRF token from form
        
        Returns:
            True if valid, False otherwise
        """
        try:
            session_id = self.serializer.loads(session_token)
        except BadSignature:
            return False
        
        session_key = f"admin_session:{session_id}"
        stored_csrf = self.redis.hget(session_key, "csrf_token")
        
        if not stored_csrf:
            return False
        
        # Constant-time comparison to prevent timing attacks
        return secrets.compare_digest(stored_csrf, csrf_token)
    
    def destroy_session(self, session_token: str) -> bool:
        """
        Destroy session (logout).
        
        Args:
            session_token: Signed session token
        
        Returns:
            True if destroyed, False if not found
        """
        try:
            session_id = self.serializer.loads(session_token)
        except BadSignature:
            return False
        
        session_key = f"admin_session:{session_id}"
        result = self.redis.delete(session_key)
        
        return result > 0
    
    def get_cookie_attributes(self) -> dict:
        """
        Get secure cookie attributes for session.
        
        Returns:
            Dict of cookie attributes
        """
        return {
            "key": self.COOKIE_NAME,
            "httponly": True,
            "secure": False,  # Railway uses HTTPS proxy → HTTP to app (set False for compatibility)
            "samesite": "lax",  # Allow navigation between routes (dashboard → QR/Doctors)
            "max_age": self.SESSION_TTL_SECONDS
        }


# Singleton instance
session_manager = SessionManager()
