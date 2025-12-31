"""Doctor database model"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.base_class import Base


class Doctor(Base):
    """
    Doctor/Practitioner entity
    
    **v1.1 Hybrid Booking Support:**
    - whatsapp_number: Direct booking contact
    - city: For city-level search
    - is_searchable: Privacy opt-in (default False)
    """
    __tablename__ = "doctors"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clinic_id = Column(UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False)
    
    name = Column(String(80), nullable=False)
    specialization = Column(String(50))
    default_fee = Column(Integer)  # Default consultation fee in rupees
    
    # **NEW v1.1:** Hybrid booking support
    whatsapp_number = Column(String(20), unique=True, nullable=True)  # E.164 format
    city = Column(String(100), nullable=True)  # For city-level search
    is_searchable = Column(Boolean, default=False, nullable=False)  # Privacy opt-in
    
    # Optional: Per-doctor availability override
    custom_availability = Column(JSON, nullable=True)  # Override clinic timing if needed
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    clinic = relationship("Clinic", back_populates="doctors")
    appointments = relationship("Appointment", back_populates="doctor")
    
    # **NEW v1.1:** Hybrid booking helpers
    def get_shareable_link(self) -> str:
        """Generate WhatsApp click-to-chat link for direct booking."""
        if not self.whatsapp_number:
            return None
        clean_number = self.whatsapp_number.replace("+", "")
        return f"https://wa.me/{clean_number}?text=Hi"
    
    def get_qr_code_data(self) -> str:
        """Get data for QR code generation (WhatsApp link)."""
        return self.get_shareable_link()
    
    def set_searchable(self, searchable: bool):
        """Update search visibility (opt-in/opt-out). Privacy: default False."""
        self.is_searchable = searchable
        self.updated_at = datetime.utcnow()

