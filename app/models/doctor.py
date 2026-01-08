"""Doctor database model"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import bcrypt

from app.db.base_class import Base


class Doctor(Base):
    """
    Doctor/Practitioner entity
    """
    __tablename__ = "doctors"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    clinic_id = Column(String(36), ForeignKey("clinics.id"), nullable=False)
    
    # Basic info - ACTUAL database schema uses name/specialization (001_initial_schema.py)
    name = Column(String(100), nullable=False)
    specialization = Column(String(100))
    
    # Authentication
    whatsapp_number = Column(String(20), unique=True, nullable=False)
    password_hash = Column(String(255))
    
    # Revenue fields
    upi_id = Column(String(100), nullable=True)  # UPI ID for payment collection
    status = Column(String(20), default='active')  # active, trial, suspended
    consultation_fee = Column(Integer, default=500, nullable=False)  # Per-consultation fee in rupees
    
    # Metadata
    city = Column(String(100))  # Match DB schema
    is_searchable = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    clinic = relationship("Clinic", back_populates="doctors")
    appointments = relationship("Appointment", back_populates="doctor")
    availability_slots = relationship("DoctorAvailability", back_populates="doctor", cascade="all, delete-orphan")
    leaves = relationship("DoctorLeave", back_populates="doctor", cascade="all, delete-orphan")
    
    def set_password(self, password: str):
        """Hash and set password."""
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password: str) -> bool:
        """Verify password against hash."""
        if not self.password_hash:
            return False
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))


