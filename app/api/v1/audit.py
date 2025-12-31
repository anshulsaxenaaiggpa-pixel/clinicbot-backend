"""
Audit API - MODULE 4

Provides admin-only endpoint for querying audit logs.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.audit_service import AuditService
from app.models.audit_log import AuditLog


router = APIRouter(prefix="/audit", tags=["audit"])


class AuditQueryResponse(BaseModel):
    """Response from audit query."""
    event_id: str
    event_type: str
    actor: str
    actor_id: str
    patient_phone_hash: Optional[str]
    metadata: Optional[dict]
    timestamp: str
    
    class Config:
        orm_mode = True


@router.get("/query", response_model=List[AuditQueryResponse])
def query_audit_logs(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    actor: Optional[str] = Query(None, description="Filter by actor (system/clinic/admin/patient)"),
    patient_phone: Optional[str] = Query(None, description="Filter by patient phone (will be hashed)"),
    start_time: Optional[datetime] = Query(None, description="Start time filter"),
    end_time: Optional[datetime] = Query(None, description="End time filter"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    db: Session = Depends(get_db)
    # TODO: Add admin authentication dependency
):
    """
    Query audit logs (ADMIN ONLY).
    
    Returns filtered audit entries based on criteria.
    
    NOTE: Requires admin authentication (TODO: Add auth dependency)
    """
    results = AuditService.query_events(
        event_type=event_type,
        actor=actor,
        patient_phone=patient_phone,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        db=db
    )
    
    # Convert to response format
    return [
        AuditQueryResponse(
            event_id=log.event_id,
            event_type=log.event_type,
            actor=log.actor,
            actor_id=log.actor_id,
            patient_phone_hash=log.patient_phone_hash,
            metadata=log.metadata,
            timestamp=log.timestamp.isoformat()
        )
        for log in results
    ]


@router.get("/stats")
def get_audit_stats(db: Session = Depends(get_db)):
    """
    Get audit log statistics.
    
    Returns event type counts and recent activity.
    
    NOTE: Requires admin authentication (TODO: Add auth dependency)
    """
    # Get all logs (limit to recent for stats)
    recent_logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(1000).all()
    
    # Count by event type
    event_counts = {}
    for log in recent_logs:
        event_counts[log.event_type] = event_counts.get(log.event_type, 0) + 1
    
    return {
        "total_events": len(recent_logs),
        "event_type_counts": event_counts,
        "oldest_event": recent_logs[-1].timestamp.isoformat() if recent_logs else None,
        "newest_event": recent_logs[0].timestamp.isoformat() if recent_logs else None
    }
