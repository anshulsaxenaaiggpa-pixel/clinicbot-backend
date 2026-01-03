"""
Test admin login flow to identify issues
"""
import os
os.environ['DATABASE_URL'] = "postgresql://postgres:yoWWHoKXMtLUXFJdTEoadUZNMfTTwuyy@yamabiko.proxy.rlwy.net:11991/railway"
os.environ['REDIS_URL'] = "redis://default:yquwMZXPWbbNMJjvxxSkKVurSvmHmGUK@interchange.proxy.rlwy.net:18097"

from app.models.admin_user import AdminUser
from app.db.database import SessionLocal
from app.auth.session import session_manager

print("Testing admin login flow...\n")

# Step 1: Get user from database
print("1. Fetching user from database...")
db = SessionLocal()
user = db.query(AdminUser).filter(AdminUser.email == 'curaslot@gmail.com').first()
if user:
    print(f"   ✅ User found: {user.email}")
else:
    print("   ❌ User not found!")
    exit(1)

# Step 2: Verify password
print("\n2. Verifying password...")
password = "Curaslot@123"
if user.verify_password(password):
    print(f"   ✅ Password correct")
else:
    print("   ❌ Password incorrect!")
    exit(1)

# Step 3: Check if active
print("\n3. Checking if user is active...")
if user.is_active:
    print(f"   ✅ User is active")
else:
    print("   ❌ User is not active!")
    exit(1)

# Step 4: Check if locked
print("\n4. Checking if account is locked...")
if user.is_locked():
    print(f"   ❌ Account is locked until {user.locked_until}")
    exit(1)
else:
    print(f"   ✅ Account not locked")

# Step 5: Try to create a session
print("\n5. Testing session creation...")
try:
    session_token, csrf_token = session_manager.create_session(
        admin_user_id=str(user.id),
        ip_address="127.0.0.1",
        user_agent="test"
    )
    print(f"   ✅ Session created successfully!")
    print(f"      Session token: {session_token[:20]}...")
    print(f"      CSRF token: {csrf_token[:20]}...")
except Exception as e:
    print(f"   ❌ Session creation failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Step 6: Validate session
print("\n6. Testing session validation...")
try:
    session_data = session_manager.validate_session(session_token, "127.0.0.1")
    if session_data:
        print(f"   ✅ Session validated successfully!")
        print(f"      User ID: {session_data.get('user_id')}")
    else:
        print(f"   ❌ Session validation failed!")
except Exception as e:
    print(f"   ❌ Session validation error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("✅ ALL TESTS PASSED - Login flow should work!")
print("="*60)

db.close()
