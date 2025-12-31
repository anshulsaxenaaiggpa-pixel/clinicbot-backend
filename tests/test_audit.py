"""
Audit Logging Tests - MODULE 4

Tests for Module 4: Audit Logging requirements.

Test Coverage:
1. Events logged correctly
2. UPDATE/DELETE blocked
3. PHI sanitized in metadata
4. Query works
5. All required events covered
"""
import pytest
from datetime import datetime

from app.models.audit_log import AuditLog
from app.services.audit_service import (
    AuditService, EVENT_TYPES,
    log_consent_granted, log_consent_withdrawn,
    log_appointment_created, log_appointment_cancelled,
    log_deletion_completed, log_rate_limit_block
)
from app.db.session import SessionLocal


@pytest.fixture
def db():
    """Create test database session."""
    db = SessionLocal()
    yield db
    db.close()


# =============================================================================
# TEST 1: Events logged correctly
# =============================================================================

def test_event_logging(db):
    """Test that events are logged correctly."""
    # Log an event
    audit = AuditService.log_event(
        event_type=EVENT_TYPES["CONSENT_GRANTED"],
        actor="patient",
        actor_id="+919999999999",
        patient_phone="+919999999999",
        metadata={"action": "test"},
        db=db
    )
    
    assert audit is not None
    assert audit.event_type == EVENT_TYPES["CONSENT_GRANTED"]
    assert audit.actor == "patient"
    assert audit.patient_phone_hash is not None
    assert audit.timestamp is not None
    
    # Verify in database
    saved = db.query(AuditLog).filter_by(event_id=audit.event_id).first()
    assert saved is not None
    assert saved.event_type == EVENT_TYPES["CONSENT_GRANTED"]


# =============================================================================
# TEST 2: UPDATE/DELETE blocked
# =============================================================================

def test_audit_immutability(db):
    """Test that audit logs cannot be updated or deleted."""
    # Create audit entry
    audit = AuditService.log_event(
        event_type=EVENT_TYPES["RATE_LIMIT_BLOCK"],
        actor="system",
        actor_id="test",
        db=db
    )
    
    # Try to update (should fail silently due to DB rule)
    original_type = audit.event_type
    audit.event_type = "MODIFIED"
    db.commit()
    
    # Verify not updated
    db.refresh(audit)
    assert audit.event_type == original_type  # Should remain unchanged
    
    # Try to delete (should fail silently due to DB rule)
    db.delete(audit)
    db.commit()
    
    # Verify still exists
    still_exists = db.query(AuditLog).filter_by(event_id=audit.event_id).first()
    assert still_exists is not None


# =============================================================================
# TEST 3: PHI sanitized in metadata
# =============================================================================

def test_phi_sanitization(db):
    """Test that PHI is redacted from metadata."""
    # Log event with PHI in metadata
    metadata_with_phi = {
        "phone": "+919999999999",
        "patient_name": "Sensitive Name",
        "appointment_id": "apt-123",  # OK to store
        "message": "Secret message content"
    }
    
    audit = AuditService.log_event(
        event_type=EVENT_TYPES["APPOINTMENT_CREATED"],
        actor="patient",
        actor_id="test",
        metadata=metadata_with_phi,
        db=db
    )
    
    # Verify PHI was redacted
    assert audit.metadata["phone"] == "[REDACTED]"
    assert audit.metadata["patient_name"] == "[REDACTED]"
    assert audit.metadata["message"] == "[REDACTED]"
    
    # Non-PHI should remain
    assert audit.metadata["appointment_id"] == "apt-123"


# =============================================================================
# TEST 4: Query functionality
# =============================================================================

def test_audit_query(db):
    """Test that audit logs can be queried."""
    phone = "+919988776655"
    
    # Create multiple events
    log_consent_granted(phone, db)
    log_appointment_created("apt-1", phone, db)
    log_appointment_cancelled("apt-1", phone, "patient", db)
    
    # Query by event type
    consent_events = AuditService.query_events(
        event_type=EVENT_TYPES["CONSENT_GRANTED"],
        db=db
    )
    assert len(consent_events) >= 1
    
    # Query by patient phone (hashed)
    patient_events = AuditService.query_events(
        patient_phone=phone,
        db=db
    )
    assert len(patient_events) >= 3
    
    # Query by actor
    patient_actions = AuditService.query_events(
        actor="patient",
        db=db
    )
    assert len(patient_actions) >= 2


# =============================================================================
# TEST 5: All required events have convenience functions
# =============================================================================

def test_all_event_types_logged(db):
    """Test that all Module 4 required events can be logged."""
    phone = "+919876543210"
    
    # Consent events
    log_consent_granted(phone, db)
    log_consent_withdrawn(phone, db)
    
    # Appointment events
    log_appointment_created("apt-1", phone, db)
    log_appointment_cancelled("apt-1", phone, "clinic", db)
    
    # Deletion events
    log_deletion_completed(phone, {"patients": 1, "appointments": 2}, db)
    
    # Rate limit events
    log_rate_limit_block(phone, "booking", db)
    
    # Verify all logged
    all_events = db.query(AuditLog).all()
    assert len(all_events) >= 6
    
    # Verify event types present
    event_types = {log.event_type for log in all_events}
    assert EVENT_TYPES["CONSENT_GRANTED"] in event_types
    assert EVENT_TYPES["CONSENT_WITHDRAWN"] in event_types
    assert EVENT_TYPES["APPOINTMENT_CREATED"] in event_types
    assert EVENT_TYPES["APPOINTMENT_CANCELLED"] in event_types
    assert EVENT_TYPES["DELETION_COMPLETED"] in event_types
    assert EVENT_TYPES["RATE_LIMIT_BLOCK"] in event_types


# =============================================================================
# BONUS: Test phone number hashing
# =============================================================================

def test_phone_hashing_consistent(db):
    """Test that phone hashing is consistent."""
    phone = "+919876543210"
    
    # Hash should be consistent
    hash1 = AuditLog.hash_phone(phone)
    hash2 = AuditLog.hash_phone(phone)
    assert hash1 == hash2
    
    # Different phones should have different hashes
    hash3 = AuditLog.hash_phone("+919876543211")
    assert hash1 != hash3
    
    # Hash should be irreversible (SHA256)
    assert len(hash1) == 64  # SHA256 hex length
    assert phone not in hash1


# =============================================================================
# BONUS: Test audit logging doesn't break main operations
# =============================================================================

def test_audit_failure_doesnt_break_operation(db):
    """Test that audit log failures don't break main operations."""
    # Simulate logging failure by passing invalid data
    # The service should handle this gracefully
    
    result = AuditService.log_event(
        event_type="INVALID_TYPE_THAT_CAUSES_ERROR",
        actor="test",
        actor_id="test",
        metadata={"circular_ref": None},  # Could cause serialization issues
        db=db
    )
    
    # Result might be None (failed) but shouldn't raise exception
    # This demonstrates defensive logging
    assert result is None or isinstance(result, AuditLog)
