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
    """Doctor billing dashboard with subscriptions"""
    from app.models.appointment import Appointment
    from app.models.subscription_plan import SubscriptionPlan
    from app.core.currencies import format_price
    
    # Get recent paid appointments
    recent_appointments = db.query(Appointment)\
        .filter(Appointment.doctor_id == doctor.id, Appointment.payment_status == 'paid')\
        .order_by(Appointment.date.desc())\
        .limit(10)\
        .all()
    
    # Get current subscription plan
    current_plan = None
    if doctor.subscription_plan_id:
        current_plan = db.query(SubscriptionPlan).filter(
            SubscriptionPlan.id == doctor.subscription_plan_id
        ).first()
    
    # Get all available plans for upgrade
    all_plans = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.is_active == True
    ).order_by(SubscriptionPlan.monthly_price_inr).all()
    
    # Calculate WhatsApp usage percentage
    whatsapp_usage_pct = 0
    if doctor.whatsapp_limit and doctor.whatsapp_limit > 0:
        whatsapp_usage_pct = min(100, int((doctor.whatsapp_used / doctor.whatsapp_limit) * 100))
    
    # Format subscription price
    subscription_price_formatted = ""
    if current_plan:
        if doctor.currency_code == "INR":
            subscription_price_formatted = format_price(current_plan.monthly_price_inr, "INR")
        else:
            subscription_price_formatted = format_price(current_plan.monthly_price_usd, "USD")
    
    return templates.TemplateResponse("doctor/billing.html", {
        "request": request,
        "doctor": doctor,
        "recent_appointments": recent_appointments,
        "current_plan": current_plan,
        "all_plans": all_plans,
        "whatsapp_used": doctor.whatsapp_used or 0,
        "whatsapp_limit": doctor.whatsapp_limit or 0,
        "whatsapp_usage_pct": whatsapp_usage_pct,
        "subscription_price": subscription_price_formatted,
        "currency_code": doctor.currency_code or "INR",
        "stripe_account_connected": doctor.stripe_account_id is not None,
        "subscription_status": doctor.subscription_status or "trial"
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
