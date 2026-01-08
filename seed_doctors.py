"""Create test doctors with login credentials"""
import uuid
from datetime import datetime
from app.db.database import SessionLocal
from app.models.doctor import Doctor
from app.models.clinic import Clinic

def create_test_doctors():
    db = SessionLocal()
    try:
        # Get first clinic
        clinic = db.query(Clinic).first()
        if not clinic:
            print("❌ No clinic found! Please create a clinic first.")
            return
        
        # Test doctors with credentials
        test_doctors = [
            {
                "name": "Dr. Mehta",
                "specialization": "General Physician",
                "whatsapp_number": "+919876543210",
                "password": "doctor123",
                "consultation_fee": 500,
                "upi_id": "drmehta@paytm",
                "status": "active"
            },
            {
                "name": "Dr. Kumar",
                "specialization": "Cardiologist",
                "whatsapp_number": "+919876543211",
                "password": "doctor123",
                "consultation_fee": 800,
                "upi_id": "drkumar@phonepe",
                "status": "active"
            },
            {
                "name": "Dr. Sharma",
                "specialization": "Dermatologist",
                "whatsapp_number": "+919876543212",
                "password": "doctor123",
                "consultation_fee": 600,
                "upi_id": "drsharma@gpay",
                "status": "active"
            }
        ]
        
        print("\n" + "="*60)
        print("Creating test doctors...")
        print("="*60)
        
        for doc_data in test_doctors:
            # Check if already exists
            existing = db.query(Doctor).filter_by(whatsapp_number=doc_data["whatsapp_number"]).first()
            if existing:
                print(f"⚠️  {doc_data['name']} already exists")
                continue
            
            doctor = Doctor(
                id=str(uuid.uuid4()),
                clinic_id=str(clinic.id),
                name=doc_data["name"],
                specialization=doc_data["specialization"],
                whatsapp_number=doc_data["whatsapp_number"],
                consultation_fee=doc_data["consultation_fee"],
                upi_id=doc_data["upi_id"],
                status=doc_data["status"],
                is_active=True,
                is_searchable=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Set password
            doctor.set_password(doc_data["password"])
            
            db.add(doctor)
            print(f"✅ Created {doc_data['name']}")
        
        db.commit()
        
        print("\n" + "="*60)
        print("✅ Test doctors created successfully!")
        print("="*60)
        print("\nLogin credentials (all have same password):")
        print("-" * 60)
        for doc in test_doctors:
            print(f"\n📱 {doc['name']}")
            print(f"   WhatsApp: {doc['whatsapp_number']}")
            print(f"   Password: {doc['password']}")
            print(f"   Fee: ₹{doc['consultation_fee']}")
        
        print("\n" + "="*60)
        print("\n🔗 Test at: https://clinicbot-whatsapp-production.up.railway.app/doctor/login")
        print("\n" + "="*60 + "\n")
        
    finally:
        db.close()

if __name__ == "__main__":
    create_test_doctors()
