"""
Doctor Slot & Availability Management Routes

Allows doctors to manage their weekly schedule and leaves.
"""
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session
from datetime import datetime, date, time
import uuid

from app.api.doctor.dependencies import require_doctor, validate_csrf
from app.models.doctor import Doctor
from app.models.doctor_availability import DoctorAvailability, DoctorLeave
from app.db.session import get_db


router = APIRouter(prefix="/doctor", tags=["doctor-slots"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent.parent / "templates"))


@router.get("/slots", response_class=HTMLResponse)
async def slot_management(
    request: Request,
    doctor: Doctor = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    """Display and manage availability slots."""
    try:
        # Get doctor's weekly availability (ordered by day and time)
        availability = db.query(DoctorAvailability).filter(
            DoctorAvailability.doctor_id == doctor.id,
            DoctorAvailability.is_active == True
        ).order_by(
            DoctorAvailability.day_of_week,
            DoctorAvailability.start_time
        ).all()
        
        # Get upcoming leaves
        today = date.today()
        leaves = db.query(DoctorLeave).filter(
            DoctorLeave.doctor_id == doctor.id,
            DoctorLeave.leave_date >= today
        ).order_by(DoctorLeave.leave_date).all()
        
        # Group availability by day
        days_map = {
            0: "Monday", 1: "Tuesday", 2: "Wednesday", 
            3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"
        }
        
        availability_by_day = {}
        for slot in availability:
            day_name = days_map[slot.day_of_week]
            if day_name not in availability_by_day:
                availability_by_day[day_name] = []
            availability_by_day[day_name].append(slot)
        
        return templates.TemplateResponse(
            "doctor/slots.html",
            {
                "request": request,
                "doctor": doctor,
                "csrf_token": request.state.csrf_token,
                "availability_by_day": availability_by_day,
                "leaves": leaves,
                "days_map": days_map,
                "today": today  # For date picker min value
            }
        )
    
    except Exception as e:
        import traceback
        print(f"❌ Slots error: {traceback.format_exc()}")
        return HTMLResponse(
            content=f"<h1>Error</h1><pre>{traceback.format_exc()}</pre>",
            status_code=500
        )


@router.post("/slots/availability/add")
async def add_availability(
    request: Request,
    day_of_week: int = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    doctor: Doctor = Depends(require_doctor),
    csrf_valid: bool = Depends(validate_csrf),
    db: Session = Depends(get_db)
):
    """Add new availability slot."""
    try:
        # Parse times
        start = datetime.strptime(start_time, "%H:%M").time()
        end = datetime.strptime(end_time, "%H:%M").time()
        
        # Validate
        if start >= end:
            return RedirectResponse(
                url="/doctor/slots?error=invalid_time_range", 
                status_code=302
            )
        
        # Create availability slot
        slot = DoctorAvailability(
            id=str(uuid.uuid4()),
            doctor_id=str(doctor.id),
            day_of_week=day_of_week,
            start_time=start,
            end_time=end,
            is_active=True
        )
        db.add(slot)
        db.commit()
        
        return RedirectResponse(url="/doctor/slots?success=added", status_code=302)
    
    except Exception as e:
        import traceback
        print(f"❌ Add availability error: {traceback.format_exc()}")
        return RedirectResponse(url="/doctor/slots?error=add_failed", status_code=302)


@router.post("/slots/availability/{slot_id}/delete")
async def delete_availability(
    slot_id: str,
    request: Request,
    doctor: Doctor = Depends(require_doctor),
    csrf_valid: bool = Depends(validate_csrf),
    db: Session = Depends(get_db)
):
    """Delete availability slot."""
    try:
        slot = db.query(DoctorAvailability).filter(
            DoctorAvailability.id == slot_id,
            DoctorAvailability.doctor_id == doctor.id
        ).first()
        
        if not slot:
            return RedirectResponse(url="/doctor/slots?error=not_found", status_code=302)
        
        db.delete(slot)
        db.commit()
        
        return RedirectResponse(url="/doctor/slots?success=deleted", status_code=302)
    
    except Exception as e:
        import traceback
        print(f"❌ Delete availability error: {traceback.format_exc()}")
        return RedirectResponse(url="/doctor/slots?error=delete_failed", status_code=302)


@router.post("/slots/leave/add")
async def add_leave(
    request: Request,
    leave_date: str = Form(...),
    reason: str = Form(""),
    doctor: Doctor = Depends(require_doctor),
    csrf_valid: bool = Depends(validate_csrf),
    db: Session = Depends(get_db)
):
    """Add new leave/holiday."""
    try:
        # Parse date
        leave_dt = datetime.strptime(leave_date, "%Y-%m-%d").date()
        
        # Validate not in past
        if leave_dt < date.today():
            return RedirectResponse(
                url="/doctor/slots?error=past_date", 
                status_code=302
            )
        
        # Create leave entry
        leave = DoctorLeave(
            id=str(uuid.uuid4()),
            doctor_id=str(doctor.id),
            leave_date=leave_dt,
            reason=reason.strip() if reason else None
        )
        db.add(leave)
        db.commit()
        
        return RedirectResponse(url="/doctor/slots?success=leave_added", status_code=302)
    
    except Exception as e:
        import traceback
        print(f"❌ Add leave error: {traceback.format_exc()}")
        return RedirectResponse(url="/doctor/slots?error=leave_failed", status_code=302)


@router.post("/slots/leave/{leave_id}/delete")
async def delete_leave(
    leave_id: str,
    request: Request,
    doctor: Doctor = Depends(require_doctor),
    csrf_valid: bool = Depends(validate_csrf),
    db: Session = Depends(get_db)
):
    """Delete leave entry."""
    try:
        leave = db.query(DoctorLeave).filter(
            DoctorLeave.id == leave_id,
            DoctorLeave.doctor_id == doctor.id
        ).first()
        
        if not leave:
            return RedirectResponse(url="/doctor/slots?error=not_found", status_code=302)
        
        db.delete(leave)
        db.commit()
        
        return RedirectResponse(url="/doctor/slots?success=leave_deleted", status_code=302)
    
    except Exception as e:
        import traceback
        print(f"❌ Delete leave error: {traceback.format_exc()}")
        return RedirectResponse(url="/doctor/slots?error=delete_failed", status_code=302)
