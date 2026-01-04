"""
Admin Payments Page Route

Displays pending payment receipts for approval/rejection.
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.admin.dependencies import require_admin
from app.models.admin_user import AdminUser
from app.models.appointment import Appointment
from app.db.session import get_db


router = APIRouter(prefix="/admin", tags=["admin-payments-page"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent.parent / "templates"))


@router.get("/payments", response_class=HTMLResponse)
async def payments_page(
    request: Request,
    admin_user: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Display pending payment receipts page."""
    
    # Get pending payment receipts
    pending_payments = db.query(Appointment).filter(
        Appointment.payment_status.in_(['pending', 'verified'])
    ).order_by(
        Appointment.receipt_uploaded_at.desc()
    ).limit(50).all()
    
    # Calculate stats
    stats = {
        "verified_today": db.query(Appointment).filter(
            Appointment.payment_status == 'confirmed',
            func.date(Appointment.payment_verified_at) == func.current_date()
        ).count() if pending_payments else 0,
        "total_amount": sum([float(appt.payment_amount or appt.amount_paid or 0) for appt in pending_payments])
    }
    
    return templates.TemplateResponse(
        "admin_payments.html",
        {
            "request": request,
            "admin_user": admin_user,
            "csrf_token": request.state.csrf_token,
            "pending_payments": pending_payments,
            "stats": stats
        }
    )
