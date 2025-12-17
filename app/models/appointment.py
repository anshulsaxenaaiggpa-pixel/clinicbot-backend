"""Appointment database model"""
from sqlalchemy import Column, String, Integer, Date, BigInteger, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.database import Base


class Appointment(Base):
    """Patient appointment booking"""
    __tablename__ = "appointments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id = Column(UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=False)
    service_id = Column(UUID(as_uuid=True), ForeignKey("services.id"), nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=True)  # Legacy appointments may not have patient_id
    
    # Patient information (kept for backwards compatibility)
    patient_name = Column(String(100), nullable=False)
    patient_phone = Column(String(15), nullable=False)
    patient_notes = Column(String(500), nullable=True)
    
    # Scheduling (stored as UTC timestamps)
    date = Column(Date, nullable=False)
    start_utc_ts = Column(BigInteger, nullable=False)  # Unix timestamp
    end_utc_ts = Column(BigInteger, nullable=False)    # Unix timestamp
    
    # Status tracking
    status = Column(String(20), default="confirmed")  # confirmed, cancelled, completed, no_show
    created_via = Column(String(20), default="whatsapp")  # whatsapp, dashboard, api
    
    # Payment (optional)
    payment_status = Column(String(20), default="pending")  # pending, paid, refunded
    amount_paid = Column(Integer, nullable=True)
    
    # Reminders sent
    reminder_24h_sent = Column(DateTime(timezone=True), nullable=True)
    reminder_2h_sent = Column(DateTime(timezone=True), nullable=True)
    followup_sent = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    clinic = relationship("Clinic", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    service = relationship("Service", back_populates="appointments")
    patient = relationship("Patient", back_populates="appointments")
    
    # Indexes for fast queries
    __table_args__ = (
        Index("idx_doctor_date", "doctor_id", "date"),
        Index("idx_clinic_date", "clinic_id", "date"),
        Index("idx_patient_phone", "patient_phone"),
    )
