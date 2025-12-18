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
    # Add buffer columns with server defaults for existing rows
    op.add_column(
        "services",
        sa.Column(
            "before_buffer_mins",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "services",
        sa.Column(
            "after_buffer_mins",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("services", "after_buffer_mins")
    op.drop_column("services", "before_buffer_mins")
