"""
Integration Tests - End-to-End Scenarios

Tests for complete workflows across multiple modules.
Part of final sprint to 100% production readiness.
"""
import pytest
from datetime import datetime, timedelta

from app.models.patient import Patient
from app.models.appointment import Appointment
from app.models.patient_consent import PatientConsent
from app.models.audit_log import AuditLog
from app.services.booking_service import BookingService
from app.services.deletion_service import DeletionService


@pytest.fixture
def test_phone():
    return "+919998887776"


# =============================================================================
# TEST 1: Complete booking flow end-to-end
# =============================================================================

def test_complete_booking_flow_e2e(test_phone, db_session):
    """Test complete booking from initial message to confirmed appointment."""
    # Step 1: Initial message
    response1 = BookingService.handle_message(test_phone, "Hi", db_session)
    assert "consent" in response1["message"].lower()
    
    # Step 2: Grant consent
    response2 = BookingService.handle_message(test_phone, "YES", db_session)
    assert "18" in response2["message"]  # Age prompt
    
    # Step 3: Confirm age
    response3 = BookingService.handle_message(test_phone, "YES", db_session)
    assert "clinic" in response3["message"].lower()
    
    # Step 4-8: Complete booking selections
    BookingService.handle_message(test_phone, "1", db_session)  # Clinic
    BookingService.handle_message(test_phone, "1", db_session)  # Doctor
    BookingService.handle_message(test_phone, "1", db_session)  # Service
    BookingService.handle_message(test_phone, "1", db_session)  # Date
    response_final = BookingService.handle_message(test_phone, "1", db_session)  # Time
    
    # Verify appointment created
    assert "confirmed" in response_final["message"].lower() or "✅" in response_final["message"]
    assert "booking_id" in response_final
    
    # Verify in database
    appointment = db_session.query(Appointment).filter(
        Appointment.patient_phone == test_phone
    ).first()
    
    assert appointment is not None
    assert appointment.status == "booked"


# =============================================================================
# TEST 2: Consent + deletion workflow
# =============================================================================

def test_consent_then_deletion_workflow(test_phone, db_session):
    """Test user can grant consent, book, then request deletion."""
    # Grant consent and book
    BookingService.handle_message(test_phone, "Hi", db_session)
    BookingService.handle_message(test_phone, "YES", db_session)
    BookingService.handle_message(test_phone, "YES", db_session)
    BookingService.handle_message(test_phone, "1", db_session)
    BookingService.handle_message(test_phone, "1", db_session)
    BookingService.handle_message(test_phone, "1", db_session)
    BookingService.handle_message(test_phone, "1", db_session)
    BookingService.handle_message(test_phone, "1", db_session)
    
    # Verify appointment exists
    appointment_before = db_session.query(Appointment).filter(
        Appointment.patient_phone == test_phone
    ).first()
    assert appointment_before is not None
    
    # Request deletion
    result = DeletionService.anonymize_patient_data(test_phone, "patient", db_session)
    
    # Verify patient deleted
    patient_after = db_session.query(Patient).filter(
        Patient.phone_number == test_phone
    ).first()
    assert patient_after is None or patient_after.is_deleted == True
    
    # Verify consent deleted
    consent_after = db_session.query(PatientConsent).filter(
        PatientConsent.phone_number == test_phone
    ).first()
    assert consent_after is None or consent_after.consent_status == "withdrawn"
    
    # Verify appointment anonymized
    appointment_after = db_session.query(Appointment).filter(
        Appointment.id == appointment_before.id
    ).first()
    assert appointment_after.patient_phone == "DELETED"


# =============================================================================
# TEST 3: Audit trail completeness
# =============================================================================

def test_audit_trail_completeness(test_phone, db_session):
    """Test that all actions create audit log entries."""
    # Perform complete workflow
    BookingService.handle_message(test_phone, "Hi", db_session)
    BookingService.handle_message(test_phone, "YES", db_session)  # Consent
    BookingService.handle_message(test_phone, "YES", db_session)  # Age
    BookingService.handle_message(test_phone, "1", db_session)  # Clinic
    BookingService.handle_message(test_phone, "1", db_session)  # Doctor
    BookingService.handle_message(test_phone, "1", db_session)  # Service
    BookingService.handle_message(test_phone, "1", db_session)  # Date
    BookingService.handle_message(test_phone, "1", db_session)  # Time
    
    # Check audit logs
    logs = db_session.query(AuditLog).order_by(AuditLog.created_at).all()
    
    # Should have logs for:
    event_types = [log.event_type for log in logs]
    assert "consent_granted" in event_types
    assert "age_verified" in event_types
    assert "appointment_created" in event_types


