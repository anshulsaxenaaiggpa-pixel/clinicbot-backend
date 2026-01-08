"""add_city_and_is_searchable_to_doctors

Revision ID: f8971125cc97
Revises: 6304b58a20e7
Create Date: 2026-01-08 17:11:57.189227

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f8971125cc97'
down_revision = '6304b58a20e7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add city and is_searchable columns to doctors table if they don't exist."""
    
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('doctors')]
    
    # Add city column only if it doesn't exist
    if 'city' not in columns:
        op.add_column('doctors', 
            sa.Column('city', sa.String(100), nullable=True))
        print("✅ Added city column to doctors table")
    else:
        print("ℹ️ city column already exists, skipping")
    
    # Add is_searchable column only if it doesn't exist
    if 'is_searchable' not in columns:
        op.add_column('doctors',
            sa.Column('is_searchable', sa.Boolean(), nullable=True, server_default='false'))
        print("✅ Added is_searchable column to doctors table")
    else:
        print("ℹ️ is_searchable column already exists, skipping")



def downgrade() -> None:
    """Remove city and is_searchable columns from doctors table."""
    try:
        op.drop_column('doctors', 'is_searchable')
        print("✅ Removed is_searchable column from doctors table")
    except Exception as e:
        print(f"⚠️ Could not remove is_searchable column: {e}")
    
    try:
        op.drop_column('doctors', 'city')
        print("✅ Removed city column from doctors table")
    except Exception as e:
        print(f"⚠️ Could not remove city column: {e}")
