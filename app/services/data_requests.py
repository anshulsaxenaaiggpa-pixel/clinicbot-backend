"""
Data Requests Service - CCPA/GDPR/DPDP

Handles data subject rights requests:
- Right to access (DATA)
- Right to erasure (DELETE)
- Right to portability (EXPORT)
"""
import logging
from typing import Dict, Optional
from app.services.audit_logger import audit_logger

logger = logging.getLogger(__name__)

CCPA_COMMANDS = {
    "data": "access",
    "delete": "deletion",
    "export": "portability"
}

async def handle_ccpa_request(phone: str, command: str) -> str:
    """
    Handle data request commands (DATA, DELETE, EXPORT).
    Logs the request and notifies administrators.
    """
    cmd_lower = command.lower().strip()
    action = CCPA_COMMANDS.get(cmd_lower)
    
    if not action:
        return "Sorry, I don't recognize that command. Type 'help' for options."

    # Log the request to audit trail
    await audit_logger.log_action(
        clinic_id="GLOBAL", # CCPA requests are global to the phone
        actor_type="PATIENT",
        actor_ref=phone,
        action=f"CCPA_{action.upper()}",
        entity_type="PATIENT",
        new_state={"command": cmd_lower}
    )
    
    # In a real system, this would trigger an email or background job
    # For MVP, we log it clearly in the server logs
    logger.info(f"🚨 CCPA REQUEST RECEIVED: {action.upper()} from {phone}")
    
    return f"✅ CCPA {action} request received for {phone}"
