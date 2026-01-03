"""
Script to create consent_log table directly on Railway Postgres.
Run with: railway run python create_consent_table.py
"""
import os
import psycopg2

# Get database URL from environment
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set")
    exit(1)

print(f"Connecting to database...")

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Create consent_log table
    print("Creating consent_log table...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS consent_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            phone VARCHAR(15) NOT NULL,
            clinic_id UUID NOT NULL,
            consent_given BOOLEAN NOT NULL,
            consent_source VARCHAR(20) NOT NULL,
            consent_version VARCHAR(20) NOT NULL,
            consent_text TEXT NOT NULL,
            timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            ip_address VARCHAR(50)
        )
    """)
    print("✅ Table created!")
    
    # Create indexes
    print("Creating indexes...")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_consent_log_phone ON consent_log (phone)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_consent_clinic_phone ON consent_log (clinic_id, phone)")
    print("✅ Indexes created!")
    
    conn.commit()
    
    # Verify
    cur.execute("SELECT COUNT(*) FROM consent_log")
    count = cur.fetchone()[0]
    print(f"✅ consent_log table ready! Current rows: {count}")
    
    cur.close()
    conn.close()
    print("Done!")
    
except Exception as e:
    print(f"ERROR: {e}")
    exit(1)
