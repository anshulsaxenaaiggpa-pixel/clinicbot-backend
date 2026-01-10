"""add_city_specialty_directory_fields

Revision ID: 7864a8163c76
Revises: 7e07fe956b2b
Create Date: 2026-01-10 20:14:15.123456

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7864a8163c76'
down_revision = '7e07fe956b2b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add directory and search fields to doctors table
    op.add_column('doctors', sa.Column('specialty_primary', sa.String(100), nullable=True))
    op.add_column('doctors', sa.Column('area_locality', sa.String(100), nullable=True))
    op.add_column('doctors', sa.Column('registration_no', sa.String(50), nullable=True))
    op.add_column('doctors', sa.Column('google_rating', sa.Numeric(3, 2), nullable=True))
    op.add_column('doctors', sa.Column('clinic_name', sa.String(200), nullable=True))
    
    # Create composite index for fast city + specialty searches
    op.create_index('idx_city_specialty', 'doctors', ['city', 'specialty_primary'])


def downgrade() -> None:
    op.drop_index('idx_city_specialty', 'doctors')
    op.drop_column('doctors', 'clinic_name')
    op.drop_column('doctors', 'google_rating')
    op.drop_column('doctors', 'registration_no')
    op.drop_column('doctors', 'area_locality')
    op.drop_column('doctors', 'specialty_primary')
