"""Slot availability API schemas"""
from pydantic import BaseModel, Field
from typing import List
from datetime import date
from uuid import UUID


class DoctorAvailability(BaseModel):
    """Doctor info in slot response"""
    doctor_id: UUID
    name: str
    specialization: str
    fee: int


class ServiceAvailability(BaseModel):
    """Service info in slot response"""
    service_id: UUID
    name: str
    duration_minutes: int
    fee: int


class SlotResponse(BaseModel):
    """Individual slot availability"""
    slot_id: str
    doctor_id: UUID
    doctor_name: str
    start_local: str = Field(..., description="ISO format with timezone, e.g. '2025-12-11T10:30:00+05:30'")
    end_local: str
    start_utc_ts: int = Field(..., description="Unix timestamp for booking")
    end_utc_ts: int
    duration_mins: int
    available_services: List[ServiceAvailability]


class SlotQueryParams(BaseModel):
    """Query parameters for slot lookup"""
    clinic_id: UUID
    doctor_id: UUID
    date: date
    service_id: Optional[UUID] = Field(None, description="Filter for specific service duration")


class SlotsAvailableResponse(BaseModel):
    """Response for slot availability endpoint"""
    date: date
    doctor_id: UUID
    doctor_name: str
    total_slots: int
    slots: List[SlotResponse]
