"""
Doctor QR Code Routes

Personal booking QR code generator.
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.api.doctor.dependencies import require_doctor
from app.models.doctor import Doctor


router = APIRouter(prefix="/doctor", tags=["doctor-qr"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent.parent / "templates"))


@router.get("/qr", response_class=HTMLResponse)
async def qr_code_page(
    request: Request,
    doctor: Doctor = Depends(require_doctor)
):
    """Display personal booking QR code."""
    # Generate booking URL for this doctor
    booking_url = f"https://wa.me/{doctor.whatsapp_number}?text=I want to book an appointment"
    
    return templates.TemplateResponse(
        "doctor/qr.html",
        {
            "request": request,
            "doctor": doctor,
            "csrf_token": request.state.csrf_token,
            "booking_url": booking_url
        }
    )
