"""Appointment API schemas"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Union
from datetime import date, datetime
from uuid import UUID


class AppointmentCreate(BaseModel):
    """Schema for creating an appointment"""
    clinic_id: Union[UUID, str]
    doctor_id: Union[UUID, str]
    service_id: Union[UUID, str]
    patient_name: Optional[str] = Field(None, min_length=2, max_length=100)
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
    """Schema for appointment response - matches actual model fields"""
    id: Union[UUID, str]
    clinic_id: Union[UUID, str]
    doctor_id: Union[UUID, str]
    service_id: Union[UUID, str]
    patient_name: Optional[str] = None
    patient_phone: str
    start_utc_ts: datetime
    end_utc_ts: datetime
    status: str
    amount_paid: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class AppointmentListItem(BaseModel):
    """Lightweight schema for appointment lists"""
    id: Union[UUID, str]
    patient_name: Optional[str] = None
    doctor_name: str = Field(..., description="Joined from doctor table")
    service_name: str = Field(..., description="Joined from service table")
    start_time_local: str = Field(..., description="Formatted local time, e.g. '10:30 AM'")
    status: str
    
    class Config:
        from_attributes = True
