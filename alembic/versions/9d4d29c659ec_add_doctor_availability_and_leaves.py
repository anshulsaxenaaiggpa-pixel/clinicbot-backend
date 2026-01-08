"""add_doctor_availability_and_leaves

Revision ID: 9d4d29c659ec
Revises: f8971125cc97
Create Date: 2026-01-09 01:47:58.920700

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9d4d29c659ec'
down_revision = 'f8971125cc97'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create doctor_availability table
    op.create_table(
        'doctor_availability',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('doctor_id', sa.UUID(), nullable=False),
        sa.Column('day_of_week', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id'], ondelete='CASCADE')
    )
    
    # Create doctor_leaves table
    op.create_table(
        'doctor_leaves',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('doctor_id', sa.UUID(), nullable=False),
        sa.Column('leave_date', sa.Date(), nullable=False),
        sa.Column('reason', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id'], ondelete='CASCADE')
    )
    
    # Create indexes
    op.create_index('ix_doctor_availability_doctor_id', 'doctor_availability', ['doctor_id'])
    op.create_index('ix_doctor_leaves_doctor_id', 'doctor_leaves', ['doctor_id'])


def downgrade() -> None:
    op.drop_index('ix_doctor_leaves_doctor_id', table_name='doctor_leaves')
    op.drop_index('ix_doctor_availability_doctor_id', table_name='doctor_availability')
    op.drop_table('doctor_leaves')
    op.drop_table('doctor_availability')
