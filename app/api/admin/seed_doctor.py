"""
API endpoint to seed doctor data on Railway.
"""
from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db, SessionLocal
from app.models.doctor import Doctor
from app.models.clinic import Clinic
from app.models.appointment import Appointment
from datetime import datetime, timedelta
import uuid

router = APIRouter(prefix="/admin", tags=["admin-tools"])


@router.get("/seed-doctor")
async def seed_doctor_endpoint():
    """Create test doctor with appointments - accessible via browser."""
    db = SessionLocal()
    
    try:
        # Check if doctor already exists
        existing_doctor = db.query(Doctor).filter(Doctor.whatsapp_number == "+919876543210").first()
        if existing_doctor:
            return {
                "status": "exists",
                "message": "Test doctor already exists",
                "doctor": {
                    "id": str(existing_doctor.id),
                    "name": existing_doctor.name,
                    "whatsapp": existing_doctor.whatsapp_number
                }
            }
        
        # Get or create clinic
        clinic = db.query(Clinic).first()
        if not clinic:
            clinic = Clinic(
                id=str(uuid.uuid4()),
                name="Test Clinic",
                phone="+919876543210",
                is_active=True
            )
            db.add(clinic)
            db.flush()
        
        # Create Dr. Mehta
        doctor = Doctor(
            id=str(uuid.uuid4()),
            clinic_id=str(clinic.id),
            name="Dr. Rajesh Mehta",
            specialization="General Physician",
            whatsapp_number="+919876543210",
            upi_id="drmehta@paytm",
            status="active",
            consultation_fee=500,
            is_active=True
        )
        doctor.set_password("doctor123")  # Set password
        db.add(doctor)
        db.flush()
        
        # Create test appointments for today
        today = datetime.now().date()
        times = [
            (9, 0),   # 9:00 AM
            (11, 30), # 11:30 AM
            (14, 0)   # 2:00 PM
        ]
        
        for i, (hour, minute) in enumerate(times):
            appt_time = datetime.combine(today, datetime.min.time()).replace(hour=hour, minute=minute)
            
            appointment = Appointment(
                id=str(uuid.uuid4()),
                clinic_id=str(clinic.id),
                doctor_id=str(doctor.id),
                service_id=str(uuid.uuid4()),  # Mock service
                patient_phone=f"+9198765432{i}0",
                patient_name=f"Patient {i+1}",
                date=appt_time,
                start_utc_ts=appt_time,
                end_utc_ts=appt_time + timedelta(minutes=30),
                status='booked'
            )
            db.add(appointment)
        
        # Create some past appointments
        for i in range(5):
            past_date = today - timedelta(days=i+1)
            appt_time = datetime.combine(past_date, datetime.min.time()).replace(hour=10, minute=0)
            
            appointment = Appointment(
                id=str(uuid.uuid4()),
                clinic_id=str(clinic.id),
                doctor_id=str(doctor.id),
                service_id=str(uuid.uuid4()),
                patient_phone=f"+9198765430{i}",
                patient_name=f"Past Patient {i+1}",
                date=appt_time,
                start_utc_ts=appt_time,
                end_utc_ts=appt_time + timedelta(minutes=30),
                status='completed'
            )
            db.add(appointment)
        
        db.commit()
        
        return {
            "status": "success",
            "message": "Test doctor created successfully",
            "doctor": {
                "id": str(doctor.id),
                "name": doctor.name,
                "whatsapp": doctor.whatsapp_number,
                "password": "doctor123",
                "login_url": "/doctor/login"
            },
            "appointments": {
                "today": len(times),
                "past": 5
            }
        }
        
    except Exception as e:
        db.rollback()
        import traceback
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )
    finally:
        db.close()
