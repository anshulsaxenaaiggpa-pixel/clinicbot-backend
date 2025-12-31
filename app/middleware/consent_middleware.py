"""
Consent Middleware - MANDATORY Protection

DO NOT MODIFY LOGIC OUTSIDE CONSENT SCOPE.
DO NOT ALLOW PHI ACCESS WITHOUT CONSENT.

This middleware enforces consent checking before any patient/booking operations.
Module 2 Requirement: Block all PHI access until consent = granted.
"""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import re

from app.services.consent_service import check_consent


# Endpoints that require consent (whitelist PHI-touching endpoints)
CONSENT_REQUIRED_ENDPOINTS = [
    r"/api/v1/appointments.*",  # All appointment operations
    r"/api/v1/patients.*",       # All patient operations
    r"/api/v1/bookings.*",       # Booking operations
    r"/api/v1/whatsapp/webhook", # WhatsApp messages (except consent flow)
]

# Endpoints explicitly exempt from consent check
CONSENT_EXEMPT_ENDPOINTS = [
    r"/api/v1/consent.*",        # Consent endpoints themselves
    r"/api/v1/clinics.*",        # Public clinic info
    r"/api/v1/doctors.*",        # Public doctor info
    r"/api/v1/services.*",       # Public service info
    r"/docs.*",                  # API documentation
    r"/health.*",                # Health checks
]


class ConsentMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce consent before processing PHI.
    
    Checks if endpoint requires consent, extracts phone number,
    and verifies consent granted before allowing request through.
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Check consent before processing PHI-touching requests.
        
        Flow:
        1. Check if endpoint requires consent
        2. Extract phone number from request
        3. Verify consent granted
        4. If not granted → return 403
        5. If granted → allow request
        """
        path = request.url.path
        
        # Check if this endpoint is exempt from consent
        for exempt_pattern in CONSENT_EXEMPT_ENDPOINTS:
            if re.match(exempt_pattern, path):
                # Allow through without consent check
                return await call_next(request)
        
        # Check if this endpoint requires consent
        requires_consent = False
        for required_pattern in CONSENT_REQUIRED_ENDPOINTS:
            if re.match(required_pattern, path):
                requires_consent = True
                break
        
        if not requires_consent:
            # Endpoint doesn't touch PHI, allow through
            return await call_next(request)
        
        # Extract phone number from request
        phone_number = await self._extract_phone_number(request)
        
        if not phone_number:
            # Cannot determine phone number, block request
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number required for this operation"
            )
        
        # Check if consent granted
        if not check_consent(phone_number):
            # NO CONSENT = BLOCK REQUEST
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Consent required. No patient data can be processed without consent."
            )
        
        # Consent granted, allow request
        return await call_next(request)
    
    async def _extract_phone_number(self, request: Request) -> str:
        """
        Extract phone number from request.
        
        Checks in order:
        1. Path parameter (e.g., /patients/{phone})
        2. Query parameter (e.g., ?phone=...)
        3. Request body (JSON)
        4. Header (X-Phone-Number)
        """
        # Check path parameters
        phone = request.path_params.get("phone") or request.path_params.get("phone_number")
        if phone:
            return phone
        
        # Check query parameters
        phone = request.query_params.get("phone") or request.query_params.get("phone_number")
        if phone:
            return phone
        
        # Check request body (if JSON)
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.json()
                phone = body.get("phone") or body.get("phone_number") or body.get("patient_phone")
                if phone:
                    return phone
            except:
                pass  # Not JSON or can't parse
        
        # Check headers
        phone = request.headers.get("X-Phone-Number")
        if phone:
            return phone
        
        return None
