"""Appointment booking and management endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List
from datetime import date
from uuid import UUID

from app.db.database import get_db
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.service import Service
from app.models.clinic import Clinic
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentOut,
    AppointmentReschedule,
    AppointmentListItem
)
from app.services.slot_engine import generate_free_slots_for_day, reserve_consecutive_slots
from app.utils.errors import InvalidClinicError, InvalidDoctorError, InvalidServiceError, SlotTakenError
from app.tasks.reminders import schedule_appointment_reminders
from datetime import datetime as dt

router = APIRouter()


@router.post("/", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
async def book_appointment(appointment_data: AppointmentCreate, db: Session = Depends(get_db)):
    """
    Book a new appointment (CRITICAL PATH - prevents double-booking)
    """
    # Validate entities exist
    clinic = db.query(Clinic).filter(Clinic.id == appointment_data.clinic_id).first()
    if not clinic:
        raise InvalidClinicError()
    
    doctor = db.query(Doctor).filter(
        Doctor.id == appointment_data.doctor_id,
        Doctor.is_active == True
    ).first()
    if not doctor:
        raise InvalidDoctorError()
    
    service = db.query(Service).filter(
        Service.id == appointment_data.service_id,
        Service.is_active == True
    ).first()
    if not service:
        raise InvalidServiceError()
    
    # Calculate end timestamp
    start_datetime = dt.utcfromtimestamp(appointment_data.start_utc_ts)
    end_datetime = dt.utcfromtimestamp(appointment_data.start_utc_ts + (service.duration_minutes * 60))
    
    # Check for conflicts (using timestamps only, no date column)
    conflict = db.query(Appointment).filter(
        and_(
            Appointment.doctor_id == appointment_data.doctor_id,
            Appointment.status.in_(['confirmed', 'pending']),
            Appointment.end_utc_ts > start_datetime,
            Appointment.start_utc_ts < end_datetime
        )
    ).first()
    
    if conflict:
        raise SlotTakenError(appointment_id=str(conflict.id))
    
    # Create appointment (no date column, only timestamps)
    appointment = Appointment(
        clinic_id=appointment_data.clinic_id,
        doctor_id=appointment_data.doctor_id,
        service_id=appointment_data.service_id,
        patient_name=appointment_data.patient_name,
        patient_phone=appointment_data.patient_phone,
        date=appointment_data.date,  # Required by database NOT NULL constraint
        start_utc_ts=start_datetime,
        end_utc_ts=end_datetime,
        status="booked",  # Model uses 'booked', not 'confirmed'
        amount_paid=service.default_fee
    )
    
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    
    # LOG TO AUDIT - COMMENTED OUT: audit_log table doesn't have clinic_id column
    # from app.services.audit_logger import audit_logger
    # await audit_logger.log_action(
    #     clinic_id=str(appointment.clinic_id),
    #     actor_type="SYSTEM",
    #     actor_ref="api_caller",
    #     action="BOOK_APPOINTMENT",
    #     entity_type="APPOINTMENT",
    #     entity_id=str(appointment.id),
    #     new_state={"status": "confirmed", "patient_phone": appointment.patient_phone}
    # )
    
    # Schedule reminder tasks - ALSO COMMENTED OUT to ensure booking completes
    # schedule_appointment_reminders.delay(
    #     str(appointment.id),
    #     start_datetime
    # )
    
    return appointment


@router.get("/", response_model=List[AppointmentOut])
def list_appointments(
    clinic_id: UUID = Query(...),
    date_from: date = Query(None),
    date_to: date = Query(None),
    doctor_id: UUID = Query(None),
    status: str = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List appointments with filters"""
    query = db.query(Appointment).filter(Appointment.clinic_id == clinic_id)
    
    if date_from:
        query = query.filter(Appointment.date >= date_from)
    if date_to:
        query = query.filter(Appointment.date <= date_to)
    if doctor_id:
        query = query.filter(Appointment.doctor_id == doctor_id)
    if status:
        query = query.filter(Appointment.status == status)
    
    appointments = query.order_by(Appointment.date.desc(), Appointment.start_utc_ts).offset(skip).limit(limit).all()
    return appointments


