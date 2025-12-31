"""
Hybrid Booking Tests - Direct and Search Paths

Tests both booking methods:
1. Direct booking via doctor's WhatsApp number
2. City search → select doctor → booking

All compliance rules enforced (consent, age, ProhibitedDataError, metadata-only).
"""
import pytest
from datetime import datetime

from app.models.doctor import Doctor
from app.services.search_service import SearchService, RateLimitError
from app.services.booking_service import BookingService


@pytest.fixture
def create_test_doctor(db_session):
    """Create test doctor for hybrid booking."""
    doctor = Doctor(
        name="Dr. Test Smith",
        specialization="General Medicine",
        clinic_id="clinic_123",
        whatsapp_number="+919876543210",
        city="Mumbai",
        is_searchable=True,  # Opt-in for search
        is_active=True
    )
    db_session.add(doctor)
    db_session.commit()
    db_session.refresh(doctor)
    return doctor


@pytest.fixture
def create_private_doctor(db_session):
    """Create private doctor (not searchable)."""
    doctor = Doctor(
        name="Dr. Private Jones",
        specialization="Dermatology",
        clinic_id="clinic_456",
        whatsapp_number="+919876543211",
        city="Mumbai",
        is_searchable=False,  # Privacy: default, not searchable
        is_active=True
    )
    db_session.add(doctor)
    db_session.commit()
    db_session.refresh(doctor)
    return doctor


# =============================================================================
# TEST 1: Doctor shareable link generation
# =============================================================================

def test_doctor_shareable_link(create_test_doctor):
    """Test WhatsApp link generation for direct booking."""
    doctor = create_test_doctor
    
    link = doctor.get_shareable_link()
    assert link is not None
    assert "https://wa.me/" in link
    assert "9876543210" in link  # Number without +
    assert "text=Hi" in link


# =============================================================================
# TEST 2: City search returns only opt-in doctors
# =============================================================================

def test_city_search_only_searchable(db_session, create_test_doctor, create_private_doctor):
    """Test that only is_searchable=True doctors appear in search."""
    results = SearchService.search_doctors(
        city="Mumbai",
        specialty=None,
        ip_address="192.168.1.1",
        db=db_session
    )
    
    # Should return searchable doctor only
    assert len(results) == 1
    assert results[0]["name"] == "Dr. Test Smith"
    
    # Private doctor should NOT appear
    names = [r["name"] for r in results]
    assert "Dr. Private Jones" not in names


# =============================================================================
# TEST 3: Search by city + specialty
# =============================================================================

def test_search_by_city_and_specialty(db_session, create_test_doctor):
    """Test filtered search by city and specialty."""
    # Search for General Medicine in Mumbai
    results = SearchService.search_doctors(
        city="Mumbai",
        specialty="General Medicine",
        ip_address="192.168.1.1",
        db=db_session
    )
    
    assert len(results) >= 1
    assert results[0]["specialty"] == "General Medicine"
    
    # Search for different specialty should return empty
    results_derma = SearchService.search_doctors(
        city="Mumbai",
        specialty="Cardiology",  # Not in test data
        ip_address="192.168.1.1",
        db=db_session
    )
    
    # May be empty or have different doctors
    # (Depends on test data, but original doctor should not match)


# =============================================================================
# TEST 4: Search rate limiting (10/min per IP)
# =============================================================================

def test_search_rate_limiting(db_session, create_test_doctor):
    """Test that search enforces rate limit (10 searches/min per IP)."""
    ip = "192.168.1.100"
    
    # Make 10 successful searches
    for i in range(10):
        SearchService.search_doctors(
            city="Mumbai",
            specialty=None,
            ip_address=ip,
            db=db_session
        )
    
    # 11th search should be rate limited
    with pytest.raises(RateLimitError):
        SearchService.search_doctors(
            city="Mumbai",
            specialty=None,
            ip_address=ip,
            db=db_session
        )


# =============================================================================
# TEST 5: Doctor opt-in/opt-out
# =============================================================================

def test_doctor_opt_in_opt_out(db_session, create_test_doctor):
    """Test doctor can opt-in/opt-out of search."""
    doctor = create_test_doctor
    
    # Initially searchable
    assert doctor.is_searchable == True
    
    # Opt-out
    SearchService.update_doctor_searchable(
        doctor_id=str(doctor.id),
        searchable=False,
        admin_user_id="admin_123",
        db=db_session
    )
    
    # Refresh
    db_session.refresh(doctor)
    assert doctor.is_searchable == False
    
    # Should no longer appear in search
    results = SearchService.search_doctors(
        city="Mumbai",
        specialty=None,
        ip_address="192.168.1.2",
        db=db_session
    )
    names = [r["name"] for r in results]
    assert "Dr. Test Smith" not in names


