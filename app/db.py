"""
Database setup module.

This module uses DatabaseManager internally but maintains backward compatibility
by exposing the same interface (engine, SessionLocal, Base, get_db).

To move to a common package, use DatabaseManager directly.
"""

from app.config import get_settings
from tessera_sdk.infra.database import DatabaseManager
from sqlalchemy.orm import declarative_base

Base = declarative_base()


# Initialize database manager
settings = get_settings()
db_manager = DatabaseManager(
    database_url=settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_use_lifo=True,
    application_name=settings.db_app_name,
)

# Expose the same interface for backward compatibility
engine = db_manager.engine
SessionLocal = db_manager.SessionLocal
get_db = db_manager.get_db
