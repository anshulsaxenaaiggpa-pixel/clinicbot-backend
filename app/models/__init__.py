"""
SQLAlchemy models package.
Import all models here to ensure they're registered with SQLAlchemy.
"""

from app.models.clinic import Clinic
from app.models.clinic_timing import ClinicTiming, ClosedDate
from app.models.doctor import Doctor
from app.models.service import Service
from app.models.patient import Patient
from app.models.appointment import Appointment

__all__ = [
    "Clinic",
    "ClinicTiming",
    "ClosedDate",
    "Doctor",
    "Service",
    "Patient",
    "Appointment",
]
