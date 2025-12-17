"""Service CRUD endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.database import get_db
from app.models.service import Service
from app.schemas.service import ServiceCreate, ServiceUpdate, ServiceOut

router = APIRouter()


@router.post("/", response_model=ServiceOut, status_code=status.HTTP_201_CREATED)
def create_service(service_data: ServiceCreate, db: Session = Depends(get_db)):
    """Create a new service"""
    # Calculate required slots
    required_slots = (service_data.duration_minutes + 14) // 15
    
    service = Service(
        **service_data.model_dump(exclude={'required_slots'}),
        required_slots=required_slots
    )
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


@router.get("/", response_model=List[ServiceOut])
def list_services(clinic_id: UUID, db: Session = Depends(get_db)):
    """List all services for a clinic"""
    services = db.query(Service).filter(
        Service.clinic_id == clinic_id,
        Service.is_active == True
    ).all()
    return services


@router.get("/{service_id}", response_model=ServiceOut)
def get_service(service_id: UUID, db: Session = Depends(get_db)):
    """Get service by ID"""
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service


@router.patch("/{service_id}", response_model=ServiceOut)
def update_service(service_id: UUID, service_data: ServiceUpdate, db: Session = Depends(get_db)):
    """Update service details"""
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    update_data = service_data.model_dump(exclude_unset=True)
    
    # Recalculate slots if duration changed
    if 'duration_minutes' in update_data:
        update_data['required_slots'] = (update_data['duration_minutes'] + 14) // 15
    
    for field, value in update_data.items():
        setattr(service, field, value)
    
    db.commit()
    db.refresh(service)
    return service


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_service(service_id: UUID, db: Session = Depends(get_db)):
    """Soft delete (deactivate) a service"""
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    service.is_active = False
    db.commit()
    return None
