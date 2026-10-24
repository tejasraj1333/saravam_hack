"""API route definitions for ShikshaSetu."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, UploadFile, HTTPException, Form, Query
from fastapi.responses import FileResponse

from app.config import get_settings
from app.schemas import (
    HealthResponse, DocumentUploadResponse, DocumentInfo, DocumentListResponse,
    AskRequest, AskResponse, FeedbackRequest, ConversationHistoryResponse,
    TranscribeResponse, TTSRequest, TTSResponse,
    QuizGenerateRequest, QuizGenerateResponse, QuizSubmitRequest, QuizSubmitResponse,
    LearningProgressResponse, RevisionPlanResponse,
)
from app.models import DocStatus
from app.services.document_service import validate_upload, process_document
from app.services.retrieval_service import get_vector_index
from app.repositories.local_store import get_local_store

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Health ─────────────────────────────────────────────────────

@router.get("/api/health", response_model=HealthResponse)
def health_check():
    settings = get_settings()
    return HealthResponse(
        status="ok",
        sarvam_configured=settings.has_sarvam_key,
        mongodb_connected=False,  # Using local store for now
        version="0.1.0",
    )


# ── Documents ──────────────────────────────────────────────────

@router.post("/api/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload a PDF document for processing."""
    settings = get_settings()
    store = get_local_store()
    index = get_vector_index()

    # Read file content
    content = await file.read()
    filename = file.filename or "unknown.pdf"

    # Validate
    valid, msg = validate_upload(filename, len(content))
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    # Save file
    doc_id = uuid.uuid4().hex[:16]
    safe_name = f"{doc_id}_{filename}"
    file_path = settings.upload_path / safe_name
    file_path.write_bytes(content)

    # Process
    doc, chunks = process_document(doc_id, file_path)

    # Store document metadata
    store.insert("documents", doc.document_id, doc.model_dump())

    # Store chunks in local store and vector index
    if chunks:
        for chunk in chunks:
            store.insert("chunks", chunk.chunk_id, chunk.model_dump())
        index.add_chunks(chunks)

    status = "ready" if doc.status == DocStatus.READY else "error"
    message = f"Processed {doc.page_count} pages, {doc.chunk_count} chunks"
    if doc.is_scanned:
        message += " (scanned document - text may be incomplete)"
    if doc.error_message:
        message = doc.error_message

    return DocumentUploadResponse(
        document_id=doc.document_id,
        filename=filename,
        status=status,
        message=message,
    )


@router.get("/api/documents", response_model=DocumentListResponse)
def list_documents():
    """List all uploaded documents."""
    store = get_local_store()
    docs = store.get_all("documents")
    doc_list = []
    for d in docs:
        doc_list.append(DocumentInfo(
            document_id=d.get("document_id", ""),
            filename=d.get("filename", ""),
            title=d.get("title", ""),
            page_count=d.get("page_count", 0),
            status=d.get("status", "unknown"),
            chunk_count=d.get("chunk_count", 0),
            uploaded_at=str(d.get("uploaded_at", "")),
            error_message=d.get("error_message"),
            is_scanned=d.get("is_scanned", False),
        ))
    return DocumentListResponse(documents=doc_list, total=len(doc_list))


