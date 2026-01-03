"""
Admin Tools Routes

QR code and WhatsApp link generation for doctors.
"""
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session
import uuid

from app.api.admin.dependencies import require_admin
from app.models.admin_user import AdminUser
from app.models.doctor import Doctor
from app.services.qr_service import QRCodeService
from app.db.session import get_db


router = APIRouter(prefix="/admin/tools", tags=["admin-tools"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent.parent / "templates"))


@router.get("/qr", response_class=HTMLResponse)
async def qr_generator_page(
    request: Request,
    admin_user: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """QR code and link generation tool."""
    # Get all active doctors
    doctors = db.query(Doctor).filter(
        Doctor.is_active == True,
        Doctor.whatsapp_number.isnot(None)
    ).order_by(Doctor.full_name).all()
    
    return templates.TemplateResponse(
        "tools/qr_generator.html",
        {
            "request": request,
            "admin_user": admin_user,
            "csrf_token": request.state.csrf_token,
            "doctors": doctors
        }
    )


@router.get("/qr/{doctor_id}", response_class=HTMLResponse)
async def view_qr_code(
    request: Request,
    doctor_id: uuid.UUID,
    admin_user: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """View QR code and share message for specific doctor."""
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    if not doctor.whatsapp_number:
        raise HTTPException(status_code=400, detail="Doctor has no WhatsApp number")
    
    # Get WhatsApp link and share message
    whatsapp_link = QRCodeService.get_whatsapp_link(doctor)
    share_message = QRCodeService.get_share_message(doctor)
    
    return templates.TemplateResponse(
        "tools/qr_view.html",
        {
            "request": request,
            "admin_user": admin_user,
            "csrf_token": request.state.csrf_token,
            "doctor": doctor,
            "whatsapp_link": whatsapp_link,
            "share_message": share_message,
            "qr_download_url": f"/admin/tools/qr/{doctor_id}/download"
        }
    )


@router.get("/qr/{doctor_id}/download")
async def download_qr_code(
    doctor_id: uuid.UUID,
    admin_user: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Download QR code as PNG file."""
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    if not doctor.whatsapp_number:
        raise HTTPException(status_code=400, detail="Doctor has no WhatsApp number")
    
    # Generate QR code
    try:
        qr_bytes = QRCodeService.generate_qr_code_bytes(doctor)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Return as downloadable PNG
    filename = f"qr_{doctor.full_name.replace(' ', '_').lower()}_{doctor.city.lower()}.png"
    
    return Response(
        content=qr_bytes,
        media_type="image/png",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
