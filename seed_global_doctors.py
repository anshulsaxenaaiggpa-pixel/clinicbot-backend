"""
Seed global doctors across multiple cities for V3 marketplace
Creates 20 doctors: 10 Bhopal, 5 Dubai, 5 New York
"""
import sys
import os
from datetime import datetime, timedelta
import uuid

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.db.database import SessionLocal
from app.models.doctor import Doctor
from app.models.clinic import Clinic
from sqlalchemy import text


def create_clinic(db, name, city, country_code="IN"):
    """Create a clinic"""
    clinic = Clinic(
        id=str(uuid.uuid4()),
        name=name,
        address=f"{name}, {city}",
        phone="+911234567890",
        subscription_tier="growth",  # Upgrade to growth
        subscription_status="active",
        created_at=datetime.utcnow()
    )
    db.add(clinic)
    db.commit()
    return clinic


def create_doctor(db, clinic_id, name, specialization, city, country_code, currency_code, 
                 consultation_fee, whatsapp_number, slug, rating=4.5, review_count=0):
    """Create a doctor with V3 fields"""
    doctor = Doctor(
        id=str(uuid.uuid4()),
        clinic_id=clinic_id,
        name=name,
        specialization=specialization,
        whatsapp_number=whatsapp_number,
        city=city,
        country_code=country_code,
        currency_code=currency_code,
        consultation_fee=consultation_fee,
        slug=slug,
        rating_average=rating,
        review_count=review_count,
        languages=["English", "Hindi"] if country_code == "IN" else ["English"],
        bio=f"Experienced {specialization} with 10+ years of practice. Specializing in patient-centered care.",
        subscription_plan_id="plan-growth",  # Growth tier
        subscription_status="active",
        subscription_started_at=datetime.utcnow(),
        subscription_ends_at=datetime.utcnow() + timedelta(days=30),
        whatsapp_limit=200,
        whatsapp_used=0,
        is_searchable=True,
        is_active=True,
        created_at=datetime.utcnow()
    )
    
    # Set password
    doctor.set_password("doctor123")
    
    db.add(doctor)
    db.commit()
    return doctor


