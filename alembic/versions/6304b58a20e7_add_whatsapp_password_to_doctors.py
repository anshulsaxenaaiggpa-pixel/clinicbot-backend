"""add_whatsapp_password_to_doctors

Revision ID: 6304b58a20e7
Revises: 217e276ac601
Create Date: 2026-01-08 10:58:56.462145

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6304b58a20e7'
down_revision = '217e276ac601'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add whatsapp_number and ensure password_hash exists in doctors table."""
    
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('doctors')]
    
    # Add whatsapp_number column only if it doesn't exist
    if 'whatsapp_number' not in columns:
        op.add_column('doctors', 
            sa.Column('whatsapp_number', sa.String(20), nullable=True))
        print("✅ Added whatsapp_number column to doctors table")
        
        # Backfill existing doctors with empty string
        op.execute("UPDATE doctors SET whatsapp_number = '' WHERE whatsapp_number IS NULL")
        print("✅ Backfilled whatsapp_number with empty string for existing doctors")
    else:
        print("ℹ️ whatsapp_number column already exists, skipping")
    
    # Add password_hash column only if it doesn't exist
    if 'password_hash' not in columns:
        op.add_column('doctors', 
            sa.Column('password_hash', sa.String(255), nullable=True))
        print("✅ Added password_hash column to doctors table")
    else:
        print("ℹ️ password_hash column already exists, skipping (added by migration 217e276ac601)")


def downgrade() -> None:
    """Remove whatsapp_number (keep password_hash as it may be from a different migration)."""
    try:
        op.drop_column('doctors', 'whatsapp_number')
        print("✅ Removed whatsapp_number column")
    except Exception as e:
        print(f"⚠️ Could not remove whatsapp_number: {e}")
