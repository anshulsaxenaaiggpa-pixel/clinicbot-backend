"""
SQLAlchemy Base class - SINGLE SOURCE OF TRUTH
This is the ONLY place where declarative_base() should be called.
"""
from sqlalchemy.orm import declarative_base

# Single Base registry for ALL models
Base = declarative_base()
