"""Intent classification using OpenAI (GPT-3.5-turbo, GPT-4, or custom models)"""
import logging
import json
from typing import Dict, Any, List
from openai import OpenAI
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize OpenAI client (v1.0+ syntax)
client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None


class IntentClassifier:
    """
    Classify user intent and extract entities using OpenAI (GPT-3.5-turbo or GPT-4)
    Model is configurable via OPENAI_MODEL environment variable.
    
    Intents:
    - book_appointment
    - check_availability
    - cancel_appointment
    - reschedule_appointment
    - check_fees
    - get_location
    - help
    - greeting
    """
    
    SYSTEM_PROMPT = """You are an intent classifier for a medical clinic appointment booking system.

Classify user messages into one of these intents:
- book_appointment: User wants to book an appointment
- check_availability: User wants to check available slots
- cancel_appointment: User wants to cancel existing appointment
- reschedule_appointment: User wants to reschedule
- check_fees: User asking about consultation fees
- get_location: User asking for clinic location/address
- help: User needs assistance
- greeting: User is greeting (Hi, Hello, etc.)

Also extract entities:
- date: Any mentioned date (format as YYYY-MM-DD)
- time: Any mentioned time (format as HH:MM)
- doctor_name: Name of doctor mentioned
- service_name: Type of service (consultation, physiotherapy, etc.)

Respond ONLY with valid JSON:
{
  "intent": "intent_name",
  "confidence": 0.95,
  "entities": {
    "date": "2025-12-15",
    "time": "14:30",
    "doctor_name": "Dr. Sharma",
    "service_name": "consultation"
  }
}"""
    
    async def classify(self, message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Classify intent using OpenAI (configurable model, default: gpt-3.5-turbo)
        
        Args:
            message: User message text
            context: Conversation context (previous intent, state, etc.)
            
        Returns:
            {
                "intent": str,
                "confidence": float,
                "entities": dict
            }
        """
        # CRITICAL: If user is in the middle of a booking flow, preserve that context
        # and don't re-classify the intent (their response is part of the booking flow)
        if context and "booking_state" in context:
            booking_state = context.get("booking_state")
            # Valid mid-flow states where user is responding to prompts
            if booking_state in ["awaiting_doctor", "awaiting_service", "awaiting_date", "awaiting_slot"]:
                logger.info(f"🔄 User in booking flow (state={booking_state}), preserving 'book_appointment' intent")
                return {
                    "intent": "book_appointment",
                    "confidence": 1.0,
                    "entities": {},
                    "context_preserved": True
                }
        
        # Handle numbered menu selections when user is viewing main menu
        if context and context.get("showing_main_menu"):
            menu_intent = self._parse_menu_number(message)
            if menu_intent:
                logger.info(f"🔢 Menu selection: {message} -> {menu_intent}")
                return {
                    "intent": menu_intent,
                    "confidence": 1.0,
                    "entities": {}
                }
        
        # If OpenAI is not configured, use fallback immediately
        if not client:
            logger.warning("OpenAI not configured, using fallback classification")
            return self._fallback_classification(message, context)
            
        try:
            # Build context-aware prompt
            user_message = message
            if context:
                state = context.get("conversation_state")
                if state:
                    user_message = f"Context: User is in '{state}' state.\nMessage: {message}"
            
            # Call OpenAI using configured model (default: gpt-3.5-turbo)
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            # Parse response
            result = response.choices[0].message.content
            
            # Parse JSON
            intent_data = json.loads(result)
            
            logger.info(f"Classified intent: {intent_data}")
            return intent_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response: {e}")
            return self._fallback_classification(message, context)
        
        except Exception as e:
            logger.error(f"Error in intent classification: {str(e)}")
            return self._fallback_classification(message, context)
    
    def _fallback_classification(self, message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Simple keyword-based fallback if OpenAI API fails
        """
        message_lower = message.lower()
        
        # Keyword matching
        if any(word in message_lower for word in ["book", "appointment", "schedule"]):
            return {"intent": "book_appointment", "confidence": 0.7, "entities": {}}
        
        elif any(word in message_lower for word in ["available", "slots", "free", "when"]):
            return {"intent": "check_availability", "confidence": 0.7, "entities": {}}
        
        elif any(word in message_lower for word in ["cancel", "delete"]):
            return {"intent": "cancel_appointment", "confidence": 0.7, "entities": {}}
        
        elif any(word in message_lower for word in ["reschedule", "change", "move"]):
            return {"intent": "reschedule_appointment", "confidence": 0.7, "entities": {}}
        
        elif any(word in message_lower for word in ["fee", "cost", "price", "charge"]):
            return {"intent": "check_fees", "confidence": 0.7, "entities": {}}
        
        elif any(word in message_lower for word in ["location", "address", "where"]):
            return {"intent": "get_location", "confidence": 0.7, "entities": {}}
        
        elif any(word in message_lower for word in ["hi", "hello", "hey"]):
            return {"intent": "greeting", "confidence": 0.9, "entities": {}}
        
        else:
            return {"intent": "help", "confidence": 0.5, "entities": {}}
    
    def _parse_menu_number(self, message: str) -> Optional[str]:
        """
        Parse numbered menu selections (1-6) to intent names
        
        Menu mapping:
        1 -> book_appointment
        2 -> check_availability
        3 -> check_fees
        4 -> get_location
        5 -> cancel_appointment
        6 -> reschedule_appointment
        
        Returns:
            Intent name if valid number, None otherwise
        """
        menu_map = {
            "1": "book_appointment",
            "2": "check_availability",
            "3": "check_fees",
            "4": "get_location",
            "5": "cancel_appointment",
            "6": "reschedule_appointment"
        }
        
        return menu_map.get(message.strip())

