"""Add doctors table - Hybrid Booking Support

Revision ID: add_doctors
Revises: add_conversation_states
Create Date: 2025-12-30

Stores doctor profiles for hybrid WhatsApp booking.
Privacy-first: doctors are private by default (is_searchable=False).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'add_doctors'
down_revision = 'add_conversation_states'
branch_labels = None
depends_on = None


def upgrade():
    """Create or update doctors table."""
    
    # Drop existing doctors table from Branch A (002) if it exists
    op.execute("DROP TABLE IF EXISTS doctors")
    
    op.create_table(
        'doctors',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('full_name', sa.String(100), nullable=False),
        sa.Column('specialty', sa.String(100), nullable=True),
        sa.Column('whatsapp_number', sa.String(20), nullable=False, unique=True),
        sa.Column('clinic_id', sa.String(100), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('is_searchable', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    
    # Create indexes
    op.create_index('idx_doctor_whatsapp', 'doctors', ['whatsapp_number'])
    op.create_index('idx_doctor_searchable', 'doctors', ['is_searchable', 'city'])
    op.create_index('idx_doctor_active', 'doctors', ['is_active'])


def downgrade():
    """Remove doctors table."""
    op.drop_index('idx_doctor_active', table_name='doctors')
    op.drop_index('idx_doctor_searchable', table_name='doctors')
    op.drop_index('idx_doctor_whatsapp', table_name='doctors')
    op.drop_table('doctors')
