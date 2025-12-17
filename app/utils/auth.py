"""API key authentication middleware"""
from fastapi import Request, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from typing import Optional
import secrets

from app.db.database import get_db
from app.models.clinic import Clinic
from app.utils.errors import UnauthorizedError

# Header for API key
API_KEY_HEADER = APIKeyHeader(name="X-CLINIC-KEY", auto_error=False)


def generate_api_key() -> str:
    """Generate a secure random API key"""
    return f"clinic_{secrets.token_urlsafe(32)}"


async def verify_api_key(api_key: str, db: Session) -> Optional[Clinic]:
    """
    Verify API key and return associated clinic
    
    Args:
        api_key: API key from header
        db: Database session
        
    Returns:
        Clinic if valid, None otherwise
    """
    if not api_key:
        return None
    
    # Query clinic by API key
    clinic = db.query(Clinic).filter(
        Clinic.api_key == api_key,
        Clinic.is_active == True
    ).first()
    
    return clinic


async def get_current_clinic(
    api_key: str = API_KEY_HEADER,
    db: Session = get_db()
) -> Clinic:
    """
    Dependency to get current authenticated clinic
    
    Usage in endpoints:
        clinic: Clinic = Depends(get_current_clinic)
    """
    if not api_key:
        raise UnauthorizedError("API key required")
    
    clinic = await verify_api_key(api_key, db)
    if not clinic:
        raise UnauthorizedError("Invalid API key")
    
    return clinic


# Public endpoints that don't require auth
PUBLIC_PATHS = [
    "/",
    "/health",
    "/docs",
    "/openapi.json",
    "/api/v1/clinics",  # Clinic creation
]


def is_public_path(path: str) -> bool:
    """Check if path is public (no auth required)"""
    for public_path in PUBLIC_PATHS:
        if path.startswith(public_path):
            return True
    return False
