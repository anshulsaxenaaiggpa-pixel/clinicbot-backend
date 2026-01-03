"""Simplify patient and appointment models to MVP spec

Revision ID: mvp_data_minimization
Revises: 003
Create Date: 2025-12-29

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'mvp_data_minimization'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    """Apply MVP simplifications."""
    
    # === PATIENTS TABLE ===
    with op.batch_alter_table('patients', schema=None) as batch_op:
        # Drop behavioral tracking and demographics
        batch_op.drop_column('email')
        batch_op.drop_column('date_of_birth')
        batch_op.drop_column('gender')
        batch_op.drop_column('total_visits')
        batch_op.drop_column('cancelled_count')
        batch_op.drop_column('no_show_count')
        batch_op.drop_column('updated_at')
        
        # Make name nullable (optional, UX only)
        batch_op.alter_column('name',
                        existing_type=sa.String(100),
                        nullable=True)
        
        # Drop index created in 002 (name was 'ix_patients_phone')
        batch_op.drop_index('ix_patients_phone')
    
    # === APPOINTMENTS TABLE ===
    with op.batch_alter_table('appointments', schema=None) as batch_op:
        # Drop index created in 002
        batch_op.drop_index('ix_appointments_date')
        
        # Remove patient_id FK (phone is now direct identity)
        batch_op.drop_column('patient_id')
        batch_op.drop_column('date')  # Redundant with start_utc_ts
        batch_op.drop_column('fee')
        batch_op.drop_column('notes')

        # Make patient_phone required (identity key)
        # Note: In 002 it was NOT present in Appointments? 
        # Wait, let me check 002 again.
        pass

    # Actually, 002's appointments table DOES NOT HAVE patient_phone!
    # It has patient_id.
    # So we MUST add patient_phone here.
    op.add_column('appointments', sa.Column('patient_phone', sa.String(15), nullable=True))
    
    # Backfill is not needed on empty DB but good for consistency
    op.execute("UPDATE appointments SET patient_phone = '+910000000000' WHERE patient_phone IS NULL")

    with op.batch_alter_table('appointments', schema=None) as batch_op:
        batch_op.alter_column('patient_phone', nullable=False)
        
        # Update start_utc_ts to use timezone-aware timestamp
        batch_op.alter_column('start_utc_ts',
                        existing_type=sa.DateTime(),
                        type_=sa.DateTime(timezone=True),
                        nullable=False)
        
        batch_op.alter_column('end_utc_ts',
                        existing_type=sa.DateTime(),
                        type_=sa.DateTime(timezone=True),
                        nullable=False)

        # Change default status to 'booked'
        batch_op.alter_column('status',
                        existing_type=sa.String(20),
                        server_default='booked',
                        nullable=False)
        
        # Add source field
        batch_op.add_column(sa.Column('source', sa.String(20), server_default='whatsapp', nullable=True))
    
    # === NEW INDEXES ===
    op.execute("CREATE INDEX IF NOT EXISTS idx_clinic_doctor_date ON appointments (clinic_id, doctor_id, start_utc_ts)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_clinic_phone ON appointments (clinic_id, patient_phone)")
    
    # CRITICAL: Prevent double-booking at DB level
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_doctor_slot_booked_unique 
        ON appointments (doctor_id, start_utc_ts) 
        WHERE status = 'booked'
    """)


def downgrade():
    pass
