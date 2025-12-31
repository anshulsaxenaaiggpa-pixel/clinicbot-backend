"""
Admin UI Dependencies - RBAC Enforcement with Policy Violation Logging

FastAPI dependencies for admin authentication, RBAC, and CSRF protection.
"""
from typing import Optional
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
    Redirects to login if not authenticated.
    """
    # Get session cookie
    session_token = request.cookies.get(session_manager.COOKIE_NAME)
    
    if not session_token:
        # Not authenticated - redirect to login
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/admin/login"}
        )
    
    # Validate session
    client_ip = get_client_ip(request)
    session_data = session_manager.validate_session(session_token, client_ip)
    
    if not session_data:
        # Invalid/expired session - redirect to login
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/admin/login"}
        )
    
    # Retrieve admin user
    admin_user = db.query(AdminUser).filter(
        AdminUser.id == session_data["user_id"]
    ).first()
    
    if not admin_user or not admin_user.is_active:
        # User not found or inactive
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account inactive"
        )
    
    # Store session data in request state for templates
    request.state.admin_user = admin_user
    request.state.csrf_token = session_data["csrf_token"]
    
    return admin_user


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
