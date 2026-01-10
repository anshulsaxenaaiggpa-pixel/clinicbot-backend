"""merge_directory_and_stripe

Revision ID: 5bc067e9c91e
Revises: 4fcc74c58176, abc123456789
Create Date: 2026-01-10 21:53:47.548477

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5bc067e9c91e'
down_revision = ('4fcc74c58176', 'abc123456789')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
