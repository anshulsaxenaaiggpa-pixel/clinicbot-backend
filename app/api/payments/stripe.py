"""
Stripe Connect integration for direct doctor payments
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import stripe
import os

from app.db.session import get_db
from app.models.doctor import Doctor
from app.api.doctor.dependencies import require_doctor

router = APIRouter(prefix="/stripe", tags=["stripe-payments"])

# Configure Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


class CheckoutRequest(BaseModel):
    doctor_id: str
    patient_name: str
    patient_phone: str
    appointment_date: str
    appointment_time: str
    amount: int  # In rupees


@router.post("/connect")
async def connect_stripe_account(
    doctor: Doctor = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    """
    Create Stripe Connect Express account for doctor
    Returns account link for onboarding
    """
    try:
        if doctor.stripe_account_id:
            # Account already exists, create new login link
            account_link = stripe.AccountLink.create(
                account=doctor.stripe_account_id,
                refresh_url=f"{os.getenv('BASE_URL', 'http://localhost:8000')}/doctor/billing",
                return_url=f"{os.getenv('BASE_URL', 'http://localhost:8000')}/doctor/billing?connected=true",
                type="account_onboarding"
            )
            return {"url": account_link.url}
        
        # Create new Connect Express account
        account = stripe.Account.create(
            type="express",
            country="IN",  # India
            email=f"{doctor.whatsapp_number}@curaslot.ai",
            capabilities={
                "card_payments": {"requested": True},
                "transfers": {"requested": True}
            },
            business_type="individual"
        )
        
        # Save account ID
        doctor.stripe_account_id = account.id
        db.commit()
        
        # Create account link for onboarding
        account_link = stripe.AccountLink.create(
            account=account.id,
            refresh_url=f"{os.getenv('BASE_URL', 'http://localhost:8000')}/doctor/billing",
            return_url=f"{os.getenv('BASE_URL', 'http://localhost:8000')}/doctor/billing?connected=true",
            type="account_onboarding"
        )
        
        return {"url": account_link.url, "account_id": account.id}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe Connect error: {str(e)}")


@router.post("/create-checkout")
async def create_checkout_session(
    checkout: CheckoutRequest,
    db: Session = Depends(get_db)
):
    """
    Create Stripe Checkout session for appointment booking
    Direct payment to doctor via Connect
    """
    try:
        doctor = db.query(Doctor).filter(Doctor.id == checkout.doctor_id).first()
        
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")
        
        if not doctor.stripe_account_id:
            raise HTTPException(status_code=400, detail="Doctor has not connected Stripe account")
        
        # Create checkout session with destination charge to doctor
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "inr",
                    "product_data": {
                        "name": f"Consultation with Dr. {doctor.name}",
                        "description": f"{checkout.appointment_date} at {checkout.appointment_time}"
                    },
                    "unit_amount": checkout.amount * 100  # Convert to paise
                },
                "quantity": 1
            }],
            payment_intent_data={
                "application_fee_amount": int(checkout.amount * 0.05 * 100),  # 5% platform fee
                "transfer_data": {
                    "destination": doctor.stripe_account_id
                }
            },
            customer_email=f"{checkout.patient_phone}@patient.curaslot.ai",
            metadata={
                "doctor_id": doctor.id,
                "patient_name": checkout.patient_name,
                "patient_phone": checkout.patient_phone,
                "appointment_date": checkout.appointment_date,
                "appointment_time": checkout.appointment_time
            },
            success_url=f"{os.getenv('BASE_URL', 'http://localhost:8000')}/booking/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{os.getenv('BASE_URL', 'http://localhost:8000')}/booking/cancelled"
        )
        
        return {"session_id": session.id, "url": session.url}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Checkout error: {str(e)}")


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Stripe webhook handler for payment events
    Confirms appointments and sends WhatsApp notifications
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv("STRIPE_WEBHOOK_SECRET")
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle checkout.session.completed
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        
        # Create appointment from metadata
        from app.models.appointment import Appointment
        from datetime import datetime
        
        appointment = Appointment(
            doctor_id=session["metadata"]["doctor_id"],
            patient_name=session["metadata"]["patient_name"],
            patient_phone=session["metadata"]["patient_phone"],
            date=datetime.strptime(session["metadata"]["appointment_date"], "%Y-%m-%d").date(),
            time=datetime.strptime(session["metadata"]["appointment_time"], "%H:%M").time(),
            status="confirmed",
            payment_status="paid",
            amount_paid=session["amount_total"] / 100  # Convert from paise
        )
        db.add(appointment)
        db.commit()
        
        # Send WhatsApp confirmation
        from app.services.whatsapp_sender import WhatsAppSender
        import asyncio
        
        doctor = db.query(Doctor).filter(Doctor.id == appointment.doctor_id).first()
        
        message = (
            f"✅ *Appointment Confirmed!*\n\n"
            f"Dr. {doctor.name}\n"
            f"📅 {appointment.date.strftime('%d %b %Y')}\n"
            f"⏰ {appointment.time.strftime('%I:%M %p')}\n"
            f"💰 ₹{appointment.amount_paid} paid\n\n"
            f"See you soon! Reply CANCEL to reschedule."
        )
        
        sender = WhatsAppSender()
        asyncio.run(sender.send_message(
            to=appointment.patient_phone,
            message=message,
            provider="gupshup"
        ))
    
    return {"status": "success"}


@router.get("/dashboard")
async def stripe_dashboard_link(
    doctor: Doctor = Depends(require_doctor)
):
    """
    Generate Stripe Express Dashboard login link for doctor
    """
    if not doctor.stripe_account_id:
        raise HTTPException(status_code=400, detail="Stripe account not connected")
    
    try:
        login_link = stripe.Account.create_login_link(doctor.stripe_account_id)
        return {"url": login_link.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard link error: {str(e)}")
