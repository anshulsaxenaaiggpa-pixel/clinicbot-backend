"""
Audit Log Model - MODULE 4

Immutable event logging for compliance and debugging.
Tracks all system actions for auditability.
"""
from sqlalchemy import Column, String, DateTime, Index, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid
import hashlib

from app.db.base_class import Base


class AuditLog(Base):
    """
    Immutable audit trail for all system actions.
    
    Cannot be updated or deleted once written.
    Retention: 5 years minimum for compliance.
    """
    __tablename__ = "audit_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Event identification
    event_id = Column(String(100), nullable=False)  # Unique event identifier
    event_type = Column(String(50), nullable=False)  # Type of event
    
    # Actor (who performed the action)
    actor = Column(String(20), nullable=False)  # system/clinic/admin/patient
    actor_id = Column(String(100), nullable=False)  # ID or phone (hashed if needed)
    
    # Patient identification (hashed for privacy)
    patient_phone_hash = Column(String(64), nullable=True)  # SHA256 hash
    
    # Event details
    event_metadata = Column(JSONB, nullable=True)  # Additional context (NO PHI)
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    # Indexes for queries
    __table_args__ = (
        Index("idx_audit_event_type", "event_type"),
        Index("idx_audit_actor", "actor", "actor_id"),
        Index("idx_audit_timestamp", "timestamp"),
        Index("idx_audit_patient_hash", "patient_phone_hash"),
        # Immutability enforced via migration rules
    )
    
    @staticmethod
    def hash_phone(phone: str) -> str:
        """Hash phone number for privacy-preserving audit logs."""
        return hashlib.sha256(phone.encode()).hexdigest()
    
    def __repr__(self):
        return f"<AuditLog {self.event_type} by {self.actor} at {self.timestamp}>"
