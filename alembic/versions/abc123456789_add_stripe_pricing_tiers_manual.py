"""add_stripe_pricing_tiers_manual

Revision ID: abc123456789
Revises: 7864a8163c76
Create Date: 2026-01-10 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'abc123456789'
down_revision = '7864a8163c76'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add Stripe and pricing tier fields to doctors table
    op.add_column('doctors', sa.Column('stripe_account_id', sa.String(100), nullable=True))
    op.add_column('doctors', sa.Column('stripe_customer_id', sa.String(100), nullable=True))
    op.add_column('doctors', sa.Column('whatsapp_limit', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('doctors', sa.Column('whatsapp_used', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('doctors', sa.Column('plan_tier', sa.String(20), nullable=False, server_default="'starter'"))


def downgrade() -> None:
    op.drop_column('doctors', 'plan_tier')
    op.drop_column('doctors', 'whatsapp_used')
    op.drop_column('doctors', 'whatsapp_limit')
    op.drop_column('doctors', 'stripe_customer_id')
    op.drop_column('doctors', 'stripe_account_id')
