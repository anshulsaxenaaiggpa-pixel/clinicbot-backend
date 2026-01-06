"""
Reset Admin Password Script

Usage:
    python reset_admin_password.py <email> <new_password>

Example:
    python reset_admin_password.py curaslot@gmail.com NewSecurePassword123!
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.models.admin_user import AdminUser
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def reset_password(email: str, new_password: str):
    """Reset admin user password"""
    db = SessionLocal()
    
    try:
        # Find admin user
        user = db.query(AdminUser).filter(AdminUser.email == email).first()
        
        if not user:
            print(f"❌ Admin user not found: {email}")
            print("\nAvailable admin users:")
            all_users = db.query(AdminUser).all()
            for u in all_users:
                print(f"  - {u.email} (Active: {u.is_active})")
            return False
        
        # Hash new password
        hashed_password = pwd_context.hash(new_password)
        
        # Update user
        user.hashed_password = hashed_password
        user.failed_login_attempts = 0  # Reset failed attempts
        user.is_active = True  # Ensure account is active
        
        db.commit()
        
        print(f"✅ Password reset successful for: {email}")
        print(f"   New password: {new_password}")
        print(f"   Account active: {user.is_active}")
        print(f"   Failed attempts reset: 0")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
        
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python reset_admin_password.py <email> <new_password>")
        print("Example: python reset_admin_password.py admin@example.com NewPass123!")
        sys.exit(1)
    
    email = sys.argv[1]
    new_password = sys.argv[2]
    
    print(f"🔄 Resetting password for: {email}")
    print("=" * 60)
    
    success = reset_password(email, new_password)
    
    if success:
        print("\n✅ You can now log in with the new password!")
    else:
        print("\n❌ Password reset failed")
        sys.exit(1)
