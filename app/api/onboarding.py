"""Clinic onboarding API endpoints"""
import uuid
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, validator

from app.db.database import get_db
from app.models.clinic import Clinic
from app.models.doctor import Doctor
from app.models.service import Service
from app.services.whatsapp_sender import WhatsAppSender

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


# Pydantic Models
class OnboardingStart(BaseModel):
    """Initial onboarding request"""
    name: str = Field(..., min_length=2, max_length=100, description="Clinic name")
    owner_name: str = Field(..., min_length=2, max_length=100, description="Owner full name")
    phone: str = Field(..., description="Contact phone number")
    email: Optional[str] = Field(None, description="Contact email")
    
    @validator('phone')
    def validate_phone(cls, v):
        """Validate phone number format"""
        # Remove spaces and special characters
        clean = v.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if not clean.startswith("+"):
            raise ValueError("Phone number must start with country code (e.g., +91)")
        if len(clean) < 10:
            raise ValueError("Phone number is too short")
        return clean


class OnboardingClinic(BaseModel):
    """Complete clinic onboarding"""
    name: str = Field(..., min_length=2, max_length=100)
    owner_name: str = Field(..., min_length=2, max_length=100)
    address: str = Field(..., min_length=5, max_length=200)
    city: str = Field(..., min_length=2, max_length=50)
    state: Optional[str] = Field(None, max_length=50)
    pincode: Optional[str] = Field(None, max_length=10)
    phone: str
    email: Optional[str] = None
    whatsapp_number: str = Field(..., description="WhatsApp Business number")
    timezone: str = Field(default="Asia/Kolkata")
    subscription_tier: str = Field(..., description="starter, professional, or enterprise")
    
    @validator('subscription_tier')
    def validate_tier(cls, v):
        """Validate subscription tier"""
        valid_tiers = ["starter", "professional", "enterprise"]
        if v.lower() not in valid_tiers:
            raise ValueError(f"Tier must be one of: {', '.join(valid_tiers)}")
        return v.lower()
    
    @validator('whatsapp_number', 'phone')
    def validate_phone(cls, v):
        """Validate phone number format"""
        clean = v.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if not clean.startswith("+"):
            raise ValueError("Phone number must start with country code (e.g., +91)")
        return clean


class OnboardingResponse(BaseModel):
    """Onboarding completion response"""
    success: bool
    clinic_id: str
    api_key: str
    message: str
    next_steps: list[str]


class WhatsAppVerification(BaseModel):
    """WhatsApp number verification request"""
    whatsapp_number: str
    verification_code: Optional[str] = None


# Endpoints
@router.post("/start", response_model=dict)
async def start_onboarding(
    request: OnboardingStart,
    db: Session = Depends(get_db)
):
    """
    Initiate onboarding process
    
    Returns a session ID for continuing the onboarding
    """
    # Check if phone already exists
    existing = db.query(Clinic).filter(
        Clinic.whatsapp_number == request.phone
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A clinic with this WhatsApp number already exists"
        )
    
    # Generate onboarding session
    session_id = str(uuid.uuid4())
    
    return {
        "success": True,
        "session_id": session_id,
        "message": "Onboarding initiated. Proceed to complete registration.",
        "available_plans": {
            "starter": {
                "name": "Starter",
                "price": 999,
                "currency": "INR",
                "billing": "monthly",
                "features": [
                    "1 doctor",
                    "Unlimited appointments",
                    "WhatsApp bot",
                    "Basic dashboard",
                    "Email support"
                ]
            },
            "professional": {
                "name": "Professional",
                "price": 1999,
                "currency": "INR",
                "billing": "monthly",
                "features": [
                    "Up to 5 doctors",
                    "Unlimited appointments",
                    "WhatsApp bot with AI",
                    "Advanced dashboard",
                    "Analytics & reports",
                    "Priority support"
                ]
            },
            "enterprise": {
                "name": "Enterprise",
                "price": 2999,
                "currency": "INR",
                "billing": "monthly",
                "features": [
                    "Unlimited doctors",
                    "Unlimited appointments",
                    "WhatsApp bot with AI",
                    "Full-featured dashboard",
                    "Advanced analytics",
                    "Custom integrations",
                    "24/7 support",
                    "Dedicated account manager"
                ]
            }
        }
    }


