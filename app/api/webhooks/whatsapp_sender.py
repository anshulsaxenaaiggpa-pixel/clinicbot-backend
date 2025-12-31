"""
WhatsApp Message Sending - Background Task

Handles outbound message delivery with retry logic.
"""
import os
from twilio.rest import Client
from app.utils.log_scrubber import safe_error_log


def send_whatsapp_message(phone: str, message: str, db, retry_count: int = 0):
    """
    Send WhatsApp message via Twilio.
    
    Implements retry logic:
    - Max 3 retries
    - Exponential backoff
    
    Args:
        phone: E.164 format phone number
        message: Message text (NO PHI - already scrubbed by caller)
        db: Database session
        retry_count: Current retry attempt
    """
    if retry_count >= 3:
        # Max retries exceeded - log for manual review
        safe_error_log(
            Exception("WhatsApp message delivery failed after 3 retries"),
            {"phone": phone, "retry_count": retry_count}
        )
        return
    
    try:
        # Get Twilio credentials
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        from_number = os.getenv("TWILIO_WHATSAPP_NUMBER")  # e.g., whatsapp:+14155238886
        
        if not all([account_sid, auth_token, from_number]):
            raise ValueError("Twilio credentials not configured")
        
        # Initialize Twilio client
        client = Client(account_sid, auth_token)
        
        # Send message
        response = client.messages.create(
            body=message,
            from_=from_number,
            to=f"whatsapp:{phone}"
        )
        
        # Log successful delivery
        from app.services.audit_service import AuditService
        AuditService.log_event(
            event_type="whatsapp_message_sent",
            actor="system",
            actor_id="whatsapp_sender",
            patient_phone=phone,
            metadata={
                "message_sid": response.sid,
                "status": response.status,
                "retry_count": retry_count
            },
            db=db
        )
    
    except Exception as e:
        # Retry with exponential backoff
        import time
        backoff_seconds = 2 ** retry_count  # 1s, 2s, 4s
        time.sleep(backoff_seconds)
        
        # Recursive retry
        send_whatsapp_message(phone, message, db, retry_count + 1)


# Add to whatsapp.py imports
from app.api.webhooks.whatsapp_sender import send_whatsapp_message
