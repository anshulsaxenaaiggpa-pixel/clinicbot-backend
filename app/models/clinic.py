"""Clinic database model"""
from typing import TYPE_CHECKING
from sqlalchemy import Column, String, DateTime, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.base_class import Base

# Import for type checking only - avoids circular imports
if TYPE_CHECKING:
    from app.models.doctor import Doctor
    from app.models.service import Service
    from app.models.appointment import Appointment
    from app.models.clinic_timing import ClinicTiming, ClosedDate


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
    
    # Relationships - using direct class references via forward references
    doctors: list["Doctor"] = relationship("Doctor", back_populates="clinic")
    services: list["Service"] = relationship("Service", back_populates="clinic")
    appointments: list["Appointment"] = relationship("Appointment", back_populates="clinic")
    clinic_timing: list["ClinicTiming"] = relationship("ClinicTiming", back_populates="clinic")
    closed_dates: list["ClosedDate"] = relationship("ClosedDate", back_populates="clinic")
