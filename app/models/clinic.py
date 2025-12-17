"""Clinic database model"""
from sqlalchemy import Column, String, DateTime, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.database import Base


class Clinic(Base):
    """Clinic entity representing a medical practice"""
    __tablename__ = "clinics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    owner_name = Column(String(80))
    address = Column(String(200))
    city = Column(String(50))
    timezone = Column(String(50), default="Asia/Kolkata")
    whatsapp_number = Column(String(15), unique=True, nullable=False)
    
    # Subscription
    subscription_tier = Column(String(20), default="starter")  # starter, professional, enterprise
    subscription_status = Column(String(20), default="trial")  # trial, active, expired, cancelled
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)
    
    # WhatsApp API Configuration
    whatsapp_provider = Column(String(20))  # twilio, meta, gupshup
    whatsapp_config = Column(JSON)  # Provider-specific config
    
    # API Key for authentication
    api_key = Column(String(64), unique=True, index=True)  # clinic_xxxxx format
    
    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    doctors = relationship("Doctor", back_populates="clinic")
    services = relationship("Service", back_populates="clinic")
    appointments = relationship("Appointment", back_populates="clinic")
    clinic_timing = relationship("ClinicTiming", back_populates="clinic")
    closed_dates = relationship("ClosedDate", back_populates="clinic")
