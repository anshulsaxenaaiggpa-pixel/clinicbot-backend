"""
Doctor Patient Management Routes

View patient list and visit history.
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.doctor.dependencies import require_doctor
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.db.session import get_db


router = APIRouter(prefix="/doctor", tags=["doctor-patients"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent.parent / "templates"))


@router.get("/patients", response_class=HTMLResponse)
async def list_patients(
    request: Request,
    search: str = "",
    doctor: Doctor = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    """List all patients with visit history."""
    try:
        # Get unique patients (by phone) with their latest appointment
        subquery = db.query(
            Appointment.patient_phone,
            func.max(Appointment.patient_name).label('name'),
            func.max(Appointment.date).label('last_visit'),
            func.count(Appointment.id).label('total_visits')
        ).filter(
            Appointment.doctor_id == doctor.id
        ).group_by(Appointment.patient_phone)
        
        if search:
            search_filter = f"%{search}%"
            subquery = subquery.filter(
                (Appointment.patient_name.ilike(search_filter)) |
                (Appointment.patient_phone.ilike(search_filter))
            )
        
        patients = subquery.all()
        
        return templates.TemplateResponse(
            "doctor/patients.html",
            {
                "request": request,
                "doctor": doctor,
                "csrf_token": request.state.csrf_token,
                "patients": patients,
                "search": search
            }
        )
    
    except Exception as e:
        import traceback
        print(f"❌ Patients error: {traceback.format_exc()}")
        return HTMLResponse(
            content=f"<h1>Error</h1><pre>{traceback.format_exc()}</pre>",
            status_code=500
        )
