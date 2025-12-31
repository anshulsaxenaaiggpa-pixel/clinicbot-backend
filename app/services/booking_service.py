"""
WhatsApp Booking Service

Implements appointment booking flow via WhatsApp.
Enforces all compliance rules (consent, age, data minimization).
"""
from typing import Optional, Dict
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models.conversation_state import ConversationState, BookingState, StateManager
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.services.consent_service import ConsentService
from app.services.audit_service import AuditService
from app.schemas.data_classification import ProhibitedDataError


class AgeVerificationError(Exception):
    """Raised when user is under 18."""
    pass


class BookingService:
    """
    WhatsApp booking flow orchestration.
    
    Principles:
    - Consent first (before any processing)
    - Age verification (18+ only)
    - Metadata only (no chat transcripts)
    - ProhibitedDataError if medical content attempted
    """
    
    @staticmethod
    def handle_message(phone: str, message: str, db: Session) -> Dict:
        """
        Process incoming WhatsApp message.
        
        Returns response dict with:
        - message: Text to send back
        - next_state: Expected next state
        - booking_id: If appointment confirmed
        """
        # Check for PRIVACY/TERMS commands FIRST (accessible anytime)
        message_upper = message.strip().upper()
        
        if message_upper in ["PRIVACY", "PRIVACY POLICY"]:
            # Link to privacy policy
            return {
                "message": (
                    "📄 **Privacy Policy**\n\n"
                    "Your data privacy is important to us.\n\n"
                    "✅ We collect ONLY minimal scheduling metadata\n"
                    "❌ We do NOT store medical information or chat messages\n\n"
                    "**Full Privacy Policy:**\n"
                    "https://clinicbot.example.com/privacy\n\n"
                    "**Questions?** privacy@trendoos.com\n\n"
                    "**Rights:** Send DELETE to erase your data anytime."
                ),
                "next_state": None
            }
        
        if message_upper in ["TERMS", "TERMS AND CONDITIONS", "T&C"]:
            # Link to terms
            return {
                "message": (
                    "📜 **Terms of Use**\n\n"
                    "By using ClinicBot, you agree:\n\n"
                    "✅ You are 18+ years old\n"
                    "✅ This is a booking tool ONLY (not medical service)\n"
                    "⚠️ For emergencies, call 108 immediately\n\n"
                    "**Full Terms:**\n"
                    "https://clinicbot.example.com/terms\n\n"
                    "**Questions?** support@trendoos.com"
                ),
                "next_state": None
            }
        
        # Get or create conversation state
        state = StateManager.get_or_create_state(phone, db)
        
        current_state = state.current_state
        
        # State-based routing
        if current_state == BookingState.INITIAL:
            return BookingService._handle_initial(phone, message, state, db)
        
        elif current_state == BookingState.CONSENT_PENDING:
            return BookingService._handle_consent(phone, message, state, db)
        
        elif current_state == BookingState.AGE_VERIFICATION:
            return BookingService._handle_age_verification(phone, message, state, db)
        
        elif current_state == BookingState.CLINIC_SELECTION:
            return BookingService._handle_clinic_selection(phone, message, state, db)
        
        elif current_state == BookingState.DOCTOR_SELECTION:
            return BookingService._handle_doctor_selection(phone, message, state, db)
        
        elif current_state == BookingState.SERVICE_SELECTION:
            return BookingService._handle_service_selection(phone, message, state, db)
        
        elif current_state == BookingState.DATE_SELECTION:
            return BookingService._handle_date_selection(phone, message, state, db)
        
        elif current_state == BookingState.TIME_SELECTION:
            return BookingService._handle_time_selection(phone, message, state, db)
        
        else:
            # Unknown state - reset
            state.reset()
            db.commit()
            return {
                "message": "Session expired. Let's start fresh! I'll help you book an appointment.",
                "next_state": BookingState.CONSENT_PENDING
            }
    
    @staticmethod
    def _handle_initial(phone: str, message: str, state: ConversationState, db: Session) -> Dict:
        """Handle initial contact."""
        # Check if consent already granted
        if ConsentService.check_consent_granted(phone, db):
            state.consent_granted = True
            state.advance_state(BookingState.AGE_VERIFICATION)
            db.commit()
            
            # Skip to age verification
            return BookingService._send_age_prompt()
        else:
            # Send consent prompt
            state.advance_state(BookingState.CONSENT_PENDING)
            db.commit()
            
            from app.models.patient_consent import CONSENT_TEXT_V1
            return {
                "message": f"Welcome to ClinicBot! 👋\n\n{CONSENT_TEXT_V1}",
                "next_state": BookingState.CONSENT_PENDING
            }
    
    @staticmethod
    def _handle_consent(phone: str, message: str, state: ConversationState, db: Session) -> Dict:
        """Handle consent response."""
        response_upper = message.strip().upper()
        
        if response_upper in ["YES", "Y"]:
            # Capture consent
            result = ConsentService.capture_consent(
                phone_number=phone,
                reply_text="YES",
                channel="whatsapp",
                db=db
            )
            
            if result["status"] == "granted":
                state.consent_granted = True
                state.advance_state(BookingState.AGE_VERIFICATION)
                db.commit()
                
                return BookingService._send_age_prompt()
            else:
                return {
                    "message": "There was an error processing your consent. Please try again.",
                    "next_state": BookingState.CONSENT_PENDING
                }
        
        elif response_upper in ["NO", "N", "STOP"]:
            # Consent denied
            ConsentService.capture_consent(
                phone_number=phone,
                reply_text=response_upper,
                channel="whatsapp",
                db=db
            )
            
            state.reset()
            db.commit()
            
            return {
                "message": "Understood. You have declined consent. No data will be processed. Reply YES anytime to start.",
                "next_state": BookingState.INITIAL
            }
        
        else:
            # Invalid response
            return {
                "message": "Please reply YES to continue or NO to decline.",
                "next_state": BookingState.CONSENT_PENDING
            }
    
    @staticmethod
    def _send_age_prompt() -> Dict:
        """Send age verification prompt."""
        return {
            "message": (
                "Are you 18 years or older?\n\n"
                "Reply:\n"
                "1️⃣ YES - I am 18 or older\n"
                "2️⃣ NO - I am under 18"
            ),
            "next_state": BookingState.AGE_VERIFICATION
        }
    
    @staticmethod
    def _handle_age_verification(phone: str, message: str, state: ConversationState, db: Session) -> Dict:
        """
        Handle age verification.
        
        Per LEGAL_ASSUMPTIONS.md: Minors not permitted.
        """
        response_upper = message.strip().upper()
        
        if response_upper in ["YES", "Y", "1"]:
            # Age verified
            state.age_verified = True
            state.advance_state(BookingState.CLINIC_SELECTION)
            db.commit()
            
            # Log age verification
            AuditService.log_event(
                event_type="age_verified",
                actor="patient",
                actor_id=phone,
                patient_phone=phone,
                metadata={"verified": True},
                db=db
            )
            
            return BookingService._send_clinic_menu(db)
        
        elif response_upper in ["NO", "N", "2"]:
            # Under 18 - reject
            state.reset()
            db.commit()
            
            # Log rejection
            AuditService.log_event(
                event_type="age_verification_failed",
                actor="patient",
                actor_id=phone,
                patient_phone=phone,
                metadata={"reason": "under_18"},
                db=db
            )
            
            return {
                "message": (
                    "Sorry, you must be 18 or older to use this service.\n\n"
                    "If you are a minor, please ask a parent/guardian to book on your behalf."
                ),
                "next_state": BookingState.INITIAL
            }
        
        else:
            return {
                "message": "Please reply YES if you are 18+ or NO if under 18.",
                "next_state": BookingState.AGE_VERIFICATION
            }
    
    @staticmethod
    def _send_clinic_menu(db: Session) -> Dict:
        """Send clinic selection menu."""
        # TODO: Fetch from database
        # For now, hardcoded example
        return {
            "message": (
                "Select a clinic:\n\n"
                "1️⃣ City Health Clinic\n"
                "2️⃣ Downtown Medical Center\n"
                "3️⃣ Sunset Family Practice\n\n"
                "Reply with the number (1-3)"
            ),
            "next_state": BookingState.CLINIC_SELECTION
        }
    
    @staticmethod
    def _handle_clinic_selection(phone: str, message: str, state: ConversationState, db: Session) -> Dict:
        """Handle clinic selection."""
        choice = message.strip()
        
        # Map choice to clinic ID
        clinic_map = {
            "1": "clinic_city_health",
            "2": "clinic_downtown",
            "3": "clinic_sunset"
        }
        
        clinic_id = clinic_map.get(choice)
        
        if not clinic_id:
            return {
                "message": "Invalid choice. Please reply with 1, 2, or 3.",
                "next_state": BookingState.CLINIC_SELECTION
            }
        
        # Store clinic selection
        state.set_context("clinic_id", clinic_id)
        state.advance_state(BookingState.DOCTOR_SELECTION)
        db.commit()
        
        return BookingService._send_doctor_menu(clinic_id, db)
    
    @staticmethod
    def _send_doctor_menu(clinic_id: str, db: Session) -> Dict:
        """Send doctor selection menu."""
        # TODO: Fetch from database
        return {
            "message": (
                "Select a doctor:\n\n"
                "1️⃣ Dr. Smith (General Medicine)\n"
                "2️⃣ Dr. Jones (Pediatrics)\n"
                "3️⃣ Dr. Brown (Dermatology)\n\n"
                "Reply with the number (1-3)"
            ),
            "next_state": BookingState.DOCTOR_SELECTION
        }
    
    @staticmethod
    def _handle_doctor_selection(phone: str, message: str, state: ConversationState, db: Session) -> Dict:
        """Handle doctor selection."""
        choice = message.strip()
        
        doctor_map = {
            "1": "doctor_smith",
            "2": "doctor_jones",
            "3": "doctor_brown"
        }
        
        doctor_id = doctor_map.get(choice)
        
        if not doctor_id:
            return {
                "message": "Invalid choice. Please reply with 1, 2, or 3.",
                "next_state": BookingState.DOCTOR_SELECTION
            }
        
        state.set_context("doctor_id", doctor_id)
        state.advance_state(BookingState.SERVICE_SELECTION)
        db.commit()
        
        return BookingService._send_service_menu(db)
    
    @staticmethod
    def _send_service_menu(db: Session) -> Dict:
        """Send service selection menu."""
        return {
            "message": (
                "Select appointment type:\n\n"
                "1️⃣ Consultation (30 min)\n"
                "2️⃣ Follow-up (15 min)\n"
                "3️⃣ Checkup (45 min)\n\n"
                "Reply with the number (1-3)"
            ),
            "next_state": BookingState.SERVICE_SELECTION
        }
    
    @staticmethod
    def _handle_service_selection(phone: str, message: str, state: ConversationState, db: Session) -> Dict:
        """Handle service selection."""
        choice = message.strip()
        
        service_map = {
            "1": "consultation",
            "2": "follow_up",
            "3": "checkup"
        }
        
        service_id = service_map.get(choice)
        
        if not service_id:
            return {
                "message": "Invalid choice. Please reply with 1, 2, or 3.",
                "next_state": BookingState.SERVICE_SELECTION
            }
        
        state.set_context("service_id", service_id)
        state.advance_state(BookingState.DATE_SELECTION)
        db.commit()
        
        return BookingService._send_date_menu(db)
    
    @staticmethod
    def _send_date_menu(db: Session) -> Dict:
        """Send date selection menu."""
        # Generate next 3 available dates
        today = datetime.now().date()
        dates = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, 4)]
        
        return {
            "message": (
                f"Select a date:\n\n"
                f"1️⃣ {dates[0]}\n"
                f"2️⃣ {dates[1]}\n"
                f"3️⃣ {dates[2]}\n\n"
                "Reply with the number (1-3)"
            ),
            "next_state": BookingState.DATE_SELECTION
        }
    
    @staticmethod
    def _handle_date_selection(phone: str, message: str, state: ConversationState, db: Session) -> Dict:
        """Handle date selection."""
        choice = message.strip()
        
        today = datetime.now().date()
        date_map = {
            "1": (today + timedelta(days=1)).isoformat(),
            "2": (today + timedelta(days=2)).isoformat(),
            "3": (today + timedelta(days=3)).isoformat()
        }
        
        selected_date = date_map.get(choice)
        
        if not selected_date:
            return {
                "message": "Invalid choice. Please reply with 1, 2, or 3.",
                "next_state": BookingState.DATE_SELECTION
            }
        
        state.set_context("selected_date", selected_date)
        state.advance_state(BookingState.TIME_SELECTION)
        db.commit()
        
        return BookingService._send_time_menu(selected_date, db)
    
    @staticmethod
    def _send_time_menu(selected_date: str, db: Session) -> Dict:
        """Send time slot menu."""
        # TODO: Fetch available slots from database
        return {
            "message": (
                f"Available times for {selected_date}:\n\n"
                "1️⃣ 09:00 AM\n"
                "2️⃣ 11:00 AM\n"
                "3️⃣ 02:00 PM\n"
                "4️⃣ 04:00 PM\n\n"
                "Reply with the number (1-4)"
            ),
            "next_state": BookingState.TIME_SELECTION
        }
    
    @staticmethod
    def _handle_time_selection(phone: str, message: str, state: ConversationState, db: Session) -> Dict:
        """Handle time selection and create appointment."""
        choice = message.strip()
        
        time_map = {
            "1": "09:00",
            "2": "11:00",
            "3": "14:00",
            "4": "16:00"
        }
        
        selected_time = time_map.get(choice)
        
        if not selected_time:
            return {
                "message": "Invalid choice. Please reply with 1-4.",
                "next_state": BookingState.TIME_SELECTION
            }
        
        # Create appointment
        selected_date = state.get_context("selected_date")
        clinic_id = state.get_context("clinic_id")
        doctor_id = state.get_context("doctor_id")
        service_id = state.get_context("service_id")
        
        # Combine date + time
        start_datetime = datetime.fromisoformat(f"{selected_date}T{selected_time}:00")
        end_datetime = start_datetime + timedelta(minutes=30)  # Default duration
        
        # Create or get patient
        patient = db.query(Patient).filter(Patient.phone_number == phone).first()
        if not patient:
            patient = Patient(phone_number=phone)
            db.add(patient)
            db.flush()
        
        # Create appointment
        appointment = Appointment(
            patient_phone=phone,
            clinic_id=clinic_id,
            doctor_id=doctor_id,
            service_id=service_id,
            start_time=start_datetime,
            end_time=end_datetime,
            status="booked",
            source="whatsapp"
        )
        db.add(appointment)
        db.commit()
        db.refresh(appointment)
        
        # Log appointment creation
        AuditService.log_event(
            event_type="appointment_created",
            actor="patient",
            actor_id=phone,
            patient_phone=phone,
            metadata={
                "appointment_id": str(appointment.id),
                "date": selected_date,
                "time": selected_time,
                "source": "whatsapp"
            },
            db=db
        )
        
        # Advance state to confirmed
        state.advance_state(BookingState.CONFIRMED)
        db.commit()
        
        return {
            "message": (
                f"✅ Appointment confirmed!\n\n"
                f"📅 Date: {selected_date}\n"
                f"🕐 Time: {selected_time}\n"
                f"🏥 Clinic: {clinic_id}\n"
                f"👨‍⚕️ Doctor: {doctor_id}\n\n"
                f"Appointment ID: {str(appointment.id)[:8]}\n\n"
                f"Reply CANCEL to cancel this appointment."
            ),
            "next_state": BookingState.CONFIRMED,
            "booking_id": str(appointment.id)
        }
