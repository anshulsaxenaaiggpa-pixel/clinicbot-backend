from app.models.consent import ConsentLog
from app.db.session import SessionLocal
from app.services.audit_logger import log_consent_action

CONSENT_TEXT_V1 = """
🤖 CuraSlot Appointment Bot

We collect ONLY:
✅ Phone (for booking)
✅ Name (optional) 

We NEVER collect:
❌ Prescriptions/Medical Records
❌ Health details

Data shared ONLY with your clinic.
Privacy: curaslot.in/privacy

Reply:
1️⃣ AGREE & CONTINUE
2️⃣ DECLINE
"""

def check_consent(phone: str, clinic_id: str) -> bool:
    db = SessionLocal()
    try:
        return db.query(ConsentLog).filter(
            ConsentLog.phone == phone,
            ConsentLog.clinic_id == clinic_id,
            ConsentLog.consent_given == True
        ).first() is not None
    finally:
        db.close()

def record_consent(phone: str, clinic_id: str, agreed: bool):
    db = SessionLocal()
    try:
        consent = ConsentLog(
            phone=phone, clinic_id=clinic_id,
            consent_given=agreed, consent_source="whatsapp",
            consent_version="v1.0", consent_text=CONSENT_TEXT_V1
        )
        db.add(consent)
        db.commit()
        
        # Log to immutable audit trail
        log_consent_action(phone, clinic_id, agreed)
        
    finally:
        db.close()
