"""
Doctor subscription management endpoints
Stripe-powered subscription upgrades for Growth/Enterprise tiers
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import stripe
import os
from datetime import datetime, timedelta

from app.db.session import get_db
from app.models.doctor import Doctor
from app.models.subscription_plan import SubscriptionPlan
from app.api.doctor.dependencies import require_doctor

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])

# Configure Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


class SubscribeRequest(BaseModel):
    tier: str  # starter, growth, enterprise


@router.post("/subscribe")
async def create_subscription_checkout(
    request: SubscribeRequest,
    doctor: Doctor = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    """
    Create Stripe Checkout session for subscription upgrade
    Automatically selects INR or USD pricing based on doctor's country
    """
    try:
        # Get the subscription plan
        plan = db.query(SubscriptionPlan).filter(
            SubscriptionPlan.tier == request.tier,
            SubscriptionPlan.is_active == True
        ).first()
        
        if not plan:
            raise HTTPException(status_code=404, detail=f"Subscription tier '{request.tier}' not found")
        
        # Determine currency and price based on doctor's country
        currency_code = doctor.currency_code or "INR"
        
        if currency_code == "INR":
            if not plan.stripe_price_id_inr:
                raise HTTPException(
                    status_code=400, 
                    detail="INR pricing not configured for this tier. Please contact support."
                )
            price_id = plan.stripe_price_id_inr
            currency = "inr"
        else:
            if not plan.stripe_price_id_usd:
                raise HTTPException(
                    status_code=400, 
                    detail="USD pricing not configured for this tier. Please contact support."
                )
            price_id = plan.stripe_price_id_usd
            currency = "usd"
        
        # Create or retrieve Stripe customer
        if not doctor.stripe_customer_id:
            customer = stripe.Customer.create(
                email=f"{doctor.whatsapp_number}@curaslot.com",
                name=doctor.name,
                metadata={
                    "doctor_id": doctor.id,
                    "whatsapp": doctor.whatsapp_number
                }
            )
            doctor.stripe_customer_id = customer.id
            db.commit()
        
        # Create Stripe Checkout session
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        
        session = stripe.checkout.Session.create(
            customer=doctor.stripe_customer_id,
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{
                "price": price_id,
                "quantity": 1
            }],
            success_url=f"{base_url}/doctor/billing?success=true&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{base_url}/doctor/billing?canceled=true",
            metadata={
                "doctor_id": doctor.id,
                "tier": request.tier
            },
            subscription_data={
                "metadata": {
                    "doctor_id": doctor.id,
                    "tier": request.tier
                }
            }
        )
        
        return {
            "checkout_url": session.url,
            "session_id": session.id,
            "tier": request.tier,
            "currency": currency
        }
    
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Subscription error: {str(e)}")


@router.post("/webhook")
async def stripe_subscription_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Stripe webhook handler for subscription events
    Updates doctor's subscription status on successful payment
    """
    from fastapi import Request
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv("STRIPE_WEBHOOK_SECRET")
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle subscription created/updated
    if event["type"] in ["checkout.session.completed", "customer.subscription.updated"]:
        session = event["data"]["object"]
        
        # Get doctor ID from metadata
        doctor_id = session.get("metadata", {}).get("doctor_id")
        tier = session.get("metadata", {}).get("tier")
        
        if doctor_id and tier:
            doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
            
            if doctor:
                # Get the subscription plan
                plan = db.query(SubscriptionPlan).filter(
                    SubscriptionPlan.tier == tier
                ).first()
                
                if plan:
                    # Update doctor's subscription
                    doctor.subscription_plan_id = plan.id
                    doctor.subscription_status = "active"
                    doctor.subscription_started_at = datetime.utcnow()
                    
                    # Set subscription end date to 1 month from now
                    doctor.subscription_ends_at = datetime.utcnow() + timedelta(days=30)
                    
                    # Store Stripe subscription ID
                    if event["type"] == "checkout.session.completed":
                        subscription_id = session.get("subscription")
                        if subscription_id:
                            doctor.stripe_subscription_id = subscription_id
                    
                    # Update WhatsApp quota based on plan
                    doctor.whatsapp_limit = plan.whatsapp_quota
                    doctor.whatsapp_used = 0  # Reset usage on new subscription
                    
                    db.commit()
    
    # Handle subscription canceled
    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        subscription_id = subscription["id"]
        
        # Find doctor by subscription ID
        doctor = db.query(Doctor).filter(
            Doctor.stripe_subscription_id == subscription_id
        ).first()
        
        if doctor:
            doctor.subscription_status = "canceled"
            doctor.subscription_ends_at = datetime.utcnow()
            db.commit()
    
    return {"status": "success"}


@router.get("/plans")
async def get_subscription_plans(
    db: Session = Depends(get_db)
):
    """
    Get all active subscription plans
    Public endpoint for pricing page
    """
    plans = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.is_active == True
    ).order_by(SubscriptionPlan.monthly_price_inr).all()
    
    return {
        "plans": [plan.to_dict() for plan in plans]
    }
