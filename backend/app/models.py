"""Pydantic data models for all domain entities."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex[:16]


# ── Enums ──────────────────────────────────────────────────────

class DocStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


class QuestionType(str, Enum):
    MCQ = "mcq"
    SHORT_ANSWER = "short_answer"
    TRUE_FALSE = "true_false"


class MasteryLevel(str, Enum):
    NOT_STARTED = "not_started"
    BEGINNER = "beginner"
    DEVELOPING = "developing"
    PROFICIENT = "proficient"
    MASTERED = "mastered"


# ── Documents ──────────────────────────────────────────────────

class DocumentChunk(BaseModel):
    chunk_id: str = Field(default_factory=_new_id)
    document_id: str
    page_number: int
    heading: Optional[str] = None
    content: str
    char_count: int = 0
    metadata: dict = Field(default_factory=dict)


class Document(BaseModel):
    document_id: str = Field(default_factory=_new_id)
    filename: str
    title: str = ""
    page_count: int = 0
    status: DocStatus = DocStatus.PENDING
    error_message: Optional[str] = None
    chunk_count: int = 0
    uploaded_at: datetime = Field(default_factory=_utcnow)
    processed_at: Optional[datetime] = None
    file_size_bytes: int = 0
    is_scanned: bool = False


# ── Conversations ──────────────────────────────────────────────

class Citation(BaseModel):
    document_id: str
    document_name: str
    chunk_id: str
    page_number: int
    snippet: str


class Message(BaseModel):
    message_id: str = Field(default_factory=_new_id)
    conversation_id: str
    role: str  # "user" | "assistant"
    content: str
    speech_content: Optional[str] = None  # speech-friendly version
    citations: list[Citation] = Field(default_factory=list)
    audio_url: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow)


class Conversation(BaseModel):
    conversation_id: str = Field(default_factory=_new_id)
    document_ids: list[str] = Field(default_factory=list)
    title: str = "New Conversation"
    messages: list[Message] = Field(default_factory=list)
    language: str = "hi-IN"
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


# ── Quiz ───────────────────────────────────────────────────────

class QuizQuestion(BaseModel):
    question_id: str = Field(default_factory=_new_id)
    concept_id: str = ""
    question_text: str
    question_type: QuestionType = QuestionType.MCQ
    options: list[str] = Field(default_factory=list)
    correct_answer: str
    explanation: str = ""
    source_chunk_ids: list[str] = Field(default_factory=list)
    difficulty: int = Field(default=1, ge=1, le=5)


class QuizAttempt(BaseModel):
    attempt_id: str = Field(default_factory=_new_id)
    question_id: str
    student_answer: str
    is_correct: bool = False
    hints_used: int = 0
    time_taken_seconds: float = 0.0
    submitted_at: datetime = Field(default_factory=_utcnow)


class QuizSession(BaseModel):
    session_id: str = Field(default_factory=_new_id)
    document_ids: list[str] = Field(default_factory=list)
    topic: str = ""
    questions: list[QuizQuestion] = Field(default_factory=list)
    attempts: list[QuizAttempt] = Field(default_factory=list)
    score: float = 0.0
    created_at: datetime = Field(default_factory=_utcnow)


# ── Concept Mastery ────────────────────────────────────────────

class Concept(BaseModel):
    concept_id: str = Field(default_factory=_new_id)
    name: str
    description: str = ""
    prerequisites: list[str] = Field(default_factory=list)  # concept_ids
    domain: str = ""


class ConceptMastery(BaseModel):
    concept_id: str
    concept_name: str
    mastery_score: float = Field(default=0.0, ge=0.0, le=1.0)
    level: MasteryLevel = MasteryLevel.NOT_STARTED
    total_attempts: int = 0
    correct_attempts: int = 0
    hints_used: int = 0
    last_practiced: Optional[datetime] = None
    misconceptions: list[str] = Field(default_factory=list)
    next_review: Optional[datetime] = None


# ── Audio Cache ────────────────────────────────────────────────

class AudioCacheMeta(BaseModel):
    cache_key: str
    text_hash: str
    language: str
    file_path: str
    created_at: datetime = Field(default_factory=_utcnow)
    expires_at: Optional[datetime] = None
