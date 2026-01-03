"""Add patient_deletion_log table - Module 3

Revision ID: add_patient_deletion
Revises: add_patient_consent
Create Date: 2025-12-30

Module 3: Data Deletion Implementation
- Tracks deletion requests
- Prevents ghost recreation
- Immutable audit trail
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'add_patient_deletion'
down_revision = 'add_patient_consent'
branch_labels = None
depends_on = None


def upgrade():
    """Create patient_deletion_log table."""
    
    op.create_table(
        'patient_deletion_log',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('phone_number', sa.String(15), nullable=False),
        sa.Column('deletion_requested_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deletion_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deletion_status', sa.String(20), nullable=False),
        sa.Column('patient_records_deleted', sa.Integer(), server_default='0'),
        sa.Column('appointment_records_deleted', sa.Integer(), server_default='0'),
        sa.Column('consent_records_deleted', sa.Integer(), server_default='0'),
        sa.Column('requested_by', sa.String(20), nullable=False),
        sa.Column('verification_method', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    
    # Indexes
    op.create_index('idx_deletion_phone', 'patient_deletion_log', ['phone_number'])
    op.create_index('idx_deletion_status', 'patient_deletion_log', ['deletion_status'])
    
    # Make immutable (append-only) - PostgreSQL only
    if op.get_bind().dialect.name == 'postgresql':
        op.execute("""
            CREATE RULE patient_deletion_log_no_update AS 
            ON UPDATE TO patient_deletion_log DO INSTEAD NOTHING;
            
            CREATE RULE patient_deletion_log_no_delete AS 
            ON DELETE TO patient_deletion_log DO INSTEAD NOTHING;
        """)


def downgrade():
    """Remove patient_deletion_log table."""
    
    op.execute("DROP RULE patient_deletion_log_no_delete ON patient_deletion_log;")
    op.execute("DROP RULE patient_deletion_log_no_update ON patient_deletion_log;")
    
    op.drop_index('idx_deletion_status', table_name='patient_deletion_log')
    op.drop_index('idx_deletion_phone', table_name='patient_deletion_log')
    op.drop_table('patient_deletion_log')
