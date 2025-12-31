"""
Admin Authentication Service - Sprint Task 1

Handles login, MFA verification, session management, and admin activity logging.
"""
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import jwt
import uuid

from app.models.admin_user import AdminUser, AdminRole
from app.db.session import SessionLocal
from app.services.audit_service import AuditService, EVENT_TYPES


# JWT configuration
JWT_SECRET = None  # Loaded from environment
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Per Access Control Policy
REFRESH_TOKEN_EXPIRE_HOURS = 8     # Absolute maximum session


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class AuthService:
    """Admin authentication and session management."""
    
    @staticmethod
    def authenticate(
        email: str,
        password: str,
        mfa_token: Optional[str] = None,
        ip_address: str = "unknown",
        db: Session = None
    ) -> Tuple[AdminUser, str]:
        """
        Authenticate admin user.
        
        Returns (user, access_token) on success.
        Raises AuthenticationError on failure.
        
        Logs all authentication attempts to audit_log.
        """
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            # Find user
            user = db.query(AdminUser).filter(
                AdminUser.email == email.lower().strip()
            ).first()
            
            if not user:
                # Don't reveal whether email exists
                raise AuthenticationError("Invalid credentials")
            
            # Check if account is locked
            if user.is_locked():
                remaining = (user.locked_until - datetime.utcnow()).seconds // 60
                raise AuthenticationError(f"Account locked. Try again in {remaining} minutes.")
            
            # Check if account is active
            if not user.is_active:
                raise AuthenticationError("Account disabled")
            
            # Verify password
            if not user.verify_password(password):
                user.record_failed_login()
                db.commit()
                
                # Log failed attempt
                AuditService.log_event(
                    event_type="admin_login_failed",
                    actor="admin",
                    actor_id=email,
                    metadata={"reason": "invalid_password", "ip": ip_address},
                    db=db
                )
                
                raise AuthenticationError("Invalid credentials")
            
            # Verify MFA if enabled
            if user.mfa_enabled:
                if not mfa_token:
                    raise AuthenticationError("MFA token required")
                
                if not user.verify_mfa_token(mfa_token):
                    user.record_failed_login()
                    db.commit()
                    
                    # Log failed MFA
                    AuditService.log_event(
                        event_type="admin_mfa_failed",
                        actor="admin",
                        actor_id=email,
                        metadata={"ip": ip_address},
                        db=db
                    )
                    
                    raise AuthenticationError("Invalid MFA token")
            
            # Check if password change required
            if user.requires_password_change():
                # Still allow login but flag in response
                pass
            
            # Success - record login
            user.record_successful_login(ip_address)
            db.commit()
            
            # Generate access token
            access_token = AuthService._create_access_token(user)
            
            # Log successful login
            AuditService.log_event(
                event_type="admin_login_success",
                actor="admin",
                actor_id=str(user.id),
                metadata={
                    "email": user.email,
                    "role": user.role.value,
                    "ip": ip_address,
                    "mfa_used": user.mfa_enabled
                },
                db=db
            )
            
            return user, access_token
        
        finally:
            if should_close:
                db.close()
    
    @staticmethod
    def _create_access_token(user: AdminUser) -> str:
        """Create JWT access token."""
        global JWT_SECRET
        if JWT_SECRET is None:
            # Load from environment
            import os
            JWT_SECRET = os.getenv("JWT_SECRET")
            if not JWT_SECRET:
                raise ValueError("JWT_SECRET environment variable not set")
        
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
            "iat": datetime.utcnow(),
            "jti": str(uuid.uuid4())  # Unique token ID
        }
        
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    @staticmethod
    def verify_token(token: str) -> Dict:
        """
        Verify JWT token and return payload.
        
        Raises jwt.PyJWTError if invalid/expired.
        """
        global JWT_SECRET
        if JWT_SECRET is None:
            import os
            JWT_SECRET = os.getenv("JWT_SECRET")
            if not JWT_SECRET:
                raise ValueError("JWT_SECRET environment variable not set")
        
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    
    @staticmethod
    def get_current_user(token: str, db: Session) -> AdminUser:
        """
        Get current user from JWT token.
        
        Returns AdminUser or raises AuthenticationError.
        """
        try:
            payload = AuthService.verify_token(token)
            user_id = payload.get("sub")
            
            if not user_id:
                raise AuthenticationError("Invalid token")
            
            user = db.query(AdminUser).filter(
                AdminUser.id == user_id,
                AdminUser.is_active == True
            ).first()
            
            if not user:
                raise AuthenticationError("User not found or inactive")
            
            return user
        
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token expired")
        except jwt.PyJWTError:
            raise AuthenticationError("Invalid token")
    
    @staticmethod
    def logout(user_id: str, db: Session):
        """
        Logout user (for audit logging).
        
        Note: JWT tokens can't be invalidated without token blacklist.
        Consider implementing Redis token blacklist for production.
        """
        # Log logout event
        AuditService.log_event(
            event_type="admin_logout",
            actor="admin",
            actor_id=user_id,
            metadata={},
            db=db
        )
    
    @staticmethod
    def change_password(
        user: AdminUser,
        current_password: str,
        new_password: str,
        db: Session
    ):
        """
        Change user password.
        
        Validates current password and enforces password policy.
        """
        # Verify current password
        if not user.verify_password(current_password):
            raise AuthenticationError("Current password incorrect")
        
        # Validate new password (basic policy)
        if len(new_password) < 12:
            raise ValueError("Password must be at least 12 characters")
        
        # Check password complexity (basic check)
        has_upper = any(c.isupper() for c in new_password)
        has_lower = any(c.islower() for c in new_password)
        has_digit = any(c.isdigit() for c in new_password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in new_password)
        
        if not (has_upper and has_lower and has_digit and has_special):
            raise ValueError("Password must contain uppercase, lowercase, digit, and special character")
        
        # Set new password
        user.set_password(new_password)
        user.must_change_password = False
        db.commit()
        
        # Log password change
        AuditService.log_event(
            event_type="admin_password_changed",
            actor="admin",
            actor_id=str(user.id),
            metadata={"email": user.email},
            db=db
        )


# Dependency for protected endpoints
def require_auth(required_role: Optional[AdminRole] = None):
    """
    Dependency to require authentication and optionally specific role.
    
    Usage:
        @router.get("/protected")
        def protected_endpoint(user: AdminUser = Depends(require_auth(AdminRole.SUPER_ADMIN))):
            ...
    """
    def _require_auth(
        authorization: str = Header(None),
        db: Session = Depends(get_db)
    ) -> AdminUser:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        token = authorization.replace("Bearer ", "")
        
        try:
            user = AuthService.get_current_user(token, db)
            
            # Check role if required
            if required_role and not user.has_permission(required_role):
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            
            return user
        
        except AuthenticationError as e:
            raise HTTPException(status_code=401, detail=str(e))
    
    return _require_auth
