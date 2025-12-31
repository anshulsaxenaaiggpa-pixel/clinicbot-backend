"""Add hybrid booking fields to doctors table

Revision ID: add_doctor_hybrid_fields
Revises: add_doctors
Create Date: 2025-12-30

Adds WhatsApp number, city, and is_searchable for hybrid booking.
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_doctor_hybrid_fields'
down_revision = 'add_conversation_states'
branch_labels = None
depends_on = None


def upgrade():
    """Add hybrid booking fields to existing doctors table."""
    
    # Add new columns
    op.add_column('doctors', sa.Column('whatsapp_number', sa.String(20), nullable=True, unique=True))
    op.add_column('doctors', sa.Column('city', sa.String(100), nullable=True))
    op.add_column('doctors', sa.Column('is_searchable', sa.Boolean(), nullable=False, server_default='false'))
    
    # Add indexes for hybrid booking
    op.create_index('idx_doctor_whatsapp_hybrid', 'doctors', ['whatsapp_number'])
    op.create_index('idx_doctor_city_search', 'doctors', ['is_searchable', 'city'])


def downgrade():
    """Remove hybrid booking fields."""
    op.drop_index('idx_doctor_city_search', table_name='doctors')
    op.drop_index('idx_doctor_whatsapp_hybrid', table_name='doctors')
    op.drop_column('doctors', 'is_searchable')
    op.drop_column('doctors', 'city')
    op.drop_column('doctors', 'whatsapp_number')
