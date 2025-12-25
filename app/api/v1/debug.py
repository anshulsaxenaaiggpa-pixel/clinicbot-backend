"""Debug endpoints for diagnosing deployment issues"""
from fastapi import APIRouter
import httpx
import os

router = APIRouter()


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
