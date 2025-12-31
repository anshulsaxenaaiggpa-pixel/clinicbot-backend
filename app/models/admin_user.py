"""
Admin User Model - Sprint Task 1

Role-based access control for ClinicBot admin panel.
Implements authentication, MFA, and audit logging.
"""
from sqlalchemy import Column, String, DateTime, Boolean, Index, Enum as SQLEnum, Integer
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timedelta
import uuid
import bcrypt
import pyotp
from enum import Enum

from app.db.base_class import Base


class AdminRole(str, Enum):
    """Admin role enumeration."""
    SUPER_ADMIN = "super_admin"
    CLINIC_ADMIN = "clinic_admin"
    SUPPORT_VIEWER = "support_viewer"


class AdminUser(Base):
    """
    Admin user model with authentication and RBAC.
    
    Security features:
    - Bcrypt password hashing (cost 12)
    - TOTP-based MFA
    - Account lockout after failed attempts
    - Session management
    - Activity audit logging
    """
    __tablename__ = "admin_users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Identity
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    
    # Profile
    full_name = Column(String(100), nullable=False)
    role = Column(SQLEnum(AdminRole, name="admin_role"), nullable=False)
    
    # MFA
    mfa_secret = Column(String(32), nullable=True)  # TOTP secret
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    
    # Security controls
    is_active = Column(Boolean, default=True, nullable=False)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # Password management
    password_last_changed = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    must_change_password = Column(Boolean, default=False, nullable=False)
    
    # Session tracking
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(45), nullable=True)  # IPv6 compatible
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index("idx_admin_email", "email"),
        Index("idx_admin_role", "role"),
        Index("idx_admin_active", "is_active"),
    )
    
    def set_password(self, password: str):
        """
        Hash password using bcrypt (cost 12).
        
        Assumption: bcrypt chosen over Argon2 for simplicity.
        """
        salt = bcrypt.gensalt(rounds=12)
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        self.password_last_changed = datetime.utcnow()
    
    def verify_password(self, password: str) -> bool:
        """Verify password against stored hash."""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def enable_mfa(self) -> str:
        """
        Enable MFA and return secret for QR code generation.
        
        Returns TOTP secret that user must save in authenticator app.
        """
        self.mfa_secret = pyotp.random_base32()
        self.mfa_enabled = True
        return self.mfa_secret
    
    def verify_mfa_token(self, token: str) -> bool:
        """Verify MFA token."""
        if not self.mfa_enabled or not self.mfa_secret:
            return True  # MFA not enabled
        
        totp = pyotp.TOTP(self.mfa_secret)
        return totp.verify(token, valid_window=1)  # Allow 1 step clock drift
    
    def get_mfa_uri(self, issuer: str = "ClinicBot") -> str:
        """Get MFA provisioning URI for QR code."""
        if not self.mfa_secret:
            raise ValueError("MFA not enabled")
        
        totp = pyotp.TOTP(self.mfa_secret)
        return totp.provisioning_uri(name=self.email, issuer_name=issuer)
    
    def record_failed_login(self):
        """Record failed login attempt and lock account if threshold exceeded."""
        self.failed_login_attempts += 1
        
        # Lock account after 5 failed attempts (per Access Control Policy)
        if self.failed_login_attempts >= 5:
            self.locked_until = datetime.utcnow() + timedelta(minutes=30)
    
    def record_successful_login(self, ip_address: str):
        """Record successful login and reset failed attempts."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login_at = datetime.utcnow()
        self.last_login_ip = ip_address
    
    def is_locked(self) -> bool:
        """Check if account is currently locked."""
        if self.locked_until is None:
            return False
        
        if datetime.utcnow() > self.locked_until:
            # Lock expired, reset
            self.locked_until = None
            self.failed_login_attempts = 0
            return False
        
        return True
    
    def requires_password_change(self) -> bool:
        """Check if password change is required (90 days or forced)."""
        if self.must_change_password:
            return True
        
        # Password rotation: 90 days (per Access Control Policy)
        days_since_change = (datetime.utcnow() - self.password_last_changed).days
        return days_since_change > 90
    
    def has_permission(self, required_role: AdminRole) -> bool:
        """
        Check if user has permission for required role.
        
        Permission hierarchy:
        super_admin > clinic_admin > support_viewer
        """
        role_hierarchy = {
            AdminRole.SUPER_ADMIN: 3,
            AdminRole.CLINIC_ADMIN: 2,
            AdminRole.SUPPORT_VIEWER: 1,
        }
        
        user_level = role_hierarchy.get(self.role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        return user_level >= required_level
    
    def __repr__(self):
        return f"<AdminUser {self.email} ({self.role})>"
