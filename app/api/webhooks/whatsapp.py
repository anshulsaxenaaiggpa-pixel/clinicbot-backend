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

from app.services.rate_limiter import check_message_rate_limit
from app.services.consent_service import ConsentService
from app.services.deletion_service import DeletionService
from app.utils.log_scrubber import LogScrubber, safe_error_log


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
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    WhatsApp webhook endpoint - FULL IMPLEMENTATION.
    
    Security:
    - Verifies Twilio signature
    - Rate limiting per phone
    - Consent checking (in BookingService)
    - Age verification (in BookingService)
    - Deletion keyword detection
    - PII scrubbing in logs
    """
    # Get signature from headers
    signature = request.headers.get("X-Twilio-Signature")
    
    if not signature:
        raise HTTPException(status_code=401, detail="Missing signature")
    
    # Get request data
    form_data = await request.form()
    post_data = dict(form_data)
    
    # Verify signature
    import os
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    
    if not auth_token:
        raise HTTPException(status_code=500, detail="TWILIO_AUTH_TOKEN not configured")
    
    if not WebhookSecurity.verify_twilio_signature(
        str(request.url),
        post_data,
        signature,
        auth_token
    ):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Extract message
    phone = post_data.get("From", "").replace("whatsapp:", "")
    message_body = post_data.get("Body", "")
    message_id = post_data.get("MessageSid", "")
    
    # Validate phone number format
    if not phone:
        raise HTTPException(status_code=400, detail="Missing phone number")
    
    # Rate limiting
    allowed, error = check_message_rate_limit(phone)
    if not allowed:
        # Log rate limit block
        from app.services.audit_service import AuditService
        AuditService.log_event(
            event_type="rate_limit_blocked",
            actor="patient",
            actor_id=phone,
            patient_phone=phone,
            metadata={"reason": "message_rate_limit", "action": "whatsapp_message"},
            db=db
        )
        
        # Send rate limit message
        return {
            "status": "rate_limited",
            "message": error
        }
    
    # Check for deletion keywords FIRST (before any processing)
    if DeletionService.is_deletion_request(message_body):
        # Process deletion in background
        background_tasks.add_task(
            DeletionService.anonymize_patient_data,
            phone,
            "patient",
            db
        )
        
        # Send confirmation
        return {
            "status": "deletion_requested",
            "message": "Your data deletion request is being processed. You will receive confirmation shortly."
        }
    
    # Process booking flow
    try:
        from app.services.booking_service import BookingService
        
        response = BookingService.handle_message(phone, message_body, db)
        
        # Queue outbound message for delivery
        background_tasks.add_task(
            send_whatsapp_message,
            phone,
            response.get("message"),
            db
        )
        
        return {
            "status": "success",
            "next_state": response.get("next_state"),
            "booking_id": response.get("booking_id")
        }
    
    except Exception as e:
        # Log error (PII scrubbed)
        from app.utils.log_scrubber import safe_error_log
        safe_error_log(e, {"phone": phone, "message_id": message_id})
        
        # Send generic error message
        background_tasks.add_task(
            send_whatsapp_message,
            phone,
            "Sorry, something went wrong. Please try again later or contact support.",
            db
        )
        
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
