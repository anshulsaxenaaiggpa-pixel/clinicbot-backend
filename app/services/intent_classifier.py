"""Intent classification using GPT-4/Gemini"""
import logging
from typing import Dict, Any, List
import openai
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize OpenAI
openai.api_key = settings.OPENAI_API_KEY


class IntentClassifier:
    """
    Classify user intent and extract entities using GPT-4
    
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
        Classify intent using GPT-4
        
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
        try:
            # Build context-aware prompt
            user_message = message
            if context:
                state = context.get("conversation_state")
                if state:
                    user_message = f"Context: User is in '{state}' state.\nMessage: {message}"
            
            # Call GPT-4
            response = openai.ChatCompletion.create(
                model="gpt-4",
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
            import json
            intent_data = json.loads(result)
            
            logger.info(f"Classified intent: {intent_data}")
            return intent_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GPT-4 response: {e}")
            return self._fallback_classification(message)
        
        except Exception as e:
            logger.error(f"Error in intent classification: {str(e)}")
            return self._fallback_classification(message)
    
    def _fallback_classification(self, message: str) -> Dict[str, Any]:
        """
        Simple keyword-based fallback if GPT-4 fails
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
