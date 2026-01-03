"""
Consent Module Tests - Module 2 Requirements
Updated for ConsentLog Implementation

Test 1: No consent → No booking (check_consent returns False)
Test 2: YES → consent stored in ConsentLog
Test 3: STOP → withdraw logged → check_consent returns False
Test 4: Withdraw → New YES → Reactivate
Test 5: Consent must store full text + version
"""
import pytest
from datetime import datetime
import uuid

from app.models.consent import ConsentLog
from app.models.clinic import Clinic
from app.models.patient import Patient
from app.services.consent_service import ConsentService, ConsentRequiredException, require_consent, CONSENT_TEXT_V1, CONSENT_VERSION
from app.db.session import SessionLocal


@pytest.fixture
def test_clinic(db):
    """Create a test clinic."""
    clinic = Clinic(
        name="Test Clinic",
        whatsapp_number="+919988776655",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(clinic)
    db.commit()
    db.refresh(clinic)
    return clinic

@pytest.fixture
def test_phone():
    """Test phone number in E.164 format."""
    return "+919999999999"

@pytest.fixture
def test_patient(db, test_clinic, test_phone):
    """Create a test patient associated with the test clinic."""
    patient = Patient(
        clinic_id=test_clinic.id,
        phone=test_phone,
        name="Test Patient",
        created_at=datetime.utcnow()
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient

# =============================================================================
# TEST 1: No consent → No booking (MUST FAIL)
# =============================================================================

def test_no_consent_blocks_booking(db, test_phone):
    """
    Module 2 Test 1: No consent → No booking
    """
    # Verify no consent exists
    status = ConsentService.get_consent_status(test_phone, db)
    assert status["status"] == "none"
    
    # Also verify direct check returns False
    assert ConsentService.check_consent_granted(test_phone, db) == False

# =============================================================================
# TEST 2: YES → consent stored
# =============================================================================

def test_yes_stores_consent(db, test_phone, test_patient):
    """
    Module 2 Test 2: YES → consent stored
    Requires a Patient record to exist so clinic_id can be resolved.
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
    # Note: We check ConsentLog now
    consent = db.query(ConsentLog).filter(
        ConsentLog.phone == test_phone,
        ConsentLog.consent_given == True
    ).first()
    
    assert consent is not None
    assert consent.phone == test_phone
    assert consent.clinic_id == test_patient.clinic_id
    assert consent.consent_text == CONSENT_TEXT_V1
    assert consent.consent_version == CONSENT_VERSION
    assert consent.consent_given == True
    
    # Verify consent check passes
    assert ConsentService.check_consent_granted(test_phone, db) == True

# =============================================================================
# TEST 3: STOP → withdraw logged → block bot
# =============================================================================

def test_stop_withdraws_and_blocks(db, test_phone, test_patient):
    """
    Module 2 Test 3: STOP → withdraw logged → block bot
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
    
    # Verify database has withdrawal record (latest)
    # The ConsentService creates a NEW record for withdrawal
    latest_consent = db.query(ConsentLog).filter(
        ConsentLog.phone == test_phone
    ).order_by(ConsentLog.timestamp.desc()).first()
    
    assert latest_consent is not None
    assert latest_consent.consent_given == False  # Withdrawn
    
    # Verify consent check now fails
    assert ConsentService.check_consent_granted(test_phone, db) == False

# =============================================================================
# TEST 4: Withdraw → New YES → Reactivate
# =============================================================================

def test_withdraw_then_reactivate(db, test_phone, test_patient):
    """
    Module 2 Test 4: Withdraw → New YES → Reactivate
    """
    # User grants consent initially
    ConsentService.capture_consent(phone_number=test_phone, reply_text="YES", db=db)
    # User withdraws
    ConsentService.capture_consent(phone_number=test_phone, reply_text="STOP", db=db)
    
    # User re-consents with new YES
    result = ConsentService.capture_consent(
        phone_number=test_phone,
        reply_text="YES",
        db=db
    )
    
    # Verify re-consent worked
    assert result["status"] == "granted"
    assert ConsentService.check_consent_granted(test_phone, db) == True
    
    # Verify records count (assuming YES, STOP, YES -> 3 records)
    all_consents = db.query(ConsentLog).filter(
        ConsentLog.phone == test_phone
    ).order_by(ConsentLog.timestamp).all()
    
    assert len(all_consents) >= 3

# =============================================================================
# TEST 5: Consent must store full text + version
# =============================================================================

def test_consent_stores_full_text_and_version(db, test_phone, test_patient):
    """
    Module 2 Test 5: Consent must store full text + version
    """
    # Capture consent
    ConsentService.capture_consent(
        phone_number=test_phone,
        reply_text="YES",
        db=db
    )
    
    # Verify database record has full text and version
    consent = db.query(ConsentLog).filter(
        ConsentLog.phone == test_phone
    ).order_by(ConsentLog.timestamp.desc()).first()
    
    assert consent is not None
    
    # CRITICAL: Must store full text
    assert consent.consent_text is not None
    assert consent.consent_text == CONSENT_TEXT_V1
    assert len(consent.consent_text) > 0
    
    # CRITICAL: Must store version
    assert consent.consent_version is not None
    assert consent.consent_version == CONSENT_VERSION
    
    # Verify timestamp is set
    assert consent.timestamp is not None
