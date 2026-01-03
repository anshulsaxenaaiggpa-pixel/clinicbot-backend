"""WhatsApp message sender - supports Twilio and Meta Cloud API"""
import logging
from typing import Dict, Any, List, Optional
from twilio.rest import Client as TwilioClient
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class WhatsAppSender:
    """
    Send WhatsApp messages via Twilio or Meta Cloud API
    """
    
    def __init__(self):
        # Twilio setup
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            self.twilio_client = TwilioClient(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            self.twilio_number = settings.TWILIO_WHATSAPP_NUMBER
        else:
            self.twilio_client = None
        
        # Meta Cloud API setup
        self.meta_token = settings.META_WHATSAPP_TOKEN
        self.meta_phone_id = settings.META_PHONE_NUMBER_ID
        
        # Gupshup setup (India optimized, ₹0.30/msg, no daily limits)
        self.gupshup_api_key = settings.GUPSHUP_API_KEY
        self.gupshup_app_name = settings.GUPSHUP_APP_NAME
        self.gupshup_source = settings.GUPSHUP_SOURCE_NUMBER
        
        # Default provider from config
        self.default_provider = settings.WHATSAPP_PROVIDER
    
    async def send_message(
        self,
        to: str,
        message: str,
        buttons: Optional[List[str]] = None,
        provider: str = "twilio"
    ) -> bool:
        """
        Send WhatsApp message
        
        Args:
            to: Recipient phone number (with country code)
            message: Message text
            buttons: Optional list of button labels
            provider: 'twilio' or 'meta'
            
        Returns:
            True if successful
        """
        try:
            # Use default provider if not specified or use from message data
            if provider == "twilio":
                provider = self.default_provider
            
            logger.info(f"📤 Attempting to send WhatsApp message via {provider} to {to}")
            
            if provider == "gupshup" and self.gupshup_api_key:
                return await self._send_gupshup(to, message, buttons)
            elif provider == "twilio" and self.twilio_client:
                return await self._send_twilio(to, message, buttons)
            elif provider == "twilio" and not self.twilio_client:
                logger.error("❌ Twilio provider requested but Twilio client not initialized")
                logger.error("   → Check TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN are set")
                return False
            elif provider == "meta":
                return await self._send_meta(to, message, buttons)
            else:
                logger.error(f"❌ Unknown provider: {provider}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Critical error in send_message: {type(e).__name__}: {str(e)[:200]}")
            return False
    
    async def _send_twilio(self, to: str, message: str, buttons: Optional[List[str]]) -> bool:
        """Send via Twilio"""
        import asyncio
        
        try:
            # Sanitize phone number - URL encoding can convert + to space
            to = to.strip()  # Remove leading/trailing spaces
            to = to.replace(" ", "")  # Remove any spaces
            
            # Ensure + prefix
            if not to.startswith("+"):
                to = f"+{to}"
            
            # Twilio doesn't support buttons in basic tier,
            # so append button options to message
            if buttons:
                message += "\n\n" + "\n".join([f"{i+1}. {btn}" for i, btn in enumerate(buttons)])
            
            # Twilio SDK is synchronous - run in thread pool to avoid blocking async loop
            def _send_sync():
                return self.twilio_client.messages.create(
                    from_=self.twilio_number,
                    to=f"whatsapp:{to}",
                    body=message
                )
            
            # Run blocking Twilio call in thread pool
            await asyncio.to_thread(_send_sync)
            
            logger.info(f"Sent Twilio message to {to}")
            return True
            
        except Exception as e:
            # Enhanced error logging for diagnosis
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(f"❌ Twilio send FAILED to {to}")
            logger.error(f"   Error Type: {error_type}")
            logger.error(f"   Error Message: {error_msg[:200]}")
            
            # Check specific error types
            if "401" in error_msg or "authenticate" in error_msg.lower():
                logger.error("   → Likely AUTH issue: Check TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN")
            elif "connection" in error_msg.lower() or "attempts failed" in error_msg.lower():
                logger.error("   → Likely NETWORK issue: Railway may be blocking outbound Twilio API calls")
            elif "21211" in error_msg:
                logger.error("   → Invalid phone number format")
            elif "21608" in error_msg:
                logger.error("   → WhatsApp number not in sandbox - rejoin sandbox first")
                
            return False
    
    async def _send_meta(self, to: str, message: str, buttons: Optional[List[str]]) -> bool:
        """Send via Meta Cloud API"""
        try:
            url = f"https://graph.facebook.com/v18.0/{self.meta_phone_id}/messages"
            
            headers = {
                "Authorization": f"Bearer {self.meta_token}",
                "Content-Type": "application/json"
            }
            
            # Build payload
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": message}
            }
            
            # Add buttons if provided
            if buttons:
                payload["type"] = "interactive"
                payload["interactive"] = {
                    "type": "button",
                    "body": {"text": message},
                    "action": {
                        "buttons": [
                            {"type": "reply", "reply": {"id": f"btn_{i}", "title": btn[:20]}}
                            for i, btn in enumerate(buttons[:3])  # Max 3 buttons
                        ]
                    }
                }
            
            # Send request
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
            
            logger.info(f"Sent Meta message to {to}")
            return True
            
        except Exception as e:
            logger.error(f"Meta send error: {str(e)}")
            return False
    
    async def _send_gupshup(self, to: str, message: str, buttons: Optional[List[str]]) -> bool:
        """Send via Gupshup WhatsApp API (India optimized, ₹0.30/msg)"""
        try:
            url = "https://api.gupshup.io/wa/api/v1/msg"
            
            # Sanitize phone number
            to = to.strip().replace(" ", "")
            if to.startswith("+"):
                to = to[1:]  # Gupshup uses number without +
            
            # Add button options to message text (Gupshup template approach)
            if buttons:
                message += "\n\n" + "\n".join([f"{i+1}. {btn}" for i, btn in enumerate(buttons)])
            
            # Gupshup API payload (simple text message)
            payload = {
                "channel": "whatsapp",
                "source": self.gupshup_source.replace("+", "") if self.gupshup_source else "",
                "destination": to,
                "message": message,
                "src.name": self.gupshup_app_name or "ClinicBot"
            }
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "apikey": self.gupshup_api_key
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, data=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
                
                if result.get("status") == "submitted":
                    logger.info(f"✅ Sent Gupshup message to {to}")
                    return True
                else:
                    logger.error(f"❌ Gupshup API error: {result}")
                    return False
            
        except Exception as e:
            logger.error(f"❌ Gupshup send error: {type(e).__name__}: {str(e)[:200]}")
            return False
