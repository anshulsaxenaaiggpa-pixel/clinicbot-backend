"""Appointment database model - MVP SPEC"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.base_class import Base


class Appointment(Base):
    """
    Patient appointment booking.
    
    Critical constraint: UNIQUE(doctor_id, start_utc_ts, status='booked')
    This prevents double-booking at the database level.
    """
    __tablename__ = "appointments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id = Column(UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=False)
    service_id = Column(UUID(as_uuid=True), ForeignKey("services.id"), nullable=False)
    
    # Patient information (denormalized for performance and outage safety)
    patient_phone = Column(String(15), nullable=False)  # IDENTITY KEY
    patient_name = Column(String(100), nullable=True)   # UX only, optional
    
    # Scheduling (UTC timestamps)
    start_utc_ts = Column(DateTime(timezone=True), nullable=False)
    end_utc_ts = Column(DateTime(timezone=True), nullable=False)
    
    # Status tracking - ONLY 4 values per build brief
    # Values: 'booked', 'cancelled', 'no_show', 'completed'
    status = Column(String(20), default="booked", nullable=False)
    
    # Optional metadata
    cancellation_reason = Column(String, nullable=True)
    
    # Audit metadata
    source = Column(String(20), default="whatsapp")  # patient/staff
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    clinic = relationship("Clinic", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    service = relationship("Service", back_populates="appointments")
    
    # CRITICAL: Double-booking prevention + tenant isolation indexes
    __table_args__ = (
        # Tenant isolation (clinic_id first on all indexes)
        Index("idx_clinic_doctor_date", "clinic_id", "doctor_id", "start_utc_ts"),
        Index("idx_appt_clinic_phone", "clinic_id", "patient_phone"),
        
        # CRITICAL: Prevent double-booking at DB level
        # Only one 'booked' appointment per doctor per time slot
        Index(
            "idx_doctor_slot_booked_unique",
            "doctor_id",
            "start_utc_ts",
            unique=True,
            postgresql_where=text("status = 'booked'")
        ),
    )

