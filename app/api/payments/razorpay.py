"""
Razorpay integration for patient bookings in India
Handles UPI, cards, wallets with 2% fees
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import razorpay
import os
import hmac
import hashlib

from app.db.session import get_db
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from datetime import datetime

router = APIRouter(prefix="/api/razorpay", tags=["razorpay-payments"])

# Initialize Razorpay client
razorpay_client = razorpay.Client(
    auth=(
        os.getenv("RAZORPAY_KEY_ID"),
        os.getenv("RAZORPAY_KEY_SECRET")
    )
)


class BookingRequest(BaseModel):
    doctor_id: str
    patient_name: str
    patient_phone: str
    appointment_date: str  # YYYY-MM-DD
    appointment_time: str  # HH:MM


@router.post("/create-order")
async def create_razorpay_order(
    booking: BookingRequest,
    db: Session = Depends(get_db)
):
    """
    Create Razorpay order for appointment booking
    Returns order_id and amount for frontend checkout
    """
    try:
        # Get doctor and consultation fee
        doctor = db.query(Doctor).filter(Doctor.id == booking.doctor_id).first()
        
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")
        
        if doctor.country_code != "IN":
            raise HTTPException(
                status_code=400, 
                detail="Razorpay only for India. Use Stripe for international bookings."
            )
        
        # Create Razorpay order
        amount_paisa = doctor.consultation_fee * 100  # Convert rupees to paisa
        
        order_data = {
            "amount": amount_paisa,
            "currency": "INR",
            "receipt": f"booking_{booking.doctor_id}_{int(datetime.utcnow().timestamp())}",
            "notes": {
                "doctor_id": doctor.id,
                "doctor_name": doctor.name,
                "patient_name": booking.patient_name,
                "patient_phone": booking.patient_phone,
                "appointment_date": booking.appointment_date,
                "appointment_time": booking.appointment_time
            }
        }
        
        order = razorpay_client.order.create(data=order_data)
        
        return {
            "order_id": order["id"],
            "amount": doctor.consultation_fee,
            "currency": "INR",
            "doctor_name": doctor.name,
            "razorpay_key": os.getenv("RAZORPAY_KEY_ID")
        }
    
    except razorpay.errors.BadRequestError as e:
        raise HTTPException(status_code=400, detail=f"Razorpay error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Order creation error: {str(e)}")


@router.post("/verify-payment")
async def verify_razorpay_payment(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Verify Razorpay payment signature and create appointment
    Called after successful payment from frontend
    """
    try:
        body = await request.json()
        
        razorpay_order_id = body.get("razorpay_order_id")
        razorpay_payment_id = body.get("razorpay_payment_id")
        razorpay_signature = body.get("razorpay_signature")
        
        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            raise HTTPException(status_code=400, detail="Missing payment details")
        
        # Verify signature
        generated_signature = hmac.new(
            os.getenv("RAZORPAY_KEY_SECRET").encode(),
            f"{razorpay_order_id}|{razorpay_payment_id}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        if generated_signature != razorpay_signature:
            raise HTTPException(status_code=400, detail="Invalid payment signature")
        
        # Fetch order details
        order = razorpay_client.order.fetch(razorpay_order_id)
        payment = razorpay_client.payment.fetch(razorpay_payment_id)
        
        # Create appointment from order notes
        notes = order.get("notes", {})
        
        appointment = Appointment(
            doctor_id=notes.get("doctor_id"),
            patient_name=notes.get("patient_name"),
            patient_phone=notes.get("patient_phone"),
            date=datetime.strptime(notes.get("appointment_date"), "%Y-%m-%d").date(),
            time=datetime.strptime(notes.get("appointment_time"), "%H:%M").time(),
            status="confirmed",
            payment_status="paid",
            amount_paid=order["amount"] / 100,  # Convert paisa to rupees
            payment_method="razorpay",
            payment_id=razorpay_payment_id
        )
        
        db.add(appointment)
        db.commit()
        db.refresh(appointment)
        
        # Send WhatsApp confirmation
        try:
            from app.services.whatsapp_sender import WhatsAppSender
            
            doctor = db.query(Doctor).filter(Doctor.id == appointment.doctor_id).first()
            
            message = (
                f"✅ *Booking Confirmed!*\n\n"
                f"Dr. {doctor.name}\n"
                f"📅 {appointment.date.strftime('%d %b %Y')}\n"
                f"⏰ {appointment.time.strftime('%I:%M %p')}\n"
                f"💰 ₹{appointment.amount_paid} paid (Razorpay)\n\n"
                f"Clinic: {doctor.clinic.name if doctor.clinic else 'TBD'}\n"
                f"Payment ID: {razorpay_payment_id[:20]}...\n\n"
                f"See you soon!"
            )
            
            sender = WhatsAppSender()
            # Send to both patient and doctor
            sender.send_message(
                to=appointment.patient_phone,
                message=message,
                provider="gupshup"
            )
            sender.send_message(
                to=doctor.whatsapp_number,
                message=f"🔔 New booking: {appointment.patient_name} on {appointment.date}",
                provider="gupshup"
            )
        except Exception as whatsapp_error:
            # Don't fail the booking if WhatsApp fails
            print(f"WhatsApp notification failed: {whatsapp_error}")
        
        return {
            "status": "success",
            "appointment_id": appointment.id,
            "message": "Booking confirmed! Confirmation sent via WhatsApp."
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Payment verification error: {str(e)}")


@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Razorpay webhook handler for payment events
    Validates webhook signature and updates appointment status
    """
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    
    try:
        # Verify webhook signature
        razorpay_client.utility.verify_webhook_signature(
            body.decode(),
            signature,
            os.getenv("RAZORPAY_WEBHOOK_SECRET")
        )
        
        event = await request.json()
        
        # Handle payment.captured event
        if event.get("event") == "payment.captured":
            payment = event.get("payload", {}).get("payment", {}).get("entity", {})
            order_id = payment.get("order_id")
            
            # Update appointment if exists
            appointment = db.query(Appointment).filter(
                Appointment.payment_id == payment.get("id")
            ).first()
            
            if appointment:
                appointment.payment_status = "paid"
                appointment.status = "confirmed"
                db.commit()
        
        # Handle payment.failed event
        elif event.get("event") == "payment.failed":
            payment = event.get("payload", {}).get("payment", {}).get("entity", {})
            
            # Could log failed payment or notify admin
            print(f"Payment failed: {payment.get('id')}")
        
        return {"status": "success"}
    
    except razorpay.errors.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook error: {str(e)}")
