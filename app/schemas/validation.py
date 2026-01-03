"""
Input Validation Schemas - MODULE 5

Pydantic schemas for input validation across all endpoints.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
import re


# E.164 phone number validation pattern
E164_PATTERN = re.compile(r'^\+[1-9]\d{1,14}$')


class E164PhoneValidator:
    """Helper class for validating phone numbers."""
    
    @staticmethod
    def validate(v: str) -> bool:
        """Validate E.164 format."""
        return bool(E164_PATTERN.match(v))


class PhoneNumber(BaseModel):
    """E.164 phone number validation."""
    phone: str = Field(..., description="Phone number in E.164 format")
    
    @validator('phone')
    def validate_e164(cls, v):
        """Validate E.164 format."""
        if not E164_PATTERN.match(v):
            raise ValueError(
                "Phone number must be in E.164 format (e.g., +919999999999)"
            )
        return v


class ConsentCaptureInput(BaseModel):
    """Input validation for consent capture."""
    phone_number: str = Field(..., min_length=10, max_length=15)
    reply_text: str = Field(..., min_length=1, max_length=100)
    channel: str = Field(default="whatsapp", pattern="^(whatsapp|sms|api)$")
    ip_address: Optional[str] = Field(None, max_length=45)  # IPv6 max length
    
    @validator('phone_number')
    def validate_phone(cls, v):
        if not E164_PATTERN.match(v):
            raise ValueError("Invalid phone number format")
        return v


class DeletionInput(BaseModel):
    """Input validation for data deletion."""
    phone_number: str
    verification: str = Field(default="phone_match")
    requested_by: str = Field(default="patient", pattern="^(patient|admin|system)$")
    
    @validator('phone_number')
    def validate_phone(cls, v):
        if not E164_PATTERN.match(v):
            raise ValueError("Invalid phone number format")
        return v


class AppointmentCreateInput(BaseModel):
    """Input validation for appointment creation."""
    patient_phone: str
    patient_name: Optional[str] = Field(None, max_length=100)
    clinic_id: str
    doctor_id: str
    service_id: str
    start_time: datetime
    end_time: datetime
    source: str = Field(default="whatsapp", pattern="^(whatsapp|dashboard|api)$")
    
    @validator('patient_phone')
    def validate_phone(cls, v):
        if not E164_PATTERN.match(v):
            raise ValueError("Invalid phone number format")
        return v
    
    @validator('end_time')
    def validate_end_after_start(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError("end_time must be after start_time")
        return v
    
    @validator('start_time')
    def validate_future_time(cls, v):
        if v < datetime.utcnow():
            raise ValueError("Appointment must be in the future")
        return v


class AppointmentUpdateInput(BaseModel):
    """Input validation for appointment updates."""
    status: Optional[str] = Field(None, pattern="^(booked|cancelled|no_show|completed)$")
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    cancellation_reason: Optional[str] = Field(None, max_length=500)
    
    @validator('end_time')
    def validate_end_after_start(cls, v, values):
        if v and 'start_time' in values and values['start_time'] and v <= values['start_time']:
            raise ValueError("end_time must be after start_time")
        return v


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize user input to prevent injection attacks.
    
    Removes potentially dangerous characters and limits length.
    """
    if not text:
        return ""
    
    # Truncate to max length
    text = text[:max_length]
    
    # Remove control characters except newline and tab
    sanitized = "".join(char for char in text if char.isprintable() or char in ['\n', '\t'])
    
    # Strip dangerous patterns (basic SQL injection prevention)
    dangerous_patterns = [
        "--", "/*", "*/", "xp_", "sp_", "exec", "execute",
        "<script", "javascript:", "onerror=", "onclick="
    ]
    
    lower_text = sanitized.lower()
    for pattern in dangerous_patterns:
        if pattern in lower_text:
            sanitized = sanitized.replace(pattern, "")
    
    return sanitized.strip()
