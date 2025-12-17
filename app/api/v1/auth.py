"""Auth endpoints for API key management"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.database import get_db
from app.models.clinic import Clinic
from app.utils.auth import generate_api_key
from app.utils.errors import InvalidClinicError
from pydantic import BaseModel

router = APIRouter()


class APIKeyResponse(BaseModel):
    """Response with new API key"""
    clinic_id: UUID
    api_key: str
    message: str


@router.post("/regenerate-key/{clinic_id}", response_model=APIKeyResponse)
def regenerate_api_key(clinic_id: UUID, db: Session = Depends(get_db)):
    """
    Regenerate API key for clinic (admin/owner only)
    
    WARNING: This invalidates the old key immediately
    """
    clinic = db.query(Clinic).filter(Clinic.id == clinic_id).first()
    if not clinic:
        raise InvalidClinicError()
    
    # Generate new key
    new_key = generate_api_key()
    clinic.api_key = new_key
    
    db.commit()
    db.refresh(clinic)
    
    return APIKeyResponse(
        clinic_id=clinic.id,
        api_key=new_key,
        message="API key regenerated successfully. Update your WhatsApp bot configuration."
    )


@router.get("/key/{clinic_id}", response_model=APIKeyResponse)
def get_api_key(clinic_id: UUID, db: Session = Depends(get_db)):
    """
    Get current API key for clinic (admin only)
    
    This endpoint should be protected in production
    """
    clinic = db.query(Clinic).filter(Clinic.id == clinic_id).first()
    if not clinic:
        raise InvalidClinicError()
    
    return APIKeyResponse(
        clinic_id=clinic.id,
        api_key=clinic.api_key,
        message="Current API key"
    )
