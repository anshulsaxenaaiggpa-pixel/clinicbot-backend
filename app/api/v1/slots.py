"""Slot availability endpoints - exposes slot engine via REST API"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from uuid import UUID

from app.db.database import get_db
from app.models.clinic import Clinic
from app.models.doctor import Doctor
from app.models.service import Service
from app.models.appointment import Appointment
from app.models.clinic_timing import ClinicTiming, ClosedDate
from app.schemas.slot import SlotResponse, SlotsAvailableResponse, ServiceAvailability
from app.services.slot_engine import generate_free_slots_for_day
from app.utils.errors import InvalidClinicError, InvalidDoctorError

router = APIRouter()


@router.get("/", response_model=SlotsAvailableResponse)
def get_available_slots(
    clinic_id: UUID = Query(...),
    doctor_id: UUID = Query(...),
    date: date = Query(...),
    service_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get available appointment slots for a doctor on a specific date.
    
    This is the CRITICAL endpoint that WhatsApp bot and dashboard use.
    """
    # Validate clinic exists
    clinic = db.query(Clinic).filter(Clinic.id == clinic_id).first()
    if not clinic:
        raise InvalidClinicError()
    
    # Validate doctor exists and belongs to clinic
    doctor = db.query(Doctor).filter(
        Doctor.id == doctor_id,
        Doctor.clinic_id == clinic_id,
        Doctor.is_active == True
    ).first()
    if not doctor:
        raise InvalidDoctorError()
    
    # Build clinic configuration for slot engine
    clinic_config = _build_clinic_config(clinic, db)
    
    # Get existing appointments for this doctor on this date
    existing_appointments = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.date == date,
        Appointment.status.in_(['confirmed', 'pending'])
    ).all()
    
    # Convert to slot engine format
    existing_appts = [
        {
            "doctor_id": str(appt.doctor_id),
            "start_utc_ts": appt.start_utc_ts,
            "end_utc_ts": appt.end_utc_ts
        }
        for appt in existing_appointments
    ]
    
    # Generate free slots using the slot engine
    free_slots = generate_free_slots_for_day(
        config=clinic_config,
        target_date=date,
        existing_appointments=existing_appts,
        doctor_id_filter=str(doctor_id)
    )
    
    # Get available services for this doctor
    services = db.query(Service).filter(
        Service.clinic_id == clinic_id,
        Service.is_active == True
    ).all()
    
    # Format response
    slots_response = []
    for slot in free_slots:
        # Filter services that can fit in available time
        available_services = [
            ServiceAvailability(
                service_id=svc.id,
                name=svc.name,
                duration_minutes=svc.duration_minutes,
                fee=svc.default_fee
            )
            for svc in services
            if svc.duration_minutes <= slot['duration_mins']
        ]
        
        slots_response.append(SlotResponse(
            slot_id=slot['slot_id'],
            doctor_id=UUID(slot['doctor_id']),
            doctor_name=doctor.name,
            start_local=slot['start_local'],
            end_local=slot['end_local'],
            start_utc_ts=slot['start_utc_ts'],
            end_utc_ts=slot['end_utc_ts'],
            duration_mins=slot['duration_mins'],
            available_services=available_services
        ))
    
    return SlotsAvailableResponse(
        date=date,
        doctor_id=doctor_id,
        doctor_name=doctor.name,
        total_slots=len(slots_response),
        slots=slots_response
    )


def _build_clinic_config(clinic: Clinic, db: Session) -> dict:
    """Build configuration dict for slot engine from database"""
    # Get clinic timing
    timings = db.query(ClinicTiming).filter(ClinicTiming.clinic_id == clinic.id).all()
    
    # Build timing dict
    clinic_timing = {}
    for timing in timings:
        if timing.day_of_week == "saturday":
            clinic_timing["saturday"] = {
                "closed": timing.is_closed,
                "start": timing.start_time.strftime("%H:%M") if timing.start_time else None,
                "end": timing.end_time.strftime("%H:%M") if timing.end_time else None
            }
        elif timing.day_of_week == "sunday":
            clinic_timing["sunday_closed"] = timing.is_closed
        else:
            # Weekdays - assume same for all weekdays
            if "weekdays" not in clinic_timing:
                clinic_timing["weekdays"] = {
                    "start": timing.start_time.strftime("%H:%M"),
                    "end": timing.end_time.strftime("%H:%M")
                }
                if timing.lunch_enabled:
                    clinic_timing["weekdays"]["lunch_break"] = {
                        "enabled": True,
                        "start": timing.lunch_start.strftime("%H:%M"),
                        "end": timing.lunch_end.strftime("%H:%M")
                    }
    
    # Get closed dates
    closed_dates = db.query(ClosedDate).filter(ClosedDate.clinic_id == clinic.id).all()
    clinic_timing["closed_dates"] = [cd.closed_date.strftime("%Y-%m-%d") for cd in closed_dates]
    
    # Get doctors
    doctors = db.query(Doctor).filter(
        Doctor.clinic_id == clinic.id,
        Doctor.is_active == True
    ).all()
    
    doctors_list = [
        {
            "id": str(doc.id),
            "name": doc.name,
            "specialization": doc.specialization,
            "fee": doc.default_fee
        }
        for doc in doctors
    ]
    
    # Get services
    services = db.query(Service).filter(
        Service.clinic_id == clinic.id,
        Service.is_active == True
    ).all()
    
    services_list = [
        {
            "id": str(svc.id),
            "name": svc.name,
            "duration_minutes": svc.duration_minutes,
            "duration": svc.duration_minutes,  # Alias for compatibility
            "fee": svc.default_fee
        }
        for svc in services
    ]
    
    # Build doctor-services mapping (for now, assume all doctors offer all services)
    # TODO: Replace with actual many-to-many relationship query
    doctor_services = {
        str(doc.id): [str(svc.id) for svc in services]
        for doc in doctors
    }
    
    return {
        "timezone": clinic.timezone,
        "clinic_timing": clinic_timing,
        "appointment_config": {
            "slots_per_hour": 4,
            "slot_interval_mins": 15,
            "buffer_mins": 5,
            "max_advance_days": 7
        },
        "doctors": doctors_list,
        "services": services_list,
        "doctor_services": doctor_services
    }
