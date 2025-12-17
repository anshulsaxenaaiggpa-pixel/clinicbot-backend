"""Reset and recreate schema with whatsapp_config

Revision ID: 002
Revises: 001
Create Date: 2025-12-17 20:53:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop all tables in reverse dependency order
    op.drop_table('conversations')
    op.drop_table('appointments')
    op.drop_table('clinic_timings')
    op.drop_table('patients')
    op.drop_table('services')
    op.drop_table('doctors')
    op.drop_table('clinics')
    
    # Recreate clinics table with whatsapp_config
    op.create_table('clinics',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('owner_name', sa.String(), nullable=False),
    sa.Column('address', sa.String(), nullable=True),
    sa.Column('city', sa.String(), nullable=True),
    sa.Column('timezone', sa.String(), nullable=False),
    sa.Column('whatsapp_number', sa.String(), nullable=False),
    sa.Column('subscription_tier', sa.String(), nullable=False),
    sa.Column('subscription_status', sa.String(), nullable=False),
    sa.Column('trial_ends_at', sa.DateTime(), nullable=True),
    sa.Column('whatsapp_provider', sa.String(), nullable=False),
    sa.Column('whatsapp_config', sa.JSON(), nullable=True),
    sa.Column('api_key', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('whatsapp_number'),
    sa.UniqueConstraint('api_key')
    )
    op.create_index(op.f('ix_clinics_id'), 'clinics', ['id'], unique=False)

    # Recreate other tables
    op.create_table('doctors',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('clinic_id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('specialization', sa.String(), nullable=True),
    sa.Column('default_fee', sa.Float(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_doctors_id'), 'doctors', ['id'], unique=False)

    op.create_table('services',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('clinic_id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('type', sa.String(), nullable=False),
    sa.Column('duration_minutes', sa.Integer(), nullable=False),
    sa.Column('required_slots', sa.Integer(), nullable=False),
    sa.Column('default_fee', sa.Float(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_services_id'), 'services', ['id'], unique=False)

    op.create_table('patients',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('clinic_id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('phone', sa.String(), nullable=False),
    sa.Column('email', sa.String(), nullable=True),
    sa.Column('date_of_birth', sa.Date(), nullable=True),
    sa.Column('gender', sa.String(), nullable=True),
    sa.Column('total_visits', sa.Integer(), nullable=False),
    sa.Column('cancelled_count', sa.Integer(), nullable=False),
    sa.Column('no_show_count', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_patients_id'), 'patients', ['id'], unique=False)
    op.create_index(op.f('ix_patients_phone'), 'patients', ['phone'], unique=False)

    op.create_table('clinic_timings',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('clinic_id', sa.String(), nullable=False),
    sa.Column('day_of_week', sa.Integer(), nullable=False),
    sa.Column('start_time', sa.Time(), nullable=False),
    sa.Column('end_time', sa.Time(), nullable=False),
    sa.Column('slot_duration_minutes', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('appointments',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('clinic_id', sa.String(), nullable=False),
    sa.Column('patient_id', sa.String(), nullable=False),
    sa.Column('doctor_id', sa.String(), nullable=True),
    sa.Column('service_id', sa.String(), nullable=True),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('start_utc_ts', sa.DateTime(), nullable=False),
    sa.Column('end_utc_ts', sa.DateTime(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('fee', sa.Float(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('cancellation_reason', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ),
    sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.ForeignKeyConstraint(['service_id'], ['services.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_appointments_date'), 'appointments', ['date'], unique=False)
    op.create_index(op.f('ix_appointments_id'), 'appointments', ['id'], unique=False)

    op.create_table('conversations',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('clinic_id', sa.String(), nullable=False),
    sa.Column('patient_id', sa.String(), nullable=True),
    sa.Column('phone_number', sa.String(), nullable=False),
    sa.Column('current_step', sa.String(), nullable=False),
    sa.Column('context', sa.JSON(), nullable=True),
    sa.Column('last_message_at', sa.DateTime(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conversations_id'), 'conversations', ['id'], unique=False)


def downgrade() -> None:
    # Revert to 001 schema (without whatsapp_config)
    pass
