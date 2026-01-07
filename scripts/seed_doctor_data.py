"""
Seed Doctor Test Data

Creates test doctor with appointments for dashboard testing.
"""
import sys
import os
from datetime import datetime, timedelta

# Add app directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import SessionLocal
from app.models.doctor import Doctor
from app.models.clinic import Clinic
from app.models.appointment import Appointment
import uuid


def seed_doctor_data():
    """Create Dr. Mehta with test appointments."""
    db = SessionLocal()
    
    try:
        # Check if doctor already exists
        existing_doctor = db.query(Doctor).filter(Doctor.whatsapp_number == "+919876543210").first()
        if existing_doctor:
            print("✅ Test doctor already exists")
            return
        
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
        
        print(f"✅ Created Dr. {doctor.name}")
        
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
        
        print(f"✅ Created {len(times)} test appointments for today")
        
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
        
        print(f"✅ Created 5 past appointments")
        
        db.commit()
        print("\n" + "="*60)
        print("🎉 SEED DATA CREATED SUCCESSFULLY!")
        print("="*60)
        print(f"Doctor Login:")
        print(f"  Phone: +919876543210")
        print(f"  Password: doctor123")
        print(f"  Consultation Fee: ₹500")
        print(f"  Today's Appointments: {len(times)}")
        print(f"  Expected Today's Revenue: ₹{len(times) * 500}")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Error seeding data: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_doctor_data()