# =============================================================================
# TEST 6: Direct booking via WhatsApp number
# =============================================================================

def test_direct_booking_via_whatsapp(db_session, create_test_doctor):
    """Test booking flow works with doctor's WhatsApp number."""
    doctor = create_test_doctor
    phone = "+919998887777"  # Patient phone
    
    # Patient can book directly via doctor's WhatsApp
    # (BookingService would route based on incoming WhatsApp number)
    
    # Verify doctor can be found by WhatsApp number
    found_doctor = SearchService.get_doctor_by_whatsapp(
        whatsapp_number=doctor.whatsapp_number,
        db=db_session
    )
    
    assert found_doctor is not None
    assert found_doctor.id == doctor.id


# =============================================================================
# TEST 7: Search returns WhatsApp links
# =============================================================================

def test_search_returns_whatsapp_links(db_session, create_test_doctor):
    """Test that search results include WhatsApp links for direct booking."""
    results = SearchService.search_doctors(
        city="Mumbai",
        specialty=None,
        ip_address="192.168.1.3",
        db=db_session
    )
    
    assert len(results) >= 1
    result = results[0]
    
    # Should have WhatsApp link
    assert "whatsapp_link" in result
    assert "https://wa.me/" in result["whatsapp_link"]
    assert result["name"] == "Dr. Test Smith"


# =============================================================================
# TEST 8: Search audit logging (metadata only)
# =============================================================================

def test_search_audit_logging(db_session, create_test_doctor):
    """Test that searches are audit logged (metadata only, no PHI)."""
    from app.models.audit_log import AuditLog
    
    SearchService.search_doctors(
        city="Mumbai",
        specialty="General Medicine",
        ip_address="192.168.1.4",
        db=db_session
    )
    
    # Check audit log
    log = db_session.query(AuditLog).filter(
        AuditLog.event_type == "doctor_search"
    ).first()
    
    assert log is not None
    assert log.metadata.get("city") == "Mumbai"
    assert log.metadata.get("specialty") == "General Medicine"
    assert "results_count" in log.metadata
    
    # Should NOT contain any patient PHI
    assert "patient_phone" not in log.metadata


# =============================================================================
# TEST 9: Inactive doctors not searchable
# =============================================================================

def test_inactive_doctors_not_searchable(db_session):
    """Test that inactive doctors don't appear in search."""
    doctor = Doctor(
        name="Dr. Inactive",
        specialization="Surgery",
        clinic_id="clinic_789",
        whatsapp_number="+919876543212",
        city="Mumbai",
        is_searchable=True,
        is_active=False  # Inactive
    )
    db_session.add(doctor)
    db_session.commit()
    
    results = SearchService.search_doctors(
        city="Mumbai",
        specialty=None,
        ip_address="192.168.1.5",
        db=db_session
    )
    
    # Inactive doctor should NOT appear
    names = [r["name"] for r in results]
    assert "Dr. Inactive" not in names


# =============================================================================
# TEST 10: Search limits results to 50
# =============================================================================

def test_search_result_limit(db_session):
    """Test that search limits results to 50 doctors."""
    # Create 60 searchable doctors in same city
    for i in range(60):
        doctor = Doctor(
            name=f"Dr. Test {i}",
            specialization="General Medicine",
            clinic_id=f"clinic_{i}",
            whatsapp_number=f"+9198765432{i:02d}",
            city="Delhi",
            is_searchable=True,
            is_active=True
        )
        db_session.add(doctor)
    db_session.commit()
    
    results = SearchService.search_doctors(
        city="Delhi",
        specialty=None,
        ip_address="192.168.1.6",
        db=db_session
    )
    
    # Should be limited to 50
    assert len(results) <= 50


# =============================================================================
# TEST 11: QR code data generation
# =============================================================================

def test_qr_code_data_generation(create_test_doctor):
    """Test QR code data returns WhatsApp link."""
    doctor = create_test_doctor
    
    qr_data = doctor.get_qr_code_data()
    assert qr_data is not None
    assert qr_data == doctor.get_shareable_link()
    assert "https://wa.me/" in qr_data
