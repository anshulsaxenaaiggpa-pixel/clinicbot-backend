"""
Test WhatsApp message flow locally without Railway
Simulates incoming webhook request to debug the bot logic
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

async def simulate_whatsapp_message():
    """Simulate an incoming WhatsApp message"""
    print("\n" + "="*60)
    print("SIMULATING WHATSAPP MESSAGE FLOW")
    print("="*60)
    
    # Test phone number (change this to your test number)
    test_phone = input("\nEnter test phone number (e.g., +919876543210): ").strip()
    if not test_phone:
        test_phone = "+919876543210"  # Default
    
    # Test message
    print("\nWhat message should we simulate?")
    print("1. First-time user (should get consent prompt)")
    print("2. User replying '1' to consent (should get booking menu)")
    print("3. User saying 'Hi' (normal flow)")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        message_text = "Hi"
        print("\n→ Simulating first-time user message: 'Hi'")
    elif choice == "2":
        message_text = "1"
        print("\n→ Simulating consent agreement: '1'")
    else:
        message_text = "Hi"
        print("\n→ Simulating normal message: 'Hi'")
    
    # Get clinic WhatsApp number from environment
    import os
    clinic_number = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886").replace("whatsapp:", "")
    
    # Construct message data (Twilio format)
    message_data = {
        "provider": "twilio",
        "from": test_phone,
        "to": clinic_number,
        "message_id": "TEST_MSG_" + str(int(asyncio.get_event_loop().time())),
        "body": message_text,
        "timestamp": "2026-01-01T08:00:00Z",
        "profile_name": "Test User"
    }
    
    print("\n" + "-"*60)
    print("MESSAGE DATA:")
    print("-"*60)
    for key, value in message_data.items():
        print(f"  {key}: {value}")
    
    # Import handler
    try:
        from app.services.whatsapp_handler import WhatsAppMessageHandler
        
        print("\n" + "-"*60)
        print("PROCESSING MESSAGE...")
        print("-"*60)
        
        handler = WhatsAppMessageHandler()
        await handler.handle_message(message_data)
        
        print("\n✅ Message processed successfully!")
        print("\nCheck the output above for:")
        print("  - Patient lookup/creation")
        print("  - Consent check")
        print("  - Intent classification")
        print("  - Response generation")
        print("  - Message sending attempt")
        
    except Exception as e:
        import traceback
        print(f"\n❌ Error processing message!")
        print(f"   Error: {type(e).__name__}: {str(e)}")
        print("\nFull traceback:")
        print(traceback.format_exc())
        return False
    
    return True

async def test_consent_flow():
    """Test the consent checking logic"""
    print("\n" + "="*60)
    print("TESTING CONSENT FLOW")
    print("="*60)
    
    test_phone = input("\nEnter test phone number: ").strip() or "+919876543210"
    
    try:
        from app.services.consent_handler import check_consent, get_consent_text
        from app.db.database import SessionLocal
        from app.models.clinic import Clinic
        
        # Get first clinic
        db = SessionLocal()
        clinic = db.query(Clinic).first()
        
        if not clinic:
            print("❌ No clinic found in database")
            print("   Run seed_test_data.py first")
            db.close()
            return False
        
        clinic_id = str(clinic.id)
        db.close()
        
        print(f"\nTesting consent for:")
        print(f"  Phone: {test_phone}")
        print(f"  Clinic: {clinic.name} ({clinic_id})")
        
        # Check consent
        has_consent = check_consent(test_phone, clinic_id)
        
        print(f"\n{'✅' if has_consent else '❌'} Has Consent: {has_consent}")
        
        if not has_consent:
            print("\nConsent text that would be sent:")
            print("-"*60)
            consent_text = get_consent_text(test_phone)
            print(consent_text)
            print("-"*60)
        
        return True
        
    except Exception as e:
        import traceback
        print(f"\n❌ Error testing consent: {type(e).__name__}: {str(e)}")
        print(traceback.format_exc())
        return False

async def main():
    """Main test menu"""
    print("\n" + "="*60)
    print("WHATSAPP BOT LOCAL TESTING TOOL")
    print("="*60)
    print("\nThis tool simulates WhatsApp messages locally to test")
    print("your bot logic without needing Railway deployment.\n")
    
    while True:
        print("\nWhat would you like to test?")
        print("1. Simulate WhatsApp message")
        print("2. Test consent flow")
        print("3. Exit")
        
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == "1":
            await simulate_whatsapp_message()
        elif choice == "2":
            await test_consent_flow()
        elif choice == "3":
            print("\nExiting...")
            break
        else:
            print("Invalid choice")
        
        input("\nPress Enter to continue...")
        print("\n" + "="*60)

if __name__ == "__main__":
    # Load .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Loaded .env file\n")
    except ImportError:
        print("⚠️  python-dotenv not installed")
        print("   Install with: pip install python-dotenv\n")
    except Exception as e:
        print(f"⚠️  Could not load .env: {e}\n")
    
    # Run async main
    asyncio.run(main())
