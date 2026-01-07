"""add_doctor_password_fields

Revision ID: 217e276ac601
Revises: bbb95cfbd844
Create Date: 2026-01-07 10:32:58.535474

Adds password_hash field to doctors table for authentication.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '217e276ac601'
down_revision = 'bbb95cfbd844'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add password_hash column (use try/except for SQLite compatibility)
    try:
        op.add_column('doctors', sa.Column('password_hash', sa.String(255), nullable=True))
        print("✅ Added password_hash to doctors table")
    except Exception as e:
        print(f"⚠️ password_hash column may already exist: {e}")


def downgrade() -> None:
    try:
        op.drop_column('doctors', 'password_hash')
    except Exception:
        pass
