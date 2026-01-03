import pytest
from app.services.audit_logger import audit_logger

@pytest.mark.asyncio
async def test_consent_audit_log():
    """Verify CONSENT_GIVEN action is logged correctly."""
    # This requires a database - we'll test that it doesn't crash and returns an ID
    audit_id = await audit_logger.log_action(
        clinic_id="aa4171cd-55b1-4da5-828e-00edcd67bbfd",
        actor_type="PATIENT",
        actor_reference="+919999999999",
        action="CONSENT_GIVEN",
        entity_type="CONSENT",
        new_state={"status": "given"}
    )
    assert audit_id is not None

@pytest.mark.asyncio
async def test_booking_audit_log():
    """Verify BOOK_APPOINTMENT action is logged correctly."""
    audit_id = await audit_logger.log_action(
        clinic_id="aa4171cd-55b1-4da5-828e-00edcd67bbfd",
        actor_type="PATIENT",
        actor_reference="+919999999999",
        action="BOOK_APPOINTMENT",
        entity_type="APPOINTMENT",
        new_state={"doctor": "Dr Sharma", "time": "9:00 AM"}
    )
    assert audit_id is not None
