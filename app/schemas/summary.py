"""Summary and analytics schemas"""
from pydantic import BaseModel, Field
from typing import Any, Dict, List
from datetime import date
from uuid import UUID


class DailySummary(BaseModel):
    """Summary for a single day"""
    date: date
    total_slots: int
    booked_slots: int
    free_slots: int
    occupancy_rate: float = Field(..., ge=0.0, le=1.0, description="Percentage as decimal")
    color: str = Field(..., pattern='^(red|yellow|green)$')
    status: str = Field(..., description="Fully Booked / Limited / Available")


class WeeklySummary(BaseModel):
    """Summary for a week"""
    start_date: date
    end_date: date
    daily_summaries: List[DailySummary]
    total_appointments: int
    total_revenue: int = Field(..., description="Total revenue in rupees")
    no_show_count: int
    cancellation_count: int


class DashboardStats(BaseModel):
    """Dashboard overview stats"""
    clinic_id: UUID
    today_appointments: int
    today_revenue: int
    week_appointments: int
    week_revenue: int
    month_appointments: int
    month_revenue: int
    current_occupancy: float
    top_services: List[Dict[str, Any]] = Field(..., description="Top 5 services by bookings")
