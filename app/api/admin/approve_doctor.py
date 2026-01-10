"""
Admin endpoints for approving/rejecting pending doctor applications
"""
from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.session import get_db
from app.models.doctor import Doctor
from app.utils.qr_generator import generate_doctor_qr, generate_temp_password


router = APIRouter(prefix="", tags=["admin-doctor-approval"])


@router.post("/admin/doctors/{doctor_id}/approve")
async def approve_doctor(
    doctor_id: str,
    db: Session = Depends(get_db)
):
    """
    Approve pending doctor application
    - Generate temp password
    - Create QR code
    - Set status to approved
    - TODO: Send onboarding WhatsApp message
    """
    try:
        doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
        
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")
        
        if doctor.pending_status != 'pending':
            raise HTTPException(status_code=400, detail="Doctor is not in pending status")
        
        # Generate temporary password
        temp_password = generate_temp_password()
        doctor.set_password(temp_password)  # Hash and store
        
        # Generate QR code for WhatsApp link
        if doctor.whatsapp_link:
            qr_path = generate_doctor_qr(doctor.id, doctor.whatsapp_link)
            doctor.qr_code_path = qr_path
        
        # Update status
        doctor.pending_status = 'approved'
        doctor.approval_date = datetime.utcnow()
        doctor.is_active = True
        
        db.commit()
        db.refresh(doctor)
        
        print(f"✅ Doctor approved: {doctor.name} ({doctor.whatsapp_number})")
        print(f"   Temp password: {temp_password}")
        print(f"   WhatsApp link: {doctor.whatsapp_link}")
        print(f"   QR code: {doctor.qr_code_path}")
        
        # TODO: Send onboarding WhatsApp message with credentials
        # WhatsApp message flow:
        # "🎉 Welcome to CuraSlot, Dr. {name}!
        #  Login: https://curaslot.ai/doctor/login
        #  WhatsApp: {whatsapp_number}
        #  Password: {temp_password}
        #  Your booking link: {whatsapp_link}
        #  Share with patients to start receiving appointments!"
        
        return RedirectResponse(url="/admin/doctors?approved=true", status_code=303)
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Approval error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Approval failed: {str(e)}")


@router.post("/admin/doctors/{doctor_id}/reject")
async def reject_doctor(
    doctor_id: str,
    reason: str = Form("Application did not meet requirements"),
    db: Session = Depends(get_db)
):
    """
    Reject pending doctor application
    """
    try:
        doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
        
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")
        
        if doctor.pending_status != 'pending':
            raise HTTPException(status_code=400, detail="Doctor is not in pending status")
        
        doctor.pending_status = 'rejected'
        doctor.rejected_reason = reason
        
        db.commit()
        
        print(f"❌ Doctor rejected: {doctor.name} - Reason: {reason}")
        
        # TODO: Optional - send rejection notification
        
        return RedirectResponse(url="/admin/doctors?rejected=true", status_code=303)
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Rejection error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Rejection failed: {str(e)}")
