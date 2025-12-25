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

# Redis for session storage - lazy connection to avoid startup crashes
_redis_client = None

# In-memory session fallback when Redis unavailable
_memory_sessions = {}

def get_redis_client():
    """Get Redis client with lazy initialization and URL validation"""
    global _redis_client
    
    # Only try once - if we've already determined Redis is unavailable, return None
    if _redis_client is None:
        try:
            # Validate Redis URL exists and has proper scheme
            if not settings.REDIS_URL:
                logger.info("[Redis Disabled] No REDIS_URL configured. Falling back to in-memory sessions.")
                _redis_client = False  # Mark as attempted but failed
                return None
            
            if not settings.REDIS_URL.startswith(("redis://", "rediss://", "unix://")):
                logger.warning(f"[Redis Disabled] Invalid Redis URL scheme: {settings.REDIS_URL[:20]}... Falling back to in-memory sessions.")
                _redis_client = False
                return None
            
            # Try to connect
            logger.info(f"[Redis] Attempting to connect to Redis at {settings.REDIS_URL[:20]}...")
            _redis_client = redis.from_url(
                settings.REDIS_URL, 
                decode_responses=True,
                socket_connect_timeout=5,  # 5 second timeout
                socket_timeout=5,
                retry_on_timeout=True
            )
            _redis_client.ping()  # Test connection
            logger.info(f"✅ [Redis Connected] Successfully connected to Redis")
            return _redis_client
            
        except redis.ConnectionError as e:
            logger.warning(f"[Redis Disabled] Connection failed: {str(e)[:100]}. Falling back to in-memory sessions.")
            _redis_client = False
            return None
        except redis.TimeoutError as e:
            logger.warning(f"[Redis Disabled] Connection timeout: {str(e)[:100]}. Falling back to in-memory sessions.")
            _redis_client = False
            return None
        except Exception as e:
            logger.warning(f"[Redis Disabled] Unexpected error: {type(e).__name__}: {str(e)[:100]}. Falling back to in-memory sessions.")
            _redis_client = False  # Mark as attempted but failed
            return None
    
    # Return the cached client (or None if it failed previously)
    return _redis_client if _redis_client is not False else None


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
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"Error handling message from {user_phone}: {type(e).__name__}: {str(e)}")
            logger.error(f"Full traceback:\n{error_trace}")
            
            # Send fallback message
            try:
                await self.whatsapp_sender.send_message(
                    to=user_phone,
                    message="Sorry, I encountered an error. Please try again or type 'help' for assistance.",
                    provider=message_data.get("provider")
                )
            except Exception as send_error:
                logger.error(f"Failed to send error message: {send_error}")
    
    def _get_session(self, user_phone: str) -> Dict[str, Any]:
        """Get user session from Redis or in-memory fallback"""
        redis_client = get_redis_client()
        
        if redis_client:
            try:
                session_key = f"session:{user_phone}"
                session_data = redis_client.get(session_key)
                
                if session_data:
                    logger.info(f"Retrieved session from Redis for {user_phone}")
                    return json.loads(session_data)
            except Exception as e:
                logger.warning(f"Redis get failed: {e}. Using in-memory session.")
        
        # Use in-memory fallback
        global _memory_sessions
        if user_phone in _memory_sessions:
            logger.info(f"Retrieved session from memory for {user_phone}")
            return _memory_sessions[user_phone]
        
        # Create new session
        logger.info(f"Creating new session for {user_phone}")
        new_session = {
            "user_phone": user_phone,
            "clinic_id": None,  # Set after clinic selection
            "context": {},
            "conversation_state": "idle",
            "created_at": None
        }
        _memory_sessions[user_phone] = new_session
        return new_session
    
    def _update_session(self, user_phone: str, updates: Dict[str, Any]):
        """Update user session in Redis or in-memory fallback"""
        redis_client = get_redis_client()
        
        # Get existing session
        current_session = self._get_session(user_phone)
        
        # Merge updates (deep merge for context)
        if "context" in updates:
            if "context" not in current_session:
                current_session["context"] = {}
            current_session["context"].update(updates["context"])
            del updates["context"]
        current_session.update(updates)
        
        logger.info(f"Updating session for {user_phone}: context={current_session.get('context', {})}")
        
        # Save to Redis if available
        if redis_client:
            try:
                session_key = f"session:{user_phone}"
                redis_client.setex(
                    session_key,
                    1800,  # 30 minutes
                    json.dumps(current_session)
                )
                logger.info(f"Session saved to Redis for {user_phone}")
                return
            except Exception as e:
                logger.warning(f"Redis setex failed: {e}. Falling back to memory.")
        
        # Save to in-memory fallback
        global _memory_sessions
        _memory_sessions[user_phone] = current_session
        logger.info(f"Session saved to memory for {user_phone}")
    
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
