"""
Data Deletion Service - MODULE 3

Implements DPDP-compliant patient data deletion with:
- Keyword detection (DELETE/REMOVE/ERASE/FORGET)
- Identity verification
- Anonymization of PHI
- Immutable audit trail
- Ghost recreation prevention
"""
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_
import hashlib

from app.models.patient import Patient
from app.models.appointment import Appointment
from app.models.consent import ConsentLog
from app.models.patient_deletion import PatientDeletion
from app.db.session import SessionLocal


# Deletion keywords per Module 3 spec
DELETION_KEYWORDS = ["DELETE", "REMOVE", "ERASE", "FORGET"]


class DeletionService:
    """Service for handling patient data deletion requests."""
    
    @staticmethod
    def is_deletion_request(message: str) -> bool:
        """
        Check if message is a deletion request.
        
        Recognizes: DELETE, REMOVE, ERASE, FORGET (case-insensitive)
        """
        normalized = message.strip().upper()
        return normalized in DELETION_KEYWORDS
    
    @staticmethod
    def check_already_deleted(phone_number: str, db: Session = None) -> bool:
        """
        Check if phone number was already deleted.
        
        Prevents ghost recreation collisions.
        """
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            deletion = db.query(PatientDeletion).filter(
                PatientDeletion.phone_number == phone_number,
                PatientDeletion.deletion_status == "completed"
            ).first()
            
            return deletion is not None
        
        finally:
            if should_close:
                db.close()
    
    @staticmethod
    def anonymize_patient_data(
        phone_number: str,
        requested_by: str = "patient",
        db: Session = None
    ) -> Dict:
        """
        Delete patient data and anonymize records.
        
        Module 3 Workflow:
        1. Verify identity via phone number match
        2. Delete patient profile
        3. Anonymize appointments (keep for audit)
        4. Delete consent records
        5. Retain anonymized audit logs
        6. Mark as deleted to prevent recreation
        7. Return confirmation
        
        Returns:
            {
                "status": "completed" | "failed",
                "phone_masked": masked phone,
                "records_deleted": {
                    "patients": count,
                    "appointments": count,
                    "consents": count
                },
                "timestamp": ISO timestamp
            }
        """
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            # Check if already deleted
            if DeletionService.check_already_deleted(phone_number, db):
                return {
                    "status": "already_deleted",
                    "message": "This phone number was previously deleted.",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Create deletion log entry (pending)
            deletion_log = PatientDeletion(
                phone_number=phone_number,
                deletion_requested_at=datetime.utcnow(),
                deletion_status="pending",
                requested_by=requested_by,
                verification_method="phone_match"
            )
            db.add(deletion_log)
            db.flush()  # Get ID but don't commit yet
            
            # Count records before deletion
            patient_count = 0
            appointment_count = 0
            consent_count = 0
            
            # Generate anonymized identifiers
            phone_hash = hashlib.sha256(phone_number.encode()).hexdigest()[:12]
            masked_phone = "+91XXXXXXXXX"
            anon_name = f"DELETED_USER_{phone_hash}"
            
            # Delete patient record
            patient = db.query(Patient).filter(
                Patient.phone == phone_number
            ).first()
            
            if patient:
                db.delete(patient)
                patient_count = 1
            
            # Anonymize appointments (keep for audit/stats)
            appointments = db.query(Appointment).filter(
                Appointment.patient_phone == phone_number
            ).all()
            
            for apt in appointments:
                apt.patient_phone = masked_phone
                apt.patient_name = anon_name
                appointment_count += 1
            
            # Delete consent records (using ConsentLog)
            consents = db.query(ConsentLog).filter(
                ConsentLog.phone == phone_number
            ).all()
            
            for consent in consents:
                db.delete(consent)
                consent_count += 1
            
            # Update deletion log with counts
            deletion_log.patient_records_deleted = patient_count
            deletion_log.appointment_records_deleted = appointment_count
            deletion_log.consent_records_deleted = consent_count
            deletion_log.deletion_completed_at = datetime.utcnow()
            deletion_log.deletion_status = "completed"
            
            # Commit all changes atomically
            db.commit()
            
            return {
                "status": "completed",
                "phone_masked": masked_phone,
                "records_deleted": {
                    "patients": patient_count,
                    "appointments": appointment_count,
                    "consents": consent_count
                },
                "message": "Your data has been deleted. Anonymized records retained for legal audit purposes only.",
                "timestamp": deletion_log.deletion_completed_at.isoformat()
            }
        
        except Exception as e:
            db.rollback()
            
            # Mark deletion as failed in log
            try:
                deletion_log.deletion_status = "failed"
                db.commit()
            except:
                pass
            
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        
        finally:
            if should_close:
                db.close()
    
    @staticmethod
    def get_deletion_status(phone_number: str, db: Session = None) -> Optional[Dict]:
        """
        Get deletion status for a phone number.
        
        Returns None if no deletion requested, otherwise status dict.
        """
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            deletion = db.query(PatientDeletion).filter(
                PatientDeletion.phone_number == phone_number
            ).order_by(PatientDeletion.created_at.desc()).first()
            
            if deletion is None:
                return None
            
            return {
                "status": deletion.deletion_status,
                "requested_at": deletion.deletion_requested_at.isoformat(),
                "completed_at": deletion.deletion_completed_at.isoformat() if deletion.deletion_completed_at else None,
                "records_deleted": {
                    "patients": deletion.patient_records_deleted,
                    "appointments": deletion.appointment_records_deleted,
                    "consents": deletion.consent_records_deleted
                }
            }
        
        finally:
            if should_close:
                db.close()


# Convenience function
def delete_patient_data(phone_number: str, requested_by: str = "patient") -> Dict:
    """Delete patient data (convenience wrapper)."""
    return DeletionService.anonymize_patient_data(phone_number, requested_by)
