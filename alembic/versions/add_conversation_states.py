"""Add conversation_states table - Booking State Machine

Revision ID: add_conversation_states
Revises: add_admin_users
Create Date: 2025-12-30

Manages WhatsApp booking conversation state (metadata only, no chat transcripts).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime, timedelta

revision = 'add_conversation_states'
down_revision = 'add_admin_users'
branch_labels = None
depends_on = None


def upgrade():
    """Create conversation_states table."""
    
    # Create booking_state enum
    booking_state_enum = postgresql.ENUM(
        'initial',
        'consent_pending',
        'age_verification',
        'clinic_selection',
        'doctor_selection',
        'service_selection',
        'date_selection',
        'time_selection',
        'confirmed',
        'cancelled',
        name='booking_state',
        create_type=True
    )
    booking_state_enum.create(op.get_bind())
    
    # Create conversation_states table
    op.create_table(
        'conversation_states',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('phone_number', sa.String(20), nullable=False, unique=True),
        sa.Column('current_state', booking_state_enum, nullable=False, server_default='initial'),
        sa.Column('context', postgresql.JSONB, nullable=True),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('consent_granted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('age_verified', sa.Boolean(), nullable=False, server_default='false'),
    )
    
    # Create indexes
    op.create_index('idx_conversation_phone', 'conversation_states', ['phone_number'])
    op.create_index('idx_conversation_state', 'conversation_states', ['current_state'])
    op.create_index('idx_conversation_expires', 'conversation_states', ['expires_at'])
    
    # Create cleanup function for expired states (run via cron)
    op.execute("""
        CREATE OR REPLACE FUNCTION cleanup_expired_conversations()
        RETURNS void AS $$
        BEGIN
            DELETE FROM conversation_states
            WHERE expires_at < NOW();
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade():
    """Remove conversation_states table."""
    op.execute("DROP FUNCTION IF EXISTS cleanup_expired_conversations();")
    op.drop_index('idx_conversation_expires', table_name='conversation_states')
    op.drop_index('idx_conversation_state', table_name='conversation_states')
    op.drop_index('idx_conversation_phone', table_name='conversation_states')
    op.drop_table('conversation_states')
    op.execute("DROP TYPE booking_state;")
