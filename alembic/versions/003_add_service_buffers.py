"""Add buffer minutes to services

Revision ID: 003
Revises: 002
Create Date: 2025-12-18 16:40:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Buffer columns already created in 002_add_whatsapp_config.py
    pass


def downgrade() -> None:
    op.drop_column("services", "after_buffer_mins")
    op.drop_column("services", "before_buffer_mins")
