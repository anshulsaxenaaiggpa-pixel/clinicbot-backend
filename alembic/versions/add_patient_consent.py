"""Add patient_consent table for DPDP compliance

Revision ID: add_patient_consent
Revises: mvp_data_minimization
Create Date: 2025-12-30

Module 2: Consent Capture Implementation
- Stores explicit patient consent before PHI processing
- Tracks granted/withdrawn status
- Immutable append-only records
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'add_patient_consent'
down_revision = 'mvp_data_minimization'
branch_labels = None
depends_on = None


def upgrade():
    """Create patient_consent table with required indexes."""
    
    # Create consent_status enum
    consent_status_enum = postgresql.ENUM('granted', 'withdrawn', name='consent_status')
    consent_status_enum.create(op.get_bind())
    
    # Create channel enum
    channel_enum = postgresql.ENUM('whatsapp', name='channel')
    channel_enum.create(op.get_bind())
    
    # Create patient_consent table
    op.create_table(
        'patient_consent',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('phone_number', sa.String(15), nullable=False),
        sa.Column('consent_text', sa.String(), nullable=False),
        sa.Column('consent_version', sa.String(50), nullable=False),
        sa.Column('consent_status', consent_status_enum, nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('channel', channel_enum, nullable=False, server_default='whatsapp'),
    )
    
    # Create indexes for fast consent checks
    op.create_index(
        'idx_phone_consent_status',
        'patient_consent',
        ['phone_number', 'consent_status']
    )
    
    op.create_index(
        'idx_phone_timestamp',
        'patient_consent',
        ['phone_number', 'timestamp']
    )


def downgrade():
    """Remove patient_consent table and enums."""
    
    # Drop indexes
    op.drop_index('idx_phone_timestamp', table_name='patient_consent')
    op.drop_index('idx_phone_consent_status', table_name='patient_consent')
    
    # Drop table
    op.drop_table('patient_consent')
    
    # Drop enums
    op.execute('DROP TYPE channel')
    op.execute('DROP TYPE consent_status')
