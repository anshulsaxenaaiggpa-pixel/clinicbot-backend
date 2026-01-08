"""
Doctor Availability Models

Allows doctors to set their own working hours and holidays.
"""
from sqlalchemy import Column, String, Time, Boolean, Date, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from app.db.base_class import Base


class DoctorAvailability(Base):
    """
    Doctor's weekly availability schedule.
    
    Each doctor can have multiple availability slots per week.
    Example: Monday 9am-12pm, Monday 5pm-8pm, Saturday 10am-2pm
    """
    __tablename__ = "doctor_availability"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=False)
    
    # Day of week (0=Monday, 6=Sunday)
    day_of_week = Column(Integer, nullable=False)  # 0-6
    
    # Time range
    start_time = Column(Time, nullable=False)  # e.g., 09:00:00
    end_time = Column(Time, nullable=False)    # e.g., 17:00:00
    
    # Active/Inactive
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    doctor = relationship("Doctor", back_populates="availability_slots")


class DoctorLeave(Base):
    """
    Doctor's leaves/holidays for specific dates.
    
    Blocks availability for specific days.
    """
    __tablename__ = "doctor_leaves"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=False)
    
    # Leave date
    leave_date = Column(Date, nullable=False)
    
    # Optional reason
    reason = Column(String(200), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    doctor = relationship("Doctor", back_populates="leaves")
