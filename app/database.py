"""
database.py — Async SQLAlchemy engine, session factory, and base declaration.

Usage:
    from app.database import get_db, Base, engine

    async with get_db() as db:   # standalone usage
        ...

    # In FastAPI routes use the Depends(get_db) dependency instead.
"""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# ── Declarative Base ──────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """
    Single declarative base shared by all ORM models.
    Import this in every model file:

        from app.database import Base

        class MyModel(Base):
            __tablename__ = "my_table"
            ...
    """
    pass


# ── Engine ────────────────────────────────────────────────────────────────────

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,           # Log SQL in debug mode
    pool_size=10,                  # Number of persistent connections
    max_overflow=20,               # Extra connections when pool is full
    pool_timeout=30,               # Seconds to wait for a connection
    pool_recycle=1800,             # Recycle connections every 30 min (avoids stale)
    pool_pre_ping=True,            # Verify connection health before use
)


# ── Session Factory ───────────────────────────────────────────────────────────

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,        # Don't expire objects after commit (safer for async)
    autocommit=False,
    autoflush=False,
)


# ── Health check helper ───────────────────────────────────────────────────────

async def check_db_connection() -> bool:
    """
    Ping the database. Returns True if reachable, False otherwise.
    Called by the /health endpoint.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False


# ── Table creation (dev/test only) ────────────────────────────────────────────

async def create_all_tables() -> None:
    """
    Creates all tables defined in ORM models.
    ⚠️  For production use Alembic migrations instead.
    Safe to call in tests / local dev.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_all_tables() -> None:
    """Drop all tables — test teardown only."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ── Dependency ────────────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a transactional database session.

    - Commits on success
    - Rolls back on any exception
    - Always closes the session

    Usage in a route:
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except SQLAlchemyError as exc:
            await session.rollback()
            raise exc
        finally:
            await session.close()