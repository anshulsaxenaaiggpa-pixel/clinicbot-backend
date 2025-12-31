"""
Consent API Endpoints - Module 2 Implementation

Provides endpoints for consent capture and status checking.
"""
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Literal
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.consent_service import ConsentService
from app.models.patient_consent import CONSENT_TEXT_V1


router = APIRouter(prefix="/consent", tags=["consent"])


class ConsentCaptureRequest(BaseModel):
    """Request body for consent capture."""
    phone_number: str = Field(..., description="E.164 format phone number")
    reply_text: str = Field(..., description="User's consent response (YES/NO/STOP)")
    channel: Literal["whatsapp"] = Field(default="whatsapp", description="Channel")
    ip_address: Optional[str] = Field(None, description="Optional IP address")


class ConsentCaptureResponse(BaseModel):
    """Response from consent capture."""
    status: str  # granted | withdrawn | invalid
    message: str
    timestamp: Optional[str] = None
    version: Optional[str] = None


class ConsentStatusResponse(BaseModel):
    """Response from consent status check."""
    status: str  # granted | withdrawn | none
    timestamp: Optional[str] = None
    version: Optional[str] = None


@router.post("/capture", response_model=ConsentCaptureResponse)
def capture_consent(
    request: ConsentCaptureRequest,
    db: Session = Depends(get_db)
):
    """
    Capture patient consent response.
    
    Process:
    - Normalize reply_text
    - If YES → store consent as granted
    - If NO/STOP → store consent as withdrawn
    - Return status
    
    Module 2 Requirement: Store explicit, timestamped consent.
    """
    result = ConsentService.capture_consent(
        phone_number=request.phone_number,
        reply_text=request.reply_text,
        channel=request.channel,
        ip_address=request.ip_address,
        db=db
    )
    
    return ConsentCaptureResponse(**result)


@router.get("/status/{phone_number}", response_model=ConsentStatusResponse)
def get_consent_status(
    phone_number: str,
    db: Session = Depends(get_db)
):
    """
    Get current consent status for a phone number.
    
    Returns:
    - granted: User has consented
    - withdrawn: User has withdrawn consent
    - none: No consent record exists
    
    Module 2 Requirement: Check consent before processing PHI.
    """
    result = ConsentService.get_consent_status(phone_number, db)
    return ConsentStatusResponse(**result)


@router.get("/prompt")
def get_consent_prompt():
    """
    Get the exact consent text to show users.
    
    Returns the MODULE 2 specified consent wording.
    """
    return {
        "consent_text": CONSENT_TEXT_V1,
        "version": "dpdp-whatsapp-consent-v1.0"
    }
