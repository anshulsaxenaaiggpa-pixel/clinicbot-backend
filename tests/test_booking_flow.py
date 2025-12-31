"""
Booking Flow Tests - Autonomous Sprint

Tests for WhatsApp booking state machine and flow.
Validates consent/age enforcement and ProhibitedDataError triggers.
"""
import pytest
from datetime import datetime, timedelta

from app.models.conversation_state import ConversationState, BookingState, StateManager
from app.services.booking_service import BookingService, AgeVerificationError
from app.schemas.data_classification import ProhibitedDataError


@pytest.fixture
def test_phone():
    return "+919999888877"


# =============================================================================
# TEST 1: Consent required before booking
# =============================================================================

def test_consent_required_before_booking(test_phone, db_session):
    """Test that consent is required before any booking."""
    # Initial message without consent
    response = BookingService.handle_message(test_phone, "Hi", db_session)
    
    # Should send consent prompt
    assert "consent" in response["message"].lower()
    assert response["next_state"] == BookingState.CONSENT_PENDING


# =============================================================================
# TEST 2: Consent granted advances to age verification
# =============================================================================

def test_consent_granted_advances_to_age(test_phone, db_session):
    """Test that YES consent advances to age verification."""
    # Send initial message
    BookingService.handle_message(test_phone, "Hi", db_session)
    
    # Grant consent
    response = BookingService.handle_message(test_phone, "YES", db_session)
    
    # Should ask for age
    assert "18" in response["message"]
    assert response["next_state"] == BookingState.AGE_VERIFICATION


# =============================================================================
# TEST 3: Age verification - under 18 rejected
# =============================================================================

def test_under_18_rejected(test_phone, db_session):
    """Test that minors are rejected per LEGAL_ASSUMPTIONS.md."""
    # Get to age verification
    BookingService.handle_message(test_phone, "Hi", db_session)
    BookingService.handle_message(test_phone, "YES", db_session)
    
    # Reply NO to age verification
    response = BookingService.handle_message(test_phone, "NO", db_session)
    
    # Should be rejected
    assert "18" in response["message"]
    assert "parent" in response["message"].lower() or "guardian" in response["message"].lower()
    assert response["next_state"] == BookingState.INITIAL


# =============================================================================
# TEST 4: Age verification - 18+ proceeds
# =============================================================================

def test_age_verified_proceeds(test_phone, db_session):
    """Test that 18+ proceeds to clinic selection."""
    # Get through consent and age
    BookingService.handle_message(test_phone, "Hi", db_session)
    BookingService.handle_message(test_phone, "YES", db_session)
    response = BookingService.handle_message(test_phone, "YES", db_session)  # Age YES
    
    # Should show clinic menu
    assert "clinic" in response["message"].lower()
    assert response["next_state"] == BookingState.CLINIC_SELECTION


# =============================================================================
# TEST 5: Full booking flow completes
# =============================================================================

def test_full_booking_flow(test_phone, db_session):
    """Test complete booking flow from start to confirmation."""
    # Step 1: Initial
    BookingService.handle_message(test_phone, "Hi", db_session)
    
    # Step 2: Consent
    BookingService.handle_message(test_phone, "YES", db_session)
    
    # Step 3: Age verification
    BookingService.handle_message(test_phone, "YES", db_session)
    
    # Step 4: Clinic selection
    BookingService.handle_message(test_phone, "1", db_session)
    
    # Step 5: Doctor selection
    BookingService.handle_message(test_phone, "1", db_session)
    
    # Step 6: Service selection
    BookingService.handle_message(test_phone, "1", db_session)
    
    # Step 7: Date selection
    BookingService.handle_message(test_phone, "1", db_session)
    
    # Step 8: Time selection (final step)
    response = BookingService.handle_message(test_phone, "1", db_session)
    
    # Should be confirmed
    assert response["next_state"] == BookingState.CONFIRMED
    assert "booking_id" in response
    assert "✅" in response["message"] or "confirmed" in response["message"].lower()


