"""
Consent Module Tests - Module 2 Requirements

These tests MUST PASS before shipping consent capture.

Test 1: No consent → No booking
Test 2: YES → consent stored
Test 3: STOP → withdraw logged → block bot
Test 4: Withdraw → New YES → Reactivate
Test 5: Consent must store full text + version
"""
import pytest
from fastapi import HTTPException
from datetime import datetime

from app.models.patient_consent import PatientConsent, ConsentStatus, CONSENT_TEXT_V1, CONSENT_VERSION
from app.services.consent_service import ConsentService, ConsentRequiredException, require_consent
from app.db.session import SessionLocal


# Test fixtures
@pytest.fixture
def db():
    """Create test database session."""
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def test_phone():
    """Test phone number in E.164 format."""
    return "+919999999999"


# =============================================================================
# TEST 1: No consent → No booking (MUST FAIL with 403)
# =============================================================================

def test_no_consent_blocks_booking(db, test_phone):
    """
    Module 2 Test 1: No consent → No booking
    
    Expected: ConsentRequiredException raised when trying to access PHI
    """
    # Verify no consent exists
    status = ConsentService.get_consent_status(test_phone, db)
    assert status["status"] == "none"
    
    # Attempt to require consent (simulates booking endpoint check)
    with pytest.raises(ConsentRequiredException) as exc_info:
        require_consent(test_phone)
    
    assert "Consent required" in str(exc_info.value)
    
    # Also verify direct check returns False
    assert ConsentService.check_consent_granted(test_phone, db) == False


# =============================================================================
# TEST 2: YES → consent stored
# =============================================================================

def test_yes_stores_consent(db, test_phone):
    """
    Module 2 Test 2: YES → consent stored
    
    Expected: Consent record exists with status=granted
    """
    # User replies YES
    result = ConsentService.capture_consent(
        phone_number=test_phone,
        reply_text="YES",
        channel="whatsapp",
        db=db
    )
    
    # Verify response
    assert result["status"] == "granted"
    assert result["version"] == CONSENT_VERSION
    assert result["timestamp"] is not None
    
    # Verify database record
    consent = db.query(PatientConsent).filter(
        PatientConsent.phone_number == test_phone,
        PatientConsent.consent_status == ConsentStatus.GRANTED
    ).first()
    
    assert consent is not None
    assert consent.phone_number == test_phone
    assert consent.consent_text == CONSENT_TEXT_V1
    assert consent.consent_version == CONSENT_VERSION
    assert consent.consent_status == ConsentStatus.GRANTED
    
    # Verify consent check passes
    assert ConsentService.check_consent_granted(test_phone, db) == True


# =============================================================================
# TEST 3: STOP → withdraw logged → block bot
# =============================================================================

def test_stop_withdraws_and_blocks(db, test_phone):
    """
    Module 2 Test 3: STOP → withdraw logged → block bot
    
    Expected: 
    - Withdrawal recorded
    - Subsequent access blocked (403)
    """
    # First, user had granted consent
    ConsentService.capture_consent(
        phone_number=test_phone,
        reply_text="YES",
        db=db
    )
    
    # Verify consent granted initially
    assert ConsentService.check_consent_granted(test_phone, db) == True
    
    # User sends STOP
    result = ConsentService.capture_consent(
        phone_number=test_phone,
        reply_text="STOP",
        db=db
    )
    
    # Verify withdrawal response
    assert result["status"] == "withdrawn"
    
    # Verify database has withdrawal record
    withdrawal = db.query(PatientConsent).filter(
        PatientConsent.phone_number == test_phone,
        PatientConsent.consent_status == ConsentStatus.WITHDRAWN
    ).order_by(PatientConsent.timestamp.desc()).first()
    
    assert withdrawal is not None
    assert withdrawal.consent_status == ConsentStatus.WITHDRAWN
    
    # Verify consent check now fails (most recent is WITHDRAWN)
    assert ConsentService.check_consent_granted(test_phone, db) == False
    
    # Verify require_consent raises exception
    with pytest.raises(ConsentRequiredException):
        require_consent(test_phone)


# =============================================================================
# TEST 4: Withdraw → New YES → Reactivate
# =============================================================================

