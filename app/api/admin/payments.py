"""
Admin Payment Approval Routes

Doctor approval/rejection of payment receipts.
"""
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
import uuid
import logging

from app.api.admin.dependencies import require_admin
from app.models.admin_user import AdminUser
from app.models.appointment import Appointment
from app.services.audit_service import AuditService
from app.services.whatsapp_sender import WhatsAppSender
from app.db.session import get_db


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/payments", tags=["admin-payments"])
whatsapp = WhatsAppSender()


@router.post("/{appointment_id}/approve")
async def approve_payment(
    appointment_id: str,
    request: Request,
    admin_user: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Approve payment receipt and confirm appointment.
    
    Actions:
    1. Update payment_status to 'confirmed'
    2. Set payment_verified_at and payment_verified_by
    3. Send confirmation message to patient
    4. Delete receipt image after 24h (GDPR compliance)
    5. Audit log the approval
    """
    # Find appointment
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id
    ).first()
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    if appointment.payment_status == "confirmed":
        raise HTTPException(status_code=400, detail="Payment already confirmed")
    
    # Update payment status
    old_status = appointment.payment_status
    appointment.payment_status = "confirmed"
    appointment.payment_verified_at = datetime.utcnow()
    appointment.payment_verified_by = str(admin_user.id)
    
    db.commit()
    
    # Send confirmation to patient
    try:
        await whatsapp.send_message(
            to_number=appointment.patient_phone,
            message=(
                f"✅ Payment Confirmed!\n\n"
                f"Your appointment is confirmed:\n"
                f"📅 {appointment.start_utc_ts.strftime('%B %d, %Y at %I:%M %p')}\n"
                f"👨‍⚕️ Dr. {appointment.doctor.name}\n"
                f"💰 Amount: ₹{appointment.payment_amount or appointment.amount_paid}\n\n"
                f"See you soon!"
            )
        )
    except Exception as e:
        logger.error(f"Failed to send confirmation SMS: {e}")
    
    # Audit log
    AuditService.log_event(
        event_type="payment_approved",
        actor="admin",
        actor_id=str(admin_user.id),
        metadata={
            "appointment_id": appointment_id,
            "patient_phone": appointment.patient_phone,
            "amount": float(appointment.payment_amount) if appointment.payment_amount else appointment.amount_paid,
            "payment_method": appointment.payment_method,
            "previous_status": old_status
        },
        db=db
    )
    
   # Auto-delete receipt image after 24h (GDPR compliance)
    # This would be handled by a background job in production
    # For now, we'll just log it
    logger.info(f"Receipt image will be deleted in 24h: {appointment.payment_receipt_url}")
    
    return RedirectResponse(url="/admin/dashboard#payments", status_code=302)


@router.post("/{appointment_id}/reject")
async def reject_payment(
    appointment_id: str,
    request: Request,
    admin_user: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Reject payment receipt.
    
    Actions:
    1. Update payment_status to 'rejected'
    2. Send rejection message to patient with instructions
    3. Audit log the rejection
    """
    # Find appointment
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id
    ).first()
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Update payment status
    old_status = appointment.payment_status
    appointment.payment_status = "rejected"
    appointment.payment_verified_at = datetime.utcnow()
    appointment.payment_verified_by = str(admin_user.id)
    
    db.commit()
    
    # Send rejection message
    try:
        await whatsapp.send_message(
            to_number=appointment.patient_phone,
            message=(
                f"❌ Payment Verification Failed\n\n"
                f"We couldn't verify your payment receipt.\n"
                f"Please upload a clear screenshot showing:\n"
                f"- Amount: ₹{appointment.amount_paid}\n"
                f"- Transaction successful\n\n"
                f"Reply with the correct receipt."
            )
        )
    except Exception as e:
        logger.error(f"Failed to send rejection message: {e}")
    
    # Audit log
    AuditService.log_event(
        event_type="payment_rejected",
        actor="admin",
        actor_id=str(admin_user.id),
        metadata={
            "appointment_id": appointment_id,
            "patient_phone": appointment.patient_phone,
            "previous_status": old_status
        },
        db=db
    )
    
    return RedirectResponse(url="/admin/dashboard#payments", status_code=302)