# =============================================================================
# TEST 6: ProhibitedDataError if medical content attempted
# =============================================================================

def test_prohibited_data_error_on_medical_content(test_phone, db_session):
    """Test that storing prohibited medical data raises ProhibitedDataError."""
    state = StateManager.get_or_create_state(test_phone, db_session)
    
    # Attempt to store prohibited keys
    with pytest.raises(ProhibitedDataError):
        state.set_context("symptoms", "headache")  # PROHIBITED
    
    with pytest.raises(ProhibitedDataError):
        state.set_context("diagnosis", "flu")  # PROHIBITED
    
    with pytest.raises(ProhibitedDataError):
        state.set_context("medical_notes", "patient looks unwell")  # PROHIBITED


# =============================================================================
# TEST 7: Only metadata stored (no chat transcripts)
# =============================================================================

def test_only_metadata_stored(test_phone, db_session):
    """Test that only allowed metadata is stored per COMPLIANCE_BASELINE.md."""
    # Complete booking
    BookingService.handle_message(test_phone, "Hi", db_session)
    BookingService.handle_message(test_phone, "YES", db_session)
    BookingService.handle_message(test_phone, "YES", db_session)
    BookingService.handle_message(test_phone, "1", db_session)  # Clinic
    BookingService.handle_message(test_phone, "1", db_session)  # Doctor
    
    # Get state
    state = db_session.query(ConversationState).filter(
        ConversationState.phone_number == test_phone
    ).first()
    
    # Check context contains only allowed keys
    assert state.context is not None
    allowed_keys = ['clinic_id', 'doctor_id', 'service_id', 'selected_date', 'selected_time']
    
    for key in state.context.keys():
        assert key in allowed_keys, f"Unexpected key '{key}' in context"
    
    # Verify NO message content stored
    assert 'message_body' not in state.context
    assert 'chat_transcript' not in state.context


# =============================================================================
# TEST 8: Conversation expires after 24 hours
# =============================================================================

def test_conversation_expiry(test_phone, db_session):
    """Test that inactive conversations expire."""
    state = StateManager.get_or_create_state(test_phone, db_session)
    
    # Manually set expiry to past
    state.expires_at = datetime.utcnow() - timedelta(hours=1)
    db_session.commit()
    
    # Check expiry
    assert state.is_expired() == True
    
    # Getting state again should reset
    state_refreshed = StateManager.get_or_create_state(test_phone, db_session)
    assert state_refreshed.current_state == BookingState.INITIAL
    assert state_refreshed.context == {} or state_refreshed.context is None


# =============================================================================
# TEST 9: Consent withdrawal stops processing
# =============================================================================

def test_consent_withdrawal_stops_processing(test_phone, db_session):
    """Test that STOP/NO stops all processing."""
    # Start booking
    BookingService.handle_message(test_phone, "Hi", db_session)
    
    # Withdraw consent
    response = BookingService.handle_message(test_phone, "NO", db_session)
    
    # Should stop processing
    assert "decline" in response["message"].lower() or "no data" in response["message"].lower()
    assert response["next_state"] == BookingState.INITIAL
    
    # Verify consent not granted
    state = db_session.query(ConversationState).filter(
        ConversationState.phone_number == test_phone
    ).first()
    assert state.consent_granted == False


# =============================================================================
# TEST 10: Invalid inputs handled gracefully
# =============================================================================

def test_invalid_input_handled(test_phone, db_session):
    """Test that invalid inputs don't crash the system."""
    # Get to clinic selection
    BookingService.handle_message(test_phone, "Hi", db_session)
    BookingService.handle_message(test_phone, "YES", db_session)
    BookingService.handle_message(test_phone, "YES", db_session)
    
    # Send invalid choice
    response = BookingService.handle_message(test_phone, "99", db_session)
    
    # Should ask again
    assert "invalid" in response["message"].lower() or "reply" in response["message"].lower()
    assert response["next_state"] == BookingState.CLINIC_SELECTION
