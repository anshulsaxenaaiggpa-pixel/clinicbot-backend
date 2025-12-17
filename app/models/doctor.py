"""Doctor database model"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.base_class import Base


class Doctor(Base):
    """Doctor/Practitioner entity"""
    __tablename__ = "doctors"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id = Column(UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False)
    
    name = Column(String(80), nullable=False)
    specialization = Column(String(50))
    default_fee = Column(Integer)  # Default consultation fee in rupees
    
    # Optional: Per-doctor availability override
    custom_availability = Column(JSON, nullable=True)  # Override clinic timing if needed
    
    # Metadata
    is_active = Column(Boolean, default=True)
   created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    clinic = relationship("Clinic", back_populates="doctors")
    appointments = relationship("Appointment", back_populates="doctor")