def seed_global_doctors():
    """Seed 20 doctors across 3 cities"""
    db = SessionLocal()
    
    try:
        print("🌍 SEEDING V3 GLOBAL MARKETPLACE DOCTORS")
        print("=" * 60)
        
        # === BHOPAL, INDIA (10 doctors) ===
        print("\n🇮🇳 Creating Bhopal doctors (10)...")
        bhopal_clinic = create_clinic(db, "Bhopal Medical Center", "Bhopal", "IN")
        
        bhopal_doctors = [
            {
                "name": "Dr. Rajesh Mehta",
                "specialization": "Cardiology",
                "whatsapp_number": "+919876543201",
                "slug": "rajesh-mehta-bhopal",
                "consultation_fee": 800,
                "rating": 4.8,
                "review_count": 45
            },
            {
                "name": "Dr. Priya Sharma",
                "specialization": "Dermatology",
                "whatsapp_number": "+919876543202",
                "slug": "priya-sharma-bhopal",
                "consultation_fee": 600,
                "rating": 4.7,
                "review_count": 38
            },
            {
                "name": "Dr. Amit Kumar",
                "specialization": "Orthopedics",
                "whatsapp_number": "+919876543203",
                "slug": "amit-kumar-bhopal",
                "consultation_fee": 700,
                "rating": 4.6,
                "review_count": 32
            },
            {
                "name": "Dr. Neha Gupta",
                "specialization": "Pediatrics",
                "whatsapp_number": "+919876543204",
                "slug": "neha-gupta-bhopal",
                "consultation_fee": 500,
                "rating": 4.9,
                "review_count": 52
            },
            {
                "name": "Dr. Suresh Patel",
                "specialization": "ENT",
                "whatsapp_number": "+919876543205",
                "slug": "suresh-patel-bhopal",
                "consultation_fee": 550,
                "rating": 4.5,
                "review_count": 28
            },
            {
                "name": "Dr. Kavita Singh",
                "specialization": "Gynecology",
                "whatsapp_number": "+919876543206",
                "slug": "kavita-singh-bhopal",
                "consultation_fee": 650,
                "rating": 4.8,
                "review_count": 41
            },
            {
                "name": "Dr. Vikram Jain",
                "specialization": "Neurology",
                "whatsapp_number": "+919876543207",
                "slug": "vikram-jain-bhopal",
                "consultation_fee": 900,
                "rating": 4.7,
                "review_count": 35
            },
            {
                "name": "Dr. Anita Verma",
                "specialization": "Ophthalmology",
                "whatsapp_number": "+919876543208",
                "slug": "anita-verma-bhopal",
                "consultation_fee": 600,
                "rating": 4.6,
                "review_count": 30
            },
            {
                "name": "Dr. Ravi Malhotra",
                "specialization": "General Medicine",
                "whatsapp_number": "+919876543209",
                "slug": "ravi-malhotra-bhopal",
                "consultation_fee": 400,
                "rating": 4.5,
                "review_count": 48
            },
            {
                "name": "Dr. Sunita Rao",
                "specialization": "Dentistry",
                "whatsapp_number": "+919876543210",
                "slug": "sunita-rao-bhopal",
                "consultation_fee": 500,
                "rating": 4.8,
                "review_count": 44
            }
        ]
        
        for doc_data in bhopal_doctors:
            create_doctor(
                db, bhopal_clinic.id,
                name=doc_data["name"],
                specialization=doc_data["specialization"],
                city="Bhopal",
                country_code="IN",
                currency_code="INR",
                consultation_fee=doc_data["consultation_fee"],
                whatsapp_number=doc_data["whatsapp_number"],
                slug=doc_data["slug"],
                rating=doc_data["rating"],
                review_count=doc_data["review_count"]
            )
            print(f"  ✓ {doc_data['name']} - {doc_data['specialization']}")
        
        # === DUBAI, UAE (5 doctors) ===
        print("\n🇦🇪 Creating Dubai doctors (5)...")
        dubai_clinic = create_clinic(db, "Dubai Healthcare Clinic", "Dubai", "AE")
        
        dubai_doctors = [
            {
                "name": "Dr. Sarah Ahmed",
                "specialization": "Dermatology",
                "whatsapp_number": "+971501234501",
                "slug": "sarah-ahmed-dubai",
                "consultation_fee": 250,  # AED
                "rating": 4.9,
                "review_count": 67
            },
            {
                "name": "Dr. Mohammed Ali",
                "specialization": "Cardiology",
                "whatsapp_number": "+971501234502",
                "slug": "mohammed-ali-dubai",
                "consultation_fee": 300,
                "rating": 4.8,
                "review_count": 54
            },
            {
                "name": "Dr. Fatima Khan",
                "specialization": "Pediatrics",
                "whatsapp_number": "+971501234503",
                "slug": "fatima-khan-dubai",
                "consultation_fee": 200,
                "rating": 4.7,
                "review_count": 43
            },
            {
                "name": "Dr. Omar Hassan",
                "specialization": "Orthopedics",
                "whatsapp_number": "+971501234504",
                "slug": "omar-hassan-dubai",
                "consultation_fee": 280,
                "rating": 4.6,
                "review_count": 38
            },
            {
                "name": "Dr. Layla Mansoor",
                "specialization": "Gynecology",
                "whatsapp_number": "+971501234505",
                "slug": "layla-mansoor-dubai",
                "consultation_fee": 260,
                "rating": 4.8,
                "review_count": 51
            }
        ]
        
        for doc_data in dubai_doctors:
            create_doctor(
                db, dubai_clinic.id,
                name=doc_data["name"],
                specialization=doc_data["specialization"],
                city="Dubai",
                country_code="AE",
                currency_code="AED",
                consultation_fee=doc_data["consultation_fee"],
                whatsapp_number=doc_data["whatsapp_number"],
                slug=doc_data["slug"],
                rating=doc_data["rating"],
                review_count=doc_data["review_count"]
            )
            print(f"  ✓ {doc_data['name']} - {doc_data['specialization']}")
        
        # === NEW YORK, USA (5 doctors) ===
        print("\n🇺🇸 Creating New York doctors (5)...")
        nyc_clinic = create_clinic(db, "NYC Medical Associates", "New York", "US")
        
        nyc_doctors = [
            {
                "name": "Dr. James Anderson",
                "specialization": "Cardiology",
                "whatsapp_number": "+12125551001",
                "slug": "james-anderson-nyc",
                "consultation_fee": 150,  # USD
                "rating": 4.8,
                "review_count": 89
            },
            {
                "name": "Dr. Emily Chen",
                "specialization": "Dermatology",
                "whatsapp_number": "+12125551002",
                "slug": "emily-chen-nyc",
                "consultation_fee": 120,
                "rating": 4.9,
                "review_count": 76
            },
            {
                "name": "Dr. Michael Rodriguez",
                "specialization": "Pediatrics",
                "whatsapp_number": "+12125551003",
                "slug": "michael-rodriguez-nyc",
                "consultation_fee": 100,
                "rating": 4.7,
                "review_count": 64
            },
            {
                "name": "Dr. Jessica Williams",
                "specialization": "Gynecology",
                "whatsapp_number": "+12125551004",
                "slug": "jessica-williams-nyc",
                "consultation_fee": 130,
                "rating": 4.8,
                "review_count": 71
            },
            {
                "name": "Dr. David Lee",
                "specialization": "Neurology",
                "whatsapp_number": "+12125551005",
                "slug": "david-lee-nyc",
                "consultation_fee": 180,
                "rating": 4.9,
                "review_count": 82
            }
        ]
        
        for doc_data in nyc_doctors:
            create_doctor(
                db, nyc_clinic.id,
                name=doc_data["name"],
                specialization=doc_data["specialization"],
                city="New York",
                country_code="US",
                currency_code="USD",
                consultation_fee=doc_data["consultation_fee"],
                whatsapp_number=doc_data["whatsapp_number"],
                slug=doc_data["slug"],
                rating=doc_data["rating"],
                review_count=doc_data["review_count"]
            )
            print(f"  ✓ {doc_data['name']} - {doc_data['specialization']}")
        
        print("\n" + "=" * 60)
        print("✅ SUCCESSFULLY SEEDED 20 DOCTORS")
        print("   • 10 in Bhopal, India (INR)")
        print("   • 5 in Dubai, UAE (AED)")
        print("   • 5 in New York, USA (USD)")
        print("=" * 60)
        
        # Calculate MRR
        total_doctors = 20
        avg_price_inr = 3999
        mrr = total_doctors * avg_price_inr
        print(f"\n💰 PROJECTED MRR: ₹{mrr:,} ({total_doctors} doctors × ₹{avg_price_inr})")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_global_doctors()
