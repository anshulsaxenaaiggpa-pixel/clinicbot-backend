"""
Admin Authentication Routes

Login, logout, and session management for admin UI.
"""
from fastapi import APIRouter, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session

from app.auth.session import session_manager
from app.api.admin.dependencies import get_client_ip, require_admin
from app.models.admin_user import AdminUser
from app.services.audit_service import AuditService
from app.services.rate_limiter import RateLimiter
from app.db.session import get_db


router = APIRouter(prefix="/admin", tags=["admin-auth"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent.parent / "templates"))


@router.get("/", response_class=HTMLResponse)
async def admin_root(request: Request):
    """Redirect /admin to /admin/login"""
    return RedirectResponse(url="/admin/login", status_code=302)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Display login form."""
    # If already logged in, redirect to dashboard
    session_token = request.cookies.get(session_manager.COOKIE_NAME)
    if session_token:
        client_ip = get_client_ip(request)
        session_data = session_manager.validate_session(session_token, client_ip)
        if session_data:
            return RedirectResponse(url="/admin/dashboard", status_code=302)
    
    return templates.TemplateResponse(
        "login.html",
        {"request": request}
    )


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    mfa_token: str = Form(None),
    db: Session = Depends(get_db)
):
    try:
        return await _login_impl(request, email, password, mfa_token, db)
    except Exception as e:
        import traceback
        return HTMLResponse(
            content=f"<h1>Login Error</h1><p>{str(e)}</p><pre>{traceback.format_exc()}</pre>",
            status_code=500
        )

async def _login_impl(
    request: Request,
    email: str,
    password: str,
    mfa_token: str,
    db: Session
):
    """
    Authenticate admin user.
    
    Flow:
    1. Rate limit check (5 attempts/15 min per IP)
    2. Find user by email
    3. Check account lockout
    4. Verify password
    5. Verify MFA if enabled
    6. Create session
    7. Redirect to dashboard
    """
    client_ip = get_client_ip(request)
    rate_limiter = RateLimiter()
    
    # Rate limit: 5 login attempts per 15 minutes per IP
    rate_limit_key = f"login_attempt:{client_ip}"
    allowed, error_msg = rate_limiter.check_rate_limit(rate_limit_key, "login", max_requests=5, window_seconds=900)
    if not allowed:
        # Log failed attempt
        AuditService.log_event(
            event_type="admin_login_rate_limited",
            actor="system",
            actor_id=client_ip,
            metadata={"email": email, "reason": "rate_limit"},
            db=db
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again in 15 minutes."
        )
    
    # Find user
    user = db.query(AdminUser).filter(AdminUser.email == email).first()
    
    if not user:
        # User not found - log and return generic error
        AuditService.log_event(
            event_type="admin_login_failed",
            actor="system",
            actor_id=client_ip,
            metadata={"email": email, "reason": "user_not_found"},
            db=db
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check account lockout
    if user.is_locked():
        AuditService.log_event(
            event_type="admin_login_failed",
            actor="admin",
            actor_id=str(user.id),
            metadata={"email": email, "reason": "account_locked"},
            db=db
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account locked until {user.locked_until.strftime('%H:%M')}. Too many failed attempts."
        )
    
    # Verify password
    if not user.verify_password(password):
        # Record failed attempt
        user.record_failed_login()
        db.commit()
        
        AuditService.log_event(
            event_type="admin_login_failed",
            actor="admin",
            actor_id=str(user.id),
            metadata={
                "email": email,
                "reason": "invalid_password",
                "failed_attempts": user.failed_login_attempts,
                "ip_address": client_ip
            },
            db=db
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if account is active
    if not user.is_active:
        AuditService.log_event(
            event_type="admin_login_failed",
            actor="admin",
            actor_id=str(user.id),
            metadata={"email": email, "reason": "account_inactive"},
            db=db
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account inactive. Contact administrator."
        )
    
    # Verify MFA if enabled
    if user.mfa_enabled:
        if not mfa_token:
            # MFA required but not provided - return to login with MFA prompt
            return templates.TemplateResponse(
                "login.html",
                {
                    "request": request,
                    "email": email,
                    "require_mfa": True
                }
            )
        
        if not user.verify_mfa_token(mfa_token):
            # Invalid MFA token
            user.record_failed_login()
            db.commit()
            
            AuditService.log_event(
                event_type="admin_login_failed",
                actor="admin",
                actor_id=str(user.id),
                metadata={"email": email, "reason": "invalid_mfa", "ip_address": client_ip},
                db=db
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid MFA token"
            )
    
    # Authentication successful
    user.record_successful_login(client_ip)
    db.commit()
    
    # Create session
    user_agent = request.headers.get("user-agent", "unknown")
    session_token, csrf_token = session_manager.create_session(
        admin_user_id=str(user.id),
        ip_address=client_ip,
        user_agent=user_agent
    )
    
    # Log successful login
    AuditService.log_event(
        event_type="admin_login_success",
        actor="admin",
        actor_id=str(user.id),
        metadata={
            "email": email,
            "ip_address": client_ip,
            "user_agent": user_agent
        },
        db=db
    )
    
    # Set session cookie and redirect
    response = RedirectResponse(url="/admin/dashboard", status_code=302)
    cookie_attrs = session_manager.get_cookie_attributes()
    response.set_cookie(
        **cookie_attrs,
        value=session_token
    )
    
    return response


@router.api_route("/logout", methods=["GET", "POST"])
async def logout(
    request: Request,
    admin_user: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Logout admin user and destroy session."""
    session_token = request.cookies.get(session_manager.COOKIE_NAME)
    
    # Destroy session
    session_manager.destroy_session(session_token)
    
    # Log logout
    client_ip = get_client_ip(request)
    AuditService.log_event(
        event_type="admin_logout",
        actor="admin",
        actor_id=str(admin_user.id),
        metadata={"ip_address": client_ip},
        db=db
    )
    
    # Clear cookie and redirect to login
    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie(session_manager.COOKIE_NAME)
    
    return response


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    admin_user: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin dashboard with overview stats."""
    from app.models.doctor import Doctor
    from app.models.audit_log import AuditLog
    
    # Get stats
    total_doctors = db.query(Doctor).count()
    active_doctors = db.query(Doctor).filter(Doctor.is_active == True).count()

    
    # Recent audit events - TEMPORARILY DISABLED due to schema mismatch
    # TODO: Run alembic migration to fix audit_log table schema
    # recent_events = db.query(AuditLog).order_by(
    #     AuditLog.timestamp.desc()
    # ).limit(10).all()
    recent_events = []  # Empty for now until migration is run
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "admin_user": admin_user,
            "csrf_token": request.state.csrf_token,
            "stats": {
                "total_doctors": total_doctors,
                "active_doctors": active_doctors
            },
            "recent_events": recent_events
        }
    )
