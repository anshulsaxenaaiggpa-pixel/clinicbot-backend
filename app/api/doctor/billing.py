"""
Doctor billing and pricing endpoints
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.doctor import Doctor
from app.api.doctor.dependencies import require_doctor

router = APIRouter(prefix="/doctor", tags=["doctor-billing"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/billing", response_class=HTMLResponse)
async def billing_page(
    request: Request,
    doctor: Doctor = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    """Doctor billing dashboard"""
    from app.models.appointment import Appointment
    
    # Get recent paid appointments
    recent_appointments = db.query(Appointment)\
        .filter(Appointment.doctor_id == doctor.id, Appointment.payment_status == 'paid')\
        .order_by(Appointment.date.desc())\
        .limit(10)\
        .all()
    
    return templates.TemplateResponse("doctor/billing.html", {
        "request": request,
        "doctor": doctor,
        "recent_appointments": recent_appointments
    })


@router.get("/pricing", response_class=HTMLResponse)
async def pricing_page(
    request: Request,
    doctor: Doctor = Depends(require_doctor)
):
    """Pricing tiers page"""
    return templates.TemplateResponse("doctor/pricing.html", {
        "request": request,
        "doctor": doctor
    })
