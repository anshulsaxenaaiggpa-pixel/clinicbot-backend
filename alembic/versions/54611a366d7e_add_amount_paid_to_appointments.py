"""add_amount_paid_to_appointments

Revision ID: 54611a366d7e
Revises: b743960d0114
Create Date: 2025-12-31 22:30:29.653111

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '54611a366d7e'
down_revision = 'b743960d0114'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add amount_paid to appointments table (only if not exists)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('appointments')]
    if 'amount_paid' not in columns:
        op.add_column('appointments', sa.Column('amount_paid', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    pass
