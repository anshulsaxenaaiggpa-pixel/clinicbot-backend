from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.db.base_class import Base

class ConsentLog(Base):
    __tablename__ = "consent_log"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone = Column(String(15), nullable=False, index=True)
    clinic_id = Column(String(36), ForeignKey("clinics.id"), nullable=False)
    consent_given = Column(Boolean, nullable=False)
    consent_source = Column(String(20), default="whatsapp", nullable=False)
    consent_version = Column(String(20), default="v1.0", nullable=False)
    consent_text = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    ip_address = Column(String(50), nullable=True)
    
    clinic = relationship("Clinic")
    __table_args__ = (Index("idx_consent_clinic_phone", "clinic_id", "phone"),)
