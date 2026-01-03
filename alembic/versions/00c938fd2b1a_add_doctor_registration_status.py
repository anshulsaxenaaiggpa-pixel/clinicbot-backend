"""add_doctor_registration_status

Revision ID: 00c938fd2b1a
Revises: 54611a366d7e
Create Date: 2025-12-31 22:36:18.491155

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '00c938fd2b1a'
down_revision = '54611a366d7e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('doctors')]
    
    # Add new columns if missing
    if 'clinic_name' not in columns:
        op.add_column('doctors', sa.Column('clinic_name', sa.String(length=100), nullable=True))
    if 'phone' not in columns:
        op.add_column('doctors', sa.Column('phone', sa.String(length=15), nullable=True))
    if 'email' not in columns:
        op.add_column('doctors', sa.Column('email', sa.String(length=100), nullable=True))
    if 'status' not in columns:
        op.add_column('doctors', sa.Column('status', sa.String(length=20), nullable=True, server_default='pending_otp'))
    if 'clinic_whatsapp' not in columns:
        op.add_column('doctors', sa.Column('clinic_whatsapp', sa.String(length=15), nullable=True))
    if 'approved_at' not in columns:
        op.add_column('doctors', sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True))
    
    # Make clinic_id nullable if it exists and is not already nullable
    # SQLite doesn't support easy alter column to nullable, but focusing on PG for production
    if op.get_bind().dialect.name == 'postgresql':
        op.alter_column('doctors', 'clinic_id', existing_type=sa.String(length=36), nullable=True)


def downgrade() -> None:
    pass
