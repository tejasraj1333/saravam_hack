"""Speech service — handles voice input (STT) and voice output (TTS) workflows."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import BinaryIO

from app.config import get_settings
from app.services.sarvam_service import transcribe_audio, text_to_speech

logger = logging.getLogger(__name__)


def handle_voice_input(audio_file: BinaryIO, filename: str = "audio.wav") -> dict:
    """Process voice input: save temporarily, transcribe via Saaras.

    Returns dict with: transcript, language
    """
    settings = get_settings()

    # Save to temp location
    temp_path = settings.upload_path / f"voice_{uuid.uuid4().hex[:8]}_{filename}"
    content = audio_file.read()
    temp_path.write_bytes(content)

    try:
        # Transcribe using Sarvam Saaras
        from io import BytesIO
        result = transcribe_audio(BytesIO(content))

        return {
            "transcript": result["transcript"],
            "language": result.get("language"),
        }
    finally:
        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()


def generate_speech(text: str, language: str = "hi-IN") -> tuple[bytes, str]:
    """Generate TTS audio and return (audio_bytes, cache_filename).

    Returns the audio bytes and a filename for serving.
    """
    audio_bytes = text_to_speech(text=text, language_code=language)
    filename = f"tts_{uuid.uuid4().hex[:8]}.wav"

    # Save to audio cache for serving
    settings = get_settings()
    out_path = settings.audio_cache_path / filename
    out_path.write_bytes(audio_bytes)

    return audio_bytes, filename
