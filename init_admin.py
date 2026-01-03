#!/usr/bin/env python3
"""
Initialize First Admin User

This script creates the initial admin user for the ClinicBot Admin UI.
Run this on Railway or locally to set up your first admin account.

Usage:
    python init_admin.py

You'll be prompted for:
    - Email
    - Full Name
    - Password (must meet security requirements)
"""
import uuid
from datetime import datetime
from getpass import getpass
import re


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_password(password: str) -> tuple[bool, str]:
    """
    Validate password meets security requirements.
    
    Requirements:
    - Minimum 12 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character
    """
    if len(password) < 12:
        return False, "Password must be at least 12 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is valid"


def create_admin_user(db_session, email: str, full_name: str, password: str):
    """Create the super admin user."""
    from app.models.admin_user import AdminUser, AdminRole
    
    # Check if admin already exists
    existing = db_session.query(AdminUser).filter(AdminUser.email == email.lower()).first()
    if existing:
        print(f"\n❌ Admin user with email '{email}' already exists!")
        print(f"   Use the Admin UI to manage existing users or choose a different email.\n")
        return None
    
    # Create new admin user
    admin = AdminUser(
        id=str(uuid.uuid4()),
        email=email.lower().strip(),
        full_name=full_name.strip(),
        role=AdminRole.SUPER_ADMIN,
        is_active=True,
        mfa_enabled=False,  # User can enable MFA after first login
        failed_login_attempts=0,
        must_change_password=False,
        password_last_changed=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # Set password (will be hashed automatically)
    admin.set_password(password)
    
    # Save to database
    db_session.add(admin)
    db_session.commit()
    
    return admin


def main():
    """Main initialization flow."""
    print("\n" + "="*60)
    print("🔐 ClinicBot Admin User Initialization")
    print("="*60)
    print("\nThis will create your first Super Admin account.")
    print("\n⚠️  Password Requirements:")
    print("   • Minimum 12 characters")
    print("   • At least one uppercase letter")
    print("   • At least one lowercase letter")
    print("   • At least one number")
    print("   • At least one special character (!@#$%^&*...)")
    print("\n" + "-"*60 + "\n")
    
    # Get email
    while True:
        email = input("Enter admin email: ").strip()
        if validate_email(email):
            break
        print("❌ Invalid email format. Please try again.\n")
    
    # Get full name
    full_name = input("Enter full name: ").strip()
    while not full_name or len(full_name) < 2:
        print("❌ Name must be at least 2 characters.\n")
        full_name = input("Enter full name: ").strip()
    
    # Get password
    while True:
        password = getpass("Enter password: ")
        password_confirm = getpass("Confirm password: ")
        
        if password != password_confirm:
            print("❌ Passwords don't match. Please try again.\n")
            continue
        
        is_valid, message = validate_password(password)
        if not is_valid:
            print(f"❌ {message}\n")
            continue
        
        break
    
    print("\n" + "-"*60)
    print("📝 Creating admin user...")
    print("-"*60 + "\n")
    
    # Initialize database connection
    try:
        from app.db.database import SessionLocal
        from sqlalchemy.orm import configure_mappers
        
        # Import models to register them
        from app.db.base import Base
        configure_mappers()
        
        db = SessionLocal()
        
        # Create admin user
        admin = create_admin_user(db, email, full_name, password)
        
        if admin:
            print("="*60)
            print("✅ Admin User Created Successfully!")
            print("="*60)
            print(f"   Email: {admin.email}")
            print(f"   Name: {admin.full_name}")
            print(f"   Role: {admin.role.value}")
            print(f"   ID: {admin.id}")
            print("\n📋 Next Steps:")
            print("   1. Visit your admin login page")
            print("   2. Log in with the credentials you just created")
            print("   3. Enable MFA from your profile settings (recommended)")
            print("="*60 + "\n")
        
        db.close()
        
    except Exception as e:
        print(f"\n❌ Error creating admin user: {e}")
        import traceback
        traceback.print_exc()
        print("\nMake sure you have:")
        print("  1. Run all Alembic migrations (alembic upgrade head)")
        print("  2. Database is accessible")
        print("  3. All environment variables are set\n")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
