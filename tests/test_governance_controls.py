"""
Unit Tests for Governance Controls

Tests for:
1. Startup config fail-fast validation
2. RBAC enforcement with policy logging
3. Pre-CI validation script

Total: 7 tests
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from app.startup_validator import StartupValidator
from app.api.admin.dependencies import require_role, get_client_ip
from app.models.admin_user import AdminUser, AdminRole
from app.models.audit_log import AuditLog
from fastapi import HTTPException


# ============================================================================
# CATEGORY 1: Startup Config Validation (3 tests)
# ============================================================================

def test_startup_validator_fails_on_debug_true_in_production():
    """Test 1: Startup validation fails if DEBUG=True in production."""
    with patch('app.startup_validator.settings') as mock_settings:
        mock_settings.ENVIRONMENT = "production"
        mock_settings.DEBUG = True
        mock_settings.ADMIN_UI_HTTPS_ONLY = True
        mock_settings.SESSION_SECRET_KEY = "a" * 32
        mock_settings.DATABASE_URL = "postgresql://..."
        mock_settings.REDIS_URL = "redis://..."
        mock_settings.PASSWORD_HASH_ROUNDS = 12
        
        errors = StartupValidator.validate_production_config()
        
        assert len(errors) > 0
        assert any("DEBUG=True" in error for error in errors)
        assert any("CRITICAL" in error for error in errors)


def test_startup_validator_fails_on_weak_session_secret():
    """Test 2: Startup validation fails if SESSION_SECRET_KEY < 32 chars."""
    with patch('app.startup_validator.settings') as mock_settings:
        mock_settings.ENVIRONMENT = "production"
        mock_settings.DEBUG = False
        mock_settings.ADMIN_UI_HTTPS_ONLY = True
        mock_settings.SESSION_SECRET_KEY = "short"  # Only 5 chars
        mock_settings.DATABASE_URL = "postgresql://..."
        mock_settings.REDIS_URL = "redis://..."
        mock_settings.PASSWORD_HASH_ROUNDS = 12
        
        errors = StartupValidator.validate_production_config()
        
        assert len(errors) > 0
        assert any("SESSION_SECRET_KEY" in error for error in errors)
        assert any("too short" in error for error in errors)


def test_startup_validator_passes_with_secure_config():
    """Test 3: Startup validation passes with all secure settings."""
    with patch('app.startup_validator.settings') as mock_settings:
        mock_settings.ENVIRONMENT = "production"
        mock_settings.DEBUG = False
        mock_settings.ADMIN_UI_HTTPS_ONLY = True
        mock_settings.SESSION_SECRET_KEY = "a" * 64  # Strong 64-char key
        mock_settings.ADMIN_UI_ENABLED = True
        mock_settings.DATABASE_URL = "postgresql://..."
        mock_settings.REDIS_URL = "redis://..."
        mock_settings.PASSWORD_HASH_ROUNDS = 12
        
        errors = StartupValidator.validate_production_config()
        
        assert len(errors) == 0


# ============================================================================
# CATEGORY 2: RBAC Enforcement with Audit Logging (3 tests)
# ============================================================================

@pytest.mark.asyncio
async def test_rbac_denies_viewer_from_admin_action(db: Session):
    """Test 4: RBAC denies VIEWER from ADMIN-required action and logs it."""
    # Create VIEWER user
    viewer = AdminUser(
        email="viewer@test.com",
        password_hash="dummy_hash_for_testing",
        full_name="Test Viewer",
        role=AdminRole.SUPPORT_VIEWER
    )
    db.add(viewer)
    db.commit()
    
    # Mock request
    mock_request = Mock()
    mock_request.url.path = "/admin/doctors/create"
    mock_request.headers.get.return_value = "test-agent"
    mock_request.client.host = "127.0.0.1"
    
    # Create role checker for ADMIN
    role_checker = require_role(AdminRole.CLINIC_ADMIN)
    
    # Attempt to access admin route as viewer
    with pytest.raises(HTTPException) as exc_info:
        await role_checker(
            request=mock_request,
            admin_user=viewer,
            db=db
        )
    
    # Verify HTTP 403 raised
    assert exc_info.value.status_code == 403
    assert "clinic_admin" in str(exc_info.value.detail).lower()
    
    # Verify policy_violation logged in audit
    violation = db.query(AuditLog).filter(
        AuditLog.event_type == "policy_violation"
    ).first()
    
    assert violation is not None
    assert violation.actor_id == str(viewer.id)
    assert violation.event_metadata["violation_type"] == "insufficient_role"
    assert violation.event_metadata["required_role"] == "clinic_admin"
    assert violation.event_metadata["actual_role"] == "support_viewer"


@pytest.mark.asyncio
async def test_rbac_allows_admin_to_admin_action(db: Session):
    """Test 5: RBAC allows ADMIN to perform ADMIN-required action."""
    # Create ADMIN user
    admin = AdminUser(
        email="admin@test.com",
        password_hash="dummy_hash_for_testing",
        full_name="Test Admin",
        role=AdminRole.CLINIC_ADMIN
    )
    db.add(admin)
    db.commit()
    
    # Mock request
    mock_request = Mock()
    mock_request.url.path = "/admin/doctors/create"
    
    # Create role checker for ADMIN
    role_checker = require_role(AdminRole.CLINIC_ADMIN)
    
    # Attempt to access admin route as admin
    result = await role_checker(
        request=mock_request,
        admin_user=admin,
        db=db
    )
    
    # Verify access granted (no exception raised)
    assert result == admin
    
    # Verify NO policy_violation logged (success case)
    violation_count = db.query(AuditLog).filter(
        AuditLog.event_type == "policy_violation"
    ).count()
    
    assert violation_count == 0


@pytest.mark.asyncio
async def test_rbac_logs_ip_and_path_in_violation(db: Session):
    """Test 6: RBAC logs IP address and requested path in violation."""
    # Create a VIEWER user who lacks permission
    viewer = AdminUser(
        email="viewer@test.com",
        password_hash="dummy_hash_for_testing",
        full_name="Test Viewer",
        role=AdminRole.SUPPORT_VIEWER
    )
    db.add(viewer)
    db.commit()
    
    # Mock request with specific IP
    mock_request = Mock()
    mock_request.url.path = "/admin/doctors/123/delete"
    mock_request.headers.get.return_value = "Mozilla/5.0"
    mock_request.client.host = "203.0.113.45"
    
    # Create role checker for SUPERADMIN (delete requires SUPERADMIN)
    role_checker = require_role(AdminRole.SUPER_ADMIN)
    
    # Attempt to delete as viewer
    with pytest.raises(HTTPException):
        await role_checker(
            request=mock_request,
            admin_user=viewer,
            db=db
        )
    
    # Verify violation logged with IP and path
    violation = db.query(AuditLog).filter(
        AuditLog.event_type == "policy_violation"
    ).first()
    
    assert violation is not None
    assert violation.event_metadata["ip_address"] == "203.0.113.45"
    assert violation.event_metadata["requested_path"] == "/admin/doctors/123/delete"
    assert violation.event_metadata["user_agent"] == "Mozilla/5.0"


# ============================================================================
# CATEGORY 3: Pre-CI Validation Script (1 test)
# ============================================================================

def test_pre_ci_validator_detects_missing_secrets():
    """Test 7: Pre-CI validator detects missing or weak secrets."""
    from pre_ci_validation import PreCIValidator
    
    # Mock settings with weak secret
    with patch('pre_ci_validation.settings') as mock_settings:
        mock_settings.SESSION_SECRET_KEY = "weak"  # Too short
        mock_settings.SECRET_KEY = "valid_key_12345"
        mock_settings.DATABASE_URL = "postgresql://..."
        
        validator = PreCIValidator()
        result = validator.check_secrets()
        
        # Should fail due to weak SESSION_SECRET_KEY
        assert result is False
        assert len(validator.errors) > 0
        assert any("SESSION_SECRET_KEY" in error for error in validator.errors)


# ============================================================================
# FIXTURES
# ============================================================================

# Note: db fixture is provided by conftest.py
# Tests use the real in-memory SQLite database with proper SQLAlchemy operations
