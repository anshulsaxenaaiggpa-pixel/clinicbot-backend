"""add status column to doctors

Revision ID: fix_doctor_status
Revises: 54caccb6b28b
Create Date: 2026-01-06 23:06:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fix_doctor_status'
down_revision = '54caccb6b28b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Try to add status column - ignore if it exists
    try:
        op.add_column('doctors', sa.Column('status', sa.String(length=20), server_default='active', nullable=True))
        print("✅ Added status column to doctors table")
    except Exception as e:
        print(f"⚠️ Status column might already exist: {e}")
    
    # Try to add upi_id column - ignore if it exists
    try:
        op.add_column('doctors', sa.Column('upi_id', sa.String(length=100), nullable=True))
        print("✅ Added upi_id column to doctors table")
    except Exception as e:
        print(f"⚠️ UPI ID column might already exist: {e}")


def downgrade() -> None:
    op.drop_column('doctors', 'status')
    op.drop_column('doctors', 'upi_id')
