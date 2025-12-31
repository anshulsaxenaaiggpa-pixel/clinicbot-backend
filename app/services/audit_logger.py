"""
Audit Logger Service - DPDP/GDPR Compliance

Provides simple interface for logging all system actions to immutable audit trail.
All logs are append-only and cannot be modified or deleted.
"""
from typing import Optional, Dict, Any
from app.models.audit_log import AuditLog
from app.db.session import SessionLocal
import uuid
import logging

logger = logging.getLogger(__name__)


def log_action(
    event_type: str,
    actor: str,
    actor_id: str,
    patient_phone: Optional[str] = None,
    event_metadata: Optional[Dict[str, Any]] = None,
    event_id: Optional[str] = None
) -> None:
    """
    Log an action to the immutable audit trail.
    
    Args:
        event_type: Type of event (e.g., "consent_given", "appointment_booked", "login")
        actor: Actor type ("patient", "staff", "admin", "system")
        actor_id: Actor identifier (phone number, user ID, etc.)
        patient_phone: Patient phone number (will be hashed automatically)
        event_metadata: Additional event details (NO PHI!)
        event_id: Optional unique event ID (generated if not provided)
    
    Examples:
        # Consent granted
        log_action("consent_given", "patient", "+919876543210", 
                   patient_phone="+919876543210",
                   event_metadata={"clinic_id": str(clinic_id), "consent_version": "v1.0"})
        
        # Appointment booked
        log_action("appointment_booked", "patient", "+919876543210",
                   patient_phone="+919876543210",
                   event_metadata={"appointment_id": str(appt_id), "doctor_id": str(doc_id)})
        
        # Admin login
        log_action("admin_login", "admin", "admin@clinic.com",
                   event_metadata={"ip_address": "127.0.0.1", "success": True})
    """
    db = SessionLocal()
    try:
        # Generate event ID if not provided
        if not event_id:
            event_id = f"{event_type}_{uuid.uuid4().hex[:12]}"
        
        # Hash patient phone if provided
        patient_phone_hash = None
        if patient_phone:
            patient_phone_hash = AuditLog.hash_phone(patient_phone)
        
        # Create audit log entry
        audit = AuditLog(
            event_id=event_id,
            event_type=event_type,
            actor=actor,
            actor_id=actor_id,
            patient_phone_hash=patient_phone_hash,
            event_metadata=event_metadata or {}
        )
        
        db.add(audit)
        db.commit()
        
        logger.info(f"✅ Audit logged: {event_type} by {actor} ({actor_id[:20]}...)")
        
    except Exception as e:
        logger.error(f"❌ Failed to log audit event {event_type}: {e}")
        db.rollback()
        # Don't raise - audit logging should never break main flow
    finally:
        db.close()


def log_consent_action(phone: str, clinic_id: str, consent_given: bool) -> None:
    """
    Convenience function for logging consent actions.
    
    Args:
        phone: Patient phone number
        clinic_id: Clinic UUID
        consent_given: Whether consent was granted or declined
    """
    event_type = "consent_given" if consent_given else "consent_declined"
    
    log_action(
        event_type=event_type,
        actor="patient",
        actor_id=phone,
        patient_phone=phone,
        event_metadata={
            "clinic_id": clinic_id,
            "consent_version": "v1.0",
            "consent_given": consent_given
        }
    )


def log_appointment_action(
    action: str,  # "booked", "cancelled", "completed", "no_show"
    phone: str,
    clinic_id: str,
    appointment_id: str,
    doctor_id: Optional[str] = None,
    reason: Optional[str] = None
) -> None:
    """
    Convenience function for logging appointment actions.
    
    Args:
        action: Appointment action type
        phone: Patient phone number
        clinic_id: Clinic UUID
        appointment_id: Appointment UUID
        doctor_id: Optional doctor UUID
        reason: Optional cancellation/no-show reason
    """
    event_type = f"appointment_{action}"
    metadata = {
        "clinic_id": clinic_id,
        "appointment_id": appointment_id
    }
    
    if doctor_id:
        metadata["doctor_id"] = doctor_id
    if reason:
        metadata["reason"] = reason
    
    log_action(
        event_type=event_type,
        actor="patient",
        actor_id=phone,
        patient_phone=phone,
        event_metadata=metadata
    )


def log_admin_action(
    action: str,  # "login", "logout", "view_patient", "edit_appointment", etc.
    admin_email: str,
    clinic_id: str,
    target_entity_type: Optional[str] = None,
    target_entity_id: Optional[str] = None,
    ip_address: Optional[str] = None
) -> None:
    """
    Convenience function for logging admin actions.
    
    Args:
        action: Admin action type
        admin_email: Admin user email
        clinic_id: Clinic UUID
        target_entity_type: Optional entity type (e.g., "patient", "appointment")
        target_entity_id: Optional entity UUID
        ip_address: Optional IP address
    """
    metadata = {"clinic_id": clinic_id}
    
    if target_entity_type:
        metadata["target_entity_type"] = target_entity_type
    if target_entity_id:
        metadata["target_entity_id"] = target_entity_id
    if ip_address:
        metadata["ip_address"] = ip_address
    
    log_action(
        event_type=f"admin_{action}",
        actor="admin",
        actor_id=admin_email,
        event_metadata=metadata
    )
