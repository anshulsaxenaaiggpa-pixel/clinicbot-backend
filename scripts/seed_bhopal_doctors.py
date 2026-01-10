"""
Seed 5 Bhopal doctors for testing directory and Stripe flow
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import SessionLocal
from app.models.doctor import Doctor
from app.models.clinic import Clinic
import uuid
from datetime import datetime


def seed_bhopal_doctors():
    """Create 5 test doctors in Bhopal with different specialties"""
    db = SessionLocal()
    
    try:
        # Check if clinic exists, create if not
        clinic = db.query(Clinic).first()
        if not clinic:
            clinic = Clinic(
                id=str(uuid.uuid4()),
                name="Test Clinic Bhopal",
                phone="+919999999999",
                whatsapp_number="+919999999999",
                address="Test Address, Bhopal",
                is_active=True
            )
            db.add(clinic)
            db.commit()
            print(f"✅ Created clinic: {clinic.name}")
        
        # 5 Bhopal doctors with varied specialties and pricing
        doctors_data = [
            {
                "name": "Dr. Raj Mehta",
                "whatsapp_number": "+919876543210",
                "specialty_primary": "Cardiology",
                "specialization": "Cardiology",
                "clinic_name": "Heart & Vascular Clinic",
                "area_locality": "MP Nagar, Bhopal",
                "consultation_fee": 500,
                "google_rating": 4.8,
                "city": "Bhopal",
                "plan_tier": "growth",
                "whatsapp_limit": 200,
                "registration_no": "MCI12345"
            },
            {
                "name": "Dr. Priya Singh",
                "whatsapp_number": "+919812345678",
                "specialty_primary": "Dentistry",
                "specialization": "Dentistry",
                "clinic_name": "Smile Dental Care",
                "area_locality": "Arera Colony, Bhopal",
                "consultation_fee": 300,
                "google_rating": 4.9,
                "city": "Bhopal",
                "plan_tier": "starter",
                "whatsapp_limit": 0,
                "registration_no": "DCI67890"
            },
            {
                "name": "Dr. Amit Sharma",
                "whatsapp_number": "+919834567890",
                "specialty_primary": "Dermatology",
                "specialization": "Dermatology",
                "clinic_name": "Skin & Hair Clinic",
                "area_locality": "TT Nagar, Bhopal",
                "consultation_fee": 400,
                "google_rating": 4.7,
                "city": "Bhopal",
                "plan_tier": "growth",
                "whatsapp_limit": 200,
                "registration_no": "MCI54321"
            },
            {
                "name": "Dr. Neha Gupta",
                "whatsapp_number": "+919856789012",
                "specialty_primary": "Pediatrics",
                "specialization": "Pediatrics",
                "clinic_name": "Little Angels Kids Clinic",
                "area_locality": "Shahpura, Bhopal",
                "consultation_fee": 350,
                "google_rating": 4.9,
                "city": "Bhopal",
                "plan_tier": "starter",
                "whatsapp_limit": 0,
                "registration_no": "MCI98765"
            },
            {
                "name": "Dr. Vikram Patel",
                "whatsapp_number": "+919878901234",
                "specialty_primary": "Orthopedics",
                "specialization": "Orthopedics",
                "clinic_name": "Advanced Bone & Joint Hospital",
                "area_locality": "Kolar Road, Bhopal",
                "consultation_fee": 600,
                "google_rating": 4.8,
                "city": "Bhopal",
                "plan_tier": "enterprise",
                "whatsapp_limit": 999,
                "registration_no": "MCI11111"
            }
        ]
        
        created_count = 0
        for doctor_data in doctors_data:
            # Check if doctor already exists
            existing = db.query(Doctor).filter(
                Doctor.whatsapp_number == doctor_data["whatsapp_number"]
            ).first()
            
            if existing:
                print(f"⚠️ Doctor {doctor_data['name']} already exists, skipping")
                continue
            
            # Create doctor
            doctor = Doctor(
                id=str(uuid.uuid4()),
                clinic_id=clinic.id,
                **doctor_data,
                is_active=True,
                is_searchable=True,
                whatsapp_used=0,
                created_at=datetime.utcnow()
            )
            
            # Set a test password (same for all: "test123")
            doctor.set_password("test123")
            
            db.add(doctor)
            created_count += 1
            print(f"✅ Created: {doctor.name} - {doctor.specialty_primary} - ₹{doctor.consultation_fee}")
        
        db.commit()
        print(f"\n🎉 Successfully seeded {created_count} Bhopal doctors!")
        print("\n📋 Test Credentials:")
        print("   WhatsApp: +919876543210 (or any from above)")
        print("   Password: test123")
        print("\n🔗 Test URLs:")
        print("   Directory: https://clinicbot-whatsapp-production.up.railway.app/city/bhopal")
        print("   Login: https://clinicbot-whatsapp-production.up.railway.app/doctor/login")
        
    except Exception as e:
        print(f"❌ Error seeding doctors: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("🌱 Seeding Bhopal doctors for testing...\n")
    seed_bhopal_doctors()
