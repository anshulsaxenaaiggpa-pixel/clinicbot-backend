from app.models.audit_log import AuditLog
from app.db.session import SessionLocal
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

from sqlalchemy.exc import SQLAlchemyError

class AuditLogger:
    @staticmethod
    async def log_action(clinic_id: str, actor_type: str, actor_ref: str,
                        action: str, entity_type: str, entity_id: str = None,
                        old_state: dict = None, new_state: dict = None,
                        ip_address: str = None):
        db = SessionLocal()
        try:
            audit = AuditLog(
                clinic_id=clinic_id, 
                actor_type=actor_type,
                actor_reference=actor_ref, 
                action=action,
                entity_type=entity_type, 
                entity_id=entity_id,
                old_state=old_state, 
                new_state=new_state,
                ip_address=ip_address
            )
            db.add(audit)
            db.commit()
            return str(audit.id)
        except SQLAlchemyError:
            db.rollback()
            raise
        finally:
            db.close()

audit_logger = AuditLogger()
