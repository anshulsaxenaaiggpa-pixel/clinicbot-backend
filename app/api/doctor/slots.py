"""
Doctor Slot Management Routes

View and manage appointment slots.
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.api.doctor.dependencies import require_doctor
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.db.session import get_db


router = APIRouter(prefix="/doctor", tags=["doctor-slots"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent.parent / "templates"))


@router.get("/slots", response_class=HTMLResponse)
async def slot_management(
    request: Request,
    doctor: Doctor = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    """Display appointment slots for next 7 days."""
    try:
        today = datetime.now().date()
        slots_data = []
        
        # Generate next 7 days
        for i in range(7):
            day = today + timedelta(days=i)
            day_start = datetime.combine(day, datetime.min.time())
            day_end = datetime.combine(day, datetime.max.time())
            
            # Get appointments for this day
            appointments = db.query(Appointment).filter(
                Appointment.doctor_id == doctor.id,
                Appointment.date >= day_start,
                Appointment.date <= day_end
            ).order_by(Appointment.start_utc_ts).all()
            
            booked_count = sum(1 for a in appointments if a.status == 'booked')
            
            slots_data.append({
                'date': day,
                'day_name': day.strftime('%A'),
                'appointments': appointments,
                'booked_count': booked_count,
                'total_count': len(appointments)
            })
        
        return templates.TemplateResponse(
            "doctor/slots.html",
            {
                "request": request,
                "doctor": doctor,
                "csrf_token": request.state.csrf_token,
                "slots_data": slots_data
            }
        )
    
    except Exception as e:
        import traceback
        print(f"❌ Slots error: {traceback.format_exc()}")
        return HTMLResponse(
            content=f"<h1>Error</h1><pre>{traceback.format_exc()}</pre>",
            status_code=500
        )
