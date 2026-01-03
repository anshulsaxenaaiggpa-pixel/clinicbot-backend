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
    """Add hybrid booking fields already handled in add_doctors."""
    pass


def downgrade():
    """Remove hybrid booking fields."""
    op.drop_index('idx_doctor_city_search', table_name='doctors')
    op.drop_index('idx_doctor_whatsapp_hybrid', table_name='doctors')
    op.drop_column('doctors', 'is_searchable')
    op.drop_column('doctors', 'city')
    op.drop_column('doctors', 'whatsapp_number')
