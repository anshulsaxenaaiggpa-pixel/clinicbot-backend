"""
Patient Deletion Model - MODULE 3

Immutable log of data deletion requests and execution.
Prevents ghost recreation collisions and provides audit trail.
"""
from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.db.base_class import Base


class PatientDeletion(Base):
    """
    Immutable deletion log for DPDP compliance.
    
    Records all deletion requests and executions.
    Prevents re-creating deleted patients accidentally.
    """
    __tablename__ = "patient_deletion_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Identity (stored for collision prevention only)
    phone_number = Column(String(15), nullable=False)
    
    # Deletion metadata
    deletion_requested_at = Column(DateTime(timezone=True), nullable=False)
    deletion_completed_at = Column(DateTime(timezone=True), nullable=True)
    deletion_status = Column(String(20), default="pending", nullable=False)  # pending/completed/failed
    
    # What was deleted
    patient_records_deleted = Column(Integer, default=0)
    appointment_records_deleted = Column(Integer, default=0)
    consent_records_deleted = Column(Integer, default=0)
    
    # Who triggered (system/patient/admin)
    requested_by = Column(String(20), default="patient", nullable=False)
    
    # Verification
    verification_method = Column(String(50), default="phone_match", nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    # Indexes for lookup
    __table_args__ = (
        Index("idx_deletion_phone", "phone_number"),
        Index("idx_deletion_status", "deletion_status"),
        # Immutability enforced via migration rules
    )
    
    def __repr__(self):
        return f"<PatientDeletion {self.phone_number} {self.deletion_status}>"
