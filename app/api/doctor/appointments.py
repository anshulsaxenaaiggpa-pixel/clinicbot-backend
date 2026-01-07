"""
Doctor Appointments Routes

Appointment listing and management (complete/cancel).
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session
from datetime import datetime

from app.api.doctor.dependencies import require_doctor, validate_csrf
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.db.session import get_db


router = APIRouter(prefix="/doctor", tags=["doctor-appointments"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent.parent / "templates"))


@router.get("/appointments", response_class=HTMLResponse)
async def list_appointments(
    request: Request,
    filter: str = "today",
    doctor: Doctor = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    """List doctor's appointments with filter (today/upcoming/past)."""
    try:
        # Base query
        query = db.query(Appointment).filter(Appointment.doctor_id == doctor.id)
        
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        # Apply filter
        if filter == "today":
            query = query.filter(
                Appointment.date >= today_start,
                Appointment.date <= today_end
            )
        elif filter == "upcoming":
            query = query.filter(Appointment.date > today_end)
        elif filter == "past":
            query = query.filter(Appointment.date < today_start)
        
        appointments = query.order_by(Appointment.start_utc_ts.desc()).all()
        
        return templates.TemplateResponse(
            "doctor/appointments.html",
            {
                "request": request,
                "doctor": doctor,
                "csrf_token": request.state.csrf_token,
                "appointments": appointments,
                "filter": filter,
                "consultation_fee": doctor.consultation_fee
            }
        )
    
    except Exception as e:
        import traceback
        print(f"❌ Appointments error: {traceback.format_exc()}")
        return HTMLResponse(
            content=f"<h1>Error</h1><pre>{traceback.format_exc()}</pre>",
            status_code=500
        )


@router.post("/appointments/{appointment_id}/complete")
async def complete_appointment(
    request: Request,
    appointment_id: str,
    doctor: Doctor = Depends(require_doctor),
    csrf_valid: bool = Depends(validate_csrf),
    db: Session = Depends(get_db)
):
    """Mark appointment as completed."""
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.doctor_id == doctor.id
    ).first()
    
    if appointment:
        appointment.status = 'completed'
        db.commit()
    
    return RedirectResponse(url="/doctor/appointments", status_code=302)


@router.post("/appointments/{appointment_id}/cancel")
async def cancel_appointment(
    request: Request,
    appointment_id: str,
    doctor: Doctor = Depends(require_doctor),
    csrf_valid: bool = Depends(validate_csrf),
    db: Session = Depends(get_db)
):
    """Cancel appointment."""
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.doctor_id == doctor.id
    ).first()
    
    if appointment:
        appointment.status = 'cancelled'
        db.commit()
    
    return RedirectResponse(url="/doctor/appointments", status_code=302)
