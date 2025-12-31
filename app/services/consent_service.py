"""
Consent Capture Service - DPDP Compliance

DO NOT MODIFY LOGIC OUTSIDE CONSENT SCOPE.
DO NOT STORE PATIENT DATA BEFORE CONSENT.
DO NOT AUTO-CONSENT USERS.

Implements consent checking and capture per Module 2 specification.
"""
from typing import Optional, Literal
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.patient_consent import (
    PatientConsent, 
    ConsentStatus, 
    Channel,
    CONSENT_TEXT_V1,
    CONSENT_VERSION
)
from app.db.session import SessionLocal


class ConsentService:
    """Service for managing patient consent."""
    
    @staticmethod
    def check_consent_granted(phone_number: str, db: Session = None) -> bool:
        """
        Check if user has granted consent.
        
        Returns True only if most recent consent record is GRANTED.
        """
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            # Get most recent consent record for this phone
            latest_consent = db.query(PatientConsent).filter(
                PatientConsent.phone_number == phone_number
            ).order_by(desc(PatientConsent.timestamp)).first()
            
            if latest_consent is None:
                return False
            
            return latest_consent.consent_status == ConsentStatus.GRANTED
        
        finally:
            if should_close:
                db.close()
    
    @staticmethod
    def capture_consent(
        phone_number: str,
        reply_text: str,
        channel: str = "whatsapp",
        ip_address: Optional[str] = None,
        db: Session = None
    ) -> dict:
        """
        Process consent response and store result.
        
        Args:
            phone_number: E.164 format phone number
            reply_text: User's reply (YES/NO/STOP)
            channel: Channel through which consent was captured
            ip_address: Optional IP address
            db: Optional database session
        
        Returns:
            {
                "status": "granted" | "withdrawn",
                "timestamp": ISO timestamp,
                "version": consent version
            }
        """
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            # Normalize reply text
            normalized_reply = reply_text.strip().upper()
            
            # Determine consent status based on reply
            if normalized_reply in ["YES", "Y", "1", "AGREE", "ACCEPT"]:
                status = ConsentStatus.GRANTED
            elif normalized_reply in ["NO", "N", "0", "STOP", "DECLINE", "WITHDRAW", "REMOVE"]:
                status = ConsentStatus.WITHDRAWN
            else:
                # Invalid response - do not store
                return {
                    "status": "invalid",
                    "message": "Invalid response. Please reply YES to continue or NO to stop."
                }
            
            # Create consent record
            consent = PatientConsent(
                phone_number=phone_number,
                consent_text=CONSENT_TEXT_V1,
                consent_version=CONSENT_VERSION,
                consent_status=status,
                timestamp=datetime.utcnow(),
                ip_address=ip_address,
                channel=Channel(channel)
            )
            
            db.add(consent)
            db.commit()
            db.refresh(consent)
            
            return {
                "status": status.value,
                "timestamp": consent.timestamp.isoformat(),
                "version": consent.consent_version,
                "message": "✅ Thank you! You can now book appointments." if status == ConsentStatus.GRANTED 
                          else "Understood. You can start booking anytime by replying YES."
            }
        
        except Exception as e:
            db.rollback()
            raise
        
        finally:
            if should_close:
                db.close()
    
    @staticmethod
    def get_consent_status(phone_number: str, db: Session = None) -> dict:
        """
        Get current consent status for a phone number.
        
        Returns:
            {
                "status": "granted" | "withdrawn" | "none",
                "timestamp": ISO timestamp or None,
                "version": consent version or None
            }
        """
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            # Get most recent consent record
            latest_consent = db.query(PatientConsent).filter(
                PatientConsent.phone_number == phone_number
            ).order_by(desc(PatientConsent.timestamp)).first()
            
            if latest_consent is None:
                return {
                    "status": "none",
                    "timestamp": None,
                    "version": None
                }
            
            return {
                "status": latest_consent.consent_status.value,
                "timestamp": latest_consent.timestamp.isoformat(),
                "version": latest_consent.consent_version
            }
        
        finally:
            if should_close:
                db.close()
    
    @staticmethod
    def get_consent_prompt() -> str:
        """
        Get the exact consent text to show users.
        
        Returns the EXACT wording as specified in Module 2.
        """
        return CONSENT_TEXT_V1


# Convenience functions for use in other modules
def check_consent(phone_number: str) -> bool:
    """Quick check if user has granted consent."""
    return ConsentService.check_consent_granted(phone_number)


def require_consent(phone_number: str) -> None:
    """
    Raise exception if consent not granted.
    
    Use this in endpoints that process PHI.
    """
    if not check_consent(phone_number):
        raise ConsentRequiredException(
            f"Consent required for {phone_number}. No patient data can be processed without consent."
        )


class ConsentRequiredException(Exception):
    """Raised when an operation requires consent but it hasn't been granted."""
    pass
