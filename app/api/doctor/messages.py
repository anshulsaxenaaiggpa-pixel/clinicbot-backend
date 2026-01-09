"""
Doctor Messages Routes

WhatsApp messaging: individual and bulk sends.
"""
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session
from typing import Optional

from app.api.doctor.dependencies import require_doctor
from app.models.doctor import Doctor
from app.models.conversation_state import ConversationState
from app.models.patient import Patient
from app.db.session import get_db
from app.services.whatsapp_sender import WhatsAppSender


router = APIRouter(prefix="/doctor", tags=["doctor-messages"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent.parent / "templates"))


@router.get("/messages", response_class=HTMLResponse)
async def messages_page(
    request: Request,
    doctor: Doctor = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    """Display messages interface with send options."""
    try:
        # Get recent conversations (limited view)
        try:
            conversations = db.query(ConversationState).order_by(
                ConversationState.last_message_at.desc()
            ).limit(20).all()
        except Exception as db_error:
            # Table might not exist yet
            print(f"⚠️ Could not query conversations: {db_error}")
            conversations = []
        
        # Get all patients for messaging
        patients = db.query(Patient).filter(
            Patient.doctor_id == doctor.id
        ).order_by(Patient.created_at.desc()).all()
        
        return templates.TemplateResponse(
            "doctor/messages.html",
            {
                "request": request,
                "doctor": doctor,
                "csrf_token": request.state.csrf_token,
                "conversations": conversations,
                "patients": patients,
                "total_patients": len(patients)
            }
        )
    
    except Exception as e:
        import traceback
        print(f"❌ Messages error: {traceback.format_exc()}")
        return HTMLResponse(
            content=f"<h1>Error</h1><pre>{traceback.format_exc()}</pre>",
            status_code=500
        )


@router.post("/messages/send")
async def send_individual_message(
    request: Request,
    patient_id: str = Form(...),
    message: str = Form(...),
    doctor: Doctor = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    """Send individual WhatsApp message to a patient."""
    try:
        # Get patient
        patient = db.query(Patient).filter(
            Patient.id == patient_id,
            Patient.doctor_id == doctor.id
        ).first()
        
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Send WhatsApp message
        sender = WhatsAppSender()
        success = await sender.send_message(
            to=patient.phone,
            message=f"*Message from Dr. {doctor.name}*\n\n{message}",
            provider="twilio"
        )
        
        if success:
            request.session["flash_message"] = f"✅ Message sent to {patient.name}"
            request.session["flash_type"] = "success"
        else:
            request.session["flash_message"] = "❌ Failed to send message"
            request.session["flash_type"] = "danger"
        
        return RedirectResponse(url="/doctor/messages", status_code=303)
    
    except Exception as e:
        import traceback
        print(f"❌ Send message error: {traceback.format_exc()}")
        request.session["flash_message"] = f"Error: {str(e)}"
        request.session["flash_type"] = "danger"
        return RedirectResponse(url="/doctor/messages", status_code=303)


@router.post("/messages/send-bulk")
async def send_bulk_message(
    request: Request,
    message: str = Form(...),
    doctor: Doctor = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    """Send bulk WhatsApp message to all patients (additional charges apply)."""
    try:
        # Get all patients
        patients = db.query(Patient).filter(
            Patient.doctor_id == doctor.id
        ).all()
        
        if not patients:
            raise HTTPException(status_code=404, detail="No patients found")
        
        # Send to all patients
        sender = WhatsAppSender()
        success_count = 0
        failed_count = 0
        
        for patient in patients:
            try:
                success = await sender.send_message(
                    to=patient.phone,
                    message=f"*Message from Dr. {doctor.name}*\n\n{message}",
                    provider="twilio"
                )
                if success:
                    success_count += 1
                else:
                    failed_count += 1
            except:
                failed_count += 1
        
        # Cost calculation (₹0.30 per message as per Gupshup pricing)
        total_cost = len(patients) * 0.30
        
        request.session["flash_message"] = f"✅ Bulk message sent to {success_count} patients (Failed: {failed_count}). Estimated cost: ₹{total_cost:.2f}"
        request.session["flash_type"] = "success" if failed_count == 0 else "warning"
        
        return RedirectResponse(url="/doctor/messages", status_code=303)
    
    except Exception as e:
        import traceback
        print(f"❌ Bulk send error: {traceback.format_exc()}")
        request.session["flash_message"] = f"Error: {str(e)}"
        request.session["flash_type"] = "danger"
        return RedirectResponse(url="/doctor/messages", status_code=303)
