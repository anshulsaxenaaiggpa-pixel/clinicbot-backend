"""add_patient_name_to_appointments

Revision ID: b743960d0114
Revises: 0e4dac089749
Create Date: 2025-12-31 20:54:06.704795

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b743960d0114'
down_revision = '0e4dac089749'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add patient_name to appointments table (only if not exists)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('appointments')]
    if 'patient_name' not in columns:
        op.add_column('appointments', sa.Column('patient_name', sa.String(length=100), nullable=True))


def downgrade() -> None:
    # Remove patient_name from appointments table
    with op.batch_alter_table('appointments', schema=None) as batch_op:
        batch_op.drop_column('patient_name')
