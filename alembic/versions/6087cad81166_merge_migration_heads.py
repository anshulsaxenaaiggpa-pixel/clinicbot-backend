"""merge_migration_heads

Revision ID: 6087cad81166
Revises: 003, add_doctor_hybrid_fields, add_doctors
Create Date: 2025-12-31 12:29:51.288119

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6087cad81166'
down_revision = ('add_doctor_hybrid_fields', 'add_doctors')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
