"""
Admin Authentication API - Sprint Task 1

Endpoints for admin login, MFA setup, password management.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.auth_service import AuthService, AuthenticationError, require_auth
from app.models.admin_user import AdminUser, AdminRole


router = APIRouter(prefix="/admin/auth", tags=["admin_auth"])


class LoginRequest(BaseModel):
    """Login request body."""
    email: EmailStr
    password: str = Field(..., min_length=1)
    mfa_token: Optional[str] = Field(None, min_length=6, max_length=6)


class LoginResponse(BaseModel):
    """Login response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 1800  # 30 minutes in seconds
    user: dict
    requires_password_change: bool = False


class ChangePasswordRequest(BaseModel):
    """Password change request."""
    current_password: str
    new_password: str = Field(..., min_length=12)


class MFASetupResponse(BaseModel):
    """MFA setup response."""
    secret: str
    qr_code_uri: str
    instructions: str


@router.post("/login", response_model=LoginResponse)
def login(
    request: LoginRequest,
    ip_address: str = Header(None, alias="X-Forwarded-For"),
    db: Session = Depends(get_db)
):
    """
    Admin login endpoint.
    
    Requires email, password, and optionally MFA token.
    Returns JWT access token on success.
    
    Security features:
    - Account lockout after 5 failed attempts (30 minutes)
    - MFA required if enabled
    - All attempts logged to audit_log
    """
    try:
        user, access_token = AuthService.authenticate(
            email=request.email,
            password=request.password,
            mfa_token=request.mfa_token,
            ip_address=ip_address or "unknown",
            db=db
        )
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user={
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value,
                "mfa_enabled": user.mfa_enabled
            },
            requires_password_change=user.requires_password_change()
        )
    
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/logout")
def logout(
    user: AdminUser = Depends(require_auth()),
    db: Session = Depends(get_db)
):
    """
    Logout (logs event for audit).
    
    Note: JWT tokens can't be invalidated without token blacklist.
    Token will remain valid until expiry.
    """
    AuthService.logout(str(user.id), db)
    return {"message": "Logged out successfully"}


@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    user: AdminUser = Depends(require_auth()),
    db: Session = Depends(get_db)
):
    """
    Change password for current user.
    
    Requires current password verification.
    Enforces password policy (12+ chars, complexity).
    """
    try:
        AuthService.change_password(
            user=user,
            current_password=request.current_password,
            new_password=request.new_password,
            db=db
        )
        return {"message": "Password changed successfully"}
    
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mfa/setup", response_model=MFASetupResponse)
def setup_mfa(
    user: AdminUser = Depends(require_auth()),
    db: Session = Depends(get_db)
):
    """
    Enable MFA for current user.
    
    Returns TOTP secret and QR code URI for authenticator app.
    User must save secret and verify with token before MFA is active.
    """
    secret = user.enable_mfa()
    qr_uri = user.get_mfa_uri()
    
    db.commit()
    
    return MFASetupResponse(
        secret=secret,
        qr_code_uri=qr_uri,
        instructions="Scan QR code with Google Authenticator or Authy, then verify with a token"
    )


@router.post("/mfa/verify")
def verify_mfa(
    token: str = Field(..., min_length=6, max_length=6),
    user: AdminUser = Depends(require_auth()),
    db: Session = Depends(get_db)
):
    """
    Verify MFA token to confirm setup.
    
    Must be called after /mfa/setup to activate MFA.
    """
    if not user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA not set up")
    
    if not user.verify_mfa_token(token):
        raise HTTPException(status_code=400, detail="Invalid MFA token")
    
    return {"message": "MFA verified successfully"}


@router.get("/me")
def get_current_user(
    user: AdminUser = Depends(require_auth())
):
    """Get current user profile."""
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "mfa_enabled": user.mfa_enabled,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "password_last_changed": user.password_last_changed.isoformat(),
        "requires_password_change": user.requires_password_change()
    }


# Protected endpoint example
@router.get("/admin-only")
def admin_only_endpoint(
    user: AdminUser = Depends(require_auth(AdminRole.SUPER_ADMIN))
):
    """
    Example endpoint requiring super_admin role.
    
    Access control is enforced by require_auth dependency.
    """
    return {"message": f"Hello {user.email}, you are a super admin!"}
