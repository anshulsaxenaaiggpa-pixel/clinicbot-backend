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
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    if 'audit_log' in tables:
        # If it exists, it might be the old schema from a previous build.
        # Safe to drop and recreate for this MVP phase.
        op.drop_table('audit_log')

    op.create_table(
        'audit_log',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('clinic_id', sa.String(36), nullable=False),
        sa.Column('actor_type', sa.String(20), nullable=False),
        sa.Column('actor_reference', sa.String(100), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', sa.String(36), nullable=True),
        sa.Column('old_state', sa.JSON, nullable=True),
        sa.Column('new_state', sa.JSON, nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ip_address', sa.String(50), nullable=True),
    )
    
    # Indexes for fast queries
    op.create_index('idx_audit_clinic_timestamp', 'audit_log', ['clinic_id', 'timestamp'])
    op.create_index('idx_audit_action', 'audit_log', ['action'])
    op.create_index('idx_audit_entity', 'audit_log', ['entity_type', 'entity_id'])
    
    # Make immutable (append-only) - PostgreSQL only
    if op.get_bind().dialect.name == 'postgresql':
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
    
    op.drop_index('idx_audit_entity', table_name='audit_log')
    op.drop_index('idx_audit_action', table_name='audit_log')
    op.drop_index('idx_audit_clinic_timestamp', table_name='audit_log')
    op.drop_table('audit_log')
