"""ShikshaSetu Backend - Application Configuration."""

from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Central configuration loaded from environment / .env file."""

    # ── Sarvam AI ──────────────────────────────────────────────
    sarvam_api_key: str = Field(default="", description="Sarvam AI API key")

    # ── MongoDB ────────────────────────────────────────────────
    mongodb_uri: str = Field(default="mongodb://localhost:27017")
    mongodb_db_name: str = Field(default="shikshasetu")

    # ── Application ────────────────────────────────────────────
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    upload_dir: str = Field(default="./uploads")
    audio_cache_dir: str = Field(default="./audio_cache")
    max_upload_size_mb: int = Field(default=20)
    max_pages: int = Field(default=200)

    # ── Embedding ──────────────────────────────────────────────
    embedding_provider: str = Field(
        default="local",
        description="'local' for TF-IDF (free), 'sarvam' for future API embeddings",
    )

    # ── LLM model identifiers (verified from docs) ────────────
    llm_model: str = Field(default="sarvam-105b")
    stt_model: str = Field(default="saaras:v4")
    tts_model: str = Field(default="bulbul:v4-flash")
    tts_speaker: str = Field(default="simran_en_customer")
    tts_language: str = Field(default="hi-IN")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # ── Derived paths ──────────────────────────────────────────
    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def audio_cache_path(self) -> Path:
        p = Path(self.audio_cache_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def data_dir(self) -> Path:
        """Local JSON-file fallback storage directory."""
        p = Path("./data")
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def has_sarvam_key(self) -> bool:
        return bool(self.sarvam_api_key and self.sarvam_api_key != "your_sarvam_api_key_here")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
