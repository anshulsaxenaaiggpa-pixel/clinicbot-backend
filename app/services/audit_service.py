"""
Audit Service - MODULE 4

Centralized event logging for compliance and debugging.
All system actions are logged immutably.
"""
from typing import Dict, Optional
from datetime import datetime
import uuid

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.db.session import SessionLocal


# Event types as defined in Module 4 spec
EVENT_TYPES = {
    "CONSENT_GRANTED": "consent_granted",
    "CONSENT_WITHDRAWN": "consent_withdrawn",
    "APPOINTMENT_CREATED": "appointment_created",
    "APPOINTMENT_UPDATED": "appointment_updated",
    "APPOINTMENT_CANCELLED": "appointment_cancelled",
    "DELETION_REQUESTED": "deletion_requested",
    "DELETION_COMPLETED": "deletion_completed",
    "RATE_LIMIT_BLOCK": "rate_limit_block",
}


class AuditService:
    """Service for creating audit log entries."""
    
    @staticmethod
    def log_event(
        event_type: str,
        actor: str,  # system/clinic/admin/patient
        actor_id: str,  # phone number or admin ID
        patient_phone: Optional[str] = None,
        metadata: Optional[Dict] = None,
        db: Session = None
    ) -> AuditLog:
        """
        Log a system event to the immutable audit trail.
        
        Args:
            event_type: One of the EVENT_TYPES constants
            actor: Who performed the action (system/clinic/admin/patient)
            actor_id: Identifier of the actor
            patient_phone: Patient phone number (will be hashed)
            metadata: Additional context (NO PHI - will be sanitized)
            db: Optional database session
        
        Returns:
            Created AuditLog entry
        """
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            # Generate unique event ID
            event_id = str(uuid.uuid4())
            
            # Hash patient phone if provided
            patient_hash = None
            if patient_phone:
                patient_hash = AuditLog.hash_phone(patient_phone)
            
            # Sanitize metadata (remove any PHI)
            safe_metadata = AuditService._sanitize_metadata(metadata) if metadata else None
            
            # Create audit entry
            audit = AuditLog(
                event_id=event_id,
                event_type=event_type,
                actor=actor,
                actor_id=actor_id,
                patient_phone_hash=patient_hash,
                event_metadata=safe_metadata,
                timestamp=datetime.utcnow()
            )
            
            db.add(audit)
            db.commit()
            db.refresh(audit)
            
            return audit
        
        except Exception as e:
            # CRITICAL: Audit logging failure should NOT break main operation
            # Log to application logs but continue
            print(f"AUDIT LOG FAILURE: {e}")
            db.rollback()
            return None
        
        finally:
            if should_close:
                db.close()
    
    @staticmethod
    def _sanitize_metadata(metadata: Dict) -> Dict:
        """
        Remove PHI from metadata before logging.
        
        Redacts fields that might contain sensitive data.
        """
        sensitive_keys = [
            "phone", "phone_number", "patient_phone",
            "name", "patient_name", "email",
            "message", "message_body"  # WhatsApp message content
        ]
        
        sanitized = {}
        for key, value in metadata.items():
            if key.lower() in sensitive_keys:
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        
        return sanitized
    
    @staticmethod
    def query_events(
        event_type: Optional[str] = None,
        actor: Optional[str] = None,
        patient_phone: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        db: Session = None
    ) -> list:
        """
        Query audit logs (admin only).
        
        Returns filtered audit entries based on criteria.
        """
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            query = db.query(AuditLog)
            
            # Apply filters
            if event_type:
                query = query.filter(AuditLog.event_type == event_type)
            
            if actor:
                query = query.filter(AuditLog.actor == actor)
            
            if patient_phone:
                phone_hash = AuditLog.hash_phone(patient_phone)
                query = query.filter(AuditLog.patient_phone_hash == phone_hash)
            
            if start_time:
                query = query.filter(AuditLog.timestamp >= start_time)
            
            if end_time:
                query = query.filter(AuditLog.timestamp <= end_time)
            
            # Order by most recent first
            query = query.order_by(AuditLog.timestamp.desc())
            
            # Limit results
            query = query.limit(limit)
            
            return query.all()
        
        finally:
            if should_close:
                db.close()


# Convenience functions for common events
def log_consent_granted(phone: str, db: Session = None):
    """Log consent granted event."""
    return AuditService.log_event(
        event_type=EVENT_TYPES["CONSENT_GRANTED"],
        actor="patient",
        actor_id=phone,
        patient_phone=phone,
        metadata={"action": "consent_granted"},
        db=db
    )


def log_consent_withdrawn(phone: str, db: Session = None):
    """Log consent withdrawn event."""
    return AuditService.log_event(
        event_type=EVENT_TYPES["CONSENT_WITHDRAWN"],
        actor="patient",
        actor_id=phone,
        patient_phone=phone,
        metadata={"action": "consent_withdrawn"},
        db=db
    )


def log_appointment_created(appointment_id: str, patient_phone: str, db: Session = None):
    """Log appointment creation."""
    return AuditService.log_event(
        event_type=EVENT_TYPES["APPOINTMENT_CREATED"],
        actor="patient",
        actor_id=patient_phone,
        patient_phone=patient_phone,
        metadata={"appointment_id": appointment_id},
        db=db
    )


def log_appointment_cancelled(appointment_id: str, patient_phone: str, cancelled_by: str, db: Session = None):
    """Log appointment cancellation."""
    return AuditService.log_event(
        event_type=EVENT_TYPES["APPOINTMENT_CANCELLED"],
        actor=cancelled_by,  # patient/clinic/admin
        actor_id=patient_phone,
        patient_phone=patient_phone,
        metadata={"appointment_id": appointment_id},
        db=db
    )


def log_deletion_completed(phone: str, records_deleted: Dict, db: Session = None):
    """Log data deletion completion."""
    return AuditService.log_event(
        event_type=EVENT_TYPES["DELETION_COMPLETED"],
        actor="patient",
        actor_id=phone,
        patient_phone=phone,
        metadata={"records_deleted": records_deleted},
        db=db
    )


def log_rate_limit_block(phone: str, action: str, db: Session = None):
    """Log rate limiting block."""
    return AuditService.log_event(
        event_type=EVENT_TYPES["RATE_LIMIT_BLOCK"],
        actor="system",
        actor_id="rate_limiter",
        patient_phone=phone,
        metadata={"action": action, "reason": "rate_limit_exceeded"},
        db=db
    )
