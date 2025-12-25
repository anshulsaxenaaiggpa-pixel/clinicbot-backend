"""Debug endpoints for diagnosing deployment issues"""
from fastapi import APIRouter, Query
import httpx
import os
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/test-twilio-connectivity")
async def test_twilio_connectivity():
    """Test if Railway can reach Twilio API"""
    result = {
        "test": "Twilio API Connectivity",
        "env_vars_present": {
            "TWILIO_ACCOUNT_SID": bool(os.getenv("TWILIO_ACCOUNT_SID")),
            "TWILIO_AUTH_TOKEN": bool(os.getenv("TWILIO_AUTH_TOKEN")),
            "TWILIO_WHATSAPP_NUMBER": bool(os.getenv("TWILIO_WHATSAPP_NUMBER")),
        },
        "env_values_masked": {
            "TWILIO_ACCOUNT_SID": os.getenv("TWILIO_ACCOUNT_SID", "")[:6] + "..." if os.getenv("TWILIO_ACCOUNT_SID") else None,
            "TWILIO_WHATSAPP_NUMBER": os.getenv("TWILIO_WHATSAPP_NUMBER", ""),
        }
    }
    
    # Test 1: Basic HTTP connectivity
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("https://api.twilio.com")
            result["http_test"] = {
                "success": True,
                "status_code": response.status_code,
                "reachable": True,
                "message": "✅ Railway CAN reach api.twilio.com"
            }
    except httpx.ConnectError as e:
        result["http_test"] = {
            "success": False,
            "error_type": "ConnectError",
            "error_message": str(e)[:200],
            "reachable": False,
            "message": "❌ Railway CANNOT reach api.twilio.com - NETWORK ISSUE"
        }
    except httpx.TimeoutException as e:
        result["http_test"] = {
            "success": False,
            "error_type": "TimeoutException",
            "error_message": str(e)[:200],
            "reachable": False,
            "message": "❌ Connection timeout - DNS or network issue"
        }
    except Exception as e:
        result["http_test"] = {
            "success": False,
            "error_type": type(e).__name__,
            "error_message": str(e)[:200],
            "reachable": False,
            "message": f"❌ Unexpected error: {type(e).__name__}"
        }
    
    # Test 2: Twilio Auth (if reachable)
    if result["http_test"].get("reachable"):
        try:
            account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            auth_token = os.getenv("TWILIO_AUTH_TOKEN")
            
            if account_sid and auth_token:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(
                        f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}.json",
                        auth=(account_sid, auth_token)
                    )
                    result["auth_test"] = {
                        "success": response.status_code == 200,
                        "status_code": response.status_code,
                        "message": "✅ Credentials work!" if response.status_code == 200 else f"❌ Auth failed: HTTP {response.status_code}"
                    }
            else:
                result["auth_test"] = {
                    "success": False,
                    "message": "⚠️ Credentials not set in environment"
                }
        except Exception as e:
            result["auth_test"] = {
                "success": False,
                "error_type": type(e).__name__,
                "error_message": str(e)[:200]
            }
    
    return result


@router.post("/send-test-whatsapp")
async def send_test_whatsapp(to_number: str = Query(..., description="WhatsApp number to send to, e.g., +919205648624")):
    """
    Send a test WhatsApp message using the SAME code path as the bot.
    This isolates whether the issue is in message sending vs webhook logic.
    """
    from app.services.whatsapp_sender import WhatsAppSender
    
    result = {
        "test": "WhatsApp Message Send",
        "to_number": to_number[:8] + "..." if len(to_number) > 8 else to_number,
        "from_number": os.getenv("TWILIO_WHATSAPP_NUMBER", "NOT SET"),
    }
    
    # Validate environment
    if not os.getenv("TWILIO_ACCOUNT_SID"):
        result["error"] = "TWILIO_ACCOUNT_SID not set"
        result["success"] = False
        return result
    
    if not os.getenv("TWILIO_AUTH_TOKEN"):
        result["error"] = "TWILIO_AUTH_TOKEN not set"
        result["success"] = False
        return result
    
    if not os.getenv("TWILIO_WHATSAPP_NUMBER"):
        result["error"] = "TWILIO_WHATSAPP_NUMBER not set"
        result["success"] = False
        return result
    
    try:
        # Use the SAME WhatsAppSender class the bot uses
        sender = WhatsAppSender()
        
        logger.info(f"🧪 TEST: Sending WhatsApp message to {to_number}")
        
        # Send test message
        success = await sender.send_message(
            to=to_number,
            message="🧪 ClinicBot Test Message\n\nIf you receive this, WhatsApp integration is working!",
            provider="twilio"
        )
        
        result["success"] = success
        result["message"] = "✅ Message sent successfully!" if success else "❌ Message send failed - check Railway logs for details"
        
        # Add helpful debugging info
        result["debugging_notes"] = {
            "to_format": f"Sending to: whatsapp:{to_number}",
            "from_format": f"Sending from: {os.getenv('TWILIO_WHATSAPP_NUMBER')}",
            "sandbox_reminder": "Both sender and recipient must have joined the Twilio sandbox",
            "join_command": "Send 'join <your-code>' to +1 415 523 8886"
        }
        
    except Exception as e:
        result["success"] = False
        result["error_type"] = type(e).__name__
        result["error_message"] = str(e)[:300]
        result["message"] = f"❌ Exception: {type(e).__name__}"
        logger.error(f"🧪 TEST FAILED: {type(e).__name__}: {str(e)}")
    
    return result
