"""Add audit_log table - Module 4

Revision ID: add_audit_log
Revises: add_patient_deletion
Create Date: 2025-12-30

Module 4: Audit Logging Implementation
- Immutable event tracking
- All system actions logged
- Cannot be updated or deleted
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'add_audit_log'
down_revision = 'add_patient_deletion'
branch_labels = None
depends_on = None


def upgrade():
    """Create audit_log table with immutability rules."""
    
    op.create_table(
        'audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_id', sa.String(100), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('actor', sa.String(20), nullable=False),
        sa.Column('actor_id', sa.String(100), nullable=False),
        sa.Column('patient_phone_hash', sa.String(64), nullable=True),
        sa.Column('event_metadata', postgresql.JSONB, nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
    )
    
    # Indexes for fast queries
    op.create_index('idx_audit_event_type', 'audit_log', ['event_type'])
    op.create_index('idx_audit_actor', 'audit_log', ['actor', 'actor_id'])
    op.create_index('idx_audit_timestamp', 'audit_log', ['timestamp'])
    op.create_index('idx_audit_patient_hash', 'audit_log', ['patient_phone_hash'])
    
    # Make immutable (append-only)
    op.execute("""
        CREATE RULE audit_log_no_update AS 
        ON UPDATE TO audit_log DO INSTEAD NOTHING;
        
        CREATE RULE audit_log_no_delete AS 
        ON DELETE TO audit_log DO INSTEAD NOTHING;
    """)


def downgrade():
    """Remove audit_log table."""
    
    op.execute("DROP RULE audit_log_no_delete ON audit_log;")
    op.execute("DROP RULE audit_log_no_update ON audit_log;")
    
    op.drop_index('idx_audit_patient_hash', table_name='audit_log')
    op.drop_index('idx_audit_timestamp', table_name='audit_log')
    op.drop_index('idx_audit_actor', table_name='audit_log')
    op.drop_index('idx_audit_event_type', table_name='audit_log')
    op.drop_table('audit_log')
