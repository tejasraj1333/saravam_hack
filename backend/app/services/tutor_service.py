"""RAG-based tutor service — retrieves context and generates grounded answers."""

from __future__ import annotations

import logging
import re
from typing import Optional

from app.config import get_settings
from app.models import Citation, Message, Conversation
from app.services.retrieval_service import get_vector_index
from app.services.sarvam_service import chat_completion, latex_to_speech
from app.repositories.local_store import get_local_store

logger = logging.getLogger(__name__)


TUTOR_SYSTEM_PROMPT = """You are ShikshaSetu, a patient and knowledgeable AI tutor for Indian college students.

RULES:
1. Answer ONLY based on the provided document excerpts (evidence). If the evidence does not contain enough information, say so honestly.
2. Explain concepts clearly and patiently, as if teaching a student who is learning for the first time.
3. Use Hindi/Hinglish with English technical terminology when the student's preferred language is Hindi.
4. Use LaTeX notation for mathematical equations (wrap in $ or $$).
5. Give examples where helpful.
6. Distinguish between what the textbook says (cite it) and your supplementary explanation.
7. NEVER invent or fabricate source quotations, page numbers, or citations.
8. NEVER claim an answer is supported by a source unless the provided excerpt actually supports it.
9. At the end, include a "Sources:" section listing which excerpts you used, by their [Source N] labels.

RESPONSE FORMAT:
- Use clear headings and bullet points.
- Use LaTeX for equations: $E = mc^2$
- Cite sources as [Source 1], [Source 2], etc.
"""


def _build_context(chunks_with_scores: list) -> tuple[str, list[Citation]]:
    """Build context string and citation objects from retrieved chunks."""
    store = get_local_store()
    context_parts = []
    citations = []

    for i, (chunk, score) in enumerate(chunks_with_scores):
        source_label = f"[Source {i + 1}]"
        # Get document name
        doc_data = store.get("documents", chunk.document_id)
        doc_name = doc_data.get("filename", "Unknown") if doc_data else "Unknown"

        context_parts.append(
            f"{source_label} (Document: {doc_name}, Page {chunk.page_number}):\n"
            f"{chunk.content}\n"
        )
        citations.append(Citation(
            document_id=chunk.document_id,
            document_name=doc_name,
            chunk_id=chunk.chunk_id,
            page_number=chunk.page_number,
            snippet=chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
        ))

    return "\n---\n".join(context_parts), citations


def ask_question(
    question: str,
    document_ids: list[str],
    conversation_id: Optional[str] = None,
    language: str = "hi-IN",
    learning_level: Optional[str] = None,
) -> dict:
    """Main RAG pipeline: retrieve → generate → respond.

    Returns dict with: answer, speech_answer, citations, conversation_id, message_id.
    """
    store = get_local_store()
    index = get_vector_index()

    # 1. Retrieve relevant chunks
    results = index.search(
        query=question,
        document_ids=document_ids if document_ids else None,
        top_k=5,
    )

    if not results:
        no_context_answer = (
            "I couldn't find relevant information in the uploaded documents for this question. "
            "Please make sure you've uploaded the right study material, or try rephrasing your question."
        )
        return {
            "answer": no_context_answer,
            "speech_answer": no_context_answer,
            "citations": [],
            "conversation_id": conversation_id or "",
            "message_id": "",
        }

    # 2. Build context
    context, citations = _build_context(results)

    # 3. Build conversation history
    messages = [{"role": "system", "content": TUTOR_SYSTEM_PROMPT}]

    # Load conversation history if continuing
    if conversation_id:
        conv_data = store.get("conversations", conversation_id)
        if conv_data and "messages" in conv_data:
            for msg in conv_data["messages"][-6:]:  # Last 6 messages for context
                messages.append({"role": msg["role"], "content": msg["content"]})

    # 4. Add the user query with context
    language_instruction = ""
    if language == "hi-IN":
        language_instruction = "\nPlease respond in Hindi/Hinglish, using English for technical terms."
    elif language != "en-IN":
        language_instruction = f"\nPlease respond in the language with code: {language}"

    level_instruction = ""
    if learning_level:
        level_instruction = f"\nAdjust explanation for a {learning_level} level student."

    user_message = (
        f"## Student's Question:\n{question}\n\n"
        f"## Evidence from uploaded documents:\n{context}\n"
        f"{language_instruction}{level_instruction}"
    )
    messages.append({"role": "user", "content": user_message})

    # 5. Call LLM
    llm_response = chat_completion(messages)
    answer = llm_response["content"]

    # 6. Generate speech-friendly version
    speech_answer = latex_to_speech(answer)
    # Also remove markdown formatting for speech
    speech_answer = re.sub(r'#{1,6}\s*', '', speech_answer)
    speech_answer = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', speech_answer)
    speech_answer = re.sub(r'\[Source \d+\]', '', speech_answer)
    speech_answer = speech_answer.strip()

    # 7. Save to conversation
    if not conversation_id:
        conv = Conversation(document_ids=document_ids, language=language)
        conversation_id = conv.conversation_id
        store.insert("conversations", conversation_id, conv.model_dump())

    # Save user message
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=question,
    )
    # Save assistant message
    asst_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=answer,
        speech_content=speech_answer,
        citations=[c.model_dump() for c in citations],
    )

    # Update conversation in store
    conv_data = store.get("conversations", conversation_id) or {}
    conv_messages = conv_data.get("messages", [])
    conv_messages.append(user_msg.model_dump())
    conv_messages.append(asst_msg.model_dump())
    store.update("conversations", conversation_id, {"messages": conv_messages})

    return {
        "answer": answer,
        "speech_answer": speech_answer,
        "citations": citations,
        "conversation_id": conversation_id,
        "message_id": asst_msg.message_id,
    }


def get_conversation_history(conversation_id: str) -> dict | None:
    """Retrieve full conversation history."""
    store = get_local_store()
    return store.get("conversations", conversation_id)
