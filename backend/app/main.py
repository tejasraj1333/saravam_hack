"""ShikshaSetu Backend — FastAPI Application Entry Point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.api.routes import router

# ── Logging ────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan ───────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup / shutdown lifecycle."""
    settings = get_settings()
    logger.info("ShikshaSetu starting in %s mode", settings.app_env)
    logger.info("Sarvam API key configured: %s", settings.has_sarvam_key)
    logger.info("Upload directory: %s", settings.upload_path)

    # Ensure directories exist
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    settings.audio_cache_path.mkdir(parents=True, exist_ok=True)
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    # NOTE: We do NOT call any Sarvam APIs during startup.
    # The client is lazily initialized on first use.

    yield

    logger.info("ShikshaSetu shutting down.")


# ── App Creation ───────────────────────────────────────────────

app = FastAPI(
    title="ShikshaSetu",
    description="Multilingual AI Personal Tutor powered by Sarvam AI",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router)
