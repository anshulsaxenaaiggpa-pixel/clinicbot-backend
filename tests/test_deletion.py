"""
Data Deletion Tests - MODULE 3

Tests for Module 3: Data Deletion requirements.

Test Coverage:
1. Deletion keywords detected
2. Patient data deleted
3. Appointments anonymized
4. Consents deleted
5. Idempotent deletion
6. Audit logs retained
7. No PHI remains after deletion
"""
import pytest
from datetime import datetime

from app.models.patient import Patient
from app.models.appointment import Appointment
from app.models.patient_consent import PatientConsent, ConsentStatus
from app.models.patient_deletion import PatientDeletion
from app.services.deletion_service import DeletionService
from app.db.session import SessionLocal


@pytest.fixture
def db():
    """Create test database session."""
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def test_phone():
    """Test phone number."""
    return "+919988776655"


# =============================================================================
# TEST 1: Deletion keyword detection
# =============================================================================

def test_deletion_keywords_detected():
    """Test that all deletion keywords are recognized."""
    keywords = ["DELETE", "REMOVE", "ERASE", "FORGET"]
    
    for keyword in keywords:
        # Uppercase
        assert DeletionService.is_deletion_request(keyword) == True
        
        # Lowercase
        assert DeletionService.is_deletion_request(keyword.lower()) == True
        
        # Mixed case
        assert DeletionService.is_deletion_request(keyword.title()) == True
    
    # Non-keywords
    assert DeletionService.is_deletion_request("HELLO") == False
    assert DeletionService.is_deletion_request("CANCEL") == False


# =============================================================================
# TEST 2: Patient data deleted
# =============================================================================

def test_patient_data_deleted(db, test_phone):
    """Test that patient record is deleted."""
    # Create patient
    patient = Patient(
        phone=test_phone,
        name="Test User",
        clinic_id="test-clinic-id"
    )
    db.add(patient)
    db.commit()
    
    # Verify patient exists
    assert db.query(Patient).filter_by(phone=test_phone).first() is not None
    
    # Request deletion
    result = DeletionService.anonymize_patient_data(test_phone, db=db)
    
    # Verify deletion completed
    assert result["status"] == "completed"
    assert result["records_deleted"]["patients"] == 1
    
    # Verify patient no longer exists
    assert db.query(Patient).filter_by(phone=test_phone).first() is None


# =============================================================================
# TEST 3: Appointments anonymized (not deleted)
# =============================================================================

def test_appointments_anonymized(db, test_phone):
    """Test that appointments are anonymized, not deleted."""
    # Create appointment
    appointment = Appointment(
        clinic_id="test-clinic-id",
        doctor_id="test-doctor-id",
        service_id="test-service-id",
        patient_phone=test_phone,
        patient_name="Test User",
        start_utc_ts=datetime.utcnow(),
        end_utc_ts=datetime.utcnow(),
        status="booked"
    )
    db.add(appointment)
    db.commit()
    original_id = appointment.id
    
    # Request deletion
    result = DeletionService.anonymize_patient_data(test_phone, db=db)
    
    # Verify appointment still exists
    anonymized_apt = db.query(Appointment).filter_by(id=original_id).first()
    assert anonymized_apt is not None
    
    # Verify anonymized
    assert anonymized_apt.patient_phone == "+91XXXXXXXXX"
    assert "DELETED_USER_" in anonymized_apt.patient_name
    
    # Verify count
    assert result["records_deleted"]["appointments"] == 1


# =============================================================================
# TEST 4: Consents deleted
# =============================================================================

def test_consents_deleted(db, test_phone):
    """Test that consent records are deleted."""
    # Create consent
    consent = PatientConsent(
        phone_number=test_phone,
        consent_text="Test consent",
        consent_version="v1.0",
        consent_status=ConsentStatus.GRANTED
    )
    db.add(consent)
    db.commit()
    
    # Verify consent exists
    assert db.query(PatientConsent).filter_by(phone_number=test_phone).first() is not None
    
    # Request deletion
    result = DeletionService.anonymize_patient_data(test_phone, db=db)
    
    # Verify consent deleted
    assert db.query(PatientConsent).filter_by(phone_number=test_phone).first() is None
    assert result["records_deleted"]["consents"] == 1


