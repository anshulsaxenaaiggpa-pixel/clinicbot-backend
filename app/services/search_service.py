"""
City-Level Search Service - Hybrid Booking Support

Allows patients to find doctors by city + specialty.
Privacy-first: only opt-in doctors (is_searchable=True) appear.
Rate-limited to prevent scraping.
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.doctor import Doctor
from app.services.rate_limiter import RateLimiter
from app.services.audit_service import AuditService


class SearchService:
    """
    City-level doctor search.
    
    Privacy Principles:
    - Only is_searchable=True doctors appear
    - No PHI exposed (doctor info is public business data)
    - Rate-limited (10 searches/min per IP)
    - Metadata-only logging
    """
    
    @staticmethod
    def search_doctors(
        city: str,
        specialty: Optional[str] = None,
        ip_address: str = "unknown",
        db: Session = None
    ) -> List[Dict]:
        """
        Search for doctors by city and optionally specialty.
        
        Returns list of doctors with:
        - name
        - specialty
        - whatsapp_link (for direct booking)
        
        Privacy: Only searchable doctors returned.
        Rate Limited: 10 searches/min per IP.
        """
        # Rate limiting (10 searches per minute per IP)
        rate_limiter = RateLimiter()
        allowed = rate_limiter.check_rate_limit(
            identifier=ip_address,
            limit_type="search",
            max_requests=10,
            window_seconds=60
        )
        
        if not allowed:
            # Log rate limit block
            AuditService.log_event(
                event_type="search_rate_limited",
                actor="patient",
                actor_id=ip_address,
                metadata={"city": city, "specialty": specialty},
                db=db
            )
            raise RateLimitError("Too many search requests. Please try again later.")
        
        # Build query
        query = db.query(Doctor).filter(
            and_(
                Doctor.is_searchable == True,
                Doctor.is_active == True,
                Doctor.city.ilike(f"%{city}%")  # Case-insensitive partial match
            )
        )
        
        # Filter by specialty if provided
        if specialty:
            query = query.filter(Doctor.specialization.ilike(f"%{specialty}%"))
        
        # Execute query
        doctors = query.order_by(Doctor.name).limit(50).all()  # Max 50 results
        
        # Format response (metadata only)
        results = [
            {
                "id": str(doctor.id),
                "name": doctor.full_name,
                "specialty": doctor.specialty,
                "city": doctor.city,
                "whatsapp_link": doctor.get_shareable_link(),
                "clinic_id": doctor.clinic_id
            }
            for doctor in doctors
        ]
        
        # Log search (metadata only, no PHI)
        AuditService.log_event(
            event_type="doctor_search",
            actor="patient",
            actor_id=ip_address,
            metadata={
                "city": city,
                "specialty": specialty,
                "results_count": len(results)
            },
            db=db
        )
        
        return results
    
    @staticmethod
    def get_doctor_by_whatsapp(whatsapp_number: str, db: Session) -> Optional[Doctor]:
        """
        Get doctor by WhatsApp number for routing.
        
        Used internally for booking flow routing.
        Returns doctor regardless of is_searchable status.
        """
        return db.query(Doctor).filter(
            Doctor.whatsapp_number == whatsapp_number,
            Doctor.is_active == True
        ).first()
    
    @staticmethod
    def update_doctor_searchable(
        doctor_id: str,
        searchable: bool,
        admin_user_id: str,
        db: Session
    ) -> bool:
        """
        Update doctor's search visibility (opt-in/opt-out).
        
        Admin-only function.
        Logs preference change for audit.
        """
        doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
        
        if not doctor:
            return False
        
        old_status = doctor.is_searchable
        doctor.set_searchable(searchable)
        db.commit()
        
        # Log preference change
        AuditService.log_event(
            event_type="doctor_searchable_updated",
            actor="admin",
            actor_id=admin_user_id,
            metadata={
                "doctor_id": doctor_id,
                "doctor_name": doctor.full_name,
                "old_status": old_status,
                "new_status": searchable
            },
            db=db
        )
        
        return True


class RateLimitError(Exception):
    """Raised when search rate limit is exceeded."""
    pass
