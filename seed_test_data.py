"""Seed script to create test clinic data"""
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# CRITICAL: Import registry bootstrap FIRST to register all models with SQLAlchemy
print("==> Importing app.db.base...")
from app.db.base import Base
print("==> app.db.base imported successfully")

# FORCE mapper configuration NOW (before any object instantiation)
# This ensures all relationships are resolved
print("==> Configuring mappers...")
from sqlalchemy.orm import configure_mappers
configure_mappers()
print("==> Mappers configured successfully")

# Now import the model classes we need (they're already registered via app.db.base)
from app.models.clinic import Clinic
from app.models.clinic_timing import ClinicTiming
from app.models.doctor import Doctor
from app.models.service import Service
from app.models.patient import Patient
from app.models.appointment import Appointment
print("==> All models imported successfully")

def seed_test_clinic(db: Session, whatsapp_number: str = "+14155238886"):
    """
    Create a test clinic with sample doctors, services, patients, and appointments
    
    Args:
        db: Database session
        whatsapp_number: The Twilio sandbox WhatsApp number
    """
    # Create clinic
    clinic_id = uuid.uuid4()
    clinic = Clinic(
        id=clinic_id,
        name="Dr. Sharma's Clinic",
        owner_name="Dr. Rajesh Sharma",
        address="123 MG Road, Indiranagar",
        city="Bangalore",
        timezone="Asia/Kolkata",
        whatsapp_number=whatsapp_number,
        subscription_tier="trial",
        subscription_status="active",
        trial_ends_at=datetime.utcnow() + timedelta(days=7),
        whatsapp_provider="twilio",
        api_key=f"clinic_{uuid.uuid4().hex[:32]}",
        is_active=True
    )
    db.add(clinic)
    db.flush()
    
    # Create doctors
    doctors = [
        Doctor(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            name="Dr. Sharma",
            specialization="Physiotherapist",
            default_fee=1200,
            is_active=True
        ),
        Doctor(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            name="Dr. Mehta",
            specialization="General Physician",
            default_fee=500,
            is_active=True
        )
    ]
    
    for doctor in doctors:
        db.add(doctor)
    
    db.flush()
    
    # Create services
    services = [
        Service(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            name="Consultation",
            type="consultation",
            duration_minutes=30,
            required_slots=1,
            default_fee=500,
            is_active=True
        ),
        Service(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            name="Physiotherapy Session",
            type="therapy",
            duration_minutes=60,
            required_slots=2,
            default_fee=1200,
            is_active=True
        ),
        Service(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            name="Medical Checkup",
            type="checkup",
            duration_minutes=45,
            required_slots=2,
            default_fee=800,
            is_active=True
        )
    ]
    
    for service in services:
        db.add(service)
    
    db.flush()
    
    # Create sample patients
    patients = [
        Patient(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            name="John Doe",
            phone="+919876543210",
            email="john@example.com",
            total_visits=3,
            cancelled_count=0,
            no_show_count=0
        ),
        Patient(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            name="Jane Smith",
            phone="+919876543211",
            total_visits=1,
            cancelled_count=1,
            no_show_count=0
        )
    ]
    
    for patient in patients:
        db.add(patient)
    
    db.flush()
    
    # Create sample appointments (past, present, future)
    now = datetime.utcnow()
    
    appointments = [
        # Past completed appointment
        Appointment(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            patient_id=patients[0].id,
            doctor_id=doctors[0].id,
            service_id=services[0].id,
            date=(now - timedelta(days=7)).date(),
            start_utc_ts=now - timedelta(days=7, hours=5, minutes=30),  # 10:30 AM IST
            end_utc_ts=now - timedelta(days=7, hours=5),  # 11:00 AM IST
            status="completed",
            fee=500
        ),
        # Future confirmed appointment
        Appointment(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            patient_id=patients[0].id,
            doctor_id=doctors[0].id,
            service_id=services[1].id,
            date=(now + timedelta(days=2)).date(),
            start_utc_ts=now + timedelta(days=2, hours=-5, minutes=-30),  # 2:30 PM IST
            end_utc_ts=now + timedelta(days=2, hours=-4, minutes=-30),  # 3:30 PM IST
            status="confirmed",
            fee=1200
        ),
        # Cancelled appointment
        Appointment(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            patient_id=patients[1].id,
            doctor_id=doctors[1].id,
            service_id=services[0].id,
            date=(now + timedelta(days=5)).date(),
            start_utc_ts=now + timedelta(days=5, hours=-6),  # 11:00 AM IST
            end_utc_ts=now + timedelta(days=5, hours=-5, minutes=-30),  # 11:30 AM IST
            status="cancelled",
            fee=500
        )
    ]
    
    for appointment in appointments:
        db.add(appointment)
    
    db.commit()
    
    print(f"\n{'='*60}")
    print(f"✅ Test clinic created successfully!")
    print(f"{'='*60}")
    print(f"   Clinic ID: {clinic_id}")
    print(f"   Clinic Name: {clinic.name}")
    print(f"   WhatsApp Number: {clinic.whatsapp_number}")
    print(f"   API Key: {clinic.api_key}")
    print(f"\n   📊 Data Summary:")
    print(f"   Doctors: {len(doctors)}")
    print(f"   Services: {len(services)}")
    print(f"   Patients: {len(patients)}")
    print(f"   Appointments: {len(appointments)}")
    print(f"\n   💡 Next Steps:")
    print(f"   1. Save the API key above")
    print(f"   2. Use in dashboard: localStorage.setItem('clinic_api_key', '{clinic.api_key}')")
    print(f"   3. Use in dashboard: localStorage.setItem('clinic_id', '{clinic_id}')")
    print(f"   4. Start backend: uvicorn app.main:app --reload")
    print(f"   5. Visit: http://localhost:8000/docs")
    print(f"{'='*60}\n")
    
    return {
        "clinic_id": str(clinic_id),
        "api_key": clinic.api_key,
        "doctors": len(doctors),
        "services": len(services),
        "patients": len(patients),
        "appointments": len(appointments)
    }

if __name__ == "__main__":
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        # Use Twilio sandbox number by default
        result = seed_test_clinic(db, whatsapp_number="+14155238886")
    finally:
        db.close()
