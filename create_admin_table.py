"""
Create admin_users table manually in Railway database
"""
from sqlalchemy import create_engine, text
import os

# Get the database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set!")
    exit(1)

print(f"Connecting to database...")

engine = create_engine(DATABASE_URL)

# SQL to create admin_users table
create_table_sql = """
CREATE TABLE IF NOT EXISTS admin_users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL,
    mfa_secret VARCHAR(32),
    mfa_enabled BOOLEAN NOT NULL DEFAULT false,
    is_active BOOLEAN NOT NULL DEFAULT true,
    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMPTZ,
    password_last_changed TIMESTAMPTZ NOT NULL,
    must_change_password BOOLEAN NOT NULL DEFAULT false,
    last_login_at TIMESTAMPTZ,
    last_login_ip VARCHAR(45),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_admin_email ON admin_users(email);
CREATE INDEX IF NOT EXISTS idx_admin_role ON admin_users(role);
CREATE INDEX IF NOT EXISTS idx_admin_active ON admin_users(is_active);
"""

try:
    with engine.connect() as conn:
        print("Creating admin_users table...")
        conn.execute(text(create_table_sql))
        conn.commit()
        print("✅ SUCCESS! admin_users table created successfully!")
        print("\nYou can now run: python init_admin.py")
except Exception as e:
    print(f"❌ ERROR: {e}")
    exit(1)
