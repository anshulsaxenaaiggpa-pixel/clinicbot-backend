"""Conversation flow manager - handles multi-turn dialogues"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
import httpx

from app.config import settings
from app.services.audit_logger import audit_logger
from app.services.consent_handler import BOOKING_FOR_MENU

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Manages conversation flows for different intents
    
    Each intent has a specific flow:
    - book_appointment: Multi-turn (doctor → service → date → time → confirm)
    - check_availability: Single-turn or follow-up booking
    - cancel/reschedule: Fetch appointments → select → confirm
    - Others: Single-turn responses
    """
    
    def __init__(self):
        import os
        
        # Production-safe API base URL configuration
        # Priority: API_BASE_URL > PORT > localhost:8000 fallback
        api_base_url = os.getenv("API_BASE_URL")
        
        if api_base_url:
            # Use explicit override (Railway production URL)
            self.api_base = api_base_url
        else:
            # Use PORT env var (Railway injects this)
            port = os.getenv("PORT", "8000")
            self.api_base = f"http://localhost:{port}/api/v1"
        
        logger.info(f"ConversationManager initialized with API base: {self.api_base}")
    
    async def process(
        self,
        intent: str,
        entities: Dict[str, Any],
        session: Dict[str, Any],
        message_text: str
    ) -> Dict[str, Any]:
        """
        Process intent and return response + session updates
        
        Returns:
            {
                "message": str,
                "buttons": List[str] (optional),
                "session_update": dict
            }
        """
        # Route to intent handler
        if "CuraSlot" in message_text or message_text.strip().lower() == "hi":
            # Auto-start booking flow from QR scan or clean greeting
            session["conversation_state"] = "idle" # Reset
            return self._handle_greeting(session)

        if intent == "greeting":
            return self._handle_greeting(session)
        
        elif intent == "book_appointment":
            return await self._handle_booking(entities, session, message_text)
        
        elif intent == "check_availability":
            return await self._handle_availability(entities, session)
        
        elif intent == "view_upcoming":
            return await self._handle_view_upcoming(session)

        elif intent == "cancel_appointment":
            return await self._handle_cancellation(session, message_text)
        
        elif intent == "reschedule_appointment":
            return await self._handle_reschedule(session, message_text)
        
        elif intent == "check_fees":
            return await self._handle_fees(session)
        
        elif intent == "get_location":
            return await self._handle_location(session)
        
        elif intent == "help":
            return self._handle_help()
        
        else:
            return self._handle_unknown()
    
    def _handle_greeting(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Handle greeting"""
        return {
            "message": """👋 Welcome to ClinicBot!

Reply NUMBER ONLY:
1. Book new appointment
2. View upcoming
3. Cancel appointment
0. Help/Repeat""",
            "session_update": {
                "context": {"last_intent": "greeting", "showing_main_menu": True}
            }
        }
    
    async def _handle_booking(self, entities: Dict[str, Any], session: Dict[str, Any], message_text: str) -> Dict[str, Any]:
        """
        Handle appointment booking (multi-turn flow)
        
        Steps:
        1. Get clinic info
        2. Ask for doctor (if not provided)
        3. Ask for service (if not provided)
        4. Ask for date (if not provided)
        5. Show available slots
        6. Confirm booking
        """
        try:
            # Ensure context dict exists
            if "context" not in session:
                session["context"] = {}
            
            conversation_state = session.get("context", {}).get("booking_state", "start")
            clinic_id = session.get("clinic_id")
            
            logger.info(f"📋 BOOKING HANDLER: state={conversation_state}, clinic_id={clinic_id}, user_phone={session.get('user_phone')}")
            
            if not clinic_id:
                logger.warning("No clinic_id in session - using default test clinic")
                # Use default test clinic (from seed data)
                clinic_id = "aa4171cd-55b1-4da5-828e-00edcd67bbfd"
                session["clinic_id"] = clinic_id
            
            # State machine for booking flow
            if conversation_state == "start":
                # For USA users, ask if booking for self or child (COPPA)
                if session.get("user_phone", "").startswith("+1"):
                    return {
                        "message": BOOKING_FOR_MENU,
                        "session_update": {
                            "context": {
                                "booking_state": "awaiting_booking_for"
                            }
                        }
                    }
                else:
                    # Proceed directly to doctor selection for non-USA
                    conversation_state = "awaiting_booking_for"
                    message_text = "1" # Default to 'Myself' for non-USA to skip the step
            
            if conversation_state == "awaiting_booking_for":
                # Handle booking for self vs child
                if "1" in message_text or "myself" in message_text.lower():
                    session["context"]["booking_for"] = "self"
                elif "2" in message_text or "child" in message_text.lower():
                    session["context"]["booking_for"] = "child"
                    session["context"]["coppa_note"] = "Parent/Guardian booking verified"
                
                # Now proceed to doctor selection
                conversation_state = "get_doctors"
            
            if conversation_state == "get_doctors":
                # Get doctors list
                logger.info(f"Fetching doctors for clinic {clinic_id}")
                doctors = await self._fetch_doctors(clinic_id)
                
                if not doctors:
                    return {
                        "message": "No doctors available at the moment. Please try again later.",
                        "session_update": {}
                    }
                
                logger.info(f"Found {len(doctors)} doctors")
                
                doctor_list = "\n".join([f"{i+1}. Dr. {doc['name']} ({doc['specialization']})" 
                                        for i, doc in enumerate(doctors)])
                
                return {
                   "message": f"""Which doctor would you like to see?

{doctor_list}

Reply with the number or doctor name.""",
                    "session_update": {
                        "context": {
                            "booking_state": "awaiting_doctor",
                            "doctors": doctors
                        }
                    }
                }
            
            elif conversation_state == "awaiting_doctor":
                # Doctor selected, ask for service
                doctors = session["context"].get("doctors", [])
                
                # Check if user is trying to greet/get help instead of selecting
                message_lower = message_text.lower().strip()
                if message_lower in ["hi", "hello", "hey", "help", "?"]:
                    doctor_list = "\n".join([f"{i+1}. Dr. {doc['name']} ({doc['specialization']})" 
                                            for i, doc in enumerate(doctors)])
                    return {
                        "message": f"""I'm here to help you book an appointment! 

Which doctor would you like to see?

{doctor_list}

Please reply with the number (1, 2, etc.).""",
                        "session_update": {}  # Keep current state
                    }
                
                selected_doctor = self._parse_user_selection(message_text, doctors)
                
                if not selected_doctor:
                    return {
                        "message": "Invalid selection. Please reply with the number or doctor name from the list above.",
                        "session_update": {}
                    }
                
                doctor_id = selected_doctor["id"]
                
                services = await self._fetch_services(clinic_id)
                service_list = "\n".join([f"{i+1}. {svc['name']} (₹{svc['default_fee']})" 
                                         for i, svc in enumerate(services)])
                
                return {
                    "message": f"""Select service:

{service_list}

Reply with the number.""",
                    "session_update": {
                        "context": {
                            "booking_state": "awaiting_service",
                            "selected_doctor_id": doctor_id,
                            "selected_doctor_name": selected_doctor["name"],
                            "services": services
                        }
                    }
                }
            
            elif conversation_state == "awaiting_service":
                # Service selected, ask for date
                services = session["context"].get("services", [])
                selected_service = self._parse_user_selection(message_text, services)
                
                if not selected_service:
                    return {
                        "message": "Invalid selection. Please reply with the number or service name from the list above.",
                        "session_update": {}
                    }
                
                return {
                    "message": """When would you like to book?

Reply with:
• Today
• Tomorrow
• Date (e.g., Dec 15 or 15-12-2025)""",
                    "session_update": {
                        "context": {
                            "booking_state": "awaiting_date",
                            "selected_service_id": selected_service["id"],
                            "selected_service_name": selected_service["name"],
                            "selected_service_fee": selected_service["default_fee"]
                        }
                    }
                }
            
            elif conversation_state == "awaiting_date":
                # Date selected, show available slots
                # CRITICAL FIX: Parse from message_text, not from entities (which is empty in booking flow)
                target_date = self._parse_date(message_text)
                doctor_id = session["context"]["selected_doctor_id"]
                
                logger.info(f"📅 User said: '{message_text}' → Parsed as: {target_date}")
                
                # Fetch available slots for this date
                slots = await self._fetch_slots(clinic_id, doctor_id, target_date)
                
                if not slots:
                    # Format date nicely for user feedback
                    formatted_date = target_date.strftime("%d %b %Y")
                    return {
                        "message": f"""No slots available on {formatted_date}.

Please try another date:
• Today
• Tomorrow  
• Specific date (e.g., 30 Dec or 30-12-2025)""",
                        "session_update": {
                            "context": {
                                "booking_state": "awaiting_date",  # Stay in same state
                                "last_tried_date": str(target_date)
                            }
                        }
                    }
                
                # Format slot times as user-friendly (9:00 AM instead of ISO format)
                from datetime import datetime as dt
                slot_list = "\n".join([
                    f"{i+1}. {dt.fromisoformat(slot['start_local']).strftime('%I:%M %p')}" 
                    for i, slot in enumerate(slots[:10])
                ])
                
                formatted_date = target_date.strftime("%d %b %Y")
                
                return {
                    "message": f"""Available slots on {formatted_date}:

{slot_list}

Reply with the number to book.""",
                    "session_update": {
                        "context": {
                            "booking_state": "awaiting_slot",
                            "available_slots": slots,
                            "target_date": str(target_date)
                        }
                    }
                }
            
            elif conversation_state == "awaiting_slot":
                # Slot selected, confirm booking
                available_slots = session["context"].get("available_slots", [])
                
                # For slots, use index-based selection (expecting numeric input)
                selected_slot = None
                try:
                    slot_index = int(message_text.strip()) - 1
                    if 0 <= slot_index < len(available_slots):
                        selected_slot = available_slots[slot_index]
                except ValueError:
                    pass
                
                if not selected_slot:
                    return {
                        "message": "Invalid selection. Please reply with the slot number from the list above.",
                        "session_update": {}
                    }
                
                # NEW: Ask for name before creating booking
                return {
                    "message": """👤 What's your name? (Optional)

Reply: Your name
Or type 'skip' to continue""",
                    "session_update": {
                        "context": {
                            "booking_state": "awaiting_name",
                            "selected_slot": selected_slot
                        }
                    }
                }
            
            elif conversation_state == "awaiting_name":
                # Handle name input
                message_clean = message_text.strip().lower()
                patient_name = None
                
                if message_clean not in ["skip", "0", "no"]:
                    if 2 <= len(message_text) <= 100:
                        patient_name = message_text.strip()
                    else:
                        return {
                            "message": "❌ Name should be 2-100 characters. Try again or type 'skip'.",
                            "session_update": {}
                        }
                
                # Book appointment via API
                selected_slot = session["context"].get("selected_slot")
                booking_result = await self._create_booking(
                    clinic_id=clinic_id,
                    doctor_id=session["context"]["selected_doctor_id"],
                    service_id=session["context"]["selected_service_id"],
                    patient_id=session.get("patient_id"),
                    patient_phone=session["user_phone"],
                    patient_name=patient_name,
                    slot=selected_slot,
                    target_date=session["context"].get("target_date")
                )
                
                # Build confirmation display name
                patient_display = patient_name or "Guest"
                
                if booking_result.get("success"):
                    # LOG TO AUDIT (REFINED)
                    await audit_logger.log_action(
                        clinic_id=clinic_id,
                        actor_type="PATIENT",
                        actor_ref=session.get("user_phone", ""),
                        action="BOOK_APPOINTMENT",
                        entity_type="APPOINTMENT",
                        entity_id=booking_result.get("appointment_id"),
                        new_state={
                            "doctor": session["context"].get("selected_doctor_name"),
                            "time": str(session["context"].get("target_date")), # Or use slot time
                            "patient_name": patient_name
                        }
                    )
                    
                    return {
                        "message": f"""✅ Appointment Confirmed!
                        
👤 Patient: {patient_display}
📅 Date: {booking_result['date']}
🕐 Time: {booking_result['time']}
👨‍⚕️ Doctor: {session['context'].get('selected_doctor_name', 'Doctor')}
💰 Fee: ₹{session['context'].get('selected_service_fee', 0)}

You'll receive reminders 24h and 2h before.

Reply NUMBER ONLY:
1. Book another
2. View upcoming
3. Cancel
0. Main menu""",
                        "session_update": {
                            "context": {
                                "booking_state": "completed",
                                "last_appointment_id": booking_result.get("appointment_id", ""),
                                "showing_main_menu": True
                            }
                        }
                    }
                else:
                    return {
                        "message": f"""❌ Booking failed: {booking_result.get('error')}

Would you like to try again?

1️⃣ Book appointment
2️⃣ Check availability
3️⃣ Check fees
4️⃣ Get location

Reply with the number (1-4).""",
                        "session_update": {"context": {"booking_state": "start", "showing_main_menu": True}}
                    }
            
            # If we reach here, unknown state
            return self._handle_unknown()
            
        except Exception as e:
            import traceback
            logger.error(f"❌ BOOKING HANDLER ERROR: {type(e).__name__}: {str(e)}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            return {
                "message": "Sorry, the booking system is temporarily unavailable. Please type 'help' to see other options.",
                "session_update": {"context": {"booking_state": "start"}}
            }
    
    async def _handle_view_upcoming(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Show patient their upcoming appointments"""
        phone = session.get("user_phone", "")
        appts = await self._fetch_upcoming_appointments(phone)
        
        if not appts:
            return {
                "message": """You have no upcoming appointments.

Reply NUMBER ONLY:
1. Book new appointment
0. Main menu""",
                "session_update": {"context": {"showing_main_menu": True}}
            }
        
        appt_list = "\n".join([f"{i+1}. {a['date']} {a['time']} - Dr. {a['doctor']} ({a['service']})" 
                              for i, a in enumerate(appts[:5])])
        
        return {
            "message": f"""🗓️ Your upcoming appointments:
            
{appt_list}

Type 'cancel' to remove one, or '0' for main menu.""",
            "session_update": {
                "context": {
                    "upcoming_appointments": appts,
                    "showing_main_menu": True
                }
            }
        }

    async def _handle_availability(self, entities: Dict[str, Any], session: Dict[str, Any]) -> Dict[str, Any]:
        """Handle availability check"""
        return {
            "message": "To check availability, please tell me:\n1. Which doctor?\n2. What date?",
            "session_update": {}
        }
    
    async def _handle_cancellation(self, session: Dict[str, Any], message_text: str = "") -> Dict[str, Any]:
        """Multi-turn cancellation flow"""
        phone = session.get("user_phone", "")
        # Use existing context if available
        cancel_state = session.get("context", {}).get("cancel_state", "start")
        
        if cancel_state == "start":
            appts = await self._fetch_upcoming_appointments(phone)
            if not appts:
                return {
                    "message": "You have no upcoming appointments to cancel.",
                    "session_update": {"context": {"showing_main_menu": True}}
                }
            
            appt_list = "\n".join([f"{i+1}. {a['date']} at {a['time']} (Dr. {a['doctor']})" 
                                  for i, a in enumerate(appts[:5])])
            
            return {
                "message": f"""Which appointment would you like to cancel?
                
{appt_list}

Reply with the number (e.g., 1). Or '0' to go back.""",
                "session_update": {
                    "context": {
                        "cancel_state": "awaiting_selection",
                        "cancel_options": appts
                    }
                }
            }
            
        elif cancel_state == "awaiting_selection":
            options = session.get("context", {}).get("cancel_options", [])
            selection = self._parse_user_selection(message_text, options)
            
            if not selection:
                return {
                    "message": "Invalid selection. Please reply with the number from the list.",
                    "session_update": {}
                }
            
            return {
                "message": f"""Are you sure you want to cancel your appointment with Dr. {selection['doctor']} on {selection['date']} at {selection['time']}?

1. ✅ Yes, cancel it
2. ❌ No, keep it
0. Back""",
                "session_update": {
                    "context": {
                        "cancel_state": "awaiting_confirmation",
                        "to_cancel": selection
                    }
                }
            }
            
        elif cancel_state == "awaiting_confirmation":
            if "1" in message_text or "yes" in message_text.lower():
                appt = session.get("context", {}).get("to_cancel")
                
                # Perform cancellation via API
                async with httpx.AsyncClient() as client:
                    try:
                        response = await client.patch(f"{self.api_base}/appointments/{appt['id']}/cancel")
                        if response.status_code == 200:
                            # LOG TO AUDIT
                            await audit_logger.log_action(
                                clinic_id=session.get("clinic_id", ""),
                                actor_type="PATIENT",
                                actor_ref=phone,
                                action="CANCEL_APPOINTMENT",
                                entity_type="APPOINTMENT",
                                entity_id=appt["id"],
                                new_state={"status": "cancelled"}
                            )
                            
                            return {
                                "message": "✅ Appointment cancelled successfully.",
                                "session_update": {"context": {"showing_main_menu": True}}
                            }
                        else:
                            return {"message": "❌ Failed to cancel. Please try again later.", "session_update": {}}
                    except Exception as e:
                        logger.error(f"Cancellation error: {e}")
                        return {"message": "❌ Error connecting to server.", "session_update": {}}
            else:
                return {
                    "message": "Okay, the appointment was not cancelled.",
                    "session_update": {"context": {"showing_main_menu": True}}
                }
        
        return self._handle_unknown()
    
    async def _handle_reschedule(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Handle rescheduling"""
        return {
            "message": "To reschedule, I'll need:\n1. Your current appointment details\n2. New preferred date/time",
            "session_update": {}
        }
    
    async def _handle_fees(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Handle fee inquiry"""
        clinic_id = session.get("clinic_id")
        if clinic_id:
            services = await self._fetch_services(clinic_id)
            fee_list = "\n".join([f"• {svc['name']}: ₹{svc['default_fee']}" for svc in services])
            return {
                "message": f"💰 Consultation Fees:\n\n{fee_list}",
                "session_update": {}
            }
        return {
            "message": "Please provide your clinic details to check fees.",
            "session_update": {}
        }
    
    async def _handle_location(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Handle location inquiry"""
        clinic_id = session.get("clinic_id")
        if clinic_id:
            clinic = await self._fetch_clinic(clinic_id)
            return {
                "message": f"""📍 Clinic Location:

{clinic['name']}
{clinic['address']}
{clinic['city']}

WhatsApp: {clinic['whatsapp_number']}""",
                "session_update": {}
            }
        return {"message": "Please provide clinic details.", "session_update": {}}
    
    def _handle_help(self) -> Dict[str, Any]:
        """Handle help request"""
        return {
            "message": """ℹ️ How can I help you?

Reply NUMBER ONLY:
1. Book new appointment
2. View upcoming
3. Cancel appointment
0. Help/Repeat""",
            "session_update": {"context": {"showing_main_menu": True}}
        }
    
    def _handle_unknown(self) -> Dict[str, Any]:
        """Handle unknown intent"""
        return {
            "message": """I didn't quite understand that.

Reply NUMBER ONLY:
1. Book new appointment
2. View upcoming
3. Cancel appointment
0. Help/Repeat""",
            "session_update": {"context": {"showing_main_menu": True}}
        }
    
    # User input parsing helpers
    def _parse_user_selection(self, message_text: str, options: List[Dict], key: str = "name") -> Optional[Dict]:
        """
        Parse user's selection from list of options
        
        Supports:
        - Numeric selection: "1", "2", "3"
        - Name-based selection: "Dr. Sharma", "Consultation"
        
        Args:
            message_text: User's input
            options: List of option dictionaries
            key: Key to use for name matching (default: "name")
            
        Returns:
            Selected option dict or None
        """
        text = message_text.strip().lower()
        
        # Try numeric selection first (1-indexed)
        try:
            index = int(text) - 1
            if 0 <= index < len(options):
                logger.info(f"User selected option {index + 1}: {options[index].get(key)}")
                return options[index]
        except ValueError:
            pass
        
        # Try name-based matching
        for option in options:
            option_name = str(option.get(key, "")).lower()
            # Exact match
            if text == option_name:
                logger.info(f"User selected by name: {option.get(key)}")
                return option
            # Partial match (case-insensitive substring)
            if text in option_name or option_name in text:
                logger.info(f"User selected by partial match: {option.get(key)}")
                return option
        
        logger.warning(f"Could not parse selection: '{message_text}' from {len(options)} options")
        return None
    
    # Helper methods for database queries

    async def _fetch_doctors(self, clinic_id: str) -> List[Dict]:
        """Fetch doctors from database"""
        # Direct database query instead of HTTP API call (more reliable)
        from app.db.database import SessionLocal
        from app.models.doctor import Doctor
        
        db = SessionLocal()
        try:
            doctors = db.query(Doctor).filter(
                Doctor.clinic_id == clinic_id,
                Doctor.is_active == True
            ).all()
            return [{"id": str(d.id), "name": d.name, "specialization": d.specialization or "General"} for d in doctors]
        finally:
            db.close()
    
    async def _fetch_services(self, clinic_id: str) -> List[Dict]:
        """Fetch services from database"""
        from app.db.database import SessionLocal
        from app.models.service import Service
        
        db = SessionLocal()
        try:
            services = db.query(Service).filter(
                Service.clinic_id == clinic_id,
                Service.is_active == True
            ).all()
            return [{"id": str(s.id), "name": s.name, "default_fee": s.default_fee or 0} for s in services]
        finally:
            db.close()
    
    async def _fetch_slots(self, clinic_id: str, doctor_id: str, date: date) -> List[Dict]:
        """Fetch available slots - simple hardcoded for now"""
        # Return demo slots for MVP
        return [
            {"start_utc_ts": f"{date}T09:00:00", "start_local": f"{date}T09:00:00"},
            {"start_utc_ts": f"{date}T09:30:00", "start_local": f"{date}T09:30:00"},
            {"start_utc_ts": f"{date}T10:00:00", "start_local": f"{date}T10:00:00"},
            {"start_utc_ts": f"{date}T10:30:00", "start_local": f"{date}T10:30:00"},
            {"start_utc_ts": f"{date}T11:00:00", "start_local": f"{date}T11:00:00"},
        ]
    
    async def _fetch_clinic(self, clinic_id: str) -> Dict:
        """Fetch clinic details from database"""
        from app.db.database import SessionLocal
        from app.models.clinic import Clinic
        
        db = SessionLocal()
        try:
            clinic = db.query(Clinic).filter(Clinic.id == clinic_id).first()
            if clinic:
                return {"name": clinic.name, "address": clinic.address or "Address not set", 
                        "city": clinic.city or "", "whatsapp_number": clinic.whatsapp_number or ""}
            return {"name": "Clinic", "address": "", "city": "", "whatsapp_number": ""}
        finally:
            db.close()
    
    async def _fetch_upcoming_appointments(self, phone: str) -> List[Dict]:
        """Fetch future appointments for a user phone number"""
        from app.db.database import SessionLocal
        from app.models.appointment import Appointment
        from app.models.doctor import Doctor
        from app.models.service import Service
        from sqlalchemy import and_
        
        db = SessionLocal()
        try:
            today = date.today()
            appts = db.query(Appointment).join(Doctor).join(Service).filter(
                Appointment.patient_phone == phone,
                Appointment.status == "confirmed",
                Appointment.date >= today
            ).order_by(Appointment.date.asc(), Appointment.start_utc_ts.asc()).all()
            
            return [{
                "id": str(a.id),
                "date": a.date.strftime("%d %b %Y"),
                "time": a.start_utc_ts.strftime("%I:%M %p"),
                "doctor": a.doctor.name,
                "service": a.service.name,
                "fee": a.service.default_fee
            } for a in appts]
        finally:
            db.close()

    async def _create_booking(self, **kwargs) -> Dict:
        """Create appointment via API"""
        async with httpx.AsyncClient() as client:
            payload = {
                "clinic_id": str(kwargs["clinic_id"]),
                "doctor_id": str(kwargs["doctor_id"]),
                "service_id": str(kwargs["service_id"]),
                "patient_id": kwargs.get("patient_id"),  # Now included
                "patient_name": kwargs.get("patient_name", "Patient"),
                "patient_phone": kwargs["patient_phone"],
                "date": kwargs.get("target_date"),
                "start_utc_ts": kwargs["slot"]["start_utc_ts"]
            }
            
            try:
                response = await client.post(
                    f"{self.api_base}/appointments/",
                    json=payload
                )
                if response.status_code == 201:
                    return {
                        "success": True,
                        "appointment_id": "apt_123",
                        "date": kwargs.get("target_date"),
                        "time": "10:30 AM",
                        "doctor_name": "Dr. Sharma",
                        "fee": 500
                    }
                else:
                    return {"success": False, "error": response.text}
            except Exception as e:
                return {"success": False, "error": str(e)}
    
    def _parse_date(self, date_str: Optional[str]) -> date:
        """
        Parse date string to date object with DETERMINISTIC DD-MM-YYYY format
        
        Supported formats (EXPLICIT - NO GUESSING):
        - "today", "tomorrow"
        - "DD-MM-YYYY" (31-12-2025)
        - "DD-MM-YY" (31-12-25 → 2025)
        - "DD.MM.YYYY" (31.12.2025)
        - "DD.MM.YY" (31.12.25)
        - "DD Month" (31 Dec, 15 December)
        - "Month DD" (Dec 31, December 15)
        
        Note: ALWAYS uses DAY-MONTH-YEAR order (Indian/European format)
        """
        import re
        import dateparser
        
        if not date_str:
            return date.today()
        
        text = date_str.strip().lower()
        
        # 1. Handle exact shortcuts
        if text == "today":
            logger.info(f"📅 '{date_str}' → today ({date.today()})")
            return date.today()
        
        if text == "tomorrow":
            result = date.today() + timedelta(days=1)
            logger.info(f"📅 '{date_str}' → tomorrow ({result})")
            return result
        
        # 2. Handle explicit DD-MM-YYYY patterns (prevent US-format ambiguity)
        
        # DD-MM-YYYY (31-12-2025)
        match = re.match(r'^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$', date_str.strip())
        if match:
            day, month, year = match.groups()
            try:
                result = date(int(year), int(month), int(day))
                logger.info(f"📅 '{date_str}' → DD-MM-YYYY format ({result})")
                return result
            except ValueError as e:
                logger.warning(f"Invalid date components: {day}/{month}/{year} - {e}")
        
        # DD-MM-YY (31-12-25 → 2025, using pivot: 00-69 = 2000s, 70-99 = 1900s)
        match = re.match(r'^(\d{1,2})[/-](\d{1,2})[/-](\d{2})$', date_str.strip())
        if match:
            day, month, yy = match.groups()
            year = int(yy)
            # Pivot: 00-69 → 2000-2069, 70-99 → 1970-1999
            full_year = 2000 + year if year <= 69 else 1900 + year
            try:
                result = date(full_year, int(month), int(day))
                logger.info(f"📅 '{date_str}' → DD-MM-YY format ({result})")
                return result
            except ValueError as e:
                logger.warning(f"Invalid date components: {day}/{month}/{full_year} - {e}")
        
        # DD.MM.YYYY (31.12.2025)
        match = re.match(r'^(\d{1,2})\.(\d{1,2})\.(\d{4})$', date_str.strip())
        if match:
            day, month, year = match.groups()
            try:
                result = date(int(year), int(month), int(day))
                logger.info(f"📅 '{date_str}' → DD.MM.YYYY format ({result})")
                return result
            except ValueError as e:
                logger.warning(f"Invalid date components: {day}.{month}.{year} - {e}")
        
        # DD.MM.YY (31.12.25)
        match = re.match(r'^(\d{1,2})\.(\d{1,2})\.(\d{2})$', date_str.strip())
        if match:
            day, month, yy = match.groups()
            year = int(yy)
            full_year = 2000 + year if year <= 69 else 1900 + year
            try:
                result = date(full_year, int(month), int(day))
                logger.info(f"📅 '{date_str}' → DD.MM.YY format ({result})")
                return result
            except ValueError as e:
                logger.warning(f"Invalid date components: {day}.{month}.{full_year} - {e}")
        
        # 3. Use dateparser for natural language ONLY (with DAY_FIRST enforced)
        try:
            parsed = dateparser.parse(
                date_str,
                settings={
                    'PREFER_DATES_FROM': 'future',
                    'PREFER_DAY_OF_MONTH': 'first',
                    'DATE_ORDER': 'DMY',  # ← CRITICAL: Force DAY-MONTH-YEAR
                    'TIMEZONE': 'Asia/Kolkata',
                    'RETURN_AS_TIMEZONE_AWARE': False
                }
            )
            if parsed:
                result = parsed.date()
                logger.info(f"📅 '{date_str}' → Natural language ({result})")
                return result
        except Exception as e:
            logger.warning(f"Dateparser failed for '{date_str}': {e}")
        
        # 4. Fallback to today
        logger.warning(f"⚠️ Could not parse '{date_str}', defaulting to today")
        return date.today()


