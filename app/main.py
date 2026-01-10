"""FastAPI main application entry point - CuraSlot Admin API"""
# CRITICAL: Import registry bootstrap FIRST to ensure all models are registered
import app.db.base  # noqa - Must be first to register SQLAlchemy models

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import traceback
import logging
import sys
from datetime import datetime
from app.config import settings

# Configure logging to flush immediately
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s',
    stream=sys.stdout,
    force=True
)
logger = logging.getLogger(__name__)

# Force stdout to be unbuffered
sys.stdout.reconfigure(line_buffering=True)

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
    - Missing database URLs
    - HTTPS not enforced in production
    
    This prevents insecure deployment while providing detailed error info.
    """
    print("\n" + "=" * 80)
    print("🔒 RUNNING STARTUP SECURITY VALIDATION - CuraSlot Admin")
    print("=" * 80)
    
    try:
        startup_validator.validate_or_exit()
        print("=" * 80)
        print("✅ SECURITY VALIDATION PASSED - Application starting")
        print("=" * 80 + "\n")
    except SystemExit as e:
        # Validator failed with exit code - re-raise to stop startup
        print("=" * 80)
        print("🛑 STARTUP ABORTED DUE TO VALIDATION FAILURE")
        print("=" * 80 + "\n")
        raise
    except Exception as e:
        # Unexpected error in validator itself
        print("=" * 80)
        print(f"⚠️ VALIDATION ERROR (non-fatal): {e}")
        print("Continuing startup - please review configuration")
        print("=" * 80 + "\n")
        import traceback
        traceback.print_exc()
    
    # ===== ENSURE DOCTOR COLUMNS EXIST (PostgreSQL compatible) =====
    print("🔧 Ensuring doctor table has required columns...")
    try:
        from app.db.database import engine
        from sqlalchemy import text
        
        # Helper function to check if column exists
        def column_exists(conn, table_name, column_name):
            """Check if a column exists in PostgreSQL or SQLite"""
            try:
                # Try PostgreSQL information_schema first
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name=:table AND column_name=:column
                """), {"table": table_name, "column": column_name})
                return result.fetchone() is not None
            except:
                # Fallback for SQLite - try to query the column
                try:
                    conn.execute(text(f"SELECT {column_name} FROM {table_name} LIMIT 1"))
                    return True
                except:
                    return False
        
        with engine.connect() as conn:
            # Add upi_id if missing
            if not column_exists(conn, 'doctors', 'upi_id'):
                try:
                    conn.execute(text("ALTER TABLE doctors ADD COLUMN upi_id VARCHAR(100)"))
                    conn.commit()
                    print("✅ Added upi_id column")
                except Exception as e:
                    print(f"⚠️ upi_id column error: {e}")
            else:
                print("✅ upi_id column exists")
            
            # Add status if missing
            if not column_exists(conn, 'doctors', 'status'):
                try:
                    conn.execute(text("ALTER TABLE doctors ADD COLUMN status VARCHAR(20) DEFAULT 'active'"))
                    conn.commit()
                    print("✅ Added status column")
                except Exception as e:
                    print(f"⚠️ status column error: {e}")
            else:
                print("✅ status column exists")
            
            # Add consultation_fee if missing
            if not column_exists(conn, 'doctors', 'consultation_fee'):
                try:
                    conn.execute(text("ALTER TABLE doctors ADD COLUMN consultation_fee INTEGER DEFAULT 500"))
                    conn.commit()
                    print("✅ Added consultation_fee column")
                except Exception as e:
                    print(f"⚠️ consultation_fee column error: {e}")
            else:
                print("✅ consultation_fee column exists")
            
            # Add city if missing
            if not column_exists(conn, 'doctors', 'city'):
                try:
                    conn.execute(text("ALTER TABLE doctors ADD COLUMN city VARCHAR(100)"))
                    conn.commit()
                    print("✅ Added city column")
                except Exception as e:
                    print(f"⚠️ city column error: {e}")
            else:
                print("✅ city column exists")
            
            # Add is_searchable if missing
            if not column_exists(conn, 'doctors', 'is_searchable'):
                try:
                    conn.execute(text("ALTER TABLE doctors ADD COLUMN is_searchable BOOLEAN DEFAULT FALSE"))
                    conn.commit()
                    print("✅ Added is_searchable column")
                except Exception as e:
                    print(f"⚠️ is_searchable column error: {e}")
            else:
                print("✅ is_searchable column exists")
                
        print("✅ Doctor columns verified\n")
    except Exception as e:
        import traceback
        print(f"⚠️ Could not verify doctor columns: {e}")
        print(f"Traceback: {traceback.format_exc()}\n")
    # ===== END COLUMN CHECK =====
    
    # ===== AUTO-RUN ALEMBIC MIGRATIONS =====
    print("🔄 RUNNING DATABASE MIGRATIONS")
    print("=" * 80)
    try:
        from alembic.config import Config
        from alembic import command
        
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        print("=" * 80)
        print("✅ Database migrations completed successfully")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print(traceback.format_exc())
        print("⚠️ App continuing without migrations - some features may not work")
    print("=" * 80 + "\n")
    # ===== END AUTO-MIGRATION =====
    
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

