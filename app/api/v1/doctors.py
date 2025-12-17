"""Doctor CRUD endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.database import get_db
from app.models.doctor import Doctor
from app.schemas.doctor import DoctorCreate, DoctorUpdate, DoctorOut

router = APIRouter()


@router.post("/", response_model=DoctorOut, status_code=status.HTTP_201_CREATED)
def create_doctor(doctor_data: DoctorCreate, db: Session = Depends(get_db)):
    """Add a doctor to a clinic"""
    doctor = Doctor(**doctor_data.model_dump())
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor


@router.get("/", response_model=List[DoctorOut])
def list_doctors(clinic_id: UUID, db: Session = Depends(get_db)):
    """List all doctors for a clinic"""
    doctors = db.query(Doctor).filter(
        Doctor.clinic_id == clinic_id,
        Doctor.is_active == True
    ).all()
    return doctors


@router.get("/{doctor_id}", response_model=DoctorOut)
def get_doctor(doctor_id: UUID, db: Session = Depends(get_db)):
    """Get doctor by ID"""
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor


@router.patch("/{doctor_id}", response_model=DoctorOut)
def update_doctor(doctor_id: UUID, doctor_data: DoctorUpdate, db: Session = Depends(get_db)):
    """Update doctor details"""
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    update_data = doctor_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(doctor, field, value)
    
    db.commit()
    db.refresh(doctor)
    return doctor


@router.delete("/{doctor_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_doctor(doctor_id: UUID, db: Session = Depends(get_db)):
    """Soft delete (deactivate) a doctor"""
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    doctor.is_active = False
    db.commit()
    return None
