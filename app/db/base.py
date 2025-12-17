"""
Registry Bootstrap - Import all models to register them with SQLAlchemy
This ensures all models are discovered before any operations.
"""
from app.db.base_class import Base

# Import all models so they register with the Base registry
# This MUST happen before any table creation or queries
import app.models.clinic
import app.models.clinic_timing  # Imports both ClinicTiming and ClosedDate
import app.models.doctor
import app.models.service
import app.models.patient
import app.models.appointment

# Explicitly reference the classes to ensure they're fully loaded
from app.models.clinic import Clinic
from app.models.clinic_timing import ClinicTiming, ClosedDate
from app.models.doctor import Doctor
from app.models.service import Service
from app.models.patient import Patient
from app.models.appointment import Appointment

__all__ = ["Base", "Clinic", "ClinicTiming", "ClosedDate", "Doctor", "Service", "Patient", "Appointment"]