# Session Middleware (Required for Admin UI - Railway proxy setup)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET_KEY,
    max_age=1800,  # 30 minutes
    same_site="lax",  # Allow navigation between routes (not "strict")
    https_only=False  # Railway proxy terminates HTTPS → HTTP to app
)

# GLOBAL EXCEPTION HANDLERS
from fastapi.exceptions import HTTPException as StarletteHTTPException
from starlette.exceptions import HTTPException as StarletteHTTPExceptionBase

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch ALL unhandled exceptions and log them"""
    error_trace = traceback.format_exc()
    
    # Force immediate log output
    logger.error("=" * 80)
    logger.error("🔥 UNHANDLED EXCEPTION")
    logger.error("=" * 80)
    logger.error(f"Path: {request.url.path}")
    logger.error(f"Method: {request.method}")
    logger.error(f"Error Type: {type(exc).__name__}")
    logger.error(f"Error: {str(exc)}")
    logger.error("\nFull Traceback:")
    logger.error(error_trace)
    logger.error("=" * 80)
    sys.stdout.flush()
    
    # Return detailed error to browser
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "type": type(exc).__name__,
            "detail": str(exc),
            "path": request.url.path,
            "traceback": error_trace.split("\n")
        }
    )


@app.get("/startup")
async def startup_check():
    """Lightweight startup check for Railway - returns immediately"""
    return {
        "status": "starting",
        "message": "Application is responding",
        "timestamp": datetime.utcnow().isoformat()
    }


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


# GLOBAL EXCEPTION HANDLERS
from fastapi.exceptions import HTTPException as StarletteHTTPException
from starlette.exceptions import HTTPException as StarletteHTTPExceptionBase

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch ALL unhandled exceptions and log them"""
    error_trace = traceback.format_exc()
    
    # Force immediate log output
    logger.error("=" * 80)
    logger.error("🔥 UNHANDLED EXCEPTION")
    logger.error("=" * 80)
    logger.error(f"Path: {request.url.path}")
    logger.error(f"Method: {request.method}")
    logger.error(f"Error Type: {type(exc).__name__}")
    logger.error(f"Error: {str(exc)}")
    logger.error("\nFull Traceback:")
    logger.error(error_trace)
    logger.error("=" * 80)
    sys.stdout.flush()
    
    # Return detailed error to browser
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "type": type(exc).__name__,
            "detail": str(exc),
            "path": request.url.path,
            "traceback": error_trace.split("\n")
        }
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions (401, 403, 404, etc.)"""
    logger.info(f"HTTP {exc.status_code}: {request.url.path} - {exc.detail}")
    
    if exc.status_code == 401:
        # Check if request expects HTML (browser)
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            # Redirect to appropriate login based on request path
            from fastapi.responses import RedirectResponse
            
            # Check if this is a doctor route
            if request.url.path.startswith("/doctor"):
                return RedirectResponse(url="/doctor/login", status_code=302)
            else:
                return RedirectResponse(url="/admin/login", status_code=302)
    
    # For API requests or other status codes, return JSON response
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

# Mount static files for logo and assets
from pathlib import Path
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


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
    from app.api.admin import (
        auth as admin_auth,
        doctors as admin_doctors,
        tools as admin_tools,
        audit as admin_audit,
        payments as admin_payments,
        payments_page as admin_payments_page,
        test as admin_test,  # NEW: Test route
        seed_doctor as admin_seed_doctor  # NEW: Seed doctor endpoint
    )
    admin_loaded = True
except Exception as e:
    print(f"❌ Admin UI Import Failed: {e}")
    import traceback
    traceback.print_exc()
    admin_loaded = False
    admin_import_error = str(e)

# Doctor Dashboard Routes - Core modules
doctor_import_error = None
doctor_loaded = False
doctor_feedback = None
doctor_analytics = None

try:
    from app.api.doctor import (
        auth as doctor_auth,
        dashboard as doctor_dashboard,
        appointments as doctor_appointments,
        revenue as doctor_revenue,
        slots as doctor_slots,
        patients as doctor_patients,
        settings as doctor_settings,
        messages as doctor_messages,
        qr as doctor_qr
    )
    doctor_loaded = True
    print("✅ Doctor dashboard core routes imported successfully")
except Exception as e:
    print(f"❌ Doctor UI Import Failed: {e}")
    import traceback
    traceback.print_exc()
    doctor_loaded = False
    doctor_import_error = str(e)

# Optional: Load feedback and analytics modules (don't fail if these don't load)
if doctor_loaded:
    try:
        from app.api.doctor import feedback as doctor_feedback
        print("✅ Doctor feedback module imported")
    except Exception as e:
        print(f"⚠️ Doctor feedback module not available: {e}")
        doctor_feedback = None
    
    try:
        from app.api.doctor import analytics as doctor_analytics
        print("✅ Doctor analytics module imported")
    except Exception as e:
        print(f"⚠️ Doctor analytics module not available: {e}")
        doctor_analytics = None



# Admin UI routes (requires SESSION_SECRET_KEY and ADMIN_UI_ENABLED=True)
if settings.ADMIN_UI_ENABLED:
    print(f"🔧 ADMIN_UI_ENABLED=True, admin_loaded={admin_loaded}")
    if admin_loaded:
        try:
            print("📝 Registering admin routers...")
            print(f"  - admin_auth routes: {[r.path for r in admin_auth.router.routes]}")
            app.include_router(admin_auth.router, tags=["admin-auth"])
            print("  ✅ admin_auth registered")
            
            print(f"  - admin_doctors routes: {[r.path for r in admin_doctors.router.routes]}")
            app.include_router(admin_doctors.router, tags=["admin-doctors"])
            print("  ✅ admin_doctors registered")
            
            app.include_router(admin_tools.router, tags=["admin-tools"])
            print("  ✅ admin_tools registered")
            
            app.include_router(admin_audit.router, tags=["admin-audit"])
            print("  ✅ admin_audit registered")
            
            app.include_router(admin_payments.router, tags=["admin-payments"])
            print("  ✅ admin_payments registered")
            
            app.include_router(admin_payments_page.router, tags=["admin-payments-page"])
            print("  ✅ admin_payments_page registered")
            
            app.include_router(admin_test.router, tags=["admin-test"])  # NEW
            print("  ✅ admin_test registered")
            
            app.include_router(admin_seed_doctor.router, tags=["admin-seed"])  # NEW
            print("  ✅ admin_seed_doctor registered")
            
            # Admin doctor approval routes
            try:
                from app.api.admin import approve_doctor as admin_approve
                app.include_router(admin_approve.router)
                print("  ✅ admin_approve_doctor registered")
            except Exception as e:
                print(f"  ⚠️ admin_approve_doctor not available: {e}")
            
            print("✅ All admin routers registered successfully!")
        except Exception as router_error: # Fallback for Router Registration Errors
            print(f"⚠️ Admin UI router registration failed: {router_error} - activating fallback debugger")
            import traceback
            traceback.print_exc()
            admin_loaded = False # Mark as not loaded due to registration error
            admin_import_error = str(router_error) # Store the error
    
    if not admin_loaded: # This block now handles both import and registration errors
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

# Register Doctor Dashboard Routes
if doctor_loaded:
    try:
        print("📝 Registering doctor routes...")
        app.include_router(doctor_auth.router, tags=["doctor-auth"])
        app.include_router(doctor_dashboard.router, tags=["doctor-dashboard"])
        app.include_router(doctor_appointments.router, tags=["doctor-appointments"])
        app.include_router(doctor_revenue.router, tags=["doctor-revenue"])
        app.include_router(doctor_slots.router, tags=["doctor-slots"])
        app.include_router(doctor_patients.router, tags=["doctor-patients"])
        app.include_router(doctor_settings.router, tags=["doctor-settings"])
        app.include_router(doctor_messages.router, tags=["doctor-messages"])
        app.include_router(doctor_qr.router, tags=["doctor-qr"])
        
        # Optional modules
        if doctor_feedback is not None:
            app.include_router(doctor_feedback.router, tags=["doctor-feedback"])
            print("  ✅ Feedback routes registered")
        else:
            print("  ⚠️ Feedback routes skipped (module not loaded)")
            
        if doctor_analytics is not None:
            app.include_router(doctor_analytics.router, tags=["doctor-analytics"])
            print("  ✅ Analytics routes registered")
        else:
            print("  ⚠️ Analytics routes skipped (module not loaded)")
            
        print("✅ All available doctor routes registered successfully!")
    except Exception as e:
        print(f"⚠️ Doctor route registration failed: {e}")
        import traceback
        traceback.print_exc()

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

# Public landing pages
try:
    from app.api.public import landing as public_landing
    app.include_router(public_landing.router)
    print("✅ Public landing pages registered")
except Exception as e:
    print(f"⚠️ Public landing pages not available: {e}")

# Public directory (city/specialty)
try:
    from app.api.public import directory as public_directory
    app.include_router(public_directory.router)
    print("✅ Public directory registered")
except Exception as e:
    print(f"⚠️ Public directory not available: {e}")


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
