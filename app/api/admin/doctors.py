"""
Doctor Management Routes

CRUD operations for doctor profiles with compliance enforcement.
"""
from fastapi import APIRouter, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
import uuid

from app.api.admin.dependencies import require_admin, validate_csrf, get_client_ip
from app.models.admin_user import AdminUser, AdminRole
from app.models.doctor import Doctor
from app.services.audit_service import AuditService
from app.schemas.validation import E164PhoneValidator
from app.db.session import get_db


router = APIRouter(prefix="/admin/doctors", tags=["admin-doctors"], redirect_slashes=False)
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent.parent / "templates"))


@router.get("", response_class=HTMLResponse)
async def list_doctors(
    request: Request,
    page: int = 1,
    search: Optional[str] = None,
    admin_user: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List all doctors with pagination and search - SIMPLIFIED VERSION."""
    try:
        # Basic doctor query
        query = db.query(Doctor).filter(Doctor.is_active == True)
        
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                (Doctor.name.ilike(search_filter)) |
                (Doctor.specialization.ilike(search_filter))
            )
        
        doctors = query.order_by(Doctor.name).all()
        
        # Generate simple HTML table
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Doctors - CuraSlot Admin</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="p-4">
            <div class="container">
                <h1>👨‍⚕️ Doctors</h1>
                <p>Logged in as: {admin_user.email}</p>
                <p><a href="/admin/dashboard">← Back to Dashboard</a></p>
                
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Specialization</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for doctor in doctors:
            html += f"""
                        <tr>
                            <td>{doctor.name}</td>
                            <td>{doctor.specialization or 'N/A'}</td>
                            <td>{'✅ Active' if doctor.is_active else '❌ Inactive'}</td>
                        </tr>
            """
        
        html += """
                    </tbody>
                </table>
            </div>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html)
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return HTMLResponse(
            content=f"<h1>Error loading doctors</h1><pre>{error_detail}</pre>", 
            status_code=500
        )


