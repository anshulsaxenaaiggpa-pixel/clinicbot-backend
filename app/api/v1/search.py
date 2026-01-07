"""
Search API Endpoints - Hybrid Booking

City-level doctor search for patients without direct doctor contact.
Privacy-first: only opt-in doctors appear.
"""
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import Base Model
from typing import Optional, List
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.search_service import SearchService, RateLimitError


router = APIRouter(prefix="/api/v1/search", tags=["search"])


class DoctorSearchResult(BaseModel):
    """Doctor search result (public data only)."""
    id: str
    name: str
    specialty: Optional[str]
    city: str
    whatsapp_link: str
    clinic_id: Optional[str]


@router.get("/doctors", response_model=List[DoctorSearchResult])
def search_doctors(
    city: str = Query(..., min_length=2, description="City name"),
    specialty: Optional[str] = Query(None, description="Doctor specialty (optional)"),
    x_forwarded_for: str = Header(None, alias="X-Forwarded-For"),
    db: Session = Depends(get_db)
):
    """
    Search for doctors by city and optionally specialty.
    
    **Privacy:**
    - Only returns doctors with is_searchable=True
    - No patient PHI exposed
    
    **Rate Limiting:**
    - 10 searches per minute per IP
    - Returns 429 if exceeded
    
    **Returns:**
    - List of up to 50 matching doctors
    - Each with name, specialty, city, and WhatsApp link for direct booking
    """
    try:
        ip_address = x_forwarded_for or "unknown"
        
        results = SearchService.search_doctors(
            city=city,
            specialty=specialty,
            ip_address=ip_address,
            db=db
        )
        
        return results
    
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Search failed")


@router.get("/doctors/{doctor_id}/link")
def get_doctor_whatsapp_link(
    doctor_id: str,
    db: Session = Depends(get_db)
):
    """
    Get WhatsApp link for a specific doctor.
    
    Public endpoint - no auth required.
    Returns shareable link for direct booking.
    """
    from app.models.doctor import Doctor
    
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    
    if not doctor or not doctor.is_active:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    link = doctor.get_shareable_link()
    
    if not link:
        raise HTTPException(status_code=404, detail="WhatsApp number not configured")
    
    return {
        "doctor_id": str(doctor.id),
        "doctor_name": doctor.full_name,
        "whatsapp_link": link,
        "qr_code_data": doctor.get_qr_code_data()
    }
