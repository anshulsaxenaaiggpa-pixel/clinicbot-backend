"""
Audit Log Viewer Routes

View and export audit logs with filtering.
"""
from fastapi import APIRouter, Request, Query, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import csv
import io

from app.api.admin.dependencies import require_admin
from app.models.admin_user import AdminUser
from app.models.audit_log import AuditLog
from app.db.session import get_db


router = APIRouter(prefix="/admin/audit", tags=["admin-audit"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def audit_logs_page(
    request: Request,
    page: int = Query(1, ge=1),
    event_type: Optional[str] = Query(None),
    actor_id: Optional[str] = Query(None),
    days: int = Query(7, ge=1, le=90),  # Last 7 days by default
    admin_user: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """View audit logs with filters."""
    page_size = 100
    offset = (page - 1) * page_size
    
    # Base query - last N days
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    query = db.query(AuditLog).filter(AuditLog.created_at >= cutoff_date)
    
    # Apply filters
    if event_type:
        query = query.filter(AuditLog.event_type == event_type)
    
    if actor_id:
        query = query.filter(AuditLog.actor_id == actor_id)
    
    # Get total count
    total = query.count()
    
    # Paginate
    logs = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size).all()
    
    total_pages = (total + page_size - 1) // page_size
    
    # Get unique event types for filter dropdown
    event_types = db.query(AuditLog.event_type).distinct().order_by(AuditLog.event_type).all()
    event_types = [et[0] for et in event_types]
    
    return templates.TemplateResponse(
        "tools/audit_logs.html",
        {
            "request": request,
            "admin_user": admin_user,
            "csrf_token": request.state.csrf_token,
            "logs": logs,
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "event_type": event_type or "",
            "actor_id": actor_id or "",
            "days": days,
            "event_types": event_types
        }
    )


@router.get("/export")
async def export_audit_logs_csv(
    event_type: Optional[str] = Query(None),
    actor_id: Optional[str] = Query(None),
    days: int = Query(7, ge=1, le=90),
    admin_user: AdminUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Export filtered audit logs as CSV."""
    # Base query
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    query = db.query(AuditLog).filter(AuditLog.created_at >= cutoff_date)
    
    # Apply filters
    if event_type:
        query = query.filter(AuditLog.event_type == event_type)
    
    if actor_id:
        query = query.filter(AuditLog.actor_id == actor_id)
    
    # Get logs (limit to 10,000 for performance)
    logs = query.order_by(AuditLog.created_at.desc()).limit(10000).all()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow([
        "Timestamp",
        "Event Type",
        "Actor Type",
        "Actor ID",
        "Metadata",
        "IP Address"
    ])
    
    # Write rows
    for log in logs:
        # Extract IP address from metadata if present
        ip_address = ""
        if log.metadata and isinstance(log.metadata, dict):
            ip_address = log.metadata.get("ip_address", "")
        
        writer.writerow([
            log.created_at.isoformat(),
            log.event_type,
            log.actor,
            log.actor_id,
            str(log.metadata) if log.metadata else "",
            ip_address
        ])
    
    # Prepare response
    output.seek(0)
    filename = f"audit_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
