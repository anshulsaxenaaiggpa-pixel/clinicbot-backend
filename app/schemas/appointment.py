"""Appointment API schemas"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import date, datetime
from uuid import UUID


class AppointmentCreate(BaseModel):
    """Schema for creating an appointment"""
    clinic_id: UUID
    doctor_id: UUID
    service_id: UUID
    patient_name: str = Field(..., min_length=2, max_length=100)
    patient_phone: str = Field(..., pattern=r'^\+91[6-9]\d{9}$')
    patient_notes: Optional[str] = Field(None, max_length=500)
    date: date
    start_utc_ts: int = Field(..., description="Start time as Unix timestamp (UTC)")
    
    @validator('date')
    def validate_future_date(cls, v):
        if v < date.today():
            raise ValueError('Cannot book appointments in the past')
        return v


class AppointmentReschedule(BaseModel):
    """Schema for rescheduling"""
    new_date: date
    new_start_utc_ts: int
    
    @validator('new_date')
    def validate_future_date(cls, v):
        if v < date.today():
            raise ValueError('Cannot reschedule to past date')
        return v


class AppointmentOut(BaseModel):
    """Schema for appointment response"""
    id: UUID
    clinic_id: UUID
    doctor_id: UUID
    service_id: UUID
    patient_name: str
    patient_phone: str
    patient_notes: Optional[str]
    date: date
    start_utc_ts: int
    end_utc_ts: int
    status: str
    created_via: str
    payment_status: str
    amount_paid: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AppointmentListItem(BaseModel):
    """Lightweight schema for appointment lists"""
    id: UUID
    patient_name: str
    doctor_name: str = Field(..., description="Joined from doctor table")
    service_name: str = Field(..., description="Joined from service table")
    date: date
    start_time_local: str = Field(..., description="Formatted local time, e.g. '10:30 AM'")
    status: str
    
    class Config:
        from_attributes = True
