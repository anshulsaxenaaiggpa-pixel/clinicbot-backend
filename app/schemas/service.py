"""Service API schemas"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from uuid import UUID


class ServiceCreate(BaseModel):
    """Schema for creating a service"""
    clinic_id: UUID
    name: str = Field(..., max_length=100)
    type: str = Field(..., pattern='^(consultation|procedure|therapy|followup|teleconsult)$')
    duration_minutes: int = Field(..., ge=5, le=120)
    default_fee: int = Field(..., ge=100, le=50000)
    before_buffer_mins: int = Field(default=0, ge=0, le=30)
    after_buffer_mins: int = Field(default=0, ge=0, le=30)
    
    @validator('duration_minutes')
    def validate_duration(cls, v):
        # Ensure duration is multiple of 5 for clean scheduling
        if v % 5 != 0:
            raise ValueError('Duration must be multiple of 5 minutes')
        return v
    
    @property
    def required_slots(self) -> int:
        """Calculate required 15-min slots"""
        return (self.duration_minutes + 14) // 15  # Ceiling division


class ServiceUpdate(BaseModel):
    """Schema for updating service"""
    name: Optional[str] = None
    type: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, ge=5, le=120)
    default_fee: Optional[int] = Field(None, ge=100, le=50000)
    before_buffer_mins: Optional[int] = Field(None, ge=0, le=30)
    after_buffer_mins: Optional[int] = Field(None, ge=0, le=30)
    is_active: Optional[bool] = None


class ServiceOut(BaseModel):
    """Schema for service response"""
    id: UUID
    clinic_id: UUID
    name: str
    type: str
    duration_minutes: int
    required_slots: int
    default_fee: int
    before_buffer_mins: int
    after_buffer_mins: int
    is_active: bool
    
    class Config:
        from_attributes = True
