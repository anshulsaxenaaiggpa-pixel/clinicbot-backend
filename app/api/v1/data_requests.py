from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.db.database import get_db
from app.services.audit_logger import audit_logger

router = APIRouter(prefix="/api/v1/compliance", tags=["compliance"])

@router.post("/ccpa-request")
async def handle_ccpa_request(phone: str, command: str, db: Session = Depends(get_db)):
    """Handle CCPA data requests (DATA, DELETE, EXPORT)"""
    await audit_logger.log_action(
        clinic_id="usa_ccpa", # Virtual clinic ID for global compliance logs
        actor_type="PATIENT",
        actor_ref=phone,
        action=f"CCPA_{command.upper()}",
        entity_type="DATA_REQUEST",
        new_state={"command": command, "timestamp": datetime.utcnow().isoformat()}
    )
    
    if command == "delete":
        return {"message": "✅ Deletion request logged. Processed within 30 days (CCPA)."}
    elif command == "data":
        return {"message": "✅ Data access request logged. Sent to email within 30 days."}
    elif command == "export":
        return {"message": "✅ Data export request logged. Sent to email within 30 days."}
    
    return {"error": "Invalid command"}
