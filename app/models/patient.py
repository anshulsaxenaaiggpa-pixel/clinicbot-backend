"""Patient database model"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Index, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.base_class import Base


class Patient(Base):
    """
    Patient entity - tracks unique patients per clinic
    
    Key features:
    - Unique per clinic + phone number
    - Links to all appointments
    - Enables patient history and analytics
    """
    __tablename__ = "patients"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id = Column(UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False)
    
    # Patient details
    name = Column(String(100), nullable=False)
    phone = Column(String(15), nullable=False)
    email = Column(String(100), nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    gender = Column(String(10), nullable=True)
    
    # Tracking
    total_visits = Column(Integer, default=0)
    cancelled_count = Column(Integer, default=0)
    no_show_count = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    clinic = relationship("Clinic", backref="patients")
    appointments = relationship("Appointment", back_populates="patient")
    
    # Composite unique constraint on clinic + phone
    __table_args__ = (
        Index("idx_clinic_phone", "clinic_id", "phone", unique=True),
        Index("idx_patient_phone", "phone"),
    )
