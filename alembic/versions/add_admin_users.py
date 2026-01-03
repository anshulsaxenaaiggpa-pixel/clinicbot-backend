"""Add admin_users table - Sprint Task 1

Revision ID: add_admin_users
Revises: add_audit_log
Create Date: 2025-12-30

Admin authentication with RBAC and MFA support.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'add_admin_users'
down_revision = 'add_audit_log'
branch_labels = None
depends_on = None


def upgrade():
    """Create admin_users table with security features."""
    
    # Create admin_users table
    op.create_table(
        'admin_users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(100), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('mfa_secret', sa.String(32), nullable=True),
        sa.Column('mfa_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('password_last_changed', sa.DateTime(timezone=True), nullable=False),
        sa.Column('must_change_password', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login_ip', sa.String(45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    
    # Create indexes
    op.create_index('idx_admin_email', 'admin_users', ['email'])
    op.create_index('idx_admin_role', 'admin_users', ['role'])
    op.create_index('idx_admin_active', 'admin_users', ['is_active'])


def downgrade():
    """Remove admin_users table."""
    op.drop_index('idx_admin_active', table_name='admin_users')
    op.drop_index('idx_admin_role', table_name='admin_users')
    op.drop_index('idx_admin_email', table_name='admin_users')
    op.drop_table('admin_users')
    
    # Drop enum
    op.execute("DROP TYPE admin_role;")
