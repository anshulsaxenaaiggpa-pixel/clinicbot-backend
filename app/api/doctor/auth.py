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
        # Find doctor by whatsapp number
        doctor = db.query(Doctor).filter(Doctor.whatsapp_number == whatsapp_number).first()
        
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Check if account is active
        if not doctor.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account inactive. Contact administrator."
            )
        
        # Verify password
        if not doctor.verify_password(password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Create session
        client_ip = get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")
        session_token, csrf_token = session_manager.create_session(
            admin_user_id=str(doctor.id),
            ip_address=client_ip,
            user_agent=user_agent,
            user_type="doctor"  # Mark as doctor session
        )
        
        # Set cookie and redirect
        response = RedirectResponse(url="/doctor/dashboard", status_code=302)
        cookie_attrs = session_manager.get_cookie_attributes()
        response.set_cookie(
            **cookie_attrs,
            value=session_token
        )
        
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
