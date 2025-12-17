"""WhatsApp webhook endpoint for message handling"""
from fastapi import APIRouter, Request, Response, HTTPException
from typing import Dict, Any
import logging
from datetime import datetime

from app.services.whatsapp_handler import WhatsAppMessageHandler
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize message handler
message_handler = WhatsAppMessageHandler()


@router.get("/whatsapp")
async def whatsapp_webhook_verification(request: Request):
    """
    Webhook verification for WhatsApp (Twilio/Meta)
    
    When registering webhook, provider sends GET request with challenge token
    """
    # Meta Cloud API verification
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    if mode == "subscribe" and token == settings.META_VERIFY_TOKEN:
        logger.info("WhatsApp webhook verified successfully")
        return Response(content=challenge, media_type="text/plain")
    
    # Twilio verification (just responds with 200)
    return {"status": "ok"}


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    """
    Handle incoming WhatsApp messages
    
    Supports both Twilio and Meta Cloud API formats
    """
    try:
        # Parse incoming message
        body = await request.json() if request.headers.get("content-type") == "application/json" else await request.form()
        
        logger.info(f"Received WhatsApp message: {body}")
        
        # Determine provider based on payload structure
        if "From" in body or "from" in body:
            # Twilio format
            message_data = _parse_twilio_message(body)
        elif "entry" in body:
            # Meta Cloud API format
            message_data = _parse_meta_message(body)
        else:
            logger.warning(f"Unknown message format: {body}")
            return {"status": "ignored"}
        
        # Process message through handler
        await message_handler.handle_message(message_data)
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error processing WhatsApp webhook: {str(e)}")
        # Return 200 to prevent provider retries
        return {"status": "error", "message": str(e)}


def _parse_twilio_message(body: Dict[str, Any]) -> Dict[str, Any]:
    """Parse Twilio message format"""
    return {
        "provider": "twilio",
        "from": body.get("From", "").replace("whatsapp:", ""),
        "to": body.get("To", "").replace("whatsapp:", ""),
        "message_id": body.get("MessageSid"),
        "body": body.get("Body", ""),
        "timestamp": datetime.utcnow().isoformat(),
        "media_url": body.get("MediaUrl0"),  # For images/PDFs
        "profile_name": body.get("ProfileName")
    }


def _parse_meta_message(body: Dict[str, Any]) -> Dict[str, Any]:
    """Parse Meta Cloud API message format"""
    try:
        entry = body["entry"][0]
        change = entry["changes"][0]
        value = change["value"]
        message = value["messages"][0]
        
        return {
            "provider": "meta",
            "from": message["from"],
            "to": value["metadata"]["display_phone_number"],
            "message_id": message["id"],
            "body": message.get("text", {}).get("body", ""),
            "timestamp": message["timestamp"],
            "contact_name": value.get("contacts", [{}])[0].get("profile", {}).get("name")
        }
    except (KeyError, IndexError) as e:
        logger.error(f"Error parsing Meta message: {e}")
        return {}
