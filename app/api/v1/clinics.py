"""Clinic CRUD endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from datetime import datetime, timedelta

from app.db.database import get_db
from app.models.clinic import Clinic
from app.schemas.clinic import ClinicCreate, ClinicUpdate, ClinicOut
from app.utils.auth import generate_api_key
from app.utils.errors import InvalidClinicError

router = APIRouter()


@router.post("/", response_model=ClinicOut, status_code=status.HTTP_201_CREATED)
def create_clinic(clinic_data: ClinicCreate, db: Session = Depends(get_db)):
    """
    Create a new clinic with 7-day trial and auto-generated API key
    """
    # Check if WhatsApp number already exists
    existing = db.query(Clinic).filter(Clinic.whatsapp_number == clinic_data.whatsapp_number).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="WhatsApp number already registered"
        )
    
    # Create clinic with trial period and API key
    clinic = Clinic(
        **clinic_data.model_dump(),
        subscription_tier="starter",
        subscription_status="trial",
        trial_ends_at=datetime.utcnow() + timedelta(days=7),
        api_key=generate_api_key()  # Auto-generate API key
    )
    
    db.add(clinic)
    db.commit()
    db.refresh(clinic)
    
    return clinic


@router.get("/{clinic_id}", response_model=ClinicOut)
def get_clinic(clinic_id: UUID, db: Session = Depends(get_db)):
    """Get clinic by ID"""
    clinic = db.query(Clinic).filter(Clinic.id == clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    return clinic


@router.patch("/{clinic_id}", response_model=ClinicOut)
def update_clinic(clinic_id: UUID, clinic_data: ClinicUpdate, db: Session = Depends(get_db)):
    """Update clinic details"""
    clinic = db.query(Clinic).filter(Clinic.id == clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    
    # Update only provided fields
    update_data = clinic_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(clinic, field, value)
    
    clinic.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(clinic)
    
    return clinic


@router.get("/", response_model=List[ClinicOut])
def list_clinics(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all clinics (admin endpoint)"""
    clinics = db.query(Clinic).offset(skip).limit(limit).all()
    return clinics