@router.get("/api/documents/{document_id}")
def get_document(document_id: str):
    """Get document details and extracted text."""
    store = get_local_store()
    doc = store.get("documents", document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get chunks for this document
    index = get_vector_index()
    chunks = index.get_document_chunks(document_id)
    chunk_data = [
        {"chunk_id": c.chunk_id, "page_number": c.page_number,
         "heading": c.heading, "content": c.content[:500]}
        for c in chunks
    ]

    return {**doc, "chunks": chunk_data}


@router.delete("/api/documents/{document_id}")
def delete_document(document_id: str):
    """Delete a document and its chunks."""
    store = get_local_store()
    index = get_vector_index()

    doc = store.get("documents", document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove chunks from index
    removed = index.remove_document(document_id)

    # Remove from store
    # Delete chunk records
    all_chunks = store.get_all("chunks")
    for chunk in all_chunks:
        if chunk.get("document_id") == document_id:
            store.delete("chunks", chunk.get("chunk_id", ""))

    store.delete("documents", document_id)

    # Delete uploaded file
    settings = get_settings()
    for f in settings.upload_path.glob(f"{document_id}_*"):
        f.unlink()

    return {"status": "deleted", "chunks_removed": removed}


# ── Tutor ──────────────────────────────────────────────────────

@router.post("/api/tutor/ask", response_model=AskResponse)
def ask_tutor(req: AskRequest):
    """Ask a question grounded in uploaded documents."""
    from app.services.tutor_service import ask_question

    settings = get_settings()
    if not settings.has_sarvam_key:
        raise HTTPException(
            status_code=503,
            detail="Sarvam API key not configured. Set SARVAM_API_KEY in .env",
        )

    try:
        result = ask_question(
            question=req.question,
            document_ids=req.document_ids,
            conversation_id=req.conversation_id,
            language=req.language,
            learning_level=req.learning_level,
        )
        return AskResponse(**result)
    except Exception as e:
        logger.error("Tutor ask failed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Tutor error: {str(e)}")


@router.get("/api/tutor/history/{conversation_id}", response_model=ConversationHistoryResponse)
def get_history(conversation_id: str):
    """Get conversation history."""
    from app.services.tutor_service import get_conversation_history

    conv = get_conversation_history(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationHistoryResponse(
        conversation_id=conversation_id,
        messages=conv.get("messages", []),
        document_ids=conv.get("document_ids", []),
    )


@router.post("/api/tutor/feedback")
def submit_feedback(req: FeedbackRequest):
    """Submit feedback on a tutor response."""
    store = get_local_store()
    store.insert("feedback", req.message_id, {
        "message_id": req.message_id,
        "conversation_id": req.conversation_id,
        "rating": req.rating,
        "comment": req.comment,
    })
    return {"status": "recorded"}


# ── Voice ──────────────────────────────────────────────────────

@router.post("/api/voice/transcribe", response_model=TranscribeResponse)
async def transcribe_voice(file: UploadFile = File(...)):
    """Transcribe uploaded audio via Sarvam Saaras."""
    settings = get_settings()
    if not settings.has_sarvam_key:
        raise HTTPException(status_code=503, detail="Sarvam API key not configured")

    from app.services.speech_service import handle_voice_input

    try:
        result = handle_voice_input(file.file, file.filename or "audio.wav")
        return TranscribeResponse(**result)
    except Exception as e:
        logger.error("Voice transcribe failed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")


@router.post("/api/voice/tts", response_model=TTSResponse)
def generate_tts(req: TTSRequest):
    """Generate TTS audio from text via Sarvam Bulbul."""
    settings = get_settings()
    if not settings.has_sarvam_key:
        raise HTTPException(status_code=503, detail="Sarvam API key not configured")

    from app.services.speech_service import generate_speech

    try:
        _, filename = generate_speech(req.text, req.language)
        audio_url = f"/api/audio/{filename}"
        return TTSResponse(audio_url=audio_url, text=req.text)
    except Exception as e:
        logger.error("TTS failed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")


@router.get("/api/audio/{filename}")
def serve_audio(filename: str):
    """Serve cached audio files."""
    # Prevent path traversal
    if '..' in filename or '/' in filename or '\\' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    settings = get_settings()
    file_path = settings.audio_cache_path / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio not found")

    return FileResponse(file_path, media_type="audio/wav")


# ── Quiz ───────────────────────────────────────────────────────

@router.post("/api/quiz/generate", response_model=QuizGenerateResponse)
def generate_quiz_endpoint(req: QuizGenerateRequest):
    """Generate a quiz from uploaded material."""
    settings = get_settings()
    if not settings.has_sarvam_key:
        raise HTTPException(status_code=503, detail="Sarvam API key not configured")

    from app.services.quiz_service import generate_quiz

    try:
        session = generate_quiz(
            document_ids=req.document_ids,
            topic=req.topic,
            num_questions=req.num_questions,
            difficulty=req.difficulty,
        )

        # Return questions WITHOUT correct answers
        safe_questions = []
        for q in session.questions:
            safe_questions.append({
                "question_id": q.question_id,
                "concept_id": q.concept_id,
                "question_text": q.question_text,
                "question_type": q.question_type.value,
                "options": q.options,
                "difficulty": q.difficulty,
            })

        return QuizGenerateResponse(
            session_id=session.session_id,
            questions=safe_questions,
        )
    except Exception as e:
        logger.error("Quiz generation failed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Quiz error: {str(e)}")


@router.post("/api/quiz/submit", response_model=QuizSubmitResponse)
def submit_quiz_endpoint(req: QuizSubmitRequest):
    """Submit quiz answers for evaluation."""
    from app.services.quiz_service import submit_quiz
    from app.services.mastery_service import update_concept_mastery

    result = submit_quiz(req.session_id, req.answers)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    # Update concept mastery for each result
    for r in result.get("results", []):
        # Find concept_id from quiz session
        store = get_local_store()
        session_data = store.get("quiz_sessions", req.session_id)
        if session_data:
            for q in session_data.get("questions", []):
                if q["question_id"] == r["question_id"]:
                    update_concept_mastery(
                        concept_id=q.get("concept_id", "general"),
                        is_correct=r["is_correct"],
                    )
                    break

    return QuizSubmitResponse(**result)


# ── Learning Progress ─────────────────────────────────────────

@router.get("/api/learning/progress", response_model=LearningProgressResponse)
def get_progress():
    """Get overall learning progress."""
    from app.services.mastery_service import get_learning_progress
    return LearningProgressResponse(**get_learning_progress())


@router.get("/api/learning/revision-plan", response_model=RevisionPlanResponse)
def get_revision():
    """Get personalized revision plan."""
    from app.services.mastery_service import get_revision_plan
    return RevisionPlanResponse(**get_revision_plan())
