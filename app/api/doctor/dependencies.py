"""
Doctor Authentication Dependencies

Session validation and authentication for doctor-facing UI.
"""
from typing import Optional
from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.auth.session import session_manager
from app.models.doctor import Doctor
from app.db.session import get_db


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request."""
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def require_doctor(
    request: Request,
    db: Session = Depends(get_db)
) -> Doctor:
    """
    Require valid doctor session.
    
    Validates session cookie and returns authenticated doctor.
    Raises 401 if not authenticated.
    """
    try:
        # Get session cookie
        session_token = request.cookies.get(session_manager.COOKIE_NAME)
        
        if not session_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"Location": "/doctor/login"}
            )
        
        # Validate session
        client_ip = get_client_ip(request)
        session_data = session_manager.validate_session(session_token, client_ip)
        
        if not session_data or session_data.get("user_type") != "doctor":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid doctor session",
                headers={"Location": "/doctor/login"}
            )
        
        # Retrieve doctor
        doctor = db.query(Doctor).filter(
            Doctor.id == session_data["user_id"]
        ).first()
        
        if not doctor or not doctor.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Doctor not found or inactive",
                headers={"Location": "/doctor/login"}
            )
        
        # Store in request state for templates
        request.state.doctor = doctor
        request.state.csrf_token = session_data.get("csrf_token", "")
        
        return doctor
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"❌ Doctor auth error: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Authentication error: {str(e)}"
        )


async def validate_csrf(
    request: Request,
    doctor: Doctor = Depends(require_doctor)
):
    """Validate CSRF token for POST/PUT/DELETE requests."""
    form_data = await request.form()
    csrf_token = form_data.get("csrf_token") or request.headers.get("X-CSRF-Token")
    
    if not csrf_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing"
        )
    
    session_token = request.cookies.get(session_manager.COOKIE_NAME)
    
    if not session_manager.validate_csrf_token(session_token, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token"
        )
    
    return True
