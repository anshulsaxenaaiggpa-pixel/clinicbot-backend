"""
Quick script to verify doctor exists and test password.
Run this on Railway to check doctor credentials.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import SessionLocal
from app.models.doctor import Doctor

def check_doctor():
    db = SessionLocal()
    try:
        print("\n" + "="*80)
        print("🔍 CHECKING DOCTOR CREDENTIALS")
        print("="*80)
        
        # Find doctor
        doctor = db.query(Doctor).filter(Doctor.whatsapp_number == "+919876543210").first()
        
        if not doctor:
            print("❌ DOCTOR NOT FOUND!")
            print("   WhatsApp: +919876543210")
            print("\n💡 You need to run the seed script:")
            print("   python scripts/seed_doctor_data.py")
            return
        
        print(f"✅ Doctor Found:")
        print(f"   ID: {doctor.id}")
        print(f"   Name: {doctor.name}")
        print(f"   WhatsApp: {doctor.whatsapp_number}")
        print(f"   Active: {doctor.is_active}")
        print(f"   Status: {doctor.status}")
        print(f"   Consultation Fee: ₹{doctor.consultation_fee}")
        
        # Check if password_hash exists
        if hasattr(doctor, 'password_hash') and doctor.password_hash:
            print(f"   Password Hash: {doctor.password_hash[:20]}... (exists)")
            
            # Test password
            print("\n🔑 Testing Password...")
            if doctor.verify_password("doctor123"):
                print("✅ Password 'doctor123' is CORRECT!")
            else:
                print("❌ Password 'doctor123' is WRONG!")
                print("   The password hash exists but doesn't match.")
        else:
            print("   Password Hash: NOT SET!")
            print("\n❌ CRITICAL: Doctor has no password!")
            print("   Run this to set password:")
            print(f"   UPDATE doctors SET password_hash = '<hash>' WHERE id = '{doctor.id}';")
        
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check_doctor()
