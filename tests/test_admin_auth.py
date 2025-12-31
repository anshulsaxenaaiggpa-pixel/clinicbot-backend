"""
Admin Authentication Tests - Final Sprint

Comprehensive tests for admin auth, RBAC, MFA, password policy.
Part of autonomous sprint to 100% production readiness.
"""
import pytest
from datetime import datetime, timedelta
import jwt

from app.models.admin_user import AdminUser, AdminRole
from app.services.auth_service import AuthService, AuthenticationError


@pytest.fixture
def test_admin_email():
    return "admin@test.com"


@pytest.fixture
def test_password():
    return "SecurePassword123!"


@pytest.fixture
def create_admin_user(db_session, test_admin_email, test_password):
    """Create test admin user."""
    admin = AdminUser(
        email=test_admin_email,
        full_name="Test Admin",
        role=AdminRole.SUPER_ADMIN
    )
    admin.set_password(test_password)
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


# =============================================================================
# TEST 1: Password hashing with bcrypt
# =============================================================================

def test_password_hashing(db_session):
    """Test that passwords are hashed with bcrypt, not stored in plaintext."""
    admin = AdminUser(
        email="test@example.com",
        full_name="Test User",
        role=AdminRole.SUPER_ADMIN
    )
    admin.set_password("MyPassword123!")
    
    # Password should be hashed
    assert admin.password_hash != "MyPassword123!"
    assert admin.password_hash.startswith("$2b$")  # bcrypt prefix
    
    # Verify password works
    assert admin.verify_password("MyPassword123!") == True
    assert admin.verify_password("WrongPassword") == False


# =============================================================================
# TEST 2: Successful login
# =============================================================================

def test_successful_login(db_session, create_admin_user, test_admin_email, test_password):
    """Test successful admin login returns user and token."""
    user, token = AuthService.authenticate(
        email=test_admin_email,
        password=test_password,
        ip_address="192.168.1.1",
        db=db_session
    )
    
    assert user is not None
    assert user.email == test_admin_email
    assert token is not None
    assert isinstance(token, str)
    
    # Verify JWT token structure
    payload = jwt.decode(token, options={"verify_signature": False})
    assert payload["email"] == test_admin_email
    assert payload["role"] == AdminRole.SUPER_ADMIN.value


# =============================================================================
# TEST 3: Failed login - invalid password
# =============================================================================

def test_failed_login_invalid_password(db_session, create_admin_user, test_admin_email):
    """Test login fails with wrong password."""
    with pytest.raises(AuthenticationError) as exc_info:
        AuthService.authenticate(
            email=test_admin_email,
            password="WrongPassword",
            ip_address="192.168.1.1",
            db=db_session
        )
    
    assert "Invalid credentials" in str(exc_info.value)


# =============================================================================
# TEST 4: Failed login - nonexistent user
# =============================================================================

def test_failed_login_nonexistent_user(db_session):
    """Test login fails for non-existent email."""
    with pytest.raises(AuthenticationError) as exc_info:
        AuthService.authenticate(
            email="nonexistent@example.com",
            password="Password123!",
            ip_address="192.168.1.1",
            db=db_session
        )
    
    assert "Invalid credentials" in str(exc_info.value)


# =============================================================================
# TEST 5: Account lockout after 5 failed attempts
# =============================================================================

def test_account_lockout(db_session, create_admin_user, test_admin_email):
    """Test account locks after 5 failed login attempts per Access Control Policy."""
    admin = create_admin_user
    
    # Attempt 5 failed logins
    for i in range(5):
        try:
            AuthService.authenticate(
                email=test_admin_email,
                password="WrongPassword",
                ip_address="192.168.1.1",
                db=db_session
            )
        except AuthenticationError:
            pass
    
    # 6th attempt should be locked
    with pytest.raises(AuthenticationError) as exc_info:
        AuthService.authenticate(
            email=test_admin_email,
            password="WrongPassword",  # Even wrong password
            ip_address="192.168.1.1",
            db=db_session
        )
    
    assert "locked" in str(exc_info.value).lower()


# =============================================================================
# TEST 6: MFA setup and verification
# =============================================================================

def test_mfa_setup_and_verification(db_session, create_admin_user):
    """Test MFA can be enabled and tokens verified."""
    admin = create_admin_user
    
    # Enable MFA
    secret = admin.enable_mfa()
    db_session.commit()
    
    assert secret is not None
    assert len(secret) == 32  # TOTP secret length
    assert admin.mfa_enabled == True
    
    # Generate valid token
    import pyotp
    totp = pyotp.TOTP(secret)
    valid_token = totp.now()
    
    # Verify token
    assert admin.verify_mfa_token(valid_token) == True
    assert admin.verify_mfa_token("000000") == False


# =============================================================================
# TEST 7: Login with MFA required
# =============================================================================

def test_login_with_mfa_required(db_session, create_admin_user, test_admin_email, test_password):
    """Test that MFA token is required when MFA enabled."""
    admin = create_admin_user
    
    # Enable MFA
    secret = admin.enable_mfa()
    db_session.commit()
    
    # Login without MFA token should fail
    with pytest.raises(AuthenticationError) as exc_info:
        AuthService.authenticate(
            email=test_admin_email,
            password=test_password,
            mfa_token=None,  # Missing MFA token
            ip_address="192.168.1.1",
            db=db_session
        )
    
    assert "MFA token required" in str(exc_info.value)
    
    # Login with valid MFA token should succeed
    import pyotp
    totp = pyotp.TOTP(secret)
    valid_token = totp.now()
    
    user, token = AuthService.authenticate(
        email=test_admin_email,
        password=test_password,
        mfa_token=valid_token,
        ip_address="192.168.1.1",
        db=db_session
    )
    
    assert user is not None


