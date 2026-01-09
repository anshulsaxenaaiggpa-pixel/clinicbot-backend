"""Doctor Feedback Module - Patient ratings and reviews"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta

from app.db.database import get_db
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.api.doctor.dependencies import get_current_doctor

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/feedback", response_class=HTMLResponse)
async def feedback_page(
    request: Request,
    doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """
    Display patient feedback and ratings
    """
    # Calculate average rating (simulated for now - will connect to real ratings later)
    total_appointments = db.query(Appointment).filter(
        Appointment.doctor_id == doctor.id,
        Appointment.status == "completed"
    ).count()
    
    # Simulated ratings (replace with actual ratings table later)
    average_rating = 4.7
    total_ratings = int(total_appointments * 0.6)  # 60% of patients leave feedback
    
    # Rating distribution
    ratings_distribution = {
        5: int(total_ratings * 0.65),
        4: int(total_ratings * 0.25),
        3: int(total_ratings * 0.07),
        2: int(total_ratings * 0.02),
        1: int(total_ratings * 0.01)
    }
    
    # Recent feedback (simulated)
    recent_feedback = [
        {
            "patient_name": "Rajesh K.",
            "rating": 5,
            "comment": "Excellent doctor! Very caring and thorough examination.",
            "date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        },
        {
            "patient_name": "Priya M.",
            "rating": 5,
            "comment": "Great experience. Would definitely recommend!",
            "date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        },
        {
            "patient_name": "Amit S.",
            "rating": 4,
            "comment": "Good consultation, but had to wait a bit longer.",
            "date": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        }
    ]
    
    return templates.TemplateResponse("doctor/feedback.html", {
        "request": request,
        "doctor": doctor,
        "average_rating": average_rating,
        "total_ratings": total_ratings,
        "ratings_distribution": ratings_distribution,
        "recent_feedback": recent_feedback,
        "total_appointments": total_appointments
    })
