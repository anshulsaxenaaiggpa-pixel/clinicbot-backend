"""
Booking State Machine - WhatsApp Flow

Manages conversation state for appointment booking.
Stores ONLY metadata, never full chat transcripts per COMPLIANCE_BASELINE.md
"""
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from app.db.base_class import Base


class BookingState(str, Enum):
    """
    Booking conversation states.
    
    Linear flow (cannot skip steps):
    INITIAL → CONSENT_PENDING → AGE_VERIFICATION → CLINIC_SELECTION → 
    DOCTOR_SELECTION → SERVICE_SELECTION → DATE_SELECTION → TIME_SELECTION → CONFIRMED
    """
    INITIAL = "initial"
    CONSENT_PENDING = "consent_pending"
    AGE_VERIFICATION = "age_verification"
    CLINIC_SELECTION = "clinic_selection"
    DOCTOR_SELECTION = "doctor_selection"
    SERVICE_SELECTION = "service_selection"
    DATE_SELECTION = "date_selection"
    TIME_SELECTION = "time_selection"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class ConversationState(Base):
    """
    Tracks booking conversation state per user.
    
    Per COMPLIANCE_BASELINE.md:
    - NO chat transcript storage
    - Only structured metadata
    - Auto-expire after 24 hours of inactivity
    
    Privacy: This table contains NO PHI except phone number (which is deleted on request).
    """
    __tablename__ = "conversation_states"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # User identity
    phone_number = Column(String(20), unique=True, nullable=False)  # E.164
    
    # State tracking
    current_state = Column(
        SQLEnum(BookingState, name="booking_state"),
        default=BookingState.INITIAL,
        nullable=False
    )
    
    # Booking context (structured metadata only)
    context = Column(JSONB, nullable=True)  # {clinic_id, doctor_id, service_id, selected_date}
    
    # State management
    last_message_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)  # 24 hours from last_message
    
    # Flags
    consent_granted = Column(Boolean, default=False, nullable=False)
    age_verified = Column(Boolean, default=False, nullable=False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Auto-set expiry to 24 hours
        if not self.expires_at:
            from datetime import timedelta
            self.expires_at = datetime.utcnow() + timedelta(hours=24)
    
    def update_activity(self):
        """Update last activity and extend expiry."""
        from datetime import timedelta
        self.last_message_at = datetime.utcnow()
        self.expires_at = datetime.utcnow() + timedelta(hours=24)
    
    def set_context(self, key: str, value: Any):
        """
        Store booking context.
        
        ALLOWED keys: clinic_id, doctor_id, service_id, selected_date, selected_time
        PROHIBITED: Any medical content, symptoms, reasons
        """
        if self.context is None:
            self.context = {}
        
        # Validate no prohibited keys
        prohibited_keys = ['symptoms', 'reason', 'diagnosis', 'medical_notes', 'complaint']
        if key.lower() in prohibited_keys:
            from app.schemas.data_classification import ProhibitedDataError
            raise ProhibitedDataError(f"Cannot store '{key}' - medical content prohibited")
        
        self.context[key] = value
    
    def get_context(self, key: str) -> Optional[Any]:
        """Get context value."""
        if self.context is None:
            return None
        return self.context.get(key)
    
    def advance_state(self, next_state: BookingState):
        """Advance to next state."""
        self.current_state = next_state
        self.update_activity()
    
    def reset(self):
        """Reset conversation state."""
        self.current_state = BookingState.INITIAL
        self.context = {}
        self.update_activity()
    
    def is_expired(self) -> bool:
        """Check if conversation has expired."""
        return datetime.utcnow() > self.expires_at


class StateManager:
    """
    Manages conversation state transitions.
    
    Enforces linear flow and validation.
    """
    
    @staticmethod
    def get_or_create_state(phone: str, db) -> ConversationState:
        """Get existing state or create new."""
        state = db.query(ConversationState).filter(
            ConversationState.phone_number == phone
        ).first()
        
        if state:
            # Check if expired
            if state.is_expired():
                # Reset expired state
                state.reset()
                db.commit()
            return state
        
        # Create new state
        state = ConversationState(phone_number=phone)
        db.add(state)
        db.commit()
        db.refresh(state)
        return state
    
    @staticmethod
    def can_advance(current: BookingState, next_state: BookingState) -> bool:
        """
        Check if state transition is allowed.
        
        Enforces linear flow (no skipping).
        """
        valid_transitions = {
            BookingState.INITIAL: [BookingState.CONSENT_PENDING],
            BookingState.CONSENT_PENDING: [BookingState.AGE_VERIFICATION],
            BookingState.AGE_VERIFICATION: [BookingState.CLINIC_SELECTION],
            BookingState.CLINIC_SELECTION: [BookingState.DOCTOR_SELECTION],
            BookingState.DOCTOR_SELECTION: [BookingState.SERVICE_SELECTION],
            BookingState.SERVICE_SELECTION: [BookingState.DATE_SELECTION],
            BookingState.DATE_SELECTION: [BookingState.TIME_SELECTION],
            BookingState.TIME_SELECTION: [BookingState.CONFIRMED],
            BookingState.CONFIRMED: [BookingState.INITIAL],  # Start new booking
        }
        
        allowed = valid_transitions.get(current, [])
        return next_state in allowed
