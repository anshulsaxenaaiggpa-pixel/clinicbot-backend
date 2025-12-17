"""Patient API schemas"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class PatientCreate(BaseModel):
    """Schema for creating a patient"""
    clinic_id: UUID
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., pattern=r'^\+91[6-9]\d{9}$')
    whatsapp_name: Optional[str] = None


class PatientUpdate(BaseModel):
    """Schema for updating patient details"""
    name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class PatientOut(BaseModel):
    """Schema for patient response"""
    id: UUID
    clinic_id: UUID
    name: str
    phone: str
    whatsapp_name: Optional[str]
    total_visits: int
    total_cancellations: int
    total_no_shows: int
    first_visit_date: Optional[datetime]
    last_visit_date: Optional[datetime]
    created_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True


class PatientStats(BaseModel):
    """Patient statistics"""
    total_patients: int
    new_patients_this_month: int
    active_patients: int
    total_appointments: int