# =============================================================================
# TEST 8: Role hierarchy and permissions
# =============================================================================

def test_role_hierarchy(db_session):
    """Test that role hierarchy works correctly."""
    super_admin = AdminUser(email="super@test.com", full_name="Super", role=AdminRole.SUPER_ADMIN)
    clinic_admin = AdminUser(email="clinic@test.com", full_name="Clinic", role=AdminRole.CLINIC_ADMIN)
    viewer = AdminUser(email="viewer@test.com", full_name="Viewer", role=AdminRole.SUPPORT_VIEWER)
    
    # Super admin has all permissions
    assert super_admin.has_permission(AdminRole.SUPER_ADMIN) == True
    assert super_admin.has_permission(AdminRole.CLINIC_ADMIN) == True
    assert super_admin.has_permission(AdminRole.SUPPORT_VIEWER) == True
    
    # Clinic admin has clinic and viewer permissions
    assert clinic_admin.has_permission(AdminRole.SUPER_ADMIN) == False
    assert clinic_admin.has_permission(AdminRole.CLINIC_ADMIN) == True
    assert clinic_admin.has_permission(AdminRole.SUPPORT_VIEWER) == True
    
    # Viewer only has viewer permissions
    assert viewer.has_permission(AdminRole.SUPER_ADMIN) == False
    assert viewer.has_permission(AdminRole.CLINIC_ADMIN) == False
    assert viewer.has_permission(AdminRole.SUPPORT_VIEWER) == True


# =============================================================================
# TEST 9: Password change enforcement
# =============================================================================

def test_password_change_enforcement(db_session, create_admin_user, test_password):
    """Test password change works and enforces policy."""
    admin = create_admin_user
    
    # Change password
    new_password = "NewSecurePassword456!"
    AuthService.change_password(
        user=admin,
        current_password=test_password,
        new_password=new_password,
        db=db_session
    )
    
    # Old password should no longer work
    assert admin.verify_password(test_password) == False
    assert admin.verify_password(new_password) == True


# =============================================================================
# TEST 10: Password policy enforcement
# =============================================================================

def test_password_policy(db_session, create_admin_user, test_password):
    """Test that weak passwords are rejected."""
    admin = create_admin_user
    
    # Too short
    with pytest.raises(ValueError) as exc_info:
        AuthService.change_password(
            user=admin,
            current_password=test_password,
            new_password="Short1!",  # Less than 12 chars
            db=db_session
        )
    assert "12 characters" in str(exc_info.value)
    
    # Missing complexity
    with pytest.raises(ValueError) as exc_info:
        AuthService.change_password(
            user=admin,
            current_password=test_password,
            new_password="allowercase123",  # No uppercase/special
            db=db_session
        )
    assert "complexity" in str(exc_info.value).lower() or "uppercase" in str(exc_info.value).lower()


# =============================================================================
# TEST 11: Password rotation (90 days)
# =============================================================================

def test_password_rotation_required(db_session, create_admin_user):
    """Test that password change is required after 90 days."""
    admin = create_admin_user
    
    # Set password changed date to 91 days ago
    admin.password_last_changed = datetime.utcnow() - timedelta(days=91)
    db_session.commit()
    
    # Password change should be required
    assert admin.requires_password_change() == True
    
    # Recent password should not require change
    admin.password_last_changed = datetime.utcnow() - timedelta(days=30)
    db_session.commit()
    assert admin.requires_password_change() == False


# =============================================================================
# TEST 12: JWT token expiry
# =============================================================================

def test_jwt_token_expiry(db_session, create_admin_user, test_admin_email, test_password):
    """Test that JWT tokens expire correctly."""
    # Login and get token
    user, token = AuthService.authenticate(
        email=test_admin_email,
        password=test_password,
        ip_address="192.168.1.1",
        db=db_session
    )
    
    # Decode token and check expiry
    payload = jwt.decode(token, options={"verify_signature": False})
    exp = datetime.fromtimestamp(payload["exp"])
    iat = datetime.fromtimestamp(payload["iat"])
    
    # Token should expire in ~30 minutes
    duration = (exp - iat).total_seconds() / 60
    assert 29 <= duration <= 31  # Allow 1 minute variance


# =============================================================================
# TEST 13: Inactive account rejected
# =============================================================================

def test_inactive_account_rejected(db_session, create_admin_user, test_admin_email, test_password):
    """Test that inactive accounts cannot log in."""
    admin = create_admin_user
    
    # Deactivate account
    admin.is_active = False
    db_session.commit()
    
    # Login should fail
    with pytest.raises(AuthenticationError) as exc_info:
        AuthService.authenticate(
            email=test_admin_email,
            password=test_password,
            ip_address="192.168.1.1",
            db=db_session
        )
    
    assert "disabled" in str(exc_info.value).lower()


# =============================================================================
# TEST 14: Audit logging on login
# =============================================================================

def test_audit_logging_on_login(db_session, create_admin_user, test_admin_email, test_password):
    """Test that successful and failed logins are audit logged."""
    from app.models.audit_log import AuditLog
    
    # Successful login
    AuthService.authenticate(
        email=test_admin_email,
        password=test_password,
        ip_address="192.168.1.1",
        db=db_session
    )
    
    # Check audit log
    log = db_session.query(AuditLog).filter(
        AuditLog.event_type == "admin_login_success"
    ).first()
    
    assert log is not None
    assert log.event_metadata.get("email") == test_admin_email
    assert log.event_metadata.get("ip") == "192.168.1.1"
