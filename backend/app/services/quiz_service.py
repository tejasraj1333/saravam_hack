"""Quiz generation and evaluation service."""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from app.config import get_settings
from app.models import QuizQuestion, QuizSession, QuizAttempt, QuestionType
from app.services.retrieval_service import get_vector_index
from app.services.sarvam_service import chat_completion
from app.repositories.local_store import get_local_store

logger = logging.getLogger(__name__)


QUIZ_GENERATION_PROMPT = """You are a quiz generator for college students.
Based on the provided study material excerpts, generate exactly {num_questions} quiz questions.

RULES:
1. Questions must be directly answerable from the provided material.
2. Include a mix of MCQ and short-answer questions.
3. Each MCQ must have exactly 4 options.
4. Difficulty should be around {difficulty}/5.
5. Include clear explanations for each answer.
6. Tag each question with a relevant concept name.

RESPOND IN VALID JSON ONLY (no markdown, no code fences):
{{
  "questions": [
    {{
      "concept": "concept name",
      "question": "question text",
      "type": "mcq",
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "correct_answer": "A) ...",
      "explanation": "explanation text",
      "difficulty": 2
    }}
  ]
}}

Study Material:
{context}

Topic focus: {topic}
"""


def generate_quiz(
    document_ids: list[str],
    topic: str = "",
    num_questions: int = 5,
    difficulty: int = 2,
    conversation_id: Optional[str] = None,
) -> QuizSession:
    """Generate quiz questions from document content via LLM.

    Returns a QuizSession with questions (correct answers stored server-side).
    """
    index = get_vector_index()
    store = get_local_store()

    # Gather context from documents
    query = topic if topic else "key concepts and important topics"
    results = index.search(query=query, document_ids=document_ids, top_k=8)

    if not results:
        # Return empty quiz if no content
        session = QuizSession(document_ids=document_ids, topic=topic)
        store.insert("quiz_sessions", session.session_id, session.model_dump())
        return session

    context = "\n\n---\n\n".join([
        f"[Excerpt {i+1}, Page {chunk.page_number}]: {chunk.content}"
        for i, (chunk, _) in enumerate(results)
    ])

    prompt = QUIZ_GENERATION_PROMPT.format(
        num_questions=num_questions,
        difficulty=difficulty,
        context=context,
        topic=topic or "general review of the material",
    )

    response = chat_completion([
        {"role": "system", "content": "You are a quiz question generator. Respond only in valid JSON."},
        {"role": "user", "content": prompt},
    ])

    # Parse LLM response
    questions = _parse_quiz_response(response["content"], results)

    # Build session
    session = QuizSession(
        document_ids=document_ids,
        topic=topic,
        questions=questions,
    )

    # Store session (with correct answers)
    store.insert("quiz_sessions", session.session_id, session.model_dump())

    return session


def _parse_quiz_response(content: str, results: list) -> list[QuizQuestion]:
    """Parse LLM JSON response into QuizQuestion objects."""
    # Try to extract JSON from response
    try:
        # Remove potential markdown code fences
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        data = json.loads(content)
    except json.JSONDecodeError:
        # Try to find JSON object in the response
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                logger.error("Failed to parse quiz response as JSON")
                return []
        else:
            return []

    questions = []
    for q in data.get("questions", []):
        q_type = QuestionType.MCQ if q.get("type", "mcq") == "mcq" else QuestionType.SHORT_ANSWER
        source_chunks = [chunk.chunk_id for chunk, _ in results[:3]]

        questions.append(QuizQuestion(
            concept_id=q.get("concept", "general"),
            question_text=q.get("question", ""),
            question_type=q_type,
            options=q.get("options", []),
            correct_answer=q.get("correct_answer", ""),
            explanation=q.get("explanation", ""),
            source_chunk_ids=source_chunks,
            difficulty=q.get("difficulty", 2),
        ))

    return questions


def submit_quiz(session_id: str, answers: list[dict]) -> dict:
    """Evaluate quiz answers and return results.

    Args:
        session_id: Quiz session ID.
        answers: List of {question_id, student_answer}.

    Returns dict with score, results, recommendations.
    """
    store = get_local_store()
    session_data = store.get("quiz_sessions", session_id)

    if not session_data:
        return {"error": "Quiz session not found"}

    questions = {q["question_id"]: q for q in session_data.get("questions", [])}
    results_list = []
    correct_count = 0
    concepts_wrong = []

    for ans in answers:
        qid = ans.get("question_id", "")
        student_answer = ans.get("student_answer", "").strip()
        q = questions.get(qid)

        if not q:
            continue

        # Check correctness (case-insensitive, trimmed)
        correct = q.get("correct_answer", "").strip()
        is_correct = student_answer.lower() == correct.lower()

        # For MCQ, also check if just the letter matches
        if not is_correct and q.get("question_type") == "mcq":
            student_letter = student_answer[0].upper() if student_answer else ""
            correct_letter = correct[0].upper() if correct else ""
            is_correct = student_letter == correct_letter

        if is_correct:
            correct_count += 1
        else:
            concepts_wrong.append(q.get("concept_id", ""))

        attempt = QuizAttempt(
            question_id=qid,
            student_answer=student_answer,
            is_correct=is_correct,
        )

        results_list.append({
            "question_id": qid,
            "question_text": q.get("question_text", ""),
            "student_answer": student_answer,
            "correct_answer": correct,
            "is_correct": is_correct,
            "explanation": q.get("explanation", ""),
        })

    total = len(results_list)
    score = (correct_count / total * 100) if total > 0 else 0

    # Generate recommendations
    recommendations = []
    if concepts_wrong:
        unique_concepts = list(set(concepts_wrong))
        recommendations.append(f"Review these concepts: {', '.join(unique_concepts[:5])}")
    if score < 60:
        recommendations.append("Consider re-reading the source material before retaking the quiz.")
    if score >= 80:
        recommendations.append("Great job! Try harder questions or move to the next topic.")

    # Update session with attempts
    session_data["score"] = score
    session_data["attempts"] = [r for r in results_list]
    store.update("quiz_sessions", session_id, session_data)

    return {
        "session_id": session_id,
        "score": score,
        "total": total,
        "correct": correct_count,
        "results": results_list,
        "recommendations": recommendations,
    }
