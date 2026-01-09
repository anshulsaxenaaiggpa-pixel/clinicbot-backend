"""Doctor Analytics Module - Performance metrics and insights"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, timedelta

from app.db.database import get_db
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.api.doctor.dependencies import get_current_doctor

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """
    Display analytics dashboard with performance metrics
    """
    # Date range for analysis (last 30 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Total appointments in last 30 days
    total_appointments = db.query(Appointment).filter(
        Appointment.doctor_id == doctor.id,
        Appointment.date >= start_date.date()
    ).count()
    
    # Completed appointments
    completed = db.query(Appointment).filter(
        Appointment.doctor_id == doctor.id,
        Appointment.status == "completed",
        Appointment.date >= start_date.date()
    ).count()
    
    # Cancelled appointments
    cancelled = db.query(Appointment).filter(
        Appointment.doctor_id == doctor.id,
        Appointment.status == "cancelled",
        Appointment.date >= start_date.date()
    ).count()
    
    # No-shows
    no_shows = db.query(Appointment).filter(
        Appointment.doctor_id == doctor.id,
        Appointment.status == "no_show",
        Appointment.date >= start_date.date()
    ).count()
    
    # Calculate percentages
    cancellation_rate = (cancelled / total_appointments * 100) if total_appointments > 0 else 0
    no_show_rate = (no_shows / total_appointments * 100) if total_appointments > 0 else 0
    completion_rate = (completed / total_appointments * 100) if total_appointments > 0 else 0
    
    # Monthly revenue trend (last 6 months)
    revenue_trend = []
    for i in range(6, 0, -1):
        month_date = datetime.now() - timedelta(days=30*i)
        month_appointments = db.query(func.count(Appointment.id)).filter(
            Appointment.doctor_id == doctor.id,
            Appointment.status == "completed",
            extract('month', Appointment.date) == month_date.month,
            extract('year', Appointment.date) == month_date.year
        ).scalar() or 0
        
        revenue = month_appointments * (doctor.consultation_fee or 500)
        revenue_trend.append({
            "month": month_date.strftime("%b %Y"),
            "revenue": revenue,
            "appointments": month_appointments
        })
    
    # Simulated reach metrics
    profile_views = total_appointments * 3  # 3 views per booking
    whatsapp_opens = int(profile_views * 0.7)  # 70% open WhatsApp
    conversion_rate = (total_appointments / profile_views * 100) if profile_views > 0 else 0
    
    return templates.TemplateResponse("doctor/analytics.html", {
        "request": request,
        "doctor": doctor,
        "total_appointments": total_appointments,
        "completed": completed,
        "cancelled": cancelled,
        "no_shows": no_shows,
        "cancellation_rate": round(cancellation_rate, 1),
        "no_show_rate": round(no_show_rate, 1),
        "completion_rate": round(completion_rate, 1),
        "revenue_trend": revenue_trend,
        "profile_views": profile_views,
        "whatsapp_opens": whatsapp_opens,
        "conversion_rate": round(conversion_rate, 1)
    })
