"""Database session management - Compatibility wrapper

This module re-exports SessionLocal and get_db from database.py
to maintain backward compatibility with existing imports.
"""
from app.db.database import SessionLocal, get_db, engine, create_tables

__all__ = ['SessionLocal', 'get_db', 'engine', 'create_tables']