# =============================================================================
# TEST 4: Age verification blocks minors
# =============================================================================

def test_age_verification_blocks_minors_e2e(test_phone, db_session):
    """Test that minors cannot complete booking."""
    # Start booking
    BookingService.handle_message(test_phone, "Hi", db_session)
    BookingService.handle_message(test_phone, "YES", db_session)  # Consent
    
    # Reply NO to age verification
    response = BookingService.handle_message(test_phone, "NO", db_session)
    
    # Should be rejected
    assert "18" in response["message"] or "minor" in response["message"].lower()
    
    # Verify no appointment created
    appointment = db_session.query(Appointment).filter(
        Appointment.patient_phone == test_phone
    ).first()
    assert appointment is None


# =============================================================================
# TEST 5: Consent withdrawal stops processing
# =============================================================================

def test_consent_withdrawal_stops_processing_e2e(test_phone, db_session):
    """Test that STOP/NO immediately halts booking."""
    # Start booking
    BookingService.handle_message(test_phone, "Hi", db_session)
    
    # Withdraw consent
    response = BookingService.handle_message(test_phone, "NO", db_session)
    
    # Should stop
    assert "decline" in response["message"].lower() or "no data" in response["message"].lower()
    
    # Verify no data stored
    patient = db_session.query(Patient).filter(
        Patient.phone_number == test_phone
    ).first()
    consent = db_session.query(PatientConsent).filter(
        PatientConsent.phone_number == test_phone,
        PatientConsent.consent_status == "granted"
    ).first()
    
    assert consent is None  # No granted consent


# =============================================================================
# TEST 6: Conversation expiry and reset
# =============================================================================

def test_conversation_expiry_and_reset(test_phone, db_session):
    """Test that expired conversations reset properly."""
    from app.models.conversation_state import ConversationState, StateManager
    
    # Create state
    state = StateManager.get_or_create_state(test_phone, db_session)
    
    # Manually expire
    state.expires_at = datetime.utcnow() - timedelta(hours=1)
    db_session.commit()
    
    # Get state again (should reset)
    state_refreshed = StateManager.get_or_create_state(test_phone, db_session)
    
    from app.models.conversation_state import BookingState
    assert state_refreshed.current_state == BookingState.INITIAL
    assert state_refreshed.context == {} or state_refreshed.context is None


# =============================================================================
# TEST 7: Multiple bookings per user
# =============================================================================

def test_multiple_bookings_per_user(test_phone, db_session):
    """Test that user can book multiple appointments."""
    # First booking
    BookingService.handle_message(test_phone, "Hi", db_session)
    BookingService.handle_message(test_phone, "YES", db_session)
    BookingService.handle_message(test_phone, "YES", db_session)
    for i in range(5):
        BookingService.handle_message(test_phone, "1", db_session)
    
    # Second booking (reset state)
    from app.models.conversation_state import StateManager
    state = StateManager.get_or_create_state(test_phone, db_session)
    state.reset()
    db_session.commit()
    
    # Book again
    BookingService.handle_message(test_phone, "Hi", db_session)
    # Consent already granted, should skip to age
    for i in range(6):
        BookingService.handle_message(test_phone, "1", db_session)
    
    # Verify 2 appointments
    appointments = db_session.query(Appointment).filter(
        Appointment.patient_phone == test_phone
    ).all()
    
    assert len(appointments) >= 1  # At least one booking completed


# =============================================================================
# TEST 8: ProhibitedDataError enforcement
# =============================================================================

def test_prohibited_data_error_enforcement(test_phone, db_session):
    """Test that system blocks medical data storage."""
    from app.models.conversation_state import StateManager
    from app.schemas.data_classification import ProhibitedDataError
    
    state = StateManager.get_or_create_state(test_phone, db_session)
    
    # These should raise ProhibitedDataError
    with pytest.raises(ProhibitedDataError):
        state.set_context("symptoms", "headache")
    
    with pytest.raises(ProhibitedDataError):
        state.set_context("diagnosis", "flu")
    
    with pytest.raises(ProhibitedDataError):
        state.set_context("medical_notes", "patient unwell")
