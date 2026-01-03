"""
Data Retention Policy Implementation

Implements automatic data cleanup per legal retention requirements:
- Booking metadata: 180 days from appointment date
- Audit logs: 12 months from creation
- Doctor profiles: Until account deletion

Per Privacy Policy and DPDP Act 2023 compliance.
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.appointment import Appointment
from app.models.conversation_state import ConversationState
from app.models.audit_log import AuditLog
from app.services.audit_service import AuditService


class RetentionPolicy:
    """
    Data retention policy enforcement.
    
    Run as scheduled job (daily cron).
    """
    
    # Retention periods (days)
    BOOKING_METADATA_DAYS = 180
    AUDIT_LOG_DAYS = 365  # 12 months
    CONVERSATION_STATE_HOURS = 24
    
    @staticmethod
    def cleanup_expired_data(db: Session, dry_run: bool = False) -> dict:
        """
        Execute retention policy cleanup.
        
        Args:
            db: Database session
            dry_run: If True, only count records without deleting
        
        Returns:
            dict: Summary of deletions
        """
        summary = {
            "appointments_deleted": 0,
            "conversations_deleted": 0,
            "audit_logs_deleted": 0,
            "execution_time": datetime.utcnow().isoformat(),
            "dry_run": dry_run
        }
        
        # 1. Delete old appointment metadata (180 days)
        cutoff_appointment = datetime.utcnow() - timedelta(days=RetentionPolicy.BOOKING_METADATA_DAYS)
        
        appointments_to_delete = db.query(Appointment).filter(
            Appointment.start_time < cutoff_appointment
        )
        
        count_appointments = appointments_to_delete.count()
        
        if not dry_run and count_appointments > 0:
            appointments_to_delete.delete(synchronize_session=False)
            db.commit()
        
        summary["appointments_deleted"] = count_appointments
        
        # 2. Delete expired conversation states (24 hours)
        # Already handled by StateManager, but explicit cleanup
        cutoff_conversation = datetime.utcnow()
        
        conversations_to_delete = db.query(ConversationState).filter(
            ConversationState.expires_at < cutoff_conversation
        )
        
        count_conversations = conversations_to_delete.count()
        
        if not dry_run and count_conversations > 0:
            conversations_to_delete.delete(synchronize_session=False)
            db.commit()
        
        summary["conversations_deleted"] = count_conversations
        
        # 3. Audit logs - CAREFUL: Some must be retained for legal compliance
        # Only delete non-critical audit logs after 365 days
        cutoff_audit = datetime.utcnow() - timedelta(days=RetentionPolicy.AUDIT_LOG_DAYS)
        
        # Define which event types can be deleted
        deletable_event_types = [
            "whatsapp_message_sent",
            "doctor_search",
            "search_rate_limited"
        ]
        
        audit_logs_to_delete = db.query(AuditLog).filter(
            and_(
                AuditLog.timestamp < cutoff_audit,
                AuditLog.action.in_(deletable_event_types)
            )
        )
        
        count_audit = audit_logs_to_delete.count()
        
        if not dry_run and count_audit > 0:
            audit_logs_to_delete.delete(synchronize_session=False)
            db.commit()
        
        summary["audit_logs_deleted"] = count_audit
        
        # Log retention execution
        if not dry_run:
            AuditService.log_event(
                event_type="retention_policy_executed",
                actor="system",
                actor_id="retention_job",
                metadata=summary,
                db=db
            )
        
        return summary
    
    @staticmethod
    def get_retention_status(db: Session) -> dict:
        """
        Get current retention status (how much data is eligible for cleanup).
        
        Returns:
            dict: Counts of data eligible for deletion
        """
        cutoff_appointment = datetime.utcnow() - timedelta(days=RetentionPolicy.BOOKING_METADATA_DAYS)
        cutoff_conversation = datetime.utcnow()
        cutoff_audit = datetime.utcnow() - timedelta(days=RetentionPolicy.AUDIT_LOG_DAYS)
        
        status = {
            "appointments_eligible": db.query(Appointment).filter(
                Appointment.start_time < cutoff_appointment
            ).count(),
            "conversations_eligible": db.query(ConversationState).filter(
                ConversationState.expires_at < cutoff_conversation
            ).count(),
            "audit_logs_eligible": db.query(AuditLog).filter(
                AuditLog.timestamp < cutoff_audit
            ).count(),
            "cutoff_dates": {
                "appointments": cutoff_appointment.isoformat(),
                "conversations": cutoff_conversation.isoformat(),
                "audit_logs": cutoff_audit.isoformat()
            }
        }
        
        return status


# =============================================================================
# Scheduled Job Example (for cron or Celery)
# =============================================================================

def scheduled_retention_cleanup():
    """
    Cron job entry point.
    
    Add to crontab:
    0 2 * * * cd /path/to/app && python -c "from app.utils.retention_policy import scheduled_retention_cleanup; scheduled_retention_cleanup()"
    
    Or Celery beat:
    @celery.task
    def retention_cleanup_task():
        from app.db.session import SessionLocal
        db = SessionLocal()
        try:
            result = RetentionPolicy.cleanup_expired_data(db, dry_run=False)
            print(f"Retention cleanup complete: {result}")
        finally:
            db.close()
    """
    from app.db.session import SessionLocal
    
    db = SessionLocal()
    try:
        # Execute cleanup
        result = RetentionPolicy.cleanup_expired_data(db, dry_run=False)
        
        print(f"[{datetime.utcnow().isoformat()}] Retention Policy Executed")
        print(f"  Appointments deleted: {result['appointments_deleted']}")
        print(f"  Conversations deleted: {result['conversations_deleted']}")
        print(f"  Audit logs deleted: {result['audit_logs_deleted']}")
        
        return result
    finally:
        db.close()


if __name__ == "__main__":
    """
    Manual execution for testing.
    
    Usage:
        python app/utils/retention_policy.py --dry-run
        python app/utils/retention_policy.py --execute
    """
    import sys
    from app.db.session import SessionLocal
    
    dry_run = "--dry-run" in sys.argv or len(sys.argv) == 1
    
    db = SessionLocal()
    try:
        if dry_run:
            print("DRY RUN MODE - No data will be deleted\n")
            status = RetentionPolicy.get_retention_status(db)
            print("Eligible for deletion:")
            print(f"  Appointments: {status['appointments_eligible']}")
            print(f"  Conversations: {status['conversations_eligible']}")
            print(f"  Audit Logs: {status['audit_logs_eligible']}")
            print(f"\nCutoff dates:")
            for key, val in status['cutoff_dates'].items():
                print(f"  {key}: {val}")
        else:
            print("EXECUTING RETENTION POLICY\n")
            result = RetentionPolicy.cleanup_expired_data(db, dry_run=False)
            print("Cleanup complete:")
            print(f"  Appointments deleted: {result['appointments_deleted']}")
            print(f"  Conversations deleted: {result['conversations_deleted']}")
            print(f"  Audit logs deleted: {result['audit_logs_deleted']}")
    finally:
        db.close()
