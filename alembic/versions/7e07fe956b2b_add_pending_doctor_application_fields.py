"""add_pending_doctor_application_fields

Revision ID: 7e07fe956b2b
Revises: 9d4d29c659ec
Create Date: 2026-01-10 15:59:22.603507

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7e07fe956b2b'
down_revision = '9d4d29c659ec'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add pending application fields to doctors table
    op.add_column('doctors', sa.Column('pending_status', sa.String(20), nullable=False, server_default='approved'))
    op.add_column('doctors', sa.Column('application_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('doctors', sa.Column('approval_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('doctors', sa.Column('rejected_reason', sa.String(500), nullable=True))
    op.add_column('doctors', sa.Column('whatsapp_link', sa.String(200), nullable=True))
    op.add_column('doctors', sa.Column('qr_code_path', sa.String(200), nullable=True))
    op.add_column('doctors', sa.Column('expected_patients', sa.Integer, nullable=True))
    
    # Create index for fast filtering of pending applications
    op.create_index('idx_pending_status', 'doctors', ['pending_status'])


def downgrade() -> None:
    pass
