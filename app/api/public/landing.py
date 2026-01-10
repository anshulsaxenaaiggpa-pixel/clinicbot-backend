"""
Public landing pages and doctor application routes
"""
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import datetime
import secrets
import string

from app.db.session import get_db
from app.models.doctor import Doctor

router = APIRouter(tags=["public"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent.parent / "templates"))


@router.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """CuraSlot landing page"""
    return templates.TemplateResponse("public/index.html", {
        "request": request
    })


@router.get("/for-doctors", response_class=HTMLResponse)
async def for_doctors_page(request: Request):
    """Sales page for doctors"""
    return templates.TemplateResponse("public/for_doctors.html", {
        "request": request
    })


@router.get("/doctor/apply", response_class=HTMLResponse)
async def apply_page(request: Request):
    """Doctor application form"""
    return templates.TemplateResponse("public/apply.html", {
        "request": request
    })


@router.post("/api/doctors/apply")
async def submit_application(
    request: Request,
    whatsapp_number: str = Form(...),
    name: str = Form(...),
    specialization: str = Form(...),
    clinic_name: str = Form(...),
    city: str = Form(...),
    expected_patients: int = Form(50),
    db: Session = Depends(get_db)
):
    """
    Submit doctor application
    Creates pending doctor record
    """
    try:
        # Validate WhatsApp number format (+91XXXXXXXXXX)
        if not whatsapp_number.startswith('+91') or len(whatsapp_number) != 13:
            raise HTTPException(status_code=400, detail="Invalid WhatsApp number format. Use +91XXXXXXXXXX")
        
        # Check if doctor already exists (approved or pending)
        existing = db.query(Doctor).filter(Doctor.whatsapp_number == whatsapp_number).first()
        if existing:
            if existing.pending_status == 'approved':
                raise HTTPException(status_code=400, detail="You already have an account. Please login.")
            elif existing.pending_status == 'pending':
                raise HTTPException(status_code=400, detail="Your application is already pending review.")
        
        # Generate WhatsApp link
        whatsapp_link = f"https://wa.me/{whatsapp_number.replace('+', '')}?text=Hi%20Dr.%20{name.replace(' ', '%20')},%20I%20want%20to%20book%20an%20appointment"
        
        # Create pending doctor record
        doctor = Doctor(
            whatsapp_number=whatsapp_number,
            name=name,
            specialization=specialization,
            clinic_id=None,  # Will be assigned on approval
            is_active=False,  # Inactive until approved
            pending_status='pending',
            application_date=datetime.utcnow(),
            whatsapp_link=whatsapp_link,
            expected_patients=expected_patients
        )
        
        # Store clinic name in notes field temporarily
        doctor.notes = f"Clinic: {clinic_name}, City: {city}"
        
        db.add(doctor)
        db.commit()
        db.refresh(doctor)
        
        print(f"✅ New doctor application: {name} ({whatsapp_number})")
        
        # Redirect to success page
        return RedirectResponse(url="/doctor/apply/success", status_code=303)
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Application error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Application failed: {str(e)}")


@router.get("/doctor/apply/success", response_class=HTMLResponse)
async def apply_success_page(request: Request):
    """Application success page"""
    return templates.TemplateResponse("public/apply_success.html", {
        "request": request
    })
