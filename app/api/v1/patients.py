"""Patient CRUD endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from uuid import UUID
from datetime import datetime, timedelta

from app.db.database import get_db
from app.models.patient import Patient
from app.models.appointment import Appointment
from app.schemas.patient import PatientCreate, PatientUpdate, PatientOut, PatientStats
from app.utils.errors import InvalidClinicError

router = APIRouter()


@router.post("/", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(patient_data: PatientCreate, db: Session = Depends(get_db)):
    """Create a new patient"""
    # Check if patient already exists
    existing = db.query(Patient).filter(
        Patient.clinic_id == patient_data.clinic_id,
        Patient.phone == patient_data.phone
    ).first()
    
    if existing:
        return existing  # Return existing patient instead of error
    
    # Create new patient
    patient = Patient(**patient_data.model_dump())
    db.add(patient)
    db.commit()
    db.refresh(patient)
    
    return patient


@router.get("/", response_model=List[PatientOut])
def list_patients(
    clinic_id: UUID = Query(...),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all patients for a clinic"""
    patients = db.query(Patient).filter(
        Patient.clinic_id == clinic_id,
        Patient.is_active == True
    ).offset(skip).limit(limit).all()
    
    return patients


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: UUID, db: Session = Depends(get_db)):
    """Get patient by ID"""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.get("/by-phone/{phone}", response_model=PatientOut)
def get_patient_by_phone(
    phone: str,
    clinic_id: UUID = Query(...),
    db: Session = Depends(get_db)
):
    """Get patient by phone number (for WhatsApp bot)"""
    patient = db.query(Patient).filter(
        Patient.clinic_id == clinic_id,
        Patient.phone == phone
    ).first()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    return patient


@router.patch("/{patient_id}", response_model=PatientOut)
def update_patient(
    patient_id: UUID,
    patient_data: PatientUpdate,
    db: Session = Depends(get_db)
):
    """Update patient details"""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    update_data = patient_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patient, field, value)
    
    patient.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(patient)
    
    return patient


@router.get("/{patient_id}/appointments", response_model=List)
def get_patient_appointments(
    patient_id: UUID,
    db: Session = Depends(get_db)
):
    """Get all appointments for a patient"""
    appointments = db.query(Appointment).filter(
        Appointment.patient_id == patient_id
    ).order_by(Appointment.date.desc()).all()
    
    return appointments


@router.get("/stats/clinic/{clinic_id}", response_model=PatientStats)
def get_clinic_patient_stats(
    clinic_id: UUID,
    db: Session = Depends(get_db)
):
    """Get patient statistics for a clinic"""
    # Total patients
    total_patients = db.query(func.count(Patient.id)).filter(
        Patient.clinic_id == clinic_id
    ).scalar()
    
    # New patients this month
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
    new_patients = db.query(func.count(Patient.id)).filter(
        Patient.clinic_id == clinic_id,
        Patient.created_at >= month_start
    ).scalar()
    
    # Active patients (at least 1 visit)
    active_patients = db.query(func.count(Patient.id)).filter(
        Patient.clinic_id == clinic_id,
        Patient.total_visits > 0
    ).scalar()
    
    # Total appointments
    total_appointments = db.query(func.count(Appointment.id)).filter(
        Appointment.clinic_id == clinic_id
    ).scalar()
    
    return PatientStats(
        total_patients=total_patients,
        new_patients_this_month=new_patients,
        active_patients=active_patients,
        total_appointments=total_appointments
    )
