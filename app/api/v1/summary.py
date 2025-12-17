"""Summary and analytics endpoints for dashboard"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
from uuid import UUID

from app.db.database import get_db
from app.models.appointment import Appointment
from app.schemas.summary import DailySummary, WeeklySummary, DashboardStats
from app.api.v1.slots import get_available_slots

router = APIRouter()


@router.get("/daily", response_model=DailySummary)
def get_daily_summary(
    clinic_id: UUID = Query(...),
    doctor_id: UUID = Query(...),
    date: date = Query(...),
    db: Session = Depends(get_db)
):
    """
    Get daily summary for slot heatmap badges
    
    Returns:
    - Total possible slots
    - Booked slots
    - Free slots
    - Occupancy rate
    - Color coding (red/yellow/green)
    """
    # Get available slots for the day
    slots_response = get_available_slots(
        clinic_id=clinic_id,
        doctor_id=doctor_id,
        date=date,
        db=db
    )
    
    free_slots = slots_response.total_slots
    
    # Get booked appointments for the day
    booked_count = db.query(func.count(Appointment.id)).filter(
        Appointment.clinic_id == clinic_id,
        Appointment.doctor_id == doctor_id,
        Appointment.date == date,
        Appointment.status.in_(['confirmed', 'pending'])
    ).scalar()
    
    # Calculate total theoretical slots (assume 4 per hour, 10-hour day = 40)
    # TODO: Calculate this dynamically from clinic timing
    total_slots = free_slots + booked_count
    
    # Calculate occupancy
    occupancy_rate = booked_count / total_slots if total_slots > 0 else 0.0
    
    # Determine color and status
    if free_slots == 0:
        color = "red"
        status = "Fully Booked"
    elif free_slots <= 3:
        color = "yellow"
        status = "Limited"
    else:
        color = "green"
        status = "Available"
    
    return DailySummary(
        date=date,
        total_slots=total_slots,
        booked_slots=booked_count,
        free_slots=free_slots,
        occupancy_rate=occupancy_rate,
        color=color,
        status=status
    )


@router.get("/weekly", response_model=WeeklySummary)
def get_weekly_summary(
    clinic_id: UUID = Query(...),
    start_date: date = Query(...),
    db: Session = Depends(get_db)
):
    """Get weekly summary for analytics"""
    end_date = start_date + timedelta(days=6)
    
    # Get appointments for the week
    appointments = db.query(Appointment).filter(
        Appointment.clinic_id == clinic_id,
        Appointment.date >= start_date,
        Appointment.date <= end_date
    ).all()
    
    # Calculate metrics
    total_appointments = len([a for a in appointments if a.status in ['confirmed', 'completed']])
    total_revenue = sum(a.amount_paid or 0 for a in appointments if a.status == 'completed')
    no_show_count = len([a for a in appointments if a.status == 'no_show'])
    cancellation_count = len([a for a in appointments if a.status == 'cancelled'])
    
    # TODO: Generate daily summaries for each day
    daily_summaries = []
    
    return WeeklySummary(
        start_date=start_date,
        end_date=end_date,
        daily_summaries=daily_summaries,
        total_appointments=total_appointments,
        total_revenue=total_revenue,
        no_show_count=no_show_count,
        cancellation_count=cancellation_count
    )


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard_stats(
    clinic_id: UUID = Query(...),
    db: Session = Depends(get_db)
):
    """Get high-level dashboard statistics"""
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    
    # Today stats
    today_appointments = db.query(func.count(Appointment.id)).filter(
        Appointment.clinic_id == clinic_id,
        Appointment.date == today,
        Appointment.status.in_(['confirmed', 'completed'])
    ).scalar()
    
    today_revenue = db.query(func.sum(Appointment.amount_paid)).filter(
        Appointment.clinic_id == clinic_id,
        Appointment.date == today,
        Appointment.status == 'completed'
    ).scalar() or 0
    
    # Week stats
    week_appointments = db.query(func.count(Appointment.id)).filter(
        Appointment.clinic_id == clinic_id,
        Appointment.date >= week_start,
        Appointment.status.in_(['confirmed', 'completed'])
    ).scalar()
    
    week_revenue = db.query(func.sum(Appointment.amount_paid)).filter(
        Appointment.clinic_id == clinic_id,
        Appointment.date >= week_start,
        Appointment.status == 'completed'
    ).scalar() or 0
    
    # Month stats
    month_appointments = db.query(func.count(Appointment.id)).filter(
        Appointment.clinic_id == clinic_id,
        Appointment.date >= month_start,
        Appointment.status.in_(['confirmed', 'completed'])
    ).scalar()
    
    month_revenue = db.query(func.sum(Appointment.amount_paid)).filter(
        Appointment.clinic_id == clinic_id,
        Appointment.date >= month_start,
        Appointment.status == 'completed'
    ).scalar() or 0
    
    # TODO: Calculate current occupancy
    # TODO: Get top services
    
    return DashboardStats(
        clinic_id=clinic_id,
        today_appointments=today_appointments,
        today_revenue=today_revenue,
        week_appointments=week_appointments,
        week_revenue=week_revenue,
        month_appointments=month_appointments,
        month_revenue=month_revenue,
        current_occupancy=0.0,  # TODO
        top_services=[]  # TODO
    )
