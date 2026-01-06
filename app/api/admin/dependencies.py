"""
Admin UI Dependencies - RBAC Enforcement with Policy Violation Logging

FastAPI dependencies for admin authentication, RBAC, and CSRF protection.

CRITICAL FIX: require_admin now returns RedirectResponse instead of raising HTTPException
to properly handle session validation failures and prevent login loops.
"""
from typing import Optional, Union
from fastapi import Request, HTTPException, status, Depends, Header
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth.session import session_manager
from app.models.admin_user import AdminUser, AdminRole
from app.db.session import get_db


def get_client_ip(
    request: Request,
    x_forwarded_for: Optional[str] = Header(None)
) -> str:
    """Extract client IP address from request."""
    # Check if x_forwarded_for is actually a string (not Header default)
    if x_forwarded_for and isinstance(x_forwarded_for, str):
        # Use first IP in X-Forwarded-For chain
        return x_forwarded_for.split(",")[0].strip()
    
    # Fallback to request.client.host
    return request.client.host if request.client else "unknown"


async def require_admin(
    request: Request,
    db: Session = Depends(get_db)
) -> AdminUser:
    """
    Require valid admin session.
    
    Validates session cookie and returns authenticated admin user.
    Raises 401 if not authenticated (triggers redirect to login in browser).
    """
    try:
        # Get session cookie
        session_token = request.cookies.get(session_manager.COOKIE_NAME)
        
        if not session_token:
            print("❌ AUTH: No session token found in cookies")
            # Not authenticated - raise exception that will be caught by frontend
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"Location": "/admin/login"}
            )
        
        # Validate session
        client_ip = get_client_ip(request)
        print(f"🔍 AUTH: Validating session for IP: {client_ip}")
        session_data = session_manager.validate_session(session_token, client_ip)
        
        if not session_data:
            print("❌ AUTH: Session validation failed (invalid/expired)")
            # Invalid/expired session
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired",
                headers={"Location": "/admin/login"}
            )
        
        print(f"✅ AUTH: Session validated for user_id: {session_data.get('user_id')}")
        
        # Retrieve admin user
        admin_user = db.query(AdminUser).filter(
            AdminUser.id == session_data["user_id"]
        ).first()
        
        if not admin_user or not admin_user.is_active:
            print(f"❌ AUTH: User not found or inactive: {session_data.get('user_id')}")
            # User not found or inactive
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"Location": "/admin/login"}
            )
        
        print(f"✅ AUTH: Admin user loaded: {admin_user.email}")
        
        # Store session data in request state for templates
        request.state.admin_user = admin_user
        request.state.csrf_token = session_data.get("csrf_token", "")
        
        return admin_user
    
    except HTTPException:
        # Re-raise HTTP exceptions (expected auth failures)
        raise
    except Exception as e:
        # Catch ALL other errors and log them
        import traceback
        error_trace = traceback.format_exc()
        print(f"\n{'='*80}")
        print(f"❌ CRITICAL: require_admin CRASHED")
        print(f"{'='*80}")
        print(f"Error: {str(e)}")
        print(f"Error Type: {type(e).__name__}")
        print(f"\nFull Traceback:")
        print(error_trace)
        print(f"{'='*80}\n")
        
        # Return detailed error as HTTP response
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            content=f"""
            <html>
                <head><title>Authentication Error</title></head>
                <body style="font-family: monospace; padding: 2rem;">
                    <h1 style="color: red;">❌ Authentication System Error</h1>
                    <p>The authentication system encountered an unexpected error.</p>
                    <div style="background: #f5f5f5; padding: 1rem; border-radius: 5px; overflow: auto;">
                        <strong>Error:</strong> {str(e)}<br>
                        <strong>Type:</strong> {type(e).__name__}<br><br>
                        <strong>Full Traceback:</strong>
                        <pre>{error_trace}</pre>
                    </div>
                    <br>
                    <p><strong>Common causes:</strong></p>
                    <ul>
                        <li>Redis connection failure (check REDIS_URL)</li>
                        <li>Database connection issues</li>
                        <li>Session manager initialization error</li>
                    </ul>
                    <a href="/admin/login">Try logging in again</a>
                </body>
            </html>
            """,
            status_code=500
        )


def require_role(required_role: AdminRole):
    """
    Require admin has specified role or higher with policy violation logging.
    
    Logs all denied access attempts to audit trail for governance tracking.
    
    Usage:
        @router.get("/admin/doctors/edit")
        async def edit_doctor(admin: AdminUser = Depends(require_role(AdminRole.CLINIC_ADMIN))):
            ...
    """
    async def role_checker(
        request: Request,
        admin_user: AdminUser = Depends(require_admin),
        db: Session = Depends(get_db)
    ) -> AdminUser:
        if not admin_user.has_permission(required_role):
            # Log policy violation to audit trail (governance control)
            from app.services.audit_service import AuditService
            
            AuditService.log_event(
                event_type="policy_violation",
                actor="admin",
                actor_id=str(admin_user.id),
                metadata={
                    "violation_type": "insufficient_role",
                    "required_role": required_role.value,
                    "actual_role": admin_user.role.value,
                    "requested_path": str(request.url.path),
                    "ip_address": get_client_ip(request),
                    "user_agent": request.headers.get("user-agent", "unknown")
                },
                db=db
            )
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role.value} role or higher"
            )
        return admin_user
    
    return role_checker


async def validate_csrf(
    request: Request,
    admin_user: AdminUser = Depends(require_admin)
):
    """
    Validate CSRF token for POST PUT/DELETE requests.
    
    Token must be present in form data or X-CSRF-Token header.
    """
    # Get token from form or header
    form_data = await request.form()
    csrf_token = form_data.get("csrf_token") or request.headers.get("X-CSRF-Token")
    
    if not csrf_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing"
        )
    
    # Validate token
    session_token = request.cookies.get(session_manager.COOKIE_NAME)
    
    if not session_manager.validate_csrf_token(session_token, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token"
        )
    
    return True


# Role-specific dependencies for common use cases
require_viewer = require_role(AdminRole.SUPPORT_VIEWER)
require_admin_role = require_role(AdminRole.CLINIC_ADMIN)
require_superadmin = require_role(AdminRole.SUPER_ADMIN)
