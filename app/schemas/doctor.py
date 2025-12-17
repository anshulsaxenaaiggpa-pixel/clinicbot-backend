"""Doctor API schemas"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from uuid import UUID


class DoctorCreate(BaseModel):
    """Schema for creating a doctor"""
    clinic_id: UUID
    name: str = Field(..., min_length=2, max_length=80)
    specialization: str = Field(..., max_length=50)
    default_fee: int = Field(..., ge=100, le=10000, description="Consultation fee in rupees")
    custom_availability: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional per-doctor schedule override"
    )


class DoctorUpdate(BaseModel):
    """Schema for updating doctor details"""
    name: Optional[str] = None
    specialization: Optional[str] = None
    default_fee: Optional[int] = Field(None, ge=100, le=10000)
    custom_availability: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class DoctorOut(BaseModel):
    """Schema for doctor response"""
    id: UUID
    clinic_id: UUID
    name: str
    specialization: Optional[str]
    default_fee: Optional[int]
    is_active: bool
    
    class Config:
        from_attributes = True
