"""
SQLAlchemy models package.
CRITICAL: Import all models here to ensure they're registered with SQLAlchemy.
This file MUST be imported before any model usage.
"""

# Force-load ALL models - this ensures SQLAlchemy sees them before mapper configuration
from app.models.clinic import Clinic  # noqa: F401
from app.models.clinic_timing import ClinicTiming, ClosedDate  # noqa: F401
from app.models.doctor import Doctor  # noqa: F401
from app.models.service import Service  # noqa: F401
from app.models.patient import Patient  # noqa: F401
from app.models.appointment import Appointment  # noqa: F401

__all__ = [
    "Clinic",
    "ClinicTiming",
    "ClosedDate",
    "Doctor",
    "Service",
    "Patient",
    "Appointment",
]
