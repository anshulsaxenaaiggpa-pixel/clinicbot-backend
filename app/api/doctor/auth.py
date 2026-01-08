"""
Doctor Authentication Routes

Login, logout, and dashboard access for doctors.
"""
from fastapi import APIRouter, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session

from app.auth.session import session_manager
from app.api.doctor.dependencies import require_doctor, get_client_ip
from app.models.doctor import Doctor
from app.db.session import get_db


router = APIRouter(prefix="/doctor", tags=["doctor-auth"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent.parent / "templates"))


@router.get("/", response_class=HTMLResponse)
async def doctor_root(request: Request):
    """Redirect /doctor to /doctor/login"""
    return RedirectResponse(url="/doctor/login", status_code=302)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Display doctor login form."""
    # If already logged in, redirect to dashboard
    session_token = request.cookies.get(session_manager.COOKIE_NAME)
    if session_token:
        client_ip = get_client_ip(request)
        session_data = session_manager.validate_session(session_token, client_ip)
        if session_data and session_data.get("user_type") == "doctor":
            return RedirectResponse(url="/doctor/dashboard", status_code=302)
    
    return templates.TemplateResponse(
        "doctor/login.html",
        {
            "request": request,
            "csrf_token": getattr(request.state, "csrf_token", "")
        }
    )


@router.post("/login")
async def login(
    request: Request,
    whatsapp_number: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Authenticate doctor with phone number and password."""
    try:
        print(f"\n{'='*80}")
        print(f"🔐 DOCTOR LOGIN ATTEMPT")
        print(f"{'='*80}")
        print(f"WhatsApp: {whatsapp_number}")
        print(f"Password length: {len(password)}")
        print(f"Request path: {request.url.path}")
        print(f"Client IP: {request.headers.get('x-forwarded-for', request.client.host if request.client else 'unknown')}")
        
        # Find doctor by whatsapp number
        print(f"🔍 Searching for doctor with WhatsApp: {whatsapp_number}")
        doctor = db.query(Doctor).filter(Doctor.whatsapp_number == whatsapp_number).first()
        
        if not doctor:
            print(f"❌ Doctor not found for WhatsApp: {whatsapp_number}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        print(f"✅ Doctor found: ID={doctor.id}, Name={doctor.name}, Active={doctor.is_active}")
        
        # Check if account is active
        if not doctor.is_active:
            print(f"❌ Doctor account inactive: {doctor.id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account inactive. Contact administrator."
            )
        
        # Verify password
        print(f"🔑 Verifying password...")
        if not doctor.verify_password(password):
            print(f"❌ Password verification failed for doctor: {doctor.id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        print(f"✅ Password verified successfully")
        
        # Create session
        client_ip = get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")
        
        print(f"🎫 Creating session...")
        print(f"   User ID: {doctor.id}")
        print(f"   IP: {client_ip}")
        print(f"   User Agent: {user_agent[:50]}...")
        
        session_token, csrf_token = session_manager.create_session(
            user_id=str(doctor.id),
            ip_address=client_ip,
            user_agent=user_agent,
            user_type="doctor"  # Mark as doctor session
        )
        
        print(f"✅ Session created")
        print(f"   Token length: {len(session_token)}")
        print(f"   CSRF length: {len(csrf_token)}")
        
        # Set cookie and redirect
        response = RedirectResponse(url="/doctor/dashboard", status_code=302)
        cookie_attrs = session_manager.get_cookie_attributes()
        
        print(f"🍪 Setting cookie:")
        print(f"   Name: {cookie_attrs['key']}")
        print(f"   HttpOnly: {cookie_attrs['httponly']}")
        print(f"   Secure: {cookie_attrs['secure']}")
        print(f"   SameSite: {cookie_attrs['samesite']}")
        print(f"   Max Age: {cookie_attrs['max_age']}")
        
        response.set_cookie(
            **cookie_attrs,
            value=session_token
        )
        
        print(f"✅ Redirecting to /doctor/dashboard")
        print(f"{'='*80}\n")
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"❌ Login error: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Login failed: {str(e)}"
        )


@router.api_route("/logout", methods=["GET", "POST"])
async def logout(
    request: Request,
    doctor: Doctor = Depends(require_doctor)
):
    """Logout doctor and destroy session."""
    session_token = request.cookies.get(session_manager.COOKIE_NAME)
    session_manager.destroy_session(session_token)
    
    response = RedirectResponse(url="/doctor/login", status_code=302)
    response.delete_cookie(session_manager.COOKIE_NAME)
    
    return response
