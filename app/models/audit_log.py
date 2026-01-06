from sqlalchemy import Column, String, DateTime, Index
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime
import uuid
from app.db.base_class import Base

class AuditLog(Base):
    __tablename__ = "audit_log"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(String(100), nullable=False)  # Unique event identifier
    event_type = Column(String(50), nullable=False)  # Type of event
    actor = Column(String(50), nullable=False)  # Who performed (admin/patient/system)
    actor_id = Column(String(100), nullable=True)  # Actor identifier
    patient_phone_hash = Column(String(100), nullable=True)  # Hashed phone if patient-related
    event_metadata = Column(sa.Text, nullable=True)  # JSON string of metadata
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Indexes for query performance
    __table_args__ = (
        Index('idx_audit_event_type', 'event_type'),
        Index('idx_audit_timestamp', 'timestamp'),
    )
