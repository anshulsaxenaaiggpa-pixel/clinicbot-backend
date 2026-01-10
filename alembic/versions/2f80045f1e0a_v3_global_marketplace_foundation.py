"""v3_global_marketplace_foundation

Revision ID: 2f80045f1e0a
Revises: 5bc067e9c91e
Create Date: 2026-01-11 02:34:17.112351

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2f80045f1e0a'
down_revision = '5bc067e9c91e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create countries reference table
    op.create_table('countries',
        sa.Column('code', sa.String(2), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('currency_symbol', sa.String(10), nullable=False),
        sa.Column('payment_provider', sa.String(20), nullable=False),
        sa.Column('language', sa.String(5), server_default='en'),
        sa.Column('is_active', sa.Boolean(), server_default='true')
    )
    
    # Seed initial countries
    op.execute("""
        INSERT INTO countries (code, name, currency, currency_symbol, payment_provider, language) VALUES
        ('IN', 'India', 'INR', '₹', 'razorpay', 'en'),
        ('US', 'United States', 'USD', '$', 'stripe', 'en'),
        ('AE', 'United Arab Emirates', 'AED', 'د.إ', 'stripe', 'ar'),
        ('GB', 'United Kingdom', 'GBP', '£', 'stripe', 'en'),
        ('AU', 'Australia', 'AUD', 'A$', 'stripe', 'en'),
        ('EU', 'European Union', 'EUR', '€', 'stripe', 'en')
    """)
    
    # Create subscription_plans table
    op.create_table('subscription_plans',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tier', sa.String(20), unique=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('monthly_price_inr', sa.Integer(), nullable=False),
        sa.Column('monthly_price_usd', sa.Integer(), nullable=False),
        sa.Column('whatsapp_quota', sa.Integer(), nullable=False),
        sa.Column('stripe_price_id_inr', sa.String(100), nullable=True),
        sa.Column('stripe_price_id_usd', sa.String(100), nullable=True),
        sa.Column('features', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    
    # Seed subscription plans
    op.execute("""
        INSERT INTO subscription_plans (id, tier, name, monthly_price_inr, monthly_price_usd, whatsapp_quota, features) VALUES
        ('plan-starter', 'starter', 'Starter', 1999, 25, 0, '{"web_booking": true, "qr_code": true, "basic_analytics": true}'),
        ('plan-growth', 'growth', 'Growth', 3999, 50, 200, '{"whatsapp": 200, "advanced_analytics": true, "priority_support": false}'),
        ('plan-enterprise', 'enterprise', 'Enterprise', 7499, 95, 999999, '{"whatsapp": "unlimited", "priority_support": true, "custom_branding": true}')
    """)
    
    # Add global marketplace fields to doctors table
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('doctors')]
    
    if 'country_code' not in existing_columns:
        op.add_column('doctors', sa.Column('country_code', sa.String(2), server_default='IN'))
    
    if 'currency_code' not in existing_columns:
        op.add_column('doctors', sa.Column('currency_code', sa.String(3), server_default='INR'))
    
    if 'vpa' not in existing_columns:
        op.add_column('doctors', sa.Column('vpa', sa.String(100), nullable=True))  # UPI for India
    
    if 'convenience_fee_pct' not in existing_columns:
        op.add_column('doctors', sa.Column('convenience_fee_pct', sa.Numeric(5, 2), server_default='0.00'))
    
    if 'subscription_plan_id' not in existing_columns:
        op.add_column('doctors', sa.Column('subscription_plan_id', sa.String(36), nullable=True))
    
    if 'subscription_status' not in existing_columns:
        op.add_column('doctors', sa.Column('subscription_status', sa.String(20), server_default='trial'))
    
    if 'subscription_started_at' not in existing_columns:
        op.add_column('doctors', sa.Column('subscription_started_at', sa.DateTime(), nullable=True))
    
    if 'subscription_ends_at' not in existing_columns:
        op.add_column('doctors', sa.Column('subscription_ends_at', sa.DateTime(), nullable=True))
    
    if 'stripe_subscription_id' not in existing_columns:
        op.add_column('doctors', sa.Column('stripe_subscription_id', sa.String(100), nullable=True))
    
    if 'slug' not in existing_columns:
        op.add_column('doctors', sa.Column('slug', sa.String(100), nullable=True, unique=True))
    
    if 'photo_url' not in existing_columns:
        op.add_column('doctors', sa.Column('photo_url', sa.String(500), nullable=True))
    
    if 'bio' not in existing_columns:
        op.add_column('doctors', sa.Column('bio', sa.Text(), nullable=True))
    
    if 'languages' not in existing_columns:
        op.add_column('doctors', sa.Column('languages', sa.JSON(), server_default='["English"]'))
    
    if 'rating_average' not in existing_columns:
        op.add_column('doctors', sa.Column('rating_average', sa.Numeric(3, 2), server_default='0.00'))
    
    if 'review_count' not in existing_columns:
        op.add_column('doctors', sa.Column('review_count', sa.Integer(), server_default='0'))
    
    # Update existing doctors to have default subscription (starter trial)
    op.execute("""
        UPDATE doctors 
        SET subscription_plan_id = 'plan-starter', 
            subscription_status = 'trial',
            subscription_started_at = CURRENT_TIMESTAMP,
            subscription_ends_at = CURRENT_TIMESTAMP + INTERVAL '7 days'
        WHERE subscription_plan_id IS NULL
    """)


def downgrade() -> None:
    # Remove added columns from doctors table
    op.drop_column('doctors', 'review_count')
    op.drop_column('doctors', 'rating_average')
    op.drop_column('doctors', 'languages')
    op.drop_column('doctors', 'bio')
    op.drop_column('doctors', 'photo_url')
    op.drop_column('doctors', 'slug')
    op.drop_column('doctors', 'stripe_subscription_id')
    op.drop_column('doctors', 'subscription_ends_at')
    op.drop_column('doctors', 'subscription_started_at')
    op.drop_column('doctors', 'subscription_status')
    op.drop_column('doctors', 'subscription_plan_id')
    op.drop_column('doctors', 'convenience_fee_pct')
    op.drop_column('doctors', 'vpa')
    op.drop_column('doctors', 'currency_code')
    op.drop_column('doctors', 'country_code')
    
    # Drop tables
    op.drop_table('subscription_plans')
    op.drop_table('countries')
