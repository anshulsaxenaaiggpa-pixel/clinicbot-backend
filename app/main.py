"""FastAPI main application entry point"""
# CRITICAL: Import registry bootstrap FIRST to ensure all models are registered
import app.db.base  # noqa - Must be first to register SQLAlchemy models

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

# Debug: Confirm main.py is loading
print("=" * 60)
print("🚀 MAIN.PY LOADING - ClinicBot.ai API")
print("=" * 60)

app = FastAPI(
    title="ClinicBot.ai API",
    description="WhatsApp-first AI appointment booking system for clinics",
    version="0.1.0",
    debug=settings.DEBUG
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else ["https://clinicbot.ai"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ClinicBot.ai API",
        "version": "0.1.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check with actual connectivity tests"""
    from app.db.database import SessionLocal
    from sqlalchemy import text
    import redis
    
    health_status = {
        "status": "healthy",
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
    """Initialize database with migrations and test clinic data (one-time setup)"""
    import logging
    import importlib.util
    import sys
    from pathlib import Path
    
    logger = logging.getLogger(__name__)
    
    results = {
        "tables": "not_created",
        "seed": "not_run"
    }
    
    try:
        # Step 1: Create all tables using SQLAlchemy
        logger.info("Creating database tables...")
        from app.db.database import engine
        from app.db.base import Base
        
        # This will create all tables defined in the models
        Base.metadata.create_all(bind=engine)
        results["tables"] = "created"
        logger.info("Tables created successfully")
        
        # Step 2: Seed test data
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
                "message": "Database initialized successfully",
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
from app.api.v1 import clinics, doctors, services, appointments, slots, summary, auth, webhooks, patients
from app.api import onboarding

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])
app.include_router(onboarding.router, prefix="/api/v1/onboarding", tags=["onboarding"])
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
