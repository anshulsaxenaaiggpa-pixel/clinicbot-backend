"""
Diagnostic script for WhatsApp bot issues
Checks configuration, database, and connectivity
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def check_environment_variables():
    """Check if all required environment variables are set"""
    print("\n" + "="*60)
    print("ENVIRONMENT VARIABLES CHECK")
    print("="*60)
    
    required_vars = [
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_WHATSAPP_NUMBER",
        "SECRET_KEY",
        "SESSION_SECRET_KEY",
        "DATABASE_URL"
    ]
    
    optional_vars = [
        "REDIS_URL",
        "OPENAI_API_KEY",
        "WHATSAPP_PROVIDER"
    ]
    
    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if "KEY" in var or "TOKEN" in var or "SECRET" in var:
                display_value = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
        else:
            print(f"❌ {var}: NOT SET")
            missing.append(var)
    
    print("\nOptional Variables:")
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            if "KEY" in var or "TOKEN" in var:
                display_value = f"{value[:8]}..." if len(value) > 8 else "***"
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
        else:
            print(f"⚠️  {var}: Not set (optional)")
    
    if missing:
        print(f"\n⚠️  WARNING: {len(missing)} required variables are missing!")
        print("   These must be set in Railway environment variables")
        return False
    else:
        print("\n✅ All required environment variables are set!")
        return True

def check_database_connection():
    """Test database connectivity"""
    print("\n" + "="*60)
    print("DATABASE CONNECTION CHECK")
    print("="*60)
    
    try:
        from app.db.database import SessionLocal, engine
        from sqlalchemy import text
        
        # Test connection
        db = SessionLocal()
        result = db.execute(text("SELECT 1"))
        db.close()
        
        print("✅ Database connection successful!")
        print(f"   Database URL: {os.getenv('DATABASE_URL', 'sqlite:///./clinicbot.db')[:50]}...")
        return True
        
    except Exception as e:
        print(f"❌ Database connection FAILED!")
        print(f"   Error: {type(e).__name__}: {str(e)[:100]}")
        return False

def check_clinic_configuration():
    """Check if clinics are properly configured"""
    print("\n" + "="*60)
    print("CLINIC CONFIGURATION CHECK")
    print("="*60)
    
    try:
        from app.db.database import SessionLocal
        from app.models.clinic import Clinic
        
        db = SessionLocal()
        clinics = db.query(Clinic).all()
        
        if not clinics:
            print("❌ No clinics found in database!")
            print("   You need to create a clinic with a WhatsApp number")
            db.close()
            return False
        
        print(f"✅ Found {len(clinics)} clinic(s):\n")
        
        twilio_number = os.getenv("TWILIO_WHATSAPP_NUMBER", "").replace("whatsapp:", "")
        
        for clinic in clinics:
            print(f"   Clinic: {clinic.name}")
            print(f"   - ID: {clinic.id}")
            print(f"   - WhatsApp Number: {clinic.whatsapp_number}")
            print(f"   - Active: {clinic.is_active}")
            
            if clinic.whatsapp_number == twilio_number:
                print(f"   ✅ MATCHES TWILIO NUMBER!")
            print()
        
        # Check if any clinic matches Twilio number
        matching_clinic = db.query(Clinic).filter(
            Clinic.whatsapp_number == twilio_number,
            Clinic.is_active == True
        ).first()
        
        db.close()
        
        if matching_clinic:
            print(f"✅ Active clinic found matching Twilio number: {matching_clinic.name}")
            return True
        else:
            print(f"❌ No active clinic matches Twilio number: {twilio_number}")
            print("   Update a clinic's whatsapp_number to match your Twilio number")
            return False
            
    except Exception as e:
        print(f"❌ Error checking clinics: {type(e).__name__}: {str(e)[:100]}")
        return False

def check_twilio_connection():
    """Test Twilio API connection"""
    print("\n" + "="*60)
    print("TWILIO API CONNECTION CHECK")
    print("="*60)
    
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    
    if not account_sid or not auth_token:
        print("❌ Twilio credentials not set - skipping connection test")
        return False
    
    try:
        from twilio.rest import Client
        
        client = Client(account_sid, auth_token)
        
        # Test by fetching account info
        account = client.api.accounts(account_sid).fetch()
        
        print(f"✅ Twilio connection successful!")
        print(f"   Account Name: {account.friendly_name}")
        print(f"   Account Status: {account.status}")
        return True
        
    except Exception as e:
        print(f"❌ Twilio connection FAILED!")
        print(f"   Error: {type(e).__name__}: {str(e)[:150]}")
        
        error_str = str(e).lower()
        if "401" in error_str or "authenticate" in error_str:
            print("   → Check your TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN")
        elif "connection" in error_str:
            print("   → Network connectivity issue")
        
        return False

def check_redis_connection():
    """Test Redis connection"""
    print("\n" + "="*60)
    print("REDIS CONNECTION CHECK")
    print("="*60)
    
    redis_url = os.getenv("REDIS_URL")
    
    if not redis_url:
        print("⚠️  REDIS_URL not set - using in-memory session fallback")
        print("   This is OK for testing but not recommended for production")
        return True
    
    try:
        import redis
        
        client = redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=5)
        client.ping()
        
        print(f"✅ Redis connection successful!")
        return True
        
    except Exception as e:
        print(f"⚠️  Redis connection failed: {type(e).__name__}: {str(e)[:100]}")
        print("   App will fall back to in-memory sessions")
        return True  # Not critical

def main():
    """Run all diagnostic checks"""
    print("\n" + "="*60)
    print("WHATSAPP BOT DIAGNOSTIC SCRIPT")
    print("="*60)
    print("\nThis script checks your configuration to identify why")
    print("the WhatsApp bot is not responding.\n")
    
    results = {
        "Environment Variables": check_environment_variables(),
        "Database Connection": check_database_connection(),
        "Clinic Configuration": check_clinic_configuration(),
        "Twilio Connection": check_twilio_connection(),
        "Redis Connection": check_redis_connection()
    }
    
    # Summary
    print("\n" + "="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for check, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {check}")
    
    print(f"\n{passed}/{total} checks passed")
    
    if passed == total:
        print("\n✅ All checks passed! The configuration looks good.")
        print("   If the bot still isn't responding:")
        print("   1. Check Railway logs for runtime errors")
        print("   2. Verify Twilio webhook URL is correct")
        print("   3. Ensure you've joined the WhatsApp sandbox")
    else:
        print("\n❌ Some checks failed. Please fix the issues above.")
        print("   Once fixed, redeploy to Railway and test again.")
    
    return passed == total

if __name__ == "__main__":
    # Load .env file if it exists
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("Loaded .env file")
    except ImportError:
        print("python-dotenv not installed, using environment variables only")
    except Exception as e:
        print(f"Note: Could not load .env: {e}")
    
    success = main()
    sys.exit(0 if success else 1)
