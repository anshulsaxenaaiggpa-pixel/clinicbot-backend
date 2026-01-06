"""
Audit Log Viewer Routes

View and export audit logs with filtering.
"""
from fastapi import APIRouter, Request, Query, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
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
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent.parent / "templates"))


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
    try:
        return await _audit_logs_impl(request, page, event_type, actor_id, days, admin_user, db)
    except Exception as e:
        import traceback
        return HTMLResponse(content=f"<h1>Audit Logs Error</h1><pre>{traceback.format_exc()}</pre>", status_code=500)

async def _audit_logs_impl(
    request: Request,
    page: int,
    event_type: Optional[str],
    actor_id: Optional[str],
    days: int,
    admin_user: AdminUser,
    db: Session
):
    """View audit logs with filters."""
    page_size = 100
    offset = (page - 1) * page_size
    
    # Base query - last N days
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    query = db.query(AuditLog).filter(AuditLog.timestamp >= cutoff_date)
    
    # Apply filters
    if event_type:
        query = query.filter(AuditLog.action == event_type)
    
    if actor_id:
        query = query.filter(AuditLog.actor_reference == actor_id)
    
    # Get total count
    total = query.count()
    
    # Paginate
    logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(page_size).all()
    
    total_pages = (total + page_size - 1) // page_size
    
    # Get unique event types for filter dropdown
    event_types = db.query(AuditLog.action).distinct().order_by(AuditLog.action).all()
    event_types = [et[0] for et in event_types]
    
    return templates.TemplateResponse(
        "tools/audit_logs.html",
        {
            "request": request,
            "admin_user": admin_user,
            "csrf_token": getattr(request.state, 'csrf_token', ''),
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
    query = db.query(AuditLog).filter(AuditLog.timestamp >= cutoff_date)
    
    # Apply filters
    if event_type:
        query = query.filter(AuditLog.action == event_type)
    
    if actor_id:
        query = query.filter(AuditLog.actor_reference == actor_id)
    
    # Get logs (limit to 10,000 for performance)
    logs = query.order_by(AuditLog.timestamp.desc()).limit(10000).all()
    
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
        ip_address = log.ip_address or ""
        if not ip_address and log.new_state and isinstance(log.new_state, dict):
            ip_address = log.new_state.get("ip_address", "")
        
        writer.writerow([
            log.timestamp.isoformat(),
            log.action,
            log.actor_type,
            log.actor_reference,
            str(log.new_state) if log.new_state else "",
            log.ip_address or ""
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
