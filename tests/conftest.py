"""
Pytest configuration and shared fixtures for test suite.

Provides database session fixtures and test utilities.
"""
import pytest
import uuid
from sqlalchemy import create_engine, TypeDecorator, String, event
from sqlalchemy.orm import sessionmaker, Session


# UUID type handler for SQLite compatibility
class UUID(TypeDecorator):
    """
    Platform-independent UUID type.
    
    Uses PostgreSQL's UUID type when available, otherwise uses
    CHAR(36) storing as stringified hex values.
    """
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif isinstance(value, uuid.UUID):
            return str(value)
        else:
            return str(uuid.UUID(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                value = uuid.UUID(value)
            return value


# Configure pytest-asyncio and UUID/JSONB monkey-patch BEFORE any imports
def pytest_configure(config):
    """Configure pytest with custom markers, asyncio mode, and PostgreSQL type compatibility."""
    # Monkey-patch PostgreSQL-specific types to use SQLite-compatible types
    # This MUST happen before any models are imported
    import sqlalchemy.dialects.postgresql as postgresql
    from sqlalchemy import JSON
    
    # Replace UUID with our SQLite-compatible version
    postgresql.UUID = UUID
    
    # Replace JSONB with standard JSON (SQLite doesn't support JSONB)
    postgresql.JSONB = JSON
    
    # Add asyncio marker
    config.addinivalue_line(
        "markers", "asyncio: mark test as an async test"
    )
    # Set asyncio mode to auto
    config.option.asyncio_mode = "auto"


@pytest.fixture(scope="function")
def db() -> Session:
    """
    Create a fresh file-based SQLite database for each test.
    
    Using a temporary file ensures complete isolation between tests
    and prevents index duplication issues.
    """
    # Import AFTER monkey-patching is done
    from app.db.base_class import Base
    import tempfile
    import os
    import uuid
    
    # Create a unique temp file with UUID to ensure no path reuse
    temp_dir = tempfile.gettempdir()
    db_path = os.path.join(temp_dir, f"test_{uuid.uuid4().hex}.db")
    
    try:
        # Create SQLite database with the temp file
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        
        # Enable foreign key constraints in SQLite
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Create session factory
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Create session
        session = TestingSessionLocal()
        
        try:
            yield session
        finally:
            session.close()
            Base.metadata.drop_all(bind=engine)
            engine.dispose()
    finally:
        # Clean up temp file
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
        except (PermissionError, OSError):
            # Windows may keep file locked; will be cleaned up by OS later
            pass


@pytest.fixture(scope="session")
def anyio_backend():
    """Configure anyio backend for async tests."""
    return "asyncio"