# =============================================================================
# TEST 5: Idempotent deletion (second delete does nothing)
# =============================================================================

def test_idempotent_deletion(db, test_phone):
    """Test that deleting twice doesn't fail."""
    # Create patient
    patient = Patient(
        phone=test_phone,
        name="Test User",
        clinic_id="test-clinic-id"
    )
    db.add(patient)
    db.commit()
    
    # First deletion
    result1 = DeletionService.anonymize_patient_data(test_phone, db=db)
    assert result1["status"] == "completed"
    
    # Second deletion (should be idempotent)
    result2 = DeletionService.anonymize_patient_data(test_phone, db=db)
    assert result2["status"] == "already_deleted"


# =============================================================================
# TEST 6: Deletion log retained
# =============================================================================

def test_deletion_log_retained(db, test_phone):
    """Test that deletion creates immutable audit log."""
    # Create and delete patient
    patient = Patient(
        phone=test_phone,
        name="Test User",
        clinic_id="test-clinic-id"
    )
    db.add(patient)
    db.commit()
    
    result = DeletionService.anonymize_patient_data(test_phone, db=db)
    
    # Verify deletion log exists
    deletion_log = db.query(PatientDeletion).filter_by(
        phone_number=test_phone,
        deletion_status="completed"
    ).first()
    
    assert deletion_log is not None
    assert deletion_log.deletion_requested_at is not None
    assert deletion_log.deletion_completed_at is not None
    assert deletion_log.patient_records_deleted == 1


# =============================================================================
# TEST 7: No PHI remains after deletion
# =============================================================================

def test_no_phi_remains(db, test_phone):
    """Test that no identifiable PHI remains after deletion."""
    # Create all records
    patient = Patient(
        phone=test_phone,
        name="Sensitive Name",
        clinic_id="test-clinic-id"
    )
    db.add(patient)
    
    appointment = Appointment(
        clinic_id="test-clinic-id",
        doctor_id="test-doctor-id",
        service_id="test-service-id",
        patient_phone=test_phone,
        patient_name="Sensitive Name",
        start_utc_ts=datetime.utcnow(),
        end_utc_ts=datetime.utcnow(),
        status="booked"
    )
    db.add(appointment)
    
    consent = PatientConsent(
        phone_number=test_phone,
        consent_text="Test",
        consent_version="v1.0",
        consent_status=ConsentStatus.GRANTED
    )
    db.add(consent)
    db.commit()
    
    # Delete
    DeletionService.anonymize_patient_data(test_phone, db=db)
    
    # Search for original phone in ALL tables
    # Should not find it anywhere except deletion_log
    
    # Check patients
    patient_match = db.query(Patient).filter_by(phone=test_phone).first()
    assert patient_match is None
    
    # Check appointments
    apt_match = db.query(Appointment).filter_by(patient_phone=test_phone).first()
    assert apt_match is None
    
    # Check consents
    consent_match = db.query(PatientConsent).filter_by(phone_number=test_phone).first()
    assert consent_match is None
    
    # Deletion log should have it (for collision prevention)
    deletion_match = db.query(PatientDeletion).filter_by(phone_number=test_phone).first()
    assert deletion_match is not None  # This is OK - it's for ghost prevention


# =============================================================================
# BONUS: Test deletion status check
# =============================================================================

def test_deletion_status_check(db, test_phone):
    """Test that deletion status can be queried."""
    # Before deletion
    status = DeletionService.get_deletion_status(test_phone, db)
    assert status is None
    
    # Create and delete
    patient = Patient(phone=test_phone, name="Test", clinic_id="test-clinic-id")
    db.add(patient)
    db.commit()
    
    DeletionService.anonymize_patient_data(test_phone, db=db)
    
    # After deletion
    status = DeletionService.get_deletion_status(test_phone, db)
    assert status is not None
    assert status["status"] == "completed"
    assert status["records_deleted"]["patients"] == 1
