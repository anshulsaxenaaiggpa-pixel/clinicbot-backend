"""
Data Deletion API - MODULE 3

Provides endpoint for patient data deletion requests.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.deletion_service import DeletionService


router = APIRouter(prefix="/patient", tags=["patient"])


class DeletionRequest(BaseModel):
    """Request body for data deletion."""
    phone_number: str = Field(..., description="E.164 format phone number")
    verification: str = Field(default="phone_match", description="Verification method")
    requested_by: str = Field(default="patient", description="Who requested deletion")


class DeletionResponse(BaseModel):
    """Response from deletion request."""
    status: str  # completed | failed | already_deleted
    phone_masked: str = None
    records_deleted: Dict = None
    message: str
    timestamp: str


@router.post("/delete", response_model=DeletionResponse)
def request_data_deletion(
    request: DeletionRequest,
    db: Session = Depends(get_db)
):
    """
    Delete patient data per DPDP Right to Erasure.
    
    MODULE 3 Workflow:
    1. Verify identity via phone number match
    2. Delete patient profile
    3. Anonymize appointments (keep for audit)
    4. Delete consent records
    5. Retain anonymized audit logs
    6. Mark as deleted
    7. Return confirmation
    
    Deletion Keywords: DELETE, REMOVE, ERASE, FORGET
    """
    result = DeletionService.anonymize_patient_data(
        phone_number=request.phone_number,
        requested_by=request.requested_by,
        db=db
    )
    
    if result["status"] == "failed":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Deletion failed")
        )
    
    return DeletionResponse(
        status=result["status"],
        phone_masked=result.get("phone_masked"),
        records_deleted=result.get("records_deleted"),
        message=result.get("message", "Data deletion processed"),
        timestamp=result["timestamp"]
    )


@router.get("/deletion-status/{phone_number}")
def get_deletion_status(
    phone_number: str,
    db: Session = Depends(get_db)
):
    """
    Check if phone number has been deleted.
    
    Returns deletion status or None if never requested.
    """
    status_info = DeletionService.get_deletion_status(phone_number, db)
    
    if status_info is None:
        return {"status": "no_deletion_requested"}
    
    return status_info
