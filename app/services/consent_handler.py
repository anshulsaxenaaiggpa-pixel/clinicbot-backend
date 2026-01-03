from app.models.consent import ConsentLog
from app.db.session import SessionLocal
from app.services.audit_logger import audit_logger

CONSENT_TEXT_V1 = """
🤖 CuraSlot Appointment Bot

We collect ONLY:
✅ Phone (booking)
✅ Name (optional)

We NEVER collect:
❌ Prescriptions/Medical Records

Data → Clinic ONLY
Privacy: curaslot.in/privacy

Reply NUMBER ONLY:
1. AGREE & CONTINUE
2. DECLINE
"""

CONSENT_TEXT_V1_USA = """
🤖 CuraSlot USA - Compliant

COPPA (<13): PARENT/GUARDIAN consent required
HIPAA: Scheduling only (NO PHI)
CCPA: Reply DATA/DELETE for rights

Reply:
1. AGREE (Parent/Guardian)
2. DECLINE
"""

def get_consent_text(phone: str) -> str:
    """Return USA or Global consent text based on phone number."""
    if phone.startswith("+1"):
        return CONSENT_TEXT_V1_USA
    return CONSENT_TEXT_V1

# Post-consent booking menu
BOOKING_MENU = """
✅ Appointments unlocked!

Reply NUMBER ONLY:
1. Book new appointment
2. View upcoming
3. Cancel appointment
0. Help/Repeat
"""

# COPPA-compliant booking options
BOOKING_FOR_MENU = """
Booking for:
1. Myself (Adult)
2. Child (Parent booking)
"""

# Doctor selection menu (dynamic - base template)
DOCTOR_MENU_TEMPLATE = """
Doctors today:

{doctors}
0. Back to menu

Reply NUMBER ONLY:
"""

# Time slot menu (dynamic - base template)  
TIME_MENU_TEMPLATE = """
{doctor_name} available:

{slots}
0. Change doctor

Reply NUMBER ONLY:
"""

# Confirmation menu
CONFIRM_MENU_TEMPLATE = """
Confirm: {doctor_name} at {time}?

1. ✅ BOOK NOW
2. ❌ Change time
0. Change doctor

Reply NUMBER ONLY:
"""

# Success message
BOOKING_SUCCESS = """
✅ BOOKED!

{doctor_name}
📅 {date}
🕐 {time}

Reply:
0. Back to menu
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

async def record_consent(phone: str, clinic_id: str, agreed: bool, ip_address: str = None):
    db = SessionLocal()
    try:
        consent = ConsentLog(
            phone=phone, clinic_id=clinic_id,
            consent_given=agreed, consent_source="whatsapp",
            consent_version="v1.0", consent_text=CONSENT_TEXT_V1
        )
        db.add(consent)
        db.commit()
        db.refresh(consent)
        
        # LOG TO AUDIT (REFINED)
        await audit_logger.log_action(
            clinic_id=clinic_id,
            actor_type="PATIENT",
            actor_ref=phone,
            action="CONSENT_GIVEN" if agreed else "CONSENT_DECLINED",
            entity_type="CONSENT",
            entity_id=str(consent.id),
            new_state={"status": "given" if agreed else "declined"},
            ip_address=ip_address
        )
        
    finally:
        db.close()
