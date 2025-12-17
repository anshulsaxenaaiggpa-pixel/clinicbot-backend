"""Initial migration - create all tables"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# Revision identifiers
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create clinics table
    op.create_table(
        'clinics',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('owner_name', sa.String(80)),
        sa.Column('address', sa.String(200)),
        sa.Column('city', sa.String(50)),
        sa.Column('timezone', sa.String(50), server_default='Asia/Kolkata'),
        sa.Column('whatsapp_number', sa.String(15), unique=True, nullable=False),
        sa.Column('subscription_tier', sa.String(20), server_default='starter'),
        sa.Column('subscription_status', sa.String(20), server_default='trial'),
        sa.Column('trial_ends_at', sa.DateTime(timezone=True)),
        sa.Column('whatsapp_provider', sa.String(20)),
        sa.Column('whatsapp_config', sa.JSON),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('is_active', sa.Boolean, server_default='true')
    )
    
    # Create doctors table
    op.create_table(
        'doctors',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('clinic_id', UUID(as_uuid=True), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('name', sa.String(80), nullable=False),
        sa.Column('specialization', sa.String(50)),
        sa.Column('default_fee', sa.Integer),
        sa.Column('custom_availability', sa.JSON),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    
    # Create services table
    op.create_table(
        'services',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('clinic_id', UUID(as_uuid=True), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('type', sa.String(20)),
        sa.Column('duration_minutes', sa.Integer, nullable=False),
        sa.Column('required_slots', sa.Integer, nullable=False),
        sa.Column('default_fee', sa.Integer, nullable=False),
        sa.Column('before_buffer_mins', sa.Integer, server_default='0'),
        sa.Column('after_buffer_mins', sa.Integer, server_default='0'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    
    # Create appointments table
    op.create_table(
        'appointments',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('clinic_id', UUID(as_uuid=True), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('doctor_id', UUID(as_uuid=True), sa.ForeignKey('doctors.id'), nullable=False),
        sa.Column('service_id', UUID(as_uuid=True), sa.ForeignKey('services.id'), nullable=False),
        sa.Column('patient_name', sa.String(100), nullable=False),
        sa.Column('patient_phone', sa.String(15), nullable=False),
        sa.Column('patient_notes', sa.String(500)),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('start_utc_ts', sa.BigInteger, nullable=False),
        sa.Column('end_utc_ts', sa.BigInteger, nullable=False),
        sa.Column('status', sa.String(20), server_default='confirmed'),
        sa.Column('created_via', sa.String(20), server_default='whatsapp'),
        sa.Column('payment_status', sa.String(20), server_default='pending'),
        sa.Column('amount_paid', sa.Integer),
        sa.Column('reminder_24h_sent', sa.DateTime(timezone=True)),
        sa.Column('reminder_2h_sent', sa.DateTime(timezone=True)),
        sa.Column('followup_sent', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'))
    )
    
    # Create indexes
    op.create_index('idx_doctor_date', 'appointments', ['doctor_id', 'date'])
    op.create_index('idx_clinic_date', 'appointments', ['clinic_id', 'date'])
    op.create_index('idx_patient_phone', 'appointments', ['patient_phone'])
    
    # Create clinic_timing table
    op.create_table(
        'clinic_timing',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('clinic_id', UUID(as_uuid=True), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('day_of_week', sa.String(10), nullable=False),
        sa.Column('is_closed', sa.Boolean, server_default='false'),
        sa.Column('start_time', sa.Time),
        sa.Column('end_time', sa.Time),
        sa.Column('lunch_enabled', sa.Boolean, server_default='false'),
        sa.Column('lunch_start', sa.Time),
        sa.Column('lunch_end', sa.Time)
    )
    
    # Create closed_dates table
    op.create_table(
        'closed_dates',
        sa.Column('clinic_id', UUID(as_uuid=True), sa.ForeignKey('clinics.id'), primary_key=True),
        sa.Column('closed_date', sa.Date, primary_key=True),
        sa.Column('reason', sa.String(100))
    )
    
    # Create doctor_services junction table
    op.create_table(
        'doctor_services',
        sa.Column('doctor_id', UUID(as_uuid=True), sa.ForeignKey('doctors.id'), primary_key=True),
        sa.Column('service_id', UUID(as_uuid=True), sa.ForeignKey('services.id'), primary_key=True),
        sa.Column('custom_fee', sa.Integer)
    )


def downgrade():
    op.drop_table('doctor_services')
    op.drop_table('closed_dates')
    op.drop_table('clinic_timing')
    op.drop_index('idx_patient_phone', 'appointments')
    op.drop_index('idx_clinic_date', 'appointments')
    op.drop_index('idx_doctor_date', 'appointments')
    op.drop_table('appointments')
    op.drop_table('services')
    op.drop_table('doctors')
    op.drop_table('clinics')
