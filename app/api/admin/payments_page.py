"""
Admin Payments Page Route

Displays pending payment receipts for approval/rejection.
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session

from app.api.admin.dependencies import require_admin
from app.models.admin_user import AdminUser
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
    
    # TEMPORARILY SIMPLIFIED - No database queries
    # TODO: Re-enable after fixing database issues
    pending_payments = []
    stats = {
        "verified_today": 0,
        "total_amount": 0
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
