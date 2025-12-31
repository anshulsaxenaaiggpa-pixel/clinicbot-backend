"""Simplify patient and appointment models to MVP spec

Revision ID: mvp_data_minimization
Revises: 
Create Date: 2025-12-29

Changes:
1. Drop unnecessary patient fields (email, DOB, gender, whatsapp_name, behavioral counts)
2. Simplify appointment statuses to 4 values (booked/cancelled/no_show/completed)
3. Remove patient_id FK from appointments (phone is now direct identity)
4. Add critical double-booking constraint
5. Update indexes for tenant isolation

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'mvp_data_minimization'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Apply MVP simplifications."""
    
    # === PATIENTS TABLE ===
    # Drop behavioral tracking and demographics
    op.drop_column('patients', 'email')
    op.drop_column('patients', 'date_of_birth')
    op.drop_column('patients', 'gender')
    op.drop_column('patients', 'whatsapp_name')
    op.drop_column('patients', 'total_visits')
    op.drop_column('patients', 'cancelled_count')
    op.drop_column('patients', 'no_show_count')
    op.drop_column('patients', 'updated_at')
    
    # Make name nullable (optional, UX only)
    op.alter_column('patients', 'name',
                    existing_type=sa.String(100),
                    nullable=True)
    
    # Drop unnecessary index
    op.drop_index('idx_patient_phone', table_name='patients')
    
    # === APPOINTMENTS TABLE ===
    # Drop old indexes
    op.drop_index('idx_doctor_date', table_name='appointments')
    op.drop_index('idx_clinic_date', table_name='appointments')
    
    # Remove patient_id FK (phone is now direct identity)
    op.drop_constraint('appointments_patient_id_fkey', 'appointments', type_='foreignkey')
    op.drop_column('appointments', 'patient_id')
    
    # Drop unnecessary fields
    op.drop_column('appointments', 'patient_notes')
    op.drop_column('appointments', 'date')  # Redundant with start_utc_ts
    op.drop_column('appointments', 'fee')
    op.drop_column('appointments', 'notes')
    
    # Make patient_phone required (identity key)
    op.alter_column('appointments', 'patient_phone',
                    existing_type=sa.String(),
                    type_=sa.String(15),
                    nullable=False)
    
    # Update start_utc_ts to use timezone-aware timestamp
    op.alter_column('appointments', 'start_utc_ts',
                    existing_type=sa.DateTime(),
                    type_=sa.DateTime(timezone=True),
                    nullable=False)
    
    op.alter_column('appointments', 'end_utc_ts',
                    existing_type=sa.DateTime(),
                    type_=sa.DateTime(timezone=True),
                    nullable=False)
    
    # Migrate status values to 4-value enum
    # confirmed/booked → booked
    # cancelled/late_cancelled/clinic_cancelled → cancelled
    # no_show → no_show
    # completed → completed
    op.execute("""
        UPDATE appointments 
        SET status = 
            CASE 
                WHEN status IN ('confirmed', 'booked', 'slot_held') THEN 'booked'
                WHEN status IN ('cancelled', 'late_cancelled', 'clinic_cancelled') THEN 'cancelled'
                WHEN status = 'no_show' THEN 'no_show'
                WHEN status = 'completed' THEN 'completed'
                ELSE 'booked'  -- Default for unknown statuses
            END
    """)
    
    # Change default status to 'booked'
    op.alter_column('appointments', 'status',
                    existing_type=sa.String(20),
                    server_default='booked',
                    nullable=False)
    
    # Add source field
    op.add_column('appointments', 
                  sa.Column('source', sa.String(20), server_default='whatsapp', nullable=True))
    
    # === NEW INDEXES (tenant isolation + double-booking prevention) ===
    # Tenant isolation indexes (clinic_id first)
    op.create_index('idx_clinic_doctor_date', 'appointments', 
                    ['clinic_id', 'doctor_id', 'start_utc_ts'])
    op.create_index('idx_clinic_phone', 'appointments', 
                    ['clinic_id', 'patient_phone'])
    
    # CRITICAL: Prevent double-booking at DB level
    # Partial unique index: only one 'booked' appointment per doctor per slot
    op.create_index(
        'idx_doctor_slot_booked_unique',
        'appointments',
        ['doctor_id', 'start_utc_ts'],
        unique=True,
        postgresql_where=sa.text("status = 'booked'")
    )


def downgrade():
    """Revert MVP simplifications (for testing only - not safe in production)."""
    
    # WARNING: This will lose data. Only use in development/testing.
    
    # === APPOINTMENTS TABLE ===
    op.drop_index('idx_doctor_slot_booked_unique', table_name='appointments')
    op.drop_index('idx_clinic_phone', table_name='appointments')
    op.drop_index('idx_clinic_doctor_date', table_name='appointments')
    
    op.drop_column('appointments', 'source')
    
    # Restore old indexes
    op.create_index('idx_clinic_date', 'appointments', ['clinic_id', 'date'])
    op.create_index('idx_doctor_date', 'appointments', ['doctor_id', 'date'])
    
    # Restore dropped columns (data will be NULL)
    op.add_column('appointments', sa.Column('patient_id', postgresql.UUID(), nullable=True))
    op.add_column('appointments', sa.Column('patient_notes', sa.String(), nullable=True))
    op.add_column('appointments', sa.Column('date', sa.Date(), nullable=True))
    op.add_column('appointments', sa.Column('fee', sa.Integer(), nullable=True))
    op.add_column('appointments', sa.Column('notes', sa.String(), nullable=True))
    
    # Restore FK
    op.create_foreign_key('appointments_patient_id_fkey', 'appointments', 'patients', 
                          ['patient_id'], ['id'])
    
    # === PATIENTS TABLE ===
    op.create_index('idx_patient_phone', 'patients', ['phone'])
    
    # Restore dropped columns (data will be NULL)
    op.add_column('patients', sa.Column('email', sa.String(100), nullable=True))
    op.add_column('patients', sa.Column('date_of_birth', sa.DateTime(), nullable=True))
    op.add_column('patients', sa.Column('gender', sa.String(10), nullable=True))
    op.add_column('patients', sa.Column('whatsapp_name', sa.String(100), nullable=True))
    op.add_column('patients', sa.Column('total_visits', sa.Integer(), server_default='0'))
    op.add_column('patients', sa.Column('cancelled_count', sa.Integer(), server_default='0'))
    op.add_column('patients', sa.Column('no_show_count', sa.Integer(), server_default='0'))
    op.add_column('patients', sa.Column('updated_at', sa.DateTime(timezone=True), 
                                        server_default=sa.text('NOW()')))
    
    op.alter_column('patients', 'name', nullable=False)
