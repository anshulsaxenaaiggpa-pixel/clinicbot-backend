
import asyncio
from app.services.audit_logger import audit_logger
from app.db.session import SessionLocal
from app.models.audit_log import AuditLog

async def test_audit():
    print("Testing audit log...")
    await audit_logger.log_action(
        clinic_id="test-clinic",
        actor_type="PATIENT",
        actor_ref="1234567890",
        action="TEST_ACTION",
        entity_type="TEST",
        new_state={"hello": "world"}
    )
    
    db = SessionLocal()
    log = db.query(AuditLog).filter(AuditLog.action == "TEST_ACTION").first()
    if log:
        print(f"✅ Log found: {log.id}, action: {log.action}, metadata: {log.new_state}")
    else:
        print("❌ Log NOT found")
    db.close()

if __name__ == "__main__":
    asyncio.run(test_audit())
