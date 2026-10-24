"""API request / response schemas (separated from internal models)."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from app.models import Citation, QuizQuestion, ConceptMastery, MasteryLevel, QuestionType


# ── Health ─────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "ok"
    sarvam_configured: bool = False
    mongodb_connected: bool = False
    version: str = "0.1.0"


# ── Document ───────────────────────────────────────────────────

class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str
    message: str


class DocumentInfo(BaseModel):
    document_id: str
    filename: str
    title: str
    page_count: int
    status: str
    chunk_count: int
    uploaded_at: str
    error_message: Optional[str] = None
    is_scanned: bool = False


class DocumentListResponse(BaseModel):
    documents: list[DocumentInfo]
    total: int


# ── Tutor ──────────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    document_ids: list[str] = Field(default_factory=list)
    conversation_id: Optional[str] = None
    language: str = Field(default="hi-IN")
    learning_level: Optional[str] = None


class AskResponse(BaseModel):
    answer: str
    speech_answer: str  # speech-friendly (no LaTeX)
    citations: list[Citation]
    conversation_id: str
    message_id: str
    audio_url: Optional[str] = None


class FeedbackRequest(BaseModel):
    message_id: str
    conversation_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class ConversationHistoryResponse(BaseModel):
    conversation_id: str
    messages: list[dict]
    document_ids: list[str]


# ── Voice ──────────────────────────────────────────────────────

class TranscribeResponse(BaseModel):
    transcript: str
    language: Optional[str] = None


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=3000)
    language: str = Field(default="hi-IN")


class TTSResponse(BaseModel):
    audio_url: str
    text: str


# ── Quiz ───────────────────────────────────────────────────────

class QuizGenerateRequest(BaseModel):
    document_ids: list[str] = Field(default_factory=list)
    topic: str = ""
    num_questions: int = Field(default=5, ge=1, le=20)
    difficulty: int = Field(default=2, ge=1, le=5)
    conversation_id: Optional[str] = None


class QuizGenerateResponse(BaseModel):
    session_id: str
    questions: list[dict]  # questions without correct answers


class QuizSubmitRequest(BaseModel):
    session_id: str
    answers: list[dict]  # [{question_id, student_answer}]


class QuizSubmitResponse(BaseModel):
    session_id: str
    score: float
    total: int
    correct: int
    results: list[dict]
    recommendations: list[str]


# ── Learning Progress ─────────────────────────────────────────

class LearningProgressResponse(BaseModel):
    concepts: list[ConceptMastery]
    overall_mastery: float
    total_questions_attempted: int
    total_correct: int
    weak_concepts: list[str]
    revision_suggestions: list[dict]


class RevisionPlanResponse(BaseModel):
    plan: list[dict]
    next_review_date: Optional[str] = None
