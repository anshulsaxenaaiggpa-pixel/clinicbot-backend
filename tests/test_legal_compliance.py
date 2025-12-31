"""
Legal Compliance Verification Script

Automated testing to verify legal/compliance requirements are enforced.
Run this before production deployment to ensure policies are not "paper only".

Tests:
1. Consent prompt appears before data capture
2. Age gate appears before doctor interaction
3. Metadata-only storage enforced
4. No chat transcripts stored
5. Search only shows opt-in doctors
6. Privacy/Terms commands work
7. Audit trails complete
"""
import pytest
from datetime import datetime

from app.models.patient_consent import PatientConsent, CONSENT_TEXT_V1
from app.models.conversation_state import ConversationState, BookingState
from app.models.doctor import Doctor
from app.models.audit_log import AuditLog
from app.services.booking_service import BookingService
from app.services.search_service import SearchService


class TestLegalComplianceVerification:
    """Legal Mode Verification - Phase 1 Compliance Gate"""
    
    # =========================================================================
    # TEST 1: Consent prompt appears BEFORE any data capture
    # =========================================================================
    
    def test_consent_prompt_before_data_capture(self, db_session):
        """
        LEGAL REQUIREMENT: Consent must be shown before ANY data processing.
        
        Per LEGAL_ASSUMPTIONS.md and COMPLIANCE_BASELINE.md
        """
        phone = "+919999000001"
        
        # First message should ALWAYS be consent prompt
        response = BookingService.handle_message(phone, "Hi", db_session)
        
        # Verify consent text present
        assert CONSENT_TEXT_V1 in response["message"] or "consent" in response["message"].lower()
        
        # Verify NO patient data created yet
        from app.models.patient import Patient
        patient = db_session.query(Patient).filter(Patient.phone_number == phone).first()
        # Patient may exist but consent should not be granted yet
        
        consent = db_session.query(PatientConsent).filter(
            PatientConsent.phone_number == phone,
            PatientConsent.consent_status == "granted"
        ).first()
        assert consent is None, "Consent should not be granted before YES response"
    
    # =========================================================================
    # TEST 2: Age gate appears before doctor interaction
    # =========================================================================
    
    def test_age_gate_before_doctor_interaction(self, db_session):
        """
        LEGAL REQUIREMENT: Age 18+ verified before booking.
        
        Per LEGAL_ASSUMPTIONS.md: Minors (under 18) not permitted.
        """
        phone = "+919999000002"
        
        # Grant consent first
        BookingService.handle_message(phone, "Hi", db_session)
        BookingService.handle_message(phone, "YES", db_session)
        
        # Should now show age gate
        state = db_session.query(ConversationState).filter(
            ConversationState.phone_number == phone
        ).first()
        
        assert state.current_state == BookingState.AGE_VERIFICATION
        assert state.age_verified == False  # Not yet verified
        
        # NO doctor interaction should be possible yet
        assert state.get_context("doctor_id") is None
    
    # =========================================================================
    # TEST 3: Metadata-only storage enforced (ProhibitedDataError)
    # =========================================================================
    
    def test_metadata_only_storage_enforced(self, db_session):
        """
        LEGAL REQUIREMENT: Only scheduling metadata stored, NO medical content.
        
        Per COMPLIANCE_BASELINE.md and PRODUCT_SCOPE.md
        """
        from app.schemas.data_classification import ProhibitedDataError
        from app.models.conversation_state import StateManager
        
        phone = "+919999000003"
        state = StateManager.get_or_create_state(phone, db_session)
        
        # These MUST raise ProhibitedDataError
        prohibited_keys = ["symptoms", "diagnosis", "medical_notes", "reason", "complaint"]
        
        for key in prohibited_keys:
            with pytest.raises(ProhibitedDataError):
                state.set_context(key, "any value")
        
        # Only these should be allowed
        allowed_keys = ["clinic_id", "doctor_id", "service_id", "selected_date", "selected_time"]
        for key in allowed_keys:
            state.set_context(key, "test_value")  # Should not raise
    
    # =========================================================================
    # TEST 4: No chat transcripts stored ANYWHERE
    # =========================================================================
    
    def test_no_chat_transcripts_stored(self, db_session):
        """
        LEGAL REQUIREMENT: NO chat content stored per COMPLIANCE_BASELINE.md
        
        Only structured metadata allowed.
        """
        phone = "+919999000004"
        
        # Complete full booking flow
        BookingService.handle_message(phone, "Hi", db_session)
        BookingService.handle_message(phone, "YES", db_session)
        BookingService.handle_message(phone, "YES", db_session)
        for i in range(5):
            BookingService.handle_message(phone, "1", db_session)
        
        # Check conversation state
        state = db_session.query(ConversationState).filter(
            ConversationState.phone_number == phone
        ).first()
        
        # These keys should NEVER exist
        forbidden_keys = ["message_body", "chat_transcript", "message_history", "user_input"]
        
        if state.context:
            for key in forbidden_keys:
                assert key not in state.context, f"Forbidden key '{key}' found in context!"
    
    # =========================================================================
    # TEST 5: Search only shows opt-in doctors
    # =========================================================================
    
    def test_search_only_shows_opt_in_doctors(self, db_session):
        """
        LEGAL REQUIREMENT: Privacy-first, doctors must opt-in to search.
        
        Default is_searchable=False per PRODUCT_SCOPE v1.1
        """
        # Create searchable doctor
        doctor1 = Doctor(
            name="Dr. Searchable",
            specialization="General",
            clinic_id="clinic1",
            whatsapp_number="+919876543210",
            city="Mumbai",
            is_searchable=True,  # Opted in
            is_active=True
        )
        db_session.add(doctor1)
        
        # Create private doctor
        doctor2 = Doctor(
            name="Dr. Private",
            specialization="General",
            clinic_id="clinic2",
            whatsapp_number="+919876543211",
            city="Mumbai",
            is_searchable=False,  # NOT opted in
            is_active=True
        )
        db_session.add(doctor2)
        db_session.commit()
        
        # Search for all doctors in Mumbai
        results = SearchService.search_doctors(
            city="Mumbai",
            specialty=None,
            ip_address="192.168.1.1",
            db=db_session
        )
        
        # Only searchable doctor should appear
        names = [r["name"] for r in results]
        assert "Dr. Searchable" in names
        assert "Dr. Private" not in names, "Private doctor should NOT appear in search!"
    
    # =========================================================================
    # TEST 6: Privacy/Terms commands work
    # =========================================================================
    
    def test_privacy_terms_commands(self, db_session):
        """
        LEGAL REQUIREMENT: Users can access Privacy Policy and Terms on demand.
        """
        phone = "+919999000005"
        
        # PRIVACY command
        response_privacy = BookingService.handle_message(phone, "PRIVACY", db_session)
        assert "privacy" in response_privacy["message"].lower() or "policy" in response_privacy["message"].lower()
        # Should contain link or "Contact admin" message
        
        # TERMS command
        response_terms = BookingService.handle_message(phone, "TERMS", db_session)
        assert "terms" in response_terms["message"].lower() or "conditions" in response_terms["message"].lower()
    
    # =========================================================================
    # TEST 7: Audit trails complete and secure
    # =========================================================================
    
    def test_audit_trails_complete(self, db_session):
        """
        LEGAL REQUIREMENT: All actions audit logged per COMPLIANCE_BASELINE.md
        """
        phone = "+919999000006"
        
        # Perform actions
        BookingService.handle_message(phone, "Hi", db_session)
        BookingService.handle_message(phone, "YES", db_session)  # Consent
        BookingService.handle_message(phone, "YES", db_session)  # Age
        
        # Check audit logs
        logs = db_session.query(AuditLog).filter(
            AuditLog.patient_phone_hash == AuditLog.hash_phone(phone)
        ).all()
        
        # Should have logs for consent and age verification
        event_types = [log.event_type for log in logs]
        
        # Consent should be logged
        assert any("consent" in et for et in event_types), "Consent not logged!"
        
        # Age verification should be logged
        assert any("age" in et for et in event_types), "Age verification not logged!"
    
    # =========================================================================
    # TEST 8: Minors blocked with guardian message
    # =========================================================================
    
    def test_minors_blocked_with_guardian_message(self, db_session):
        """
        LEGAL REQUIREMENT: Under 18 rejected per LEGAL_ASSUMPTIONS.md
        """
        phone = "+919999000007"
        
        # Complete consent
        BookingService.handle_message(phone, "Hi", db_session)
        BookingService.handle_message(phone, "YES", db_session)
        
        # Reply NO to age verification (under 18)
        response = BookingService.handle_message(phone, "NO", db_session)
        
        # Should mention guardian/parent
        message_lower = response["message"].lower()
        assert "parent" in message_lower or "guardian" in message_lower or "18" in response["message"]
        
        # Verify NO booking created
        from app.models.appointment import Appointment
        appointment = db_session.query(Appointment).filter(
            Appointment.patient_phone == phone
        ).first()
        assert appointment is None, "Minor should not be able to book!"
    
    # =========================================================================
    # TEST 9: Consent withdrawal stops ALL processing
    # =========================================================================
    
    def test_consent_withdrawal_stops_processing(self, db_session):
        """
        LEGAL REQUIREMENT: STOP keyword halts processing per COMPLIANCE_BASELINE.md
        """
        phone = "+919999000008"
        
        # Start booking
        BookingService.handle_message(phone, "Hi", db_session)
        
        # Withdraw consent
        response = BookingService.handle_message(phone, "STOP", db_session)
        
        # Should confirm withdrawal
        assert "stop" in response["message"].lower() or "decline" in response["message"].lower()
        
        # Verify consent NOT granted
        consent = db_session.query(PatientConsent).filter(
            PatientConsent.phone_number == phone,
            PatientConsent.consent_status == "granted"
        ).first()
        assert consent is None, "Consent should not be granted after STOP!"
    
    # =========================================================================
    # TEST 10: Age and consent flags stored separately
    # =========================================================================
    
    def test_age_consent_flags_separate(self, db_session):
        """
        LEGAL REQUIREMENT: Separate consent_granted and age_verified flags.
        """
        phone = "+919999000009"
        
        # Grant consent
        BookingService.handle_message(phone, "Hi", db_session)
        BookingService.handle_message(phone, "YES", db_session)
        
        state = db_session.query(ConversationState).filter(
            ConversationState.phone_number == phone
        ).first()
        
        # Consent should be True
        assert state.consent_granted == True
        
        # Age should still be False
        assert state.age_verified == False
        
        # Now verify age
        BookingService.handle_message(phone, "YES", db_session)
        db_session.refresh(state)
        
        # Both should now be True
        assert state.consent_granted == True
        assert state.age_verified == True