def test_withdraw_then_reactivate(db, test_phone):
    """
    Module 2 Test 4: Withdraw → New YES → Reactivate
    
    Expected: User can re-consent after withdrawal
    """
    # User grants consent initially
    ConsentService.capture_consent(
        phone_number=test_phone,
        reply_text="YES",
        db=db
    )
    assert ConsentService.check_consent_granted(test_phone, db) == True
    
    # User withdraws
    ConsentService.capture_consent(
        phone_number=test_phone,
        reply_text="STOP",
        db=db
    )
    assert ConsentService.check_consent_granted(test_phone, db) == False
    
    # User re-consents with new YES
    result = ConsentService.capture_consent(
        phone_number=test_phone,
        reply_text="YES",
        db=db
    )
    
    # Verify re-consent worked
    assert result["status"] == "granted"
    assert ConsentService.check_consent_granted(test_phone, db) == True
    
    # Verify all 3 records exist (initial YES, STOP, new YES)
    all_consents = db.query(PatientConsent).filter(
        PatientConsent.phone_number == test_phone
    ).order_by(PatientConsent.timestamp).all()
    
    assert len(all_consents) == 3
    assert all_consents[0].consent_status == ConsentStatus.GRANTED
    assert all_consents[1].consent_status == ConsentStatus.WITHDRAWN
    assert all_consents[2].consent_status == ConsentStatus.GRANTED


# =============================================================================
# TEST 5: Consent must store full text + version
# =============================================================================

def test_consent_stores_full_text_and_version(db, test_phone):
    """
    Module 2 Test 5: Consent must store full text + version
    
    Expected: consent_text and consent_version are NOT NULL
    """
    # Capture consent
    ConsentService.capture_consent(
        phone_number=test_phone,
        reply_text="YES",
        db=db
    )
    
    # Verify database record has full text and version
    consent = db.query(PatientConsent).filter(
        PatientConsent.phone_number == test_phone
    ).first()
    
    assert consent is not None
    
    # CRITICAL: Must store full text
    assert consent.consent_text is not null
    assert consent.consent_text == CONSENT_TEXT_V1
    assert len(consent.consent_text) > 0
    
    # CRITICAL: Must store version
    assert consent.consent_version is not None
    assert consent.consent_version == CONSENT_VERSION
    assert consent.consent_version == "dpdp-whatsapp-consent-v1.0"
    
    # Verify timestamp is set
    assert consent.timestamp is not None
    assert isinstance(consent.timestamp, datetime)


# =============================================================================
# BONUS: Test different YES variations
# =============================================================================

def test_yes_variations_all_work(db):
    """Test that all YES variations are recognized."""
    yes_variations = ["YES", "yes", "Yes", "Y", "y", "1", "AGREE", "ACCEPT"]
    
    for idx, variation in enumerate(yes_variations):
        phone = f"+9199999999{idx:02d}"
        
        result = ConsentService.capture_consent(
            phone_number=phone,
            reply_text=variation,
            db=db
        )
        
        assert result["status"] == "granted", f"Failed for variation: {variation}"
        assert ConsentService.check_consent_granted(phone, db) == True


# =============================================================================
# BONUS: Test different NO/STOP variations
# =============================================================================

def test_no_variations_all_work(db):
    """Test that all NO/STOP variations are recognized."""
    no_variations = ["NO", "no", "No", "N", "n", "0", "STOP", "DECLINE", "WITHDRAW"]
    
    for idx, variation in enumerate(no_variations):
        phone = f"+9199999988{idx:02d}"
        
        result = ConsentService.capture_consent(
            phone_number=phone,
            reply_text=variation,
            db=db
        )
        
        assert result["status"] == "withdrawn", f"Failed for variation: {variation}"
        assert ConsentService.check_consent_granted(phone, db) == False


# =============================================================================
# BONUS: Test invalid responses
# =============================================================================

def test_invalid_response_not_stored(db, test_phone):
    """Test that invalid responses don't create consent records."""
    # Send invalid response
    result = ConsentService.capture_consent(
        phone_number=test_phone,
        reply_text="MAYBE",
        db=db
    )
    
    assert result["status"] == "invalid"
    assert "Invalid response" in result["message"]
    
    # Verify no consent record created
    consent = db.query(PatientConsent).filter(
        PatientConsent.phone_number == test_phone
    ).first()
    
    assert consent is None
    
    # Verify consent check still fails
    assert ConsentService.check_consent_granted(test_phone, db) == False
