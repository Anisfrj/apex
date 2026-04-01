"""Database connection and session management."""

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncEngine
from .config import get_settings


class Base(DeclarativeBase):
    pass


def create_session_factory():
    """Create a NEW engine + session factory. Call once per event loop / worker."""
    settings = get_settings()
    async_url = settings.database_url.replace(
        "postgresql://", "postgresql+asyncpg://"
    )
    engine: AsyncEngine = create_async_engine(
        async_url,
        echo=settings.app_env == "development",
        pool_size=5,
        max_overflow=10,
    )
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, factory


# FastAPI uses a single engine for the lifetime of the app
_fastapi_engine: AsyncEngine | None = None
_fastapi_factory: async_sessionmaker[AsyncSession] | None = None


def _get_fastapi_factory():
  global _fastapi_engine, _fastapi_factory
  if _fastapi_factory is None:
      _fastapi_engine, _fastapi_factory = create_session_factory()
  return _fastapi_factory


async def get_db():
    """FastAPI dependency — yields an async DB session."""
    factory = _get_fastapi_factory()
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Create all tables."""
    global _fastapi_engine
    if _fastapi_engine is None:
        _fastapi_engine, _ = create_session_factory()
    async with _fastapi_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ── Compatibilité: helper get_db_connection pour code existant ─────

async def _get_raw_connection():
    """Internal: get a low-level async connection from the global engine."""
    global _fastapi_engine
    if _fastapi_engine is None:
        _fastapi_engine, _ = create_session_factory()
    return await _fastapi_engine.connect()


def get_db_connection():
    """
    Compatibilité pour l'ancien code qui importait get_db_connection.

    Attention: c'est une fonction synchrone qui exécute la connexion async
    de manière bloquante. À réserver à du code non-async lancé au startup,
    pas dans les endpoints FastAPI directement.
    """
    import asyncio

    loop = asyncio.get_event_loop()
    conn = loop.run_until_complete(_get_raw_connection())
    return conn
