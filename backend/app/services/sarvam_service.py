"""Sarvam AI service layer — wraps all SDK calls behind clean functions.

Verified against official docs (Oct 2026):
- Chat:  client.chat.completions(model="sarvam-105b", messages=[...])
- STT:   client.speech_to_text.transcribe(file=..., model="saaras:v4", mode="transcribe")
- TTS:   client.text_to_speech.convert(text=..., language_code="hi-IN", model="bulbul:v4-flash", speaker="simran_en_customer")
- Translate: client.text.translate(input=..., source_language_code="auto", target_language_code="hi-IN")
"""

from __future__ import annotations

import base64
import hashlib
import logging
import re
import time
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)

# ── Lazy client singleton ──────────────────────────────────────

_client = None


def _get_client():
    """Lazily initialize the Sarvam SDK client. Never called during import/startup."""
    global _client
    if _client is not None:
        return _client

    settings = get_settings()
    if not settings.has_sarvam_key:
        raise RuntimeError(
            "SARVAM_API_KEY is not configured. Set it in backend/.env "
            "or as an environment variable."
        )

    from sarvamai import SarvamAI

    _client = SarvamAI(api_subscription_key=settings.sarvam_api_key)
    logger.info("Sarvam AI client initialized.")
    return _client


# ── LLM Chat Completion ───────────────────────────────────────

# Simple in-memory response cache to avoid repeating identical LLM calls
_llm_cache: dict[str, dict] = {}


def chat_completion(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> dict:
    """Send messages to Sarvam LLM and return the response.

    Returns dict with keys: content, role, finish_reason.
    Caches responses for identical message lists.
    """
    settings = get_settings()
    model = model or settings.llm_model

    # Cache key from message content
    cache_key = hashlib.md5(
        f"{model}:{temperature}:{str(messages)}".encode()
    ).hexdigest()
    if cache_key in _llm_cache:
        logger.debug("LLM cache hit for key %s", cache_key[:8])
        return _llm_cache[cache_key]

    client = _get_client()

    try:
        response = client.chat.completions(
            model=model,
            messages=messages,
        )
        result = {
            "content": response.choices[0].message.content,
            "role": response.choices[0].message.role,
            "finish_reason": getattr(response.choices[0], "finish_reason", "stop"),
        }
        _llm_cache[cache_key] = result
        return result
    except Exception as e:
        logger.error("Sarvam LLM call failed: %s", str(e))
        raise


# ── Speech-to-Text ─────────────────────────────────────────────

def transcribe_audio(
    audio_file: BinaryIO,
    model: str | None = None,
    mode: str = "transcribe",
) -> dict:
    """Transcribe audio using Saaras.

    Returns dict with keys: transcript, language (if available).
    """
    settings = get_settings()
    model = model or settings.stt_model

    client = _get_client()

    try:
        response = client.speech_to_text.transcribe(
            file=audio_file,
            model=model,
            mode=mode,
        )
        return {
            "transcript": response.transcript,
            "language": getattr(response, "language_code", None),
        }
    except Exception as e:
        logger.error("Sarvam STT call failed: %s", str(e))
        raise


# ── Text-to-Speech ─────────────────────────────────────────────

def text_to_speech(
    text: str,
    language_code: str | None = None,
    model: str | None = None,
    speaker: str | None = None,
) -> bytes:
    """Convert text to speech using Bulbul. Returns WAV bytes.

    Caches results in the audio_cache directory.
    """
    settings = get_settings()
    language_code = language_code or settings.tts_language
    model = model or settings.tts_model
    speaker = speaker or settings.tts_speaker

    # Check cache
    text_hash = hashlib.md5(f"{text}:{language_code}:{model}:{speaker}".encode()).hexdigest()
    cache_path = settings.audio_cache_path / f"{text_hash}.wav"
    if cache_path.exists():
        logger.debug("TTS cache hit: %s", text_hash[:8])
        return cache_path.read_bytes()

    client = _get_client()

    try:
        response = client.text_to_speech.convert(
            text=text,
            language_code=language_code,
            model=model,
            speaker=speaker,
        )

        # The SDK returns a response with base64-encoded audio in `audios` field
        # Use the SDK's save utility or decode manually
        audio_b64 = "".join(response.audios)
        audio_bytes = base64.b64decode(audio_b64)

        # Cache to disk
        cache_path.write_bytes(audio_bytes)
        logger.info("TTS generated and cached: %s (%d bytes)", text_hash[:8], len(audio_bytes))

        return audio_bytes
    except Exception as e:
        logger.error("Sarvam TTS call failed: %s", str(e))
        raise


# ── Translation ────────────────────────────────────────────────

def translate_text(
    text: str,
    target_language: str = "hi-IN",
    source_language: str = "auto",
) -> str:
    """Translate text using Sarvam Translate."""
    client = _get_client()

    try:
        response = client.text.translate(
            input=text,
            source_language_code=source_language,
            target_language_code=target_language,
        )
        return response.translated_text
    except Exception as e:
        logger.error("Sarvam translate call failed: %s", str(e))
        raise


# ── LaTeX to Speech ────────────────────────────────────────────

_LATEX_SPEECH_MAP = {
    r"\frac": "divided by",
    r"\sqrt": "square root of",
    r"\int": "integral of",
    r"\sum": "summation of",
    r"\infty": "infinity",
    r"\pi": "pi",
    r"\alpha": "alpha",
    r"\beta": "beta",
    r"\gamma": "gamma",
    r"\delta": "delta",
    r"\theta": "theta",
    r"\sigma": "sigma",
    r"\mu": "mu",
    r"\lambda": "lambda",
    r"\hbar": "h-bar",
    r"\psi": "psi",
    r"\phi": "phi",
    r"\nabla": "del",
    r"\partial": "partial",
    r"\times": "times",
    r"\cdot": "dot",
    r"\leq": "less than or equal to",
    r"\geq": "greater than or equal to",
    r"\neq": "not equal to",
    r"\approx": "approximately equal to",
    r"^2": "squared",
    r"^3": "cubed",
    r"=": "equals",
    r"+": "plus",
    r"-": "minus",
}


def latex_to_speech(text: str) -> str:
    """Convert LaTeX expressions to speech-friendly text.

    Does not read raw LaTeX aloud — converts common math symbols
    to natural spoken phrases.
    """
    # Remove display math delimiters
    result = re.sub(r'\$\$(.+?)\$\$', r' \1 ', text, flags=re.DOTALL)
    result = re.sub(r'\$(.+?)\$', r' \1 ', result)
    result = re.sub(r'\\\[(.+?)\\\]', r' \1 ', result, flags=re.DOTALL)
    result = re.sub(r'\\\((.+?)\\\)', r' \1 ', result)

    # Replace LaTeX commands with spoken equivalents
    for latex, spoken in _LATEX_SPEECH_MAP.items():
        result = result.replace(latex, f" {spoken} ")

    # Clean up braces and extra whitespace
    result = re.sub(r'[{}]', ' ', result)
    result = re.sub(r'\s+', ' ', result).strip()

    return result
