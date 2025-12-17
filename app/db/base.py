"""
Registry Bootstrap - Import all models to register them with SQLAlchemy
This ensures all models are discovered before any operations.
"""
from app.db.base_class import Base

# CRITICAL: This import triggers app/models/__init__.py which loads ALL models
# This MUST happen before any table creation, queries, or model instantiation
import app.models  # noqa: F401

__all__ = ["Base"]
