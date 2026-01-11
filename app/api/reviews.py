"""
Patient review system for doctors
Updates doctor.rating_average and doctor.review_count
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field
from datetime import datetime

from app.db.session import get_db
from app.models.doctor import Doctor
from app.models.appointment import Appointment

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


class ReviewCreate(BaseModel):
    appointment_id: str
    rating: float = Field(..., ge=1.0, le=5.0, description="Rating from 1.0 to 5.0")
    comment: str = Field(None, max_length=500, description="Optional review comment")


class Review(BaseModel):
    """Stored in appointment metadata for now"""
    appointment_id: str
    doctor_id: str
    patient_name: str
    rating: float
    comment: str
    created_at: datetime


@router.post("/", status_code=201)
async def create_review(
    review: ReviewCreate,
    db: Session = Depends(get_db)
):
    """
    Submit a review for a completed appointment
    Updates doctor's rating_average and review_count
    """
    try:
        # Get appointment
        appointment = db.query(Appointment).filter(
            Appointment.id == review.appointment_id
        ).first()
        
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")
        
        if appointment.status != "completed":
            raise HTTPException(
                status_code=400, 
                detail="Can only review completed appointments"
            )
        
        # Check if already reviewed (stored in appointment metadata)
        if hasattr(appointment, 'review_rating') and appointment.review_rating:
            raise HTTPException(status_code=400, detail="Appointment already reviewed")
        
        # Get doctor
        doctor = db.query(Doctor).filter(Doctor.id == appointment.doctor_id).first()
        
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")
        
        # Update doctor's rating
        current_total = (doctor.rating_average or 0) * (doctor.review_count or 0)
        new_count = (doctor.review_count or 0) + 1
        new_average = (current_total + review.rating) / new_count
        
        doctor.rating_average = round(new_average, 2)
        doctor.review_count = new_count
        
        # Store review in appointment (simple approach)
        # In production, you'd have a separate reviews table
        appointment.review_rating = review.rating
        appointment.review_comment = review.comment
        appointment.reviewed_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "message": "Review submitted successfully",
            "doctor_rating": {
                "average": doctor.rating_average,
                "count": doctor.review_count
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Review submission error: {str(e)}")


@router.get("/doctor/{doctor_id}")
async def get_doctor_reviews(
    doctor_id: str,
    db: Session = Depends(get_db),
    limit: int = 10,
    offset: int = 0
):
    """
    Get reviews for a specific doctor
    Returns appointments with ratings
    """
    try:
        # Get doctor
        doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
        
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")
        
        # Get reviewed appointments
        reviewed_appointments = db.query(Appointment).filter(
            Appointment.doctor_id == doctor_id,
            Appointment.review_rating.isnot(None)
        ).order_by(Appointment.reviewed_at.desc()).offset(offset).limit(limit).all()
        
        reviews = []
        for apt in reviewed_appointments:
            reviews.append({
                "appointment_id": apt.id,
                "patient_name": apt.patient_name,
                "rating": apt.review_rating,
                "comment": apt.review_comment,
                "date": apt.date.isoformat(),
                "reviewed_at": apt.reviewed_at.isoformat() if apt.reviewed_at else None
            })
        
        return {
            "doctor": {
                "id": doctor.id,
                "name": doctor.name,
                "rating_average": doctor.rating_average,
                "review_count": doctor.review_count
            },
            "reviews": reviews,
            "total": doctor.review_count or 0
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching reviews: {str(e)}")


@router.get("/stats")
async def get_review_stats(db: Session = Depends(get_db)):
    """
    Get platform-wide review statistics
    """
    try:
        total_reviews = db.query(func.sum(Doctor.review_count)).scalar() or 0
        avg_rating = db.query(func.avg(Doctor.rating_average)).filter(
            Doctor.review_count > 0
        ).scalar() or 0
        
        top_rated = db.query(Doctor).filter(
            Doctor.review_count >= 5  # At least 5 reviews
        ).order_by(Doctor.rating_average.desc()).limit(10).all()
        
        return {
            "total_reviews": total_reviews,
            "platform_average": round(avg_rating, 2),
            "top_rated_doctors": [
                {
                    "id": d.id,
                    "name": d.name,
                    "city": d.city,
                    "specialization": d.specialization,
                    "rating": d.rating_average,
                    "review_count": d.review_count
                }
                for d in top_rated
            ]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats error: {str(e)}")