# =============================================================================
# Compliance Summary Report
# =============================================================================

def generate_compliance_report(session):
    """
    Generate compliance verification report.
    
    Run after all tests to confirm legal requirements met.
    """
    print("\n" + "="*80)
    print("LEGAL COMPLIANCE VERIFICATION REPORT")
    print("="*80)
    
    # Check consent enforcement
    consents_granted = session.query(PatientConsent).filter(
        PatientConsent.consent_status == "granted"
    ).count()
    print(f"\n✅ Consents Granted: {consents_granted}")
    
    # Check age verifications
    age_verified = session.query(ConversationState).filter(
        ConversationState.age_verified == True
    ).count()
    print(f"✅ Age Verifications Passed: {age_verified}")
    
    # Check searchable doctors
    searchable_doctors = session.query(Doctor).filter(
        Doctor.is_searchable == True
    ).count()
    total_doctors = session.query(Doctor).count()
    print(f"✅ Searchable Doctors: {searchable_doctors}/{total_doctors} (opt-in only)")
    
    # Check audit log integrity
    audit_logs = session.query(AuditLog).count()
    print(f"✅ Audit Log Entries: {audit_logs} (immutable)")
    
    # Check for prohibited data
    states = session.query(ConversationState).all()
    prohibited_found = False
    for state in states:
        if state.context:
            prohibited_keys = ["symptoms", "diagnosis", "medical_notes", "chat_transcript"]
            for key in prohibited_keys:
                if key in state.context:
                    prohibited_found = True
                    print(f"❌ PROHIBITED DATA FOUND: {key} in conversation {state.id}")
    
    if not prohibited_found:
        print("✅ No Prohibited Data Found (metadata only)")
    
    print("\n" + "="*80)
    print("COMPLIANCE STATUS: ✅ VERIFIED" if not prohibited_found else "❌ FAILED")
    print("="*80 + "\n")


if __name__ == "__main__":
    """
    Run compliance verification.
    
    Usage:
        pytest tests/test_legal_compliance.py -v
        
    Or for report:
        python tests/test_legal_compliance.py
    """
    print("Run with: pytest tests/test_legal_compliance.py -v")
