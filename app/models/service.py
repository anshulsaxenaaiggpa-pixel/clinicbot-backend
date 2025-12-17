"""Service database model"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.database import Base


# Many-to-many relationship table for doctor-service mapping
doctor_services = Table(
    "doctor_services",
    Base.metadata,
    Column("doctor_id", UUID(as_uuid=True), ForeignKey("doctors.id"), primary_key=True),
    Column("service_id", UUID(as_uuid=True), ForeignKey("services.id"), primary_key=True),
    Column("custom_fee", Integer, nullable=True)  # Override default service fee for specific doctor
)


class Service(Base):
    """Service/Treatment offered by clinic"""
    __tablename__ = "services"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id = Column(UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False)
    
    name = Column(String(100), nullable=False)
    type = Column(String(20))  # consultation, procedure, therapy, followup, teleconsult
    duration_minutes = Column(Integer, nullable=False)
    required_slots = Column(Integer, nullable=False)  # Number of 15-min slots needed
    default_fee = Column(Integer, nullable=False)
    
    # Buffer times for setup/cleanup (in minutes)
    before_buffer_mins = Column(Integer, default=0)
    after_buffer_mins = Column(Integer, default=0)
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    clinic = relationship("Clinic", back_populates="services")
    appointments = relationship("Appointment", back_populates="service")
