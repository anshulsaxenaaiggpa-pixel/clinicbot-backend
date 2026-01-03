"""FastAPI main application entry point - CuraSlot Admin API"""
# CRITICAL: Import registry bootstrap FIRST to ensure all models are registered
import app.db.base  # noqa - Must be first to register SQLAlchemy models

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import traceback
from app.config import settings

# MANDATORY: Import startup validator for security checks
from app.startup_validator import startup_validator

# Debug: Confirm main.py is loading
print("=" * 60)
print("🚀 MAIN.PY LOADING - CuraSlot Admin API")
print("=" * 60)

app = FastAPI(
    title="CuraSlot Admin API",
    description="WhatsApp-first AI appointment booking system for clinics",
    version="1.0.0",
    debug=settings.DEBUG
)

# STARTUP SECURITY VALIDATION - Fail-fast on insecure config
@app.on_event("startup")
async def run_config_validation():
    """
    Run security validation on application startup.
    
    Application will exit immediately if critical security issues detected:
    - DEBUG=True in production
    - Weak session secrets (< 32 chars)
    - Missing database/Redis URLs
    - HTTPS not enforced in production
    
    This prevents insecure deployment - CANNOT BE BYPASSED.
    """
    print("\n" + "=" * 80)
    print("🔒 RUNNING STARTUP SECURITY VALIDATION - CuraSlot Admin")
    print("=" * 80)
    startup_validator.validate_or_exit()
    print("=" * 80)
    print("✅ SECURITY VALIDATION PASSED - Application starting")
    print("=" * 80 + "\n")
    
    # ENSURE CONSENT_LOG TABLE EXISTS (critical for WhatsApp flow)
    print("🗄️ Ensuring consent_log table exists...")
    try:
        from app.db.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS consent_log (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    phone VARCHAR(15) NOT NULL,
                    clinic_id UUID NOT NULL,
                    consent_given BOOLEAN NOT NULL,
                    consent_source VARCHAR(20) NOT NULL,
                    consent_version VARCHAR(20) NOT NULL,
                    consent_text TEXT NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    ip_address VARCHAR(50)
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_consent_log_phone ON consent_log (phone)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_consent_clinic_phone ON consent_log (clinic_id, phone)"))
            
            # ENSURE AUDIT_LOG TABLE EXISTS (critical for compliance)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    event_id VARCHAR(100) NOT NULL,
                    event_type VARCHAR(50) NOT NULL,
                    actor VARCHAR(50) NOT NULL,
                    actor_id VARCHAR(100),
                    patient_phone_hash VARCHAR(100),
                    event_metadata TEXT,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_audit_log_event_type ON audit_log (event_type)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_audit_log_timestamp ON audit_log (timestamp)"))
            
            conn.commit()
        print("✅ consent_log and audit_log tables ready!")
    except Exception as e:
        print(f"⚠️ Table creation warning: {e}")


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session Middleware (Required for Admin UI flash messages)
app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET_KEY)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "CuraSlot Admin API",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check with actual connectivity tests"""
    from app.db.database import SessionLocal
    from sqlalchemy import text
    import redis
    
    health_status = {
        "status": "healthy",
        "service": "CuraSlot",
        "environment": settings.ENVIRONMENT,
        "database": "unknown",
        "redis": "unknown"
    }
    
    # Check database
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Redis
    try:
        if settings.REDIS_URL and settings.REDIS_URL.strip():
            redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            redis_client.ping()
            health_status["redis"] = "connected"
        else:
            health_status["redis"] = "not configured"
    except Exception as e:
        health_status["redis"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status


@app.post("/init-db")
async def initialize_database():
    """Initialize database by dropping and recreating all tables with seed data"""
    import logging
    import importlib.util
    import sys
    from pathlib import Path
    
    logger = logging.getLogger(__name__)
    
    results = {
        "tables_dropped": "not_dropped",
        "tables_created": "not_created",
        "seed": "not_run"
    }
    
    try:
        from app.db.database import engine
        from app.db.base import Base
        
        # Step 1: Drop all existing tables (ensures schema changes are applied)
        logger.info("Dropping all existing tables...")
        Base.metadata.drop_all(bind=engine)
        results["tables_dropped"] = "success"
        logger.info("All tables dropped successfully")
        
        # Step 2: Create all tables with updated schema
        logger.info("Creating database tables with updated schema...")
        Base.metadata.create_all(bind=engine)
        results["tables_created"] = "success"
        logger.info("Tables created successfully")
        
        # Step 3: Seed test data
        logger.info("Seeding test clinic data...")
        seed_file = Path(__file__).parent.parent / "seed_test_data.py"
        spec = importlib.util.spec_from_file_location("seed_test_data", seed_file)
        seed_module = importlib.util.module_from_spec(spec)
        sys.modules["seed_test_data"] = seed_module
        spec.loader.exec_module(seed_module)
        
        # Run seed function
        from app.db.database import SessionLocal
        db = SessionLocal()
        try:
            seed_result = seed_module.seed_test_clinic(db, whatsapp_number="+14155238886")
            results["seed"] = seed_result
            logger.info("Seeding completed successfully")
            
            return {
                "status": "success",
                "message": "Database reinitialized successfully (all tables dropped and recreated)",
                "details": results
            }
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        import traceback
        return {
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc(),
            "details": results
        }


# Include API routers
from app.api.v1 import clinics, doctors, services, appointments, slots, summary, auth, webhooks, patients, debug, legal, doctor_registration
from app.api import onboarding
# Defensive Admin UI Loading
admin_import_error = None
admin_loaded = False
try:
    from app.api.admin import doctors as admin_doctors, tools as admin_tools, audit as admin_audit, auth as admin_auth
    admin_loaded = True
except Exception as e:
    print(f"❌ Admin UI Import Failed: {e}")
    traceback.print_exc()
    admin_import_error = str(e)

# Admin UI routes (requires SESSION_SECRET_KEY and ADMIN_UI_ENABLED=True)
if settings.ADMIN_UI_ENABLED:
    if admin_loaded:
        app.include_router(admin_auth.router, tags=["admin-auth"])
        app.include_router(admin_doctors.router, tags=["admin-doctors"])
        app.include_router(admin_tools.router, tags=["admin-tools"])
        app.include_router(admin_audit.router, tags=["admin-audit"])
    else:
        # Fallback for Import Errors - Prevents startup crash
        print("⚠️ Admin UI disabled due to import error - activating fallback debugger")
        templates = Jinja2Templates(directory="app/templates")
        
        @app.get("/admin/{path:path}")
        async def admin_fallback(request: Request, path: str):
            error_html = f"""
            <html>
                <body style="font-family: sans-serif; padding: 2rem;">
                    <h1 style="color: red;">⚠️ Admin UI Error</h1>
                    <p>The admin dashboard could not be loaded due to a server configuration issue.</p>
                    <div style="background: #eee; padding: 1rem; border-radius: 5px; overflow: auto; margin: 1rem 0;">
                        <strong>Backend Error:</strong>
                        <pre>{admin_import_error}</pre>
                    </div>
                    <p>Please contact support or check server logs.</p>
                    <a href="/">Return to Home</a>
                </body>
            </html>
            """
            return HTMLResponse(content=error_html, status_code=500)

app.include_router(doctor_registration.router, prefix="/api/v1/registration", tags=["registration"])

app.include_router(debug.router, prefix="/api/v1/debug", tags=["debug"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=[" auth"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])
app.include_router(onboarding.router, prefix="/api/v1/onboarding", tags=["onboarding"])
app.include_router(legal.router, prefix="/legal", tags=["legal"])  # Public legal endpoints
app.include_router(clinics.router, prefix="/api/v1/clinics", tags=["clinics"])
app.include_router(doctors.router, prefix="/api/v1/doctors", tags=["doctors"])
app.include_router(services.router, prefix="/api/v1/services", tags=["services"])
app.include_router(patients.router, prefix="/api/v1/patients", tags=["patients"])
app.include_router(appointments.router, prefix="/api/v1/appointments", tags=["appointments"])
app.include_router(slots.router, prefix="/api/v1/slots", tags=["slots"])
app.include_router(summary.router, prefix="/api/v1/summary", tags=["summary"])

# Debug: List all registered routes
print("\n" + "=" * 60)
print("✅ All routers registered successfully")
print("=" * 60)
print("📋 Available routes:")
for route in app.routes:
    if hasattr(route, 'path'):
        methods = getattr(route, 'methods', ['*'])
        print(f"  {', '.join(methods):8} {route.path}")
print("=" * 60)
print(f"🌐 Total routes: {len(app.routes)}")
print("=" * 60 + "\n")
