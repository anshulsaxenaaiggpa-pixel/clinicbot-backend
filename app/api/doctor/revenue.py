"""
Doctor Revenue Routes

Revenue tracking and consultation fee management.
"""
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from app.api.doctor.dependencies import require_doctor, validate_csrf
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.db.session import get_db


router = APIRouter(prefix="/doctor", tags=["doctor-revenue"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent.parent / "templates"))


@router.get("/revenue", response_class=HTMLResponse)
async def revenue_dashboard(
    request: Request,
    doctor: Doctor = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    """Revenue dashboard with daily/monthly stats."""
    try:
        today = datetime.now().date()
        
        # Today's revenue
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        today_count = db.query(func.count(Appointment.id)).filter(
            Appointment.doctor_id == doctor.id,
            Appointment.date >= today_start,
            Appointment.date <= today_end,
            Appointment.status.in_(['booked', 'completed'])
        ).scalar() or 0
        today_revenue = today_count * doctor.consultation_fee
        
        # This month's revenue
        month_start = today.replace(day=1)
        month_count = db.query(func.count(Appointment.id)).filter(
            Appointment.doctor_id == doctor.id,
            Appointment.date >= month_start,
            Appointment.status.in_(['booked', 'completed'])
        ).scalar() or 0
        month_revenue = month_count * doctor.consultation_fee
        
        # Last 7 days data for chart
        daily_data = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            day_start = datetime.combine(day, datetime.min.time())
            day_end = datetime.combine(day, datetime.max.time())
            day_count = db.query(func.count(Appointment.id)).filter(
                Appointment.doctor_id == doctor.id,
                Appointment.date >= day_start,
                Appointment.date <= day_end,
                Appointment.status.in_(['booked', 'completed'])
            ).scalar() or 0
            daily_data.append({
                'date': day.strftime('%d %b'),
                'appointments': day_count,
                'revenue': day_count * doctor.consultation_fee
            })
        
        return templates.TemplateResponse(
            "doctor/revenue.html",
            {
                "request": request,
                "doctor": doctor,
                "csrf_token": request.state.csrf_token,
                "today_revenue": today_revenue,
                "today_count": today_count,
                "month_revenue": month_revenue,
                "month_count": month_count,
                "consultation_fee": doctor.consultation_fee,
                "daily_data": daily_data
            }
        )
    
    except Exception as e:
        import traceback
        print(f"❌ Revenue error: {traceback.format_exc()}")
        return HTMLResponse(
            content=f"<h1>Error</h1><pre>{traceback.format_exc()}</pre>",
            status_code=500
        )


@router.post("/revenue/update-fee")
async def update_consultation_fee(
    request: Request,
    consultation_fee: int = Form(...),
    doctor: Doctor = Depends(require_doctor),
    csrf_valid: bool = Depends(validate_csrf),
    db: Session = Depends(get_db)
):
    """Update consultation fee."""
    if consultation_fee > 0:
        doctor.consultation_fee = consultation_fee
        db.commit()
    
    return RedirectResponse(url="/doctor/revenue", status_code=302)
