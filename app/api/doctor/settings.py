"""
Doctor Settings Routes

Profile and preferences management.
"""
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session

from app.api.doctor.dependencies import require_doctor, validate_csrf
from app.models.doctor import Doctor
from app.db.session import get_db


router = APIRouter(prefix="/doctor", tags=["doctor-settings"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent.parent / "templates"))


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    doctor: Doctor = Depends(require_doctor)
):
    """Display settings page."""
    return templates.TemplateResponse(
        "doctor/settings.html",
        {
            "request": request,
            "doctor": doctor,
            "csrf_token": request.state.csrf_token
        }
    )


@router.post("/settings/profile")
async def update_profile(
    request: Request,
    name: str = Form(...),
    specialization: str = Form(...),
    doctor: Doctor = Depends(require_doctor),
    csrf_valid: bool = Depends(validate_csrf),
    db: Session = Depends(get_db)
):
    """Update doctor profile."""
    doctor.full_name = name.strip()
    doctor.specialization = specialization.strip()
    db.commit()
    
    return RedirectResponse(url="/doctor/settings", status_code=302)


@router.post("/settings/password")
async def update_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    doctor: Doctor = Depends(require_doctor),
    csrf_valid: bool = Depends(validate_csrf),
    db: Session = Depends(get_db)
):
    """Update password."""
    # Verify current password
    if not doctor.verify_password(current_password):
        return RedirectResponse(url="/doctor/settings?error=invalid_password", status_code=302)
    
    # Set new password
    doctor.set_password(new_password)
    db.commit()
    
    return RedirectResponse(url="/doctor/settings?success=password_updated", status_code=302)