@router.post("/clinic", response_model=OnboardingResponse)
async def create_clinic(
    request: OnboardingClinic,
    db: Session = Depends(get_db)
):
    """
    Create new clinic with complete onboarding
    
    This endpoint:
    1. Creates clinic record
    2. Generates API key
    3. Creates default doctor
    4. Creates default services
    5. Activates trial period
    """
    # Check if WhatsApp number already exists
    existing = db.query(Clinic).filter(
        Clinic.whatsapp_number == request.whatsapp_number
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A clinic with this WhatsApp number already exists. Please use a different number."
        )
    
    try:
        # Generate unique IDs and API key
        clinic_id = uuid.uuid4()
        api_key = f"clinic_{secrets.token_urlsafe(24)}"
        
        # Create clinic
        clinic = Clinic(
            id=clinic_id,
            name=request.name,
            owner_name=request.owner_name,
            address=request.address,
            city=request.city,
            state=request.state,
            pincode=request.pincode,
            phone=request.phone,
            email=request.email,
            timezone=request.timezone,
            whatsapp_number=request.whatsapp_number,
            subscription_tier=request.subscription_tier,
            subscription_status="trial",
            trial_ends_at=datetime.utcnow() + timedelta(days=7),
            whatsapp_provider="twilio",
            api_key=api_key,
            is_active=True
        )
        db.add(clinic)
        db.flush()
        
        # Create default doctor
        default_doctor = Doctor(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            name=request.owner_name,
            specialization="General Physician",
            default_fee=500,
            is_active=True
        )
        db.add(default_doctor)
        
        # Create default services
        default_services = [
            Service(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                name="General Consultation",
                type="consultation",
                duration_minutes=30,
                required_slots=1,
                default_fee=500,
                is_active=True
            ),
            Service(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                name="Follow-up Consultation",
                type="consultation",
                duration_minutes=15,
                required_slots=1,
                default_fee=300,
                is_active=True
            )
        ]
        
        for service in default_services:
            db.add(service)
        
        db.commit()
        
        # Send welcome message to WhatsApp (optional, async)
        try:
            sender = WhatsAppSender()
            welcome_msg = f"""🎉 Welcome to ClinicBot, {request.name}!

Your clinic has been successfully registered.

📋 Your Details:
• Clinic ID: {clinic_id}
• API Key: {api_key[:20]}...
• Subscription: {request.subscription_tier.title()}
• Trial Period: 7 days

✅ What's Ready:
• 1 Doctor configured
• 2 Services available
• WhatsApp bot activated
• Admin dashboard ready

📱 Next Steps:
1. Save your API key securely
2. Access dashboard with your credentials
3. Add more doctors and services
4. Configure operating hours
5. Start accepting bookings!

Need help? Reply with 'help' anytime.

Thank you for choosing ClinicBot! 🚀"""
            
            # Note: This is async and may fail silently to not block onboarding
            await sender.send_message(
                to=request.whatsapp_number,
                message=welcome_msg,
                provider="twilio"
            )
        except Exception as e:
            # Log but don't fail onboarding
            print(f"Failed to send welcome message: {e}")
        
        return OnboardingResponse(
            success=True,
            clinic_id=str(clinic_id),
            api_key=api_key,
            message="Clinic onboarding completed successfully!",
            next_steps=[
                "Save your API key in a secure location",
                "Access the admin dashboard using your API key",
                "Add more doctors and customize services",
                "Configure clinic operating hours",
                "Test the WhatsApp bot by sending a message",
                "Upgrade before trial ends to continue service"
            ]
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create clinic: {str(e)}"
        )


@router.post("/verify-whatsapp", response_model=dict)
async def verify_whatsapp(
    request: WhatsAppVerification,
    db: Session = Depends(get_db)
):
    """
    Verify WhatsApp number ownership
    
    Step 1: Send verification code
    Step 2: Validate code (call again with code)
    """
    # For MVP, we'll use a simple verification
    # In production, integrate with Twilio Verify API
    
    if not request.verification_code:
        # Send verification code
        verification_code = str(secrets.randbelow(900000) + 100000)  # 6-digit code
        
        try:
            sender = WhatsAppSender()
            await sender.send_message(
                to=request.whatsapp_number,
                message=f"🔐 ClinicBot Verification Code: {verification_code}\n\nThis code expires in 10 minutes.",
                provider="twilio"
            )
            
            return {
                "success": True,
                "message": "Verification code sent to WhatsApp",
                "code_sent": True,
                # In production, store code in Redis with TTL
                # For demo, we return it (NOT SECURE FOR PRODUCTION)
                "demo_code": verification_code
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send verification code: {str(e)}"
            )
    else:
        # Verify code
        # In production, check against Redis stored code
        return {
            "success": True,
            "verified": True,
            "message": "WhatsApp number verified successfully"
        }


@router.get("/status/{clinic_id}", response_model=dict)
async def get_onboarding_status(
    clinic_id: str,
    db: Session = Depends(get_db)
):
    """
    Get onboarding status for a clinic
    """
    try:
        clinic_uuid = uuid.UUID(clinic_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid clinic ID format"
        )
    
    clinic = db.query(Clinic).filter(Clinic.id == clinic_uuid).first()
    
    if not clinic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinic not found"
        )
    
    # Count doctors and services
    doctors_count = db.query(Doctor).filter(
        Doctor.clinic_id == clinic_uuid,
        Doctor.is_active == True
    ).count()
    
    services_count = db.query(Service).filter(
        Service.clinic_id == clinic_uuid,
        Service.is_active == True
    ).count()
    
    return {
        "clinic_id": str(clinic.id),
        "name": clinic.name,
        "subscription_tier": clinic.subscription_tier,
        "subscription_status": clinic.subscription_status,
        "trial_ends_at": clinic.trial_ends_at.isoformat() if clinic.trial_ends_at else None,
        "is_active": clinic.is_active,
        "whatsapp_configured": bool(clinic.whatsapp_number),
        "doctors_count": doctors_count,
        "services_count": services_count,
        "onboarding_complete": doctors_count > 0 and services_count > 0,
        "created_at": clinic.created_at.isoformat()
    }
