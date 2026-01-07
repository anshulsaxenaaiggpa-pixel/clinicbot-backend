"""
Doctor Dashboard Routes

Overview dashboard with today's metrics and quick stats.
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from app.api.doctor.dependencies import require_doctor
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.db.session import get_db


router = APIRouter(prefix="/doctor", tags=["doctor-dashboard"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent.parent / "templates"))


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    doctor: Doctor = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    """Doctor dashboard with today's statistics."""
    try:
        # Get today's date range
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        # Today's appointments
        today_appointments = db.query(Appointment).filter(
            Appointment.doctor_id == doctor.id,
            Appointment.date >= today_start,
            Appointment.date <= today_end,
            Appointment.status == 'booked'
        ).count()
        
        # Today's revenue (booked + completed appointments × fee)
        completed_today = db.query(func.count(Appointment.id)).filter(
            Appointment.doctor_id == doctor.id,
            Appointment.date >= today_start,
            Appointment.date <= today_end,
            Appointment.status.in_(['booked', 'completed'])
        ).scalar() or 0
        
        today_revenue = completed_today * doctor.consultation_fee
        
        # Total patients (unique patient phones)
        total_patients = db.query(func.count(func.distinct(Appointment.patient_phone))).filter(
            Appointment.doctor_id == doctor.id
        ).scalar() or 0
        
        # Upcoming appointments (next 7 days)
        week_from_now = today + timedelta(days=7)
        upcoming_appointments = db.query(Appointment).filter(
            Appointment.doctor_id == doctor.id,
            Appointment.date > today_end,
            Appointment.date <= datetime.combine(week_from_now, datetime.max.time()),
            Appointment.status == 'booked'
        ).count()
        
        return templates.TemplateResponse(
            "doctor/dashboard.html",
            {
                "request": request,
                "doctor": doctor,
                "csrf_token": request.state.csrf_token,
                "today_appointments": today_appointments,
                "today_revenue": today_revenue,
                "total_patients": total_patients,
                "upcoming_appointments": upcoming_appointments,
                "consultation_fee": doctor.consultation_fee,
                "subscription_status": doctor.status.upper()
            }
        )
    
    except Exception as e:
        import traceback
        print(f"❌ Dashboard error: {traceback.format_exc()}")
        return HTMLResponse(
            content=f"<h1>Dashboard Error</h1><pre>{traceback.format_exc()}</pre>",
            status_code=500
        )
