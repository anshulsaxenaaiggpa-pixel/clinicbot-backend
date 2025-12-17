"""Patient helper functions for WhatsApp bot"""
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
from datetime import datetime

from app.models.patient import Patient


def get_or_create_patient(
    db: Session,
    clinic_id: UUID,
    phone: str,
    name: Optional[str] = None,
    whatsapp_name: Optional[str] = None
) -> Patient:
    """
    Get existing patient or create new one
    
    This is called automatically when a WhatsApp message arrives
    from a new number.
    
    Args:
        db: Database session
        clinic_id: Clinic UUID
        phone: Phone number (with country code)
        name: Patient name (if provided in message)
        whatsapp_name: Name from WhatsApp profile
        
    Returns:
        Patient object (existing or newly created)
    """
    # Try to find existing patient
    patient = db.query(Patient).filter(
        Patient.clinic_id == clinic_id,
        Patient.phone == phone
    ).first()
    
    if patient:
        # Update WhatsApp name if changed
        if whatsapp_name and patient.whatsapp_name != whatsapp_name:
            patient.whatsapp_name = whatsapp_name
            db.commit()
            db.refresh(patient)
        return patient
    
    # Create new patient
    patient = Patient(
        clinic_id=clinic_id,
        phone=phone,
        name=name or whatsapp_name or f"Patient {phone[-4:]}",  # Default name
        whatsapp_name=whatsapp_name
    )
    
    db.add(patient)
    db.commit()
    db.refresh(patient)
    
    return patient


def update_patient_stats(
    db: Session,
    patient_id: UUID,
    appointment_status: str
):
    """
    Update patient visit statistics
    
    Called when appointment status changes
    
    Args:
        db: Database session
        patient_id: Patient UUID
        appointment_status: 'completed', 'no_show', 'cancelled'
    """
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        return
    
    if appointment_status == "completed":
        patient.total_visits += 1
        if not patient.first_visit_date:
            patient.first_visit_date = datetime.utcnow()
        patient.last_visit_date = datetime.utcnow()
    
    elif appointment_status == "no_show":
        patient.total_no_shows += 1
    
    elif appointment_status == "cancelled":
        patient.total_cancellations += 1
    
    db.commit()
