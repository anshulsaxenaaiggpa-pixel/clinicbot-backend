"""
City/Specialty Directory API - Public doctor listings
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List

from app.db.session import get_db
from app.models.doctor import Doctor

router = APIRouter(tags=["directory"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/cities", response_class=HTMLResponse)
async def cities_list(request: Request, db: Session = Depends(get_db)):
    """List all available cities"""
    cities = db.query(Doctor.city, func.count(Doctor.id).label('count'))\
        .filter(Doctor.city.isnot(None), Doctor.is_active == True)\
        .group_by(Doctor.city)\
        .order_by(func.count(Doctor.id).desc())\
        .all()
    
    return templates.TemplateResponse("public/cities.html", {
        "request": request,
        "cities": cities
    })


@router.get("/city/{city}", response_class=HTMLResponse)
async def city_directory(
    city: str,
    request: Request,
    db: Session = Depends(get_db),
    specialty: Optional[str] = None,
    page: int = 1
):
    """
    City directory - all doctors in a city
    Optional specialty filter
    """
    query = db.query(Doctor).filter(
        Doctor.city == city.title(),
        Doctor.is_active == True
    )
    
    if specialty:
        query = query.filter(Doctor.specialty_primary == specialty.title())
    
    # Get unique specialties in this city for filter dropdown
    specialties = db.query(Doctor.specialty_primary, func.count(Doctor.id).label('count'))\
        .filter(Doctor.city == city.title(), Doctor.is_active == True, Doctor.specialty_primary.isnot(None))\
        .group_by(Doctor.specialty_primary)\
        .order_by(func.count(Doctor.id).desc())\
        .all()
    
    # Pagination
    per_page = 20
    offset = (page - 1) * per_page
    
    doctors = query.order_by(Doctor.google_rating.desc().nullslast())\
        .limit(per_page).offset(offset).all()
    
    total = query.count()
    total_pages = (total + per_page - 1) // per_page
    
    return templates.TemplateResponse("public/directory.html", {
        "request": request,
        "city": city.title(),
        "specialty": specialty.title() if specialty else None,
        "doctors": doctors,
        "specialties":  specialties,
        "page": page,
        "total_pages": total_pages,
        "total": total
    })


@router.get("/city/{city}/{specialty}", response_class=HTMLResponse)
async def city_specialty_directory(
    city: str,
    specialty: str,
    request: Request,
    db: Session = Depends(get_db),
    page: int = 1
):
    """Specific city + specialty combination"""
    return await city_directory(city, request, db, specialty, page)


@router.get("/api/cities", response_model=List[dict])
async def get_cities_api(db: Session = Depends(get_db)):
    """API endpoint for city dropdown"""
    cities = db.query(Doctor.city, func.count(Doctor.id).label('count'))\
        .filter(Doctor.city.isnot(None), Doctor.is_active == True)\
        .group_by(Doctor.city)\
        .order_by(func.count(Doctor.id).desc())\
        .all()
    
    return [{"city": c[0], "count": c[1]} for c in cities]


@router.get("/api/specialties", response_model=List[dict])
async def get_specialties_api(city: Optional[str] = None, db: Session = Depends(get_db)):
    """API endpoint for specialty dropdown"""
    query = db.query(Doctor.specialty_primary, func.count(Doctor.id).label('count'))\
        .filter(Doctor.specialty_primary.isnot(None), Doctor.is_active == True)
    
    if city:
        query = query.filter(Doctor.city == city.title())
    
    specialties = query.group_by(Doctor.specialty_primary)\
        .order_by(func.count(Doctor.id).desc())\
        .all()
    
    return [{"specialty": s[0], "count": s[1]} for s in specialties]
