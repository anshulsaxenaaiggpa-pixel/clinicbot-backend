from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime
import random
from typing import List, Optional

from app.db.database import get_db
from app.models.doctor import Doctor
from app.models.clinic import Clinic
from app.services.audit_logger import audit_logger
from app.services.whatsapp_sender import WhatsAppSender

router = APIRouter(prefix="/api/v1/registration", tags=["registration"])
whatsapp_sender = WhatsAppSender()

# Simple In-Memory Cache for OTP (MVP only)
class SimpleCache:
    def __init__(self):
        self._data = {}
    def set(self, key, value, ttl=300):
        self._data[key] = (value, datetime.utcnow().timestamp() + ttl)
    def get(self, key):
        if key in self._data:
            val, expiry = self._data[key]
            if datetime.utcnow().timestamp() < expiry:
                return val
            del self._data[key]
        return None

cache = SimpleCache()

def generate_otp():
    return str(random.randint(100000, 999999))

class DoctorRegisterRequest(BaseModel):
    clinic_name: str
    doctor_name: str
    phone: str # WhatsApp number
    email: EmailStr

@router.post("/register-doctor")
async def register_doctor(request: DoctorRegisterRequest, db: Session = Depends(get_db)):
    # Check if phone exists
    existing = db.query(Doctor).filter(Doctor.phone == request.phone).first()
    if existing:
        return {"error": "Phone already registered"}

    # Send OTP to WhatsApp
    otp = generate_otp()
    cache.set(f"otp_{request.phone}", otp, 300) # 5 mins
    
    await whatsapp_sender.send_message(
        to=request.phone,
        message=f"CuraSlot OTP: {otp}"
    )

    # Create pending doctor
    doctor = Doctor(
        clinic_name=request.clinic_name,
        name=request.doctor_name,
        phone=request.phone,
        email=request.email,
        status="pending_otp"
    )
    db.add(doctor)
    db.commit()
    db.refresh(doctor)

    await audit_logger.log_action(
        clinic_id=None, # Global registration
        actor_type="PATIENT", 
        actor_ref=request.phone,
        action="DOCTOR_REGISTRATION_REQUEST",
        entity_type="DOCTOR",
        entity_id=str(doctor.id)
    )

    return {"status": "otp_sent", "message": "Enter OTP to complete"}

@router.post("/verify-doctor-otp")
async def verify_otp(phone: str, otp: str, db: Session = Depends(get_db)):
    stored_otp = cache.get(f"otp_{phone}")
    if stored_otp != otp:
        return {"error": "Invalid OTP"}

    doctor = db.query(Doctor).filter(Doctor.phone == phone).first()
    if not doctor:
        return {"error": "Doctor not found"}
        
    doctor.status = "pending_approval"
    db.commit()

    await audit_logger.log_action(
        clinic_id=None,
        actor_type="PATIENT",
        actor_ref=phone,
        action="DOCTOR_OTP_VERIFIED",
        entity_type="DOCTOR",
        entity_id=str(doctor.id)
    )
    return {"status": "pending_admin_approval", "doctor_id": str(doctor.id)}

@router.get("/admin/pending-doctors")
async def get_pending_doctors(db: Session = Depends(get_db)):
    doctors = db.query(Doctor).filter(
        Doctor.status.in_(["pending_otp", "pending_approval"])
    ).all()
    
    return [{
        "id": str(d.id),
        "clinic_name": d.clinic_name,
        "doctor_name": d.name,
        "phone": d.phone,
        "status": d.status,
        "created_at": d.created_at.isoformat() if d.created_at else None
    } for d in doctors]

@router.post("/admin/approve-doctor/{doctor_id}")
async def approve_doctor(doctor_id: str, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor or doctor.status != "pending_approval":
        return {"error": "Invalid doctor or status"}

    # 1. Create a Clinic entry for this doctor
    # Generate unique clinic WhatsApp number (random for demo as per prompt)
    clinic_whatsapp = f"+91-8000{random.randint(100000, 999999)}"
    
    new_clinic = Clinic(
        name=doctor.clinic_name,
        owner_name=doctor.full_name,
        whatsapp_number=clinic_whatsapp,
        is_active=True
    )
    db.add(new_clinic)
    db.commit()
    db.refresh(new_clinic)

    # 2. Update Doctor entry
    doctor.clinic_id = new_clinic.id
    doctor.clinic_whatsapp = clinic_whatsapp
    doctor.status = "approved"
    doctor.approved_at = datetime.utcnow()
    db.commit()

    # Notify doctor
    await whatsapp_sender.send_message(
        to=doctor.phone, 
        message=(
            f"✅ APPROVED! CuraSlot LIVE\n\n"
            f"Clinic: {doctor.clinic_name}\n"
            f"WhatsApp Number: {doctor.clinic_whatsapp}\n\n"
            f"Login: curaslot.com/login\n"
            f"Your phone → OTP → Dashboard LIVE"
        )
    )

    await audit_logger.log_action(
        clinic_id=str(new_clinic.id),
        actor_type="ADMIN",
        actor_ref="central-admin",
        action="DOCTOR_APPROVED",
        entity_type="DOCTOR",
        entity_id=doctor_id
    )

    return {"status": "approved", "clinic_whatsapp": doctor.clinic_whatsapp}

@router.post("/login-doctor")
async def login_doctor(phone: str, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(
        Doctor.phone == phone,
        Doctor.status == "approved"
    ).first()

    if not doctor:
        return {"error": "Doctor not approved or not found"}

    otp = generate_otp()
    cache.set(f"login_otp_{phone}", otp, 300)
    
    await whatsapp_sender.send_message(
        to=phone,
        message=f"CuraSlot Login OTP: {otp}"
    )

    return {"status": "otp_sent"}

@router.post("/verify-login-otp")
async def verify_login_otp(phone: str, otp: str, db: Session = Depends(get_db)):
    stored_otp = cache.get(f"login_otp_{phone}")
    if stored_otp != otp:
        return {"error": "Invalid OTP"}

    doctor = db.query(Doctor).filter(
        Doctor.phone == phone, 
        Doctor.status == "approved"
    ).first()
    
    if not doctor:
        return {"error": "Doctor not found"}

    # Generate JWT
    from app.utils.auth import create_access_token
    token = create_access_token(data={"sub": str(doctor.id), "role": "doctor"})
    
    return {
        "access_token": token, 
        "token_type": "bearer",
        "doctor": doctor.full_name,
        "clinic_id": str(doctor.clinic_id),
        "clinic_name": doctor.clinic_name
    }
