"""Clinic API schemas"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from uuid import UUID


class ClinicCreate(BaseModel):
    """Schema for creating a new clinic"""
    name: str = Field(..., min_length=2, max_length=100)
    owner_name: str = Field(..., min_length=2, max_length=80)
    address: str = Field(..., max_length=200)
    city: str
    whatsapp_number: str = Field(..., pattern=r'^\+91[6-9]\d{9}$')
    timezone: str = Field(default="Asia/Kolkata")
    
    @validator('whatsapp_number')
    def validate_whatsapp(cls, v):
        if not v.startswith('+91'):
            raise ValueError('WhatsApp number must be Indian (+91)')
        return v


class ClinicUpdate(BaseModel):
    """Schema for updating clinic details"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    owner_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    whatsapp_number: Optional[str] = None


class WhatsAppConfig(BaseModel):
    """WhatsApp provider configuration"""
    provider: str = Field(..., pattern='^(twilio|meta|gupshup)$')
    token: Optional[str] = None
    phone_number_id: Optional[str] = None
    account_sid: Optional[str] = None


class ClinicOut(BaseModel):
    """Schema for clinic response"""
    id: UUID
    name: str
    owner_name: Optional[str]
    address: Optional[str]
    city: Optional[str]
    timezone: str
    whatsapp_number: str
    subscription_tier: str
    subscription_status: str
    trial_ends_at: Optional[datetime]
    created_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True  # For SQLAlchemy models
