"""
Patient Consent Model - DPDP Compliance

DO NOT MODIFY LOGIC OUTSIDE CONSENT SCOPE.
DO NOT STORE PATIENT DATA BEFORE CONSENT.
DO NOT AUTO-CONSENT USERS.

This module implements explicit, auditable patient consent before any PHI is processed.
"""
from sqlalchemy import Column, String, DateTime, Enum, Index
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.db.base_class import Base


class ConsentStatus(str, enum.Enum):
    """Consent status enumeration."""
    GRANTED = "granted"
    WITHDRAWN = "withdrawn"


class Channel(str, enum.Enum):
    """Channel through which consent was captured."""
    WHATSAPP = "whatsapp"


# EXACT consent text as specified in Module 2
CONSENT_TEXT_V1 = """We will use your messages only to book and manage your clinic appointment. Your data will be stored securely and shared only with the clinic you are booking with. Reply YES to continue, or NO to stop. Reply STOP anytime to withdraw consent."""

CONSENT_VERSION = "dpdp-whatsapp-consent-v1.0"


class PatientConsent(Base):
    """
    Patient consent records for DPDP compliance.
    
    Stores explicit, timestamped consent linked to phone number.
    No patient data is stored before consent = TRUE.
    """
    __tablename__ = "patient_consent"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Identity (E.164 format)
    phone_number = Column(String(15), nullable=False)
    
    # Consent metadata
    consent_text = Column(String, nullable=False)  # Full wording shown to user
    consent_version = Column(String(50), nullable=False)  # e.g., "dpdp-whatsapp-consent-v1.0"
    consent_status = Column(Enum(ConsentStatus), nullable=False)  # granted | withdrawn
    
    # Audit fields
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    ip_address = Column(String(50), nullable=True)  # Optional
    channel = Column(Enum(Channel), default=Channel.WHATSAPP, nullable=False)
    
    # Indexes for fast consent checks
    __table_args__ = (
        Index("idx_phone_consent_status", "phone_number", "consent_status"),
        Index("idx_phone_timestamp", "phone_number", "timestamp"),
    )
    
    def __repr__(self):
        return f"<PatientConsent {self.phone_number} {self.consent_status.value} at {self.timestamp}>"
