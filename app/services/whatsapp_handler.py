"""WhatsApp message handler - core bot logic"""
import logging
from typing import Dict, Any, Optional
import redis
import json

from app.config import settings
from app.services.intent_classifier import IntentClassifier
from app.services.conversation_manager import ConversationManager
from app.services.whatsapp_sender import WhatsAppSender
from app.services.patient_helpers import get_or_create_patient
from app.db.database import SessionLocal

logger = logging.getLogger(__name__)

# Redis for session storage
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


class WhatsAppMessageHandler:
    """
    Main WhatsApp bot message handler
    
    Flow:
    1. Get/create patient record
    2. Get/create user session
    3. Classify intent
    4. Route to conversation flow
    5. Update session
    6. Send response
    """
    
    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.conversation_manager = ConversationManager()
        self.whatsapp_sender = WhatsAppSender()
    
    async def handle_message(self, message_data: Dict[str, Any]):
        """Process incoming WhatsApp message"""
        user_phone = message_data.get("from")
        message_text = message_data.get("body", "").strip()
        whatsapp_name = message_data.get("profile_name") or message_data.get("contact_name")
        
        if not user_phone or not message_text:
            logger.warning(f"Invalid message data: {message_data}")
            return
        
        try:
            # Get/create patient in database
            db = SessionLocal()
            try:
                # Get clinic_id from WhatsApp business number
                clinic_id = self._get_clinic_id_for_number(message_data.get("to"))
                
                if not clinic_id:
                    # Clinic not found - send error and exit
                    await self.whatsapp_sender.send_message(
                        to=user_phone,
                        message="Sorry, this WhatsApp number is not registered with any clinic. Please contact support.",
                        provider=message_data.get("provider")
                    )
                    return
                
                patient = get_or_create_patient(
                    db=db,
                    clinic_id=clinic_id,
                    phone=user_phone,
                    whatsapp_name=whatsapp_name
                )
                
                logger.info(f"Patient {patient.id} ({patient.name}) - {user_phone}")
                
            finally:
                db.close()
            
            # Get user session
            session = self._get_session(user_phone)
            session["patient_id"] = str(patient.id)
            session["clinic_id"] = str(clinic_id)
            
            # Classify intent
            intent_result = await self.intent_classifier.classify(
                message_text,
                session.get("context", {})
            )
            
            logger.info(f"Intent: {intent_result['intent']} for user {user_phone}")
            
            # Route to conversation flow
            response = await self.conversation_manager.process(
                intent=intent_result["intent"],
                entities=intent_result.get("entities", {}),
                session=session,
                message_text=message_text
            )
            
            # Update session
            self._update_session(user_phone, response.get("session_update", {}))
            
            # Send response to user
            await self.whatsapp_sender.send_message(
                to=user_phone,
                message=response["message"],
                buttons=response.get("buttons"),
                provider=message_data.get("provider")
            )
            
        except Exception as e:
            logger.error(f"Error handling message from {user_phone}: {str(e)}")
            # Send fallback message
            await self.whatsapp_sender.send_message(
                to=user_phone,
                message="Sorry, I encountered an error. Please try again or type 'help' for assistance.",
                provider=message_data.get("provider")
            )
    
    def _get_session(self, user_phone: str) -> Dict[str, Any]:
        """Get user session from Redis"""
        session_key = f"session:{user_phone}"
        session_data = redis_client.get(session_key)
        
        if session_data:
            return json.loads(session_data)
        
        # Create new session
        return {
            "user_phone": user_phone,
            "clinic_id": None,  # Set after clinic selection
            "context": {},
            "conversation_state": "idle",
            "created_at": None
        }
    
    def _update_session(self, user_phone: str, updates: Dict[str, Any]):
        """Update user session in Redis"""
        session_key = f"session:{user_phone}"
        
        # Get existing session
        current_session = self._get_session(user_phone)
        
        # Merge updates
        current_session.update(updates)
        
        # Save to Redis (30 min TTL)
        redis_client.setex(
            session_key,
            1800,  # 30 minutes
            json.dumps(current_session)
        )
    
    def _get_clinic_id_for_number(self, to_number: str) -> Optional[str]:
        """
        Get clinic_id from WhatsApp business number
        
        Queries the clinics table by whatsapp_number to identify which clinic
        this message belongs to.
        
        Args:
            to_number: Clinic's WhatsApp number (format: +919876543210)
            
        Returns:
            Clinic UUID as string, or None if not found
        """
        from app.models.clinic import Clinic
        
        # Clean phone number (remove 'whatsapp:' prefix if present)
        clean_number = to_number.replace("whatsapp:", "").strip()
        
        # Query database for clinic
        db = SessionLocal()
        try:
            clinic = db.query(Clinic).filter(
                Clinic.whatsapp_number == clean_number,
                Clinic.is_active == True
            ).first()
            
            if clinic:
                logger.info(f"Found clinic: {clinic.name} (ID: {clinic.id}) for number {clean_number}")
                return str(clinic.id)
            else:
                logger.warning(f"No clinic found for WhatsApp number: {clean_number}")
                return None
        finally:
            db.close()
