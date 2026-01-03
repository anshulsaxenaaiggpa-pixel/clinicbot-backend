"""Patient database model - MINIMAL MVP VERSION
Data minimization: Only store what's required for appointment booking.
No medical data, no behavioral profiling, no demographics.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.base_class import Base


class Patient(Base):
    """
    Minimal patient entity for scheduling only.
    
    Purpose:
    - Identity anchor (phone + clinic)
    - Consent tracking
    - FK integrity for appointments
    
    NOT storing:
    - Medical data
    - Demographics (DOB, gender, email)
    - Behavioral metrics (visits, no-shows)
    
    This keeps us a utility tool, not an EMR system.
    """
    __tablename__ = "patients"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    clinic_id = Column(String(36), ForeignKey("clinics.id"), nullable=False)
    
    # Identity fields ONLY
    phone = Column(String(15), nullable=False)
    name = Column(String(100), nullable=True)  # Optional, UX only
    
    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    clinic = relationship("Clinic", backref="patients")
    # NOTE: No direct relationship to appointments (patient_id FK removed for data minimization)
    # Appointments can be queried via: Appointment.query.filter_by(patient_phone=patient.phone)
    
    # Composite unique constraint on clinic + phone
    __table_args__ = (
        Index("idx_patient_clinic_phone", "clinic_id", "phone", unique=True),
    )
