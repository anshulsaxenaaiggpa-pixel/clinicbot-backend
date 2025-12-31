"""
Data Classification Enforcement - Sprint Task 2

Pydantic models enforcing data minimization per COMPLIANCE_BASELINE.md
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from enum import Enum


class DataClassification(str, Enum):
    """
    Data classification levels per assumptions.md
    """
    PII = "pii"                  # Personally Identifiable Information
    NON_PII = "non_pii"          # Non-identifiable data
    SYSTEM_LOG = "system_log"    # System logs (scrubbed)
    AUDIT_LOG = "audit_log"      # Audit logs (phone hashed)


class ProhibitedDataError(ValueError):
    """Raised when prohibited data is attempted to be stored."""
    pass


class PatientDataMinimal(BaseModel):
    """
    Minimal patient data per COMPLIANCE_BASELINE.md
    
    ALLOWED:
    - WhatsApp phone number
    - Name (if shared)
    
    PROHIBITED:
    - Full chat transcripts
    - Medical content
    - Diagnosis
    - Symptoms
    - Payment data
    """
    phone_number: str = Field(..., description="E.164 format phone number")
    name: Optional[str] = Field(None, max_length=100, description="Patient name (optional)")
    
    # Classification
    _classification = DataClassification.PII
    
    @validator('phone_number')
    def validate_phone_e164(cls, v):
        """Enforce E.164 format."""
        import re
        if not re.match(r'^\+[1-9]\d{1,14}$', v):
            raise ValueError("Phone must be in E.164 format (+919999999999)")
        return v
    
    class Config:
        # Do NOT allow extra fields (strict mode)
        extra = "forbid"


class AppointmentDataMinimal(BaseModel):
    """
    Minimal appointment metadata per COMPLIANCE_BASELINE.md
    
    ALLOWED:
    - Clinic ID
    - Doctor ID
    - Date/time
    - Service name
    
    PROHIBITED:
    - Reason for visit (medical content)
    - Symptoms
    - Patient notes with medical info
    """
    clinic_id: str
    doctor_id: str
    service_id: str
    start_time: datetime
    end_time: datetime
    patient_phone: str  # For linking only
    patient_name: Optional[str] = None
    
    # Classification
    _classification = DataClassification.PII
    
    # Prohibited fields (will raise error if present)
    reason_for_visit: Optional[str] = Field(None, forbidden=True)
    symptoms: Optional[str] = Field(None, forbidden=True)
    diagnosis: Optional[str] = Field(None, forbidden=True)
    medical_notes: Optional[str] = Field(None, forbidden=True)
    
    @validator('reason_for_visit', 'symptoms', 'diagnosis', 'medical_notes', pre=True, always=True)
    def prohibit_medical_data(cls, v, field):
        """Enforce prohibition of medical data."""
        if v is not None:
            raise ProhibitedDataError(
                f"Field '{field.name}' is prohibited per COMPLIANCE_BASELINE.md. "
                f"ClinicBot does not store medical content."
            )
        return v
    
    class Config:
        extra = "forbid"


class WhatsAppMessageMetadata(BaseModel):
    """
    WhatsApp message metadata (NOT full message content).
    
    Per COMPLIANCE_BASELINE.md:
    "Chat transcripts will NOT be stored unless explicitly required"
    
    Store ONLY:
    - Message ID (for deduplication)
    - Timestamp
    - Direction (inbound/outbound)
    
    DO NOT STORE:
    - Message body/content
    - Media attachments
   - Contact details beyond phone
    """
    message_id: str  # WhatsApp message ID
    timestamp: datetime
    direction: str  # "inbound" or "outbound"
    phone_number: str  # E.164 format
    
    # PROHIBITED
    message_body: Optional[str] = Field(None, forbidden=True)
    media_url: Optional[str] = Field(None, forbidden=True)
    
    # Classification
    _classification = DataClassification.SYSTEM_LOG
    
    @validator('message_body', 'media_url', pre=True, always=True)
    def prohibit_message_content(cls, v, field):
        """Enforce no message content storage."""
        if v is not None:
            raise ProhibitedDataError(
                f"Storing '{field.name}' is prohibited. "
                f"Per COMPLIANCE_BASELINE.md, chat transcripts are NOT stored."
            )
        return v
    
    class Config:
        extra = "forbid"


# Data classification validator
def validate_data_classification(data: BaseModel):
    """
    Validate that data adheres to classification rules.
    
    Conservative principle: If uncertain, reject.
    """
    # Check if model has classification
    if not hasattr(data, '_classification'):
        raise ValueError("Data model must define _classification attribute")
    
    classification = data._classification
    
    # PII must be encrypted at rest (enforced at DB level)
    if classification == DataClassification.PII:
        # Assumption: Database encryption handled by managed service
        pass
    
    # System logs must be scrubbed
    if classification == DataClassification.SYSTEM_LOG:
        # Assumption: LogScrubber handles this before persistence
        pass
    
    return True
