"""Clinic timing configuration model"""
from typing import TYPE_CHECKING
from sqlalchemy import Column, String, Time, Boolean, ForeignKey, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.db.base_class import Base

# Import for type checking only
if TYPE_CHECKING:
    from app.models.clinic import Clinic


class ClinicTiming(Base):
    """Operating hours for each day of week"""
    __tablename__ = "clinic_timing"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id = Column(UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False)
    
    day_of_week = Column(String(10), nullable=False)  # monday, tuesday, ..., sunday
    is_closed = Column(Boolean, default=False)
    
    start_time = Column(Time)
    end_time = Column(Time)
    
    # Lunch break
    lunch_enabled = Column(Boolean, default=False)
    lunch_start = Column(Time, nullable=True)
    lunch_end = Column(Time, nullable=True)
    
    # Relationship using forward reference
    clinic: "Clinic" = relationship("Clinic", back_populates="clinic_timing")


class ClosedDate(Base):
    """Specific dates when clinic is closed (holidays, etc.)"""
    __tablename__ = "closed_dates"
    
    clinic_id = Column(UUID(as_uuid=True), ForeignKey("clinics.id"), primary_key=True)
    closed_date = Column(Date, primary_key=True)
    reason = Column(String(100), nullable=True)
    
    # Relationship using forward reference
    clinic: "Clinic" = relationship("Clinic", back_populates="closed_dates")
