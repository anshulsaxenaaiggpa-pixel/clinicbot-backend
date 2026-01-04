"""add_payment_receipt_fields

Global payment receipt upload support - UPI/Zelle/Venmo/iDEAL
Adds payment tracking to appointments and payment method fields to doctors.

Revision ID: bbb95cfbd844
Revises: 00c938fd2b1a
Create Date: 2026-01-04 21:44:52.479289

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'bbb95cfbd844'
down_revision = '00c938fd2b1a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add payment receipt fields to appointments
    op.add_column('appointments', sa.Column('payment_status', sa.String(20), server_default='pending', nullable=False))
    op.add_column('appointments', sa.Column('payment_receipt_url', sa.Text(), nullable=True))
    op.add_column('appointments', sa.Column('payment_amount', sa.Numeric(10, 2), nullable=True))
    op.add_column('appointments', sa.Column('payment_method', sa.String(50), nullable=True))  # UPI/Zelle/Venmo
    op.add_column('appointments', sa.Column('payment_verified_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('appointments', sa.Column('payment_verified_by', sa.String(36), nullable=True))  # admin user ID
    op.add_column('appointments', sa.Column('receipt_uploaded_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('appointments', sa.Column('receipt_ocr_text', sa.Text(), nullable=True))  # For audit trail
    
    # Create index for payment status queries
    op.create_index('idx_appointments_payment_status', 'appointments', ['payment_status'])
    
    # Add payment method fields to doctors
    op.add_column('doctors', sa.Column('upi_id', sa.String(255), nullable=True))
    op.add_column('doctors', sa.Column('venmo_handle', sa.String(255), nullable=True))
    op.add_column('doctors', sa.Column('zelle_email', sa.String(255), nullable=True))
    op.add_column('doctors', sa.Column('payment_instructions', sa.Text(), nullable=True))  # Custom payment info
    op.add_column('doctors', sa.Column('accepts_cash', sa.Boolean(), server_default='true', nullable=False))


def downgrade() -> None:
    # Remove doctor payment fields
    op.drop_column('doctors', 'accepts_cash')
    op.drop_column('doctors', 'payment_instructions')
    op.drop_column('doctors', 'zelle_email')
    op.drop_column('doctors', 'venmo_handle')
    op.drop_column('doctors', 'upi_id')
    
    # Remove appointment payment fields
    op.drop_index('idx_appointments_payment_status', table_name='appointments')
    op.drop_column('appointments', 'receipt_ocr_text')
    op.drop_column('appointments', 'receipt_uploaded_at')
    op.drop_column('appointments', 'payment_verified_by')
    op.drop_column('appointments', 'payment_verified_at')
    op.drop_column('appointments', 'payment_method')
    op.drop_column('appointments', 'payment_amount')
    op.drop_column('appointments', 'payment_receipt_url')
    op.drop_column('appointments', 'payment_status')