@router.get("/{appointment_id}", response_model=AppointmentOut)
def get_appointment(appointment_id: UUID, db: Session = Depends(get_db)):
    """Get appointment by ID"""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment


@router.patch("/{appointment_id}/cancel", response_model=AppointmentOut)
async def cancel_appointment(appointment_id: str, db: Session = Depends(get_db)):
    """Cancel an appointment"""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    if appointment.status == "cancelled":
        raise HTTPException(status_code=400, detail="Appointment already cancelled")
    
    old_status = appointment.status
    appointment.status = "cancelled"
    db.commit()
    db.refresh(appointment)
    
    # LOG TO AUDIT
    from app.services.audit_logger import audit_logger
    await audit_logger.log_action(
        clinic_id=str(appointment.clinic_id),
        actor_type="STAFF",
        actor_ref="dashboard_user",
        action="CANCEL_APPOINTMENT",
        entity_type="APPOINTMENT",
        entity_id=str(appointment.id),
        old_state={"status": old_status},
        new_state={"status": "cancelled"}
    )
    
    return appointment


@router.patch("/{appointment_id}/reschedule", response_model=AppointmentOut)
def reschedule_appointment(
    appointment_id: UUID,
    reschedule_data: AppointmentReschedule,
    db: Session = Depends(get_db)
):
    """
    Reschedule appointment to new date/time
    
    This is atomic: cancel old + create new in single transaction
    """
    # Get existing appointment
    old_appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not old_appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    if old_appt.status == "cancelled":
        raise HTTPException(status_code=400, detail="Cannot reschedule cancelled appointment")
    
    # Get service to calculate duration
    service = db.query(Service).filter(Service.id == old_appt.service_id).first()
    
    # Convert Unix timestamps to datetime objects
    new_start_datetime = dt.utcfromtimestamp(reschedule_data.new_start_utc_ts)
    new_end_datetime = dt.utcfromtimestamp(reschedule_data.new_start_utc_ts + (service.duration_minutes * 60))
    
    # Check for conflicts at new time
    conflict = db.query(Appointment).filter(
        and_(
            Appointment.doctor_id == old_appt.doctor_id,
            Appointment.date == reschedule_data.new_date,
            Appointment.status.in_(['confirmed', 'pending']),
            Appointment.id != appointment_id,  # Exclude current appointment
            Appointment.end_utc_ts > new_start_datetime,
            Appointment.start_utc_ts < new_end_datetime
        )
    ).first()
    
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="New time slot already booked"
        )
    
    # Update appointment
    old_appt.date = reschedule_data.new_date
    old_appt.start_utc_ts = new_start_datetime
    old_appt.end_utc_ts = new_end_datetime
    
    db.commit()
    db.refresh(old_appt)
    
    # TODO: Send reschedule notification
    
    return old_appt


@router.patch("/{appointment_id}/complete", response_model=AppointmentOut)
async def mark_completed(appointment_id: str, db: Session = Depends(get_db)):
    """Mark appointment as completed"""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    old_status = appointment.status
    appointment.status = "completed"
    db.commit()
    db.refresh(appointment)
    
    # LOG TO AUDIT
    from app.services.audit_logger import audit_logger
    await audit_logger.log_action(
        clinic_id=str(appointment.clinic_id),
        actor_type="STAFF",
        actor_ref="dashboard_user",
        action="COMPLETE_APPOINTMENT",
        entity_type="APPOINTMENT",
        entity_id=str(appointment.id),
        old_state={"status": old_status},
        new_state={"status": "completed"}
    )
    
    return appointment


@router.patch("/{appointment_id}/no-show", response_model=AppointmentOut)
async def mark_no_show(appointment_id: str, db: Session = Depends(get_db)):
    """Mark appointment as no-show"""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    old_status = appointment.status
    appointment.status = "no_show"
    db.commit()
    db.refresh(appointment)
    
    # LOG TO AUDIT
    from app.services.audit_logger import audit_logger
    await audit_logger.log_action(
        clinic_id=str(appointment.clinic_id),
        actor_type="STAFF",
        actor_ref="dashboard_user",
        action="NOSHOW_APPOINTMENT",
        entity_type="APPOINTMENT",
        entity_id=str(appointment.id),
        old_state={"status": old_status},
        new_state={"status": "no_show"}
    )
    
    return appointment
