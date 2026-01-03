from sqlalchemy import Column, String, DateTime, ForeignKey, Index
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime
import uuid
from app.db.base_class import Base

class AuditLog(Base):
    __tablename__ = "audit_log"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    clinic_id = Column(String(36), ForeignKey("clinics.id"), nullable=True)  # Changed to nullable
    actor_type = Column(String(20), nullable=False)  # PATIENT/STAFF/SYSTEM
    actor_reference = Column(String(100), nullable=False)  # phone/staff_id
    action = Column(String(50), nullable=False)  # CONSENT_GIVEN/BOOK_APPOINTMENT
    entity_type = Column(String(50), nullable=False)  # CONSENT/APPOINTMENT
    entity_id = Column(String(36), nullable=True)
    old_state = Column(sa.JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True)
    new_state = Column(sa.JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)
    ip_address = Column(String(50), nullable=True)

    # Indexes for query performance
    __table_args__ = (
        Index('idx_audit_clinic_timestamp', 'clinic_id', 'timestamp'),
        Index('idx_audit_action', 'action'),
        Index('idx_audit_entity', 'entity_type', 'entity_id'),
    )
