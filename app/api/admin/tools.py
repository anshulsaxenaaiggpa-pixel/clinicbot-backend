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
    try:
        # Get all active doctors
        doctors = db.query(Doctor).filter(
            Doctor.is_active == True
        ).order_by(Doctor.name).all()
        
        return templates.TemplateResponse(
            "tools/qr_generator.html",
            {
                "request": request,
                "admin_user": admin_user,
                "csrf_token": getattr(request.state, 'csrf_token', ''),
                "doctors": doctors
            }
        )
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"\n{'='*80}")
        print(f"❌ QR GENERATOR ERROR:")
        print(f"{'='*80}")
        print(error_trace)
        print(f"{'='*80}\n")
        return HTMLResponse(content=f"<h1>QR Generator Error</h1><pre>{error_trace}</pre>", status_code=500)


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
    
    # Note: Doctor model doesn't have whatsapp_number - would need clinic's WhatsApp
    try:
        return templates.TemplateResponse(
            "tools/qr_view.html",
            {
                "request": request,
                "admin_user": admin_user,
                "csrf_token": getattr(request.state, 'csrf_token', ''),
                "doctor": doctor,
                "whatsapp_link": "https://wa.me/",  # Placeholder - need clinic WhatsApp
                "share_message": f"Book appointment with Dr. {doctor.name}",
                "qr_download_url": f"/admin/tools/qr/{doctor_id}/download"
            }
        )
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"\n{'='*80}")
        print(f"❌ QR VIEW ERROR:")
        print(f"{'='*80}")
        print(error_trace)
        print(f"{'='*80}\n")
        return HTMLResponse(content=f"<h1>QR View Error</h1><pre>{error_trace}</pre>", status_code=500)


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
    
    # Generate simple QR code with doctor info
    try:
        # Create a simple URL or message for QR code
        qr_data = f"Doctor: {doctor.name}, Specialization: {doctor.specialization or 'General'}"
        
        import qrcode
        from io import BytesIO
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        qr_bytes = buffer.getvalue()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"QR generation failed: {str(e)}")
    
    # Return as downloadable PNG
    filename = f"qr_{doctor.name.replace(' ', '_').lower()}.png"
    
    return Response(
        content=qr_bytes,
        media_type="image/png",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
