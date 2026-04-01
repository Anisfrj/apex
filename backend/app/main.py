"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import get_settings
from .core.database import init_db
from .core.logging import setup_logging, get_logger
from .api.routes import router

setup_logging()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    settings = get_settings()
    logger.info("starting_apex_screener", env=settings.app_env)
    try:
        await init_db()
        logger.info("database_initialized")
    except Exception as e:
        logger.error("database_init_failed", error=str(e))
    yield
    logger.info("shutdown_complete")


app = FastAPI(
    title="APEX Screener",
    description="Cockpit d'Analyse Financière — Screener Top-Down",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for React dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(router)