@router.get("/new", response_class=HTMLResponse)
async def new_doctor_form(
    request: Request,
    admin_user: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Display new doctor form."""
    # Require ADMIN or SUPERADMIN role
    if not admin_user.has_permission(AdminRole.CLINIC_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires ADMIN role or higher"
        )
    
    return templates.TemplateResponse(
        "doctors/create.html",
        {
            "request": request,
            "admin_user": admin_user,
            "csrf_token": request.state.csrf_token
        }
    )


@router.post("")
async def create_doctor(
    request: Request,
    full_name: str = Form(...),
    specialty: str = Form(...),
    city: str = Form(...),
    whatsapp_number: str = Form(...),
    upi_id: str = Form(...),
    status: str = Form("active"),
    consultation_fee: int = Form(500),
    is_searchable: bool = Form(False),  # Default False (privacy-first)
    admin_user: AdminUser = Depends(require_admin),
    csrf_valid: bool = Depends(validate_csrf),
    db: Session = Depends(get_db)
):
    """Create new doctor with UPI and subscription status."""
    # Require ADMIN or SUPERADMIN role
    if not admin_user.has_permission(AdminRole.CLINIC_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires ADMIN role or higher"
        )
    
    # Validate WhatsApp number (E.164 format)
    if not E164PhoneValidator.validate(whatsapp_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid WhatsApp number. Must be in E.164 format (e.g., +919876543210)"
        )
    
    # Validate UPI ID format
    if not upi_id or '@' not in upi_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid UPI ID. Must be in format: username@provider (e.g., drname@paytm)"
        )
    
    # Validate consultation fee
    if consultation_fee < 0:
        consultation_fee = 500  # Default to ₹500 if invalid
    
    # Validate status
    if status not in ['active', 'trial', 'suspended']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be: active, trial, or suspended"
        )
    
    # Get first clinic (or create a default one if none exists)
    from app.models.clinic import Clinic
    clinic = db.query(Clinic).first()
    if not clinic:
        # Create a default clinic
        clinic = Clinic(
            id=str(uuid.uuid4()),
            name="Default Clinic",
            phone=whatsapp_number,
            is_active=True
        )
        db.add(clinic)
        db.flush()
    
    # Create doctor
    doctor = Doctor(
        id=str(uuid.uuid4()),
        clinic_id=str(clinic.id),
        name=full_name.strip(),
        specialization=specialty.strip(),
        upi_id=upi_id.strip(),
        status=status,
        consultation_fee=consultation_fee,
        is_active=True
    )
    
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    
    # Log creation
    client_ip = get_client_ip(request)
    AuditService.log_event(
        event_type="doctor_created",
        actor="admin",
        actor_id=str(admin_user.id),
        metadata={
            "doctor_id": str(doctor.id),
            "name": doctor.name,
            "specialization": doctor.specialization,
            "upi_id": doctor.upi_id,
            "status": doctor.status,
            "whatsapp_number": whatsapp_number,
            "clinic_id": str(clinic.id),
            "ip_address": client_ip
        },
        db=db
    )
    
    return RedirectResponse(url="/admin/doctors", status_code=302)


@router.get("/{doctor_id}/edit", response_class=HTMLResponse)
async def edit_doctor_form(
    request: Request,
    doctor_id: uuid.UUID,
    admin_user: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Display edit doctor form."""
    # Require ADMIN or SUPERADMIN role
    if not admin_user.has_permission(AdminRole.CLINIC_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires ADMIN role or higher"
        )
    
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    return templates.TemplateResponse(
        "doctors/edit.html",
        {
            "request": request,
            "admin_user": admin_user,
            "csrf_token": request.state.csrf_token,
            "doctor": doctor
        }
    )


@router.post("/{doctor_id}")
async def update_doctor(
    request: Request,
    doctor_id: uuid.UUID,
    full_name: str = Form(...),
    specialty: str = Form(...),
    city: str = Form(...),
    whatsapp_number: str = Form(...),
    admin_user: AdminUser = Depends(require_admin),
    csrf_valid: bool = Depends(validate_csrf),
    db: Session = Depends(get_db)
):
    """Update doctor (does NOT change is_searchable - use toggle route)."""
    # Require ADMIN or SUPERADMIN role
    if not admin_user.has_permission(AdminRole.CLINIC_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires ADMIN role or higher"
        )
    
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    # Validate WhatsApp number
    if not E164PhoneValidator.validate(whatsapp_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid WhatsApp number format"
        )
    
    # Check duplicate (excluding current doctor)
    if whatsapp_number != doctor.whatsapp_number:
        existing = db.query(Doctor).filter(
            Doctor.whatsapp_number == whatsapp_number,
            Doctor.id != doctor_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"WhatsApp number already in use by another doctor"
            )
    
    # Track changes
    changes = {}
    if doctor.name != full_name.strip():
        changes["name"] = {"old": doctor.name, "new": full_name.strip()}
        doctor.name = full_name.strip()
    
    if doctor.specialization != specialty.strip():
        changes["specialization"] = {"old": doctor.specialization, "new": specialty.strip()}
        doctor.specialization = specialty.strip()
    
    if doctor.city != city.strip():
        changes["city"] = {"old": doctor.city, "new": city.strip()}
        doctor.city = city.strip()
    
    if doctor.whatsapp_number != whatsapp_number:
        changes["whatsapp_number"] = {"old": doctor.whatsapp_number, "new": whatsapp_number}
        doctor.whatsapp_number = whatsapp_number
    
    db.commit()
    
    # Log update if changes made
    if changes:
        client_ip = get_client_ip(request)
        AuditService.log_event(
            event_type="doctor_updated",
            actor="admin",
            actor_id=str(admin_user.id),
            metadata={
                "doctor_id": str(doctor.id),
                "changes": changes,
                "ip_address": client_ip
            },
            db=db
        )
    
    return RedirectResponse(url="/admin/doctors", status_code=302)


@router.post("/{doctor_id}/toggle-search")
async def toggle_search_visibility(
    request: Request,
    doctor_id: uuid.UUID,
    admin_user: AdminUser = Depends(require_admin),
    csrf_valid: bool = Depends(validate_csrf),
    db: Session = Depends(get_db)
):
    """Toggle doctor search visibility with audit logging."""
    # Require ADMIN or SUPERADMIN role
    if not admin_user.has_permission(AdminRole.CLINIC_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires ADMIN role or higher"
        )
    
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    # Toggle visibility
    old_status = doctor.is_searchable
    doctor.is_searchable = not old_status
    new_status = doctor.is_searchable
    
    db.commit()
    
    # Log visibility change (REQUIRED for compliance)
    client_ip = get_client_ip(request)
    AuditService.log_event(
        event_type="doctor_searchable_updated",
        actor="admin",
        actor_id=str(admin_user.id),
        metadata={
            "doctor_id": str(doctor.id),
            "doctor_name": doctor.name,
            "old_status": old_status,
            "new_status": new_status,
            "ip_address": client_ip
        },
        db=db
    )
    
    return RedirectResponse(url="/admin/doctors", status_code=302)


@router.post("/{doctor_id}/delete")
async def delete_doctor(
    request: Request,
    doctor_id: uuid.UUID,
    admin_user: AdminUser = Depends(require_admin),
    csrf_valid: bool = Depends(validate_csrf),
    db: Session = Depends(get_db)
):
    """Soft delete doctor (set is_active=False)."""
    # Require SUPERADMIN role only
    if not admin_user.has_permission(AdminRole.SUPER_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires SUPERADMIN role"
        )
    
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    # Soft delete
    doctor.is_active = False
    db.commit()
    
    # Log deletion
    client_ip = get_client_ip(request)
    AuditService.log_event(
        event_type="doctor_deleted",
        actor="admin",
        actor_id=str(admin_user.id),
        metadata={
            "doctor_id": str(doctor.id),
            "doctor_name": doctor.name,
            "ip_address": client_ip
        },
        db=db
    )
    
    return RedirectResponse(url="/admin/doctors", status_code=302)
