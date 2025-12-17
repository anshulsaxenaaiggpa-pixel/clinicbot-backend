"""Standardized error responses for API"""
from fastapi import HTTPException, status
from typing import Dict, Any, Optional


class APIError(HTTPException):
    """Base API error with standardized structure"""
    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code
        self.details = details or {}
        super().__init__(
            status_code=status_code,
            detail={
                "success": False,
                "error_code": error_code,
                "message": message,
                "details": self.details
            }
        )


# Predefined errors
class SlotTakenError(APIError):
    def __init__(self, appointment_id: str = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code="SLOT_TAKEN",
            message="Requested slot overlaps with an existing appointment",
            details={"conflict_appointment_id": appointment_id} if appointment_id else {}
        )


class InvalidClinicError(APIError):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="INVALID_CLINIC",
            message="Clinic not found or inactive"
        )


class InvalidDoctorError(APIError):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="INVALID_DOCTOR",
            message="Doctor not found or inactive"
        )


class InvalidServiceError(APIError):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="INVALID_SERVICE",
            message="Service not found or inactive"
        )


class UnauthorizedError(APIError):
    def __init__(self, message: str = "Invalid or missing API key"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED",
            message=message
        )


class RateLimitError(APIError):
    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            message="Too many requests. Please try again later.",
            details={"retry_after_seconds": retry_after}
        )


class ValidationError(APIError):
    def __init__(self, field: str, message: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            message=message,
            details={"field": field}
        )
