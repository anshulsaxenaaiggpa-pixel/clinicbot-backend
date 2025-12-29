"""Add clinic timing to existing clinic - Railway migration script"""
import uuid
from datetime import datetime, time as dt_time
from sqlalchemy.orm import Session

# Import models
from app.db.base import Base
from app.models.clinic import Clinic
from app.models.clinic_timing import ClinicTiming
from app.db.database import SessionLocal

def add_timing_to_existing_clinic():
    """Add clinic timing to existing clinic (if not already present)"""
    db = SessionLocal()
    
    try:
        # Get the first clinic (should be the test clinic)
        clinic = db.query(Clinic).first()
        
        if not clinic:
            print("❌ No clinic found! Please run seed_test_data.py first.")
            return
        
        print(f"\n{'='*60}")
        print(f"🏥 Found Clinic: {clinic.name}")
        print(f"   ID: {clinic.id}")
        print(f"   WhatsApp: {clinic.whatsapp_number}")
        print(f"{'='*60}\n")
        
        # Check if timing already exists
        existing_timing = db.query(ClinicTiming).filter(
            ClinicTiming.clinic_id == clinic.id
        ).first()
        
        if existing_timing:
            print("✅ Clinic timing already exists! No action needed.")
            print(f"\n   Existing timing records:")
            
            all_timings = db.query(ClinicTiming).filter(
                ClinicTiming.clinic_id == clinic.id
            ).all()
            
            for timing in all_timings:
                status = "Closed" if timing.is_closed else f"{timing.start_time} - {timing.end_time}"
                print(f"   - {timing.day_of_week.capitalize()}: {status}")
            
            return
        
        print("📝 Adding clinic timing records...")
        
        now = datetime.utcnow()
        
        # Weekday timing (Monday-Friday): 9 AM - 6 PM with lunch break
        weekday_timing = ClinicTiming(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            day_of_week="monday",  # Represents all weekdays
            start_time=dt_time(9, 0),  # 9:00 AM
            end_time=dt_time(18, 0),  # 6:00 PM
            is_closed=False,
            lunch_enabled=True,
            lunch_start=dt_time(13, 0),  # 1:00 PM
            lunch_end=dt_time(14, 0),  # 2:00 PM
            created_at=now,
            updated_at=now
        )
        db.add(weekday_timing)
        
        # Saturday timing: 9 AM - 2 PM (shorter hours)
        saturday_timing = ClinicTiming(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            day_of_week="saturday",
            start_time=dt_time(9, 0),  # 9:00 AM
            end_time=dt_time(14, 0),  # 2:00 PM
            is_closed=False,
            lunch_enabled=False,
            created_at=now,
            updated_at=now
        )
        db.add(saturday_timing)
        
        # Sunday: Closed
        sunday_timing = ClinicTiming(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            day_of_week="sunday",
            start_time=None,
            end_time=None,
            is_closed=True,
            lunch_enabled=False,
            created_at=now,
            updated_at=now
        )
        db.add(sunday_timing)
        
        db.commit()
        
        print("✅ Clinic timing added successfully!")
        print(f"\n{'='*60}")
        print("📅 Clinic Hours:")
        print("   Monday-Friday: 9:00 AM - 6:00 PM")
        print("   Lunch Break: 1:00 PM - 2:00 PM")
        print("   Saturday: 9:00 AM - 2:00 PM")
        print("   Sunday: Closed")
        print(f"{'='*60}\n")
        
        print("🎉 DONE! Slots should now be available for booking.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("\n🚀 Adding clinic timing to existing clinic...\n")
    add_timing_to_existing_clinic()
