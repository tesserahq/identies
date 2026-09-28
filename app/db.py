"""
Database setup and the application's transaction boundary.

One execution (HTTP request, middleware lookup, background job) gets one
SQLAlchemy ``Session``. The session commits when the execution succeeds, rolls
back when an exception escapes, and closes. Repositories and commands never
end the transaction. The mechanics come from tessera_sdk
(docs/managed-transactions.md in tessera-sdk-py); this module wires them to
Identies' settings and re-exports them under the names the app imports.
"""

from sqlalchemy.orm import declarative_base
from tessera_sdk.infra import current_session, on_commit, savepoint
from tessera_sdk.infra.database import DatabaseManager
from tessera_sdk.server.dependencies import create_db_dependency

from app.config import get_settings

__all__ = [
    "Base",
    "DbSession",
    "SessionLocal",
    "current_session",
    "db_manager",
    "engine",
    "get_db",
    "on_commit",
    "savepoint",
    "session_scope",
]

Base = declarative_base()

settings = get_settings()
db_manager = DatabaseManager(
    database_url=settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_use_lifo=True,
    application_name=settings.db_app_name,
    autoflush=True,
)

engine = db_manager.engine
SessionLocal = db_manager.SessionLocal

# One managed session per execution: routes declare `db: DbSession`; the
# authentication middleware and other entry points use
# `with session_scope() as db:`.
get_db, DbSession = create_db_dependency(db_manager)
session_scope = db_manager.session_scope
