"""Concept mastery tracking and revision planning.

Uses a transparent, deterministic scoring formula:
  mastery_score = (accuracy * 0.6) + (retention * 0.3) - (hint_penalty * 0.1)

These weights are configurable. The score is an estimate, not a scientifically
validated measure of knowledge.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.models import Concept, ConceptMastery, MasteryLevel
from app.repositories.local_store import get_local_store

logger = logging.getLogger(__name__)

# ── Configurable weights ───────────────────────────────────────
ACCURACY_WEIGHT = 0.6
RETENTION_WEIGHT = 0.3
HINT_PENALTY_WEIGHT = 0.1

# ── Example prerequisite graph (Quantum Mechanics) ─────────────
EXAMPLE_CONCEPTS = [
    Concept(concept_id="qm_wave_particle", name="Wave-Particle Duality",
            description="Matter and light exhibit both wave and particle properties",
            prerequisites=[], domain="Quantum Mechanics"),
    Concept(concept_id="qm_schrodinger", name="Schrödinger Equation",
            description="Fundamental equation describing quantum state evolution",
            prerequisites=["qm_wave_particle"], domain="Quantum Mechanics"),
    Concept(concept_id="qm_uncertainty", name="Heisenberg Uncertainty Principle",
            description="Fundamental limit on measurement precision of conjugate variables",
            prerequisites=["qm_wave_particle"], domain="Quantum Mechanics"),
    Concept(concept_id="qm_hydrogen", name="Hydrogen Atom",
            description="Quantum mechanical model of the hydrogen atom",
            prerequisites=["qm_schrodinger"], domain="Quantum Mechanics"),
    Concept(concept_id="qm_spin", name="Quantum Spin",
            description="Intrinsic angular momentum of quantum particles",
            prerequisites=["qm_schrodinger", "qm_uncertainty"], domain="Quantum Mechanics"),
    Concept(concept_id="semi_band", name="Band Theory",
            description="Energy bands in crystalline solids",
            prerequisites=["qm_schrodinger"], domain="Semiconductor Physics"),
    Concept(concept_id="semi_pn", name="PN Junction",
            description="Interface between p-type and n-type semiconductors",
            prerequisites=["semi_band"], domain="Semiconductor Physics"),
    Concept(concept_id="semi_transistor", name="Transistor",
            description="Semiconductor device for amplification and switching",
            prerequisites=["semi_pn"], domain="Semiconductor Physics"),
]


def _init_concepts() -> None:
    """Initialize example concept graph if not present."""
    store = get_local_store()
    for concept in EXAMPLE_CONCEPTS:
        if not store.get("concepts", concept.concept_id):
            store.insert("concepts", concept.concept_id, concept.model_dump())


def _compute_mastery_score(correct: int, total: int, hints: int) -> float:
    """Compute mastery score using transparent formula.

    mastery = accuracy * 0.6 + retention * 0.3 - hint_penalty * 0.1
    Where retention = min(1.0, correct / 3) as a rough proxy.
    """
    if total == 0:
        return 0.0

    accuracy = correct / total
    retention = min(1.0, correct / 3)  # Needs at least 3 correct for full retention credit
    hint_penalty = min(1.0, hints / max(total, 1))

    score = (
        accuracy * ACCURACY_WEIGHT
        + retention * RETENTION_WEIGHT
        - hint_penalty * HINT_PENALTY_WEIGHT
    )
    return max(0.0, min(1.0, score))


def _score_to_level(score: float) -> MasteryLevel:
    if score >= 0.85:
        return MasteryLevel.MASTERED
    elif score >= 0.65:
        return MasteryLevel.PROFICIENT
    elif score >= 0.40:
        return MasteryLevel.DEVELOPING
    elif score > 0:
        return MasteryLevel.BEGINNER
    return MasteryLevel.NOT_STARTED


def update_concept_mastery(
    concept_id: str,
    is_correct: bool,
    hints_used: int = 0,
) -> ConceptMastery:
    """Update mastery record for a concept after a quiz attempt."""
    _init_concepts()
    store = get_local_store()

    # Get or create mastery record
    mastery_data = store.get("mastery", concept_id)
    if mastery_data:
        mastery = ConceptMastery(**mastery_data)
    else:
        concept_data = store.get("concepts", concept_id)
        concept_name = concept_data["name"] if concept_data else concept_id
        mastery = ConceptMastery(concept_id=concept_id, concept_name=concept_name)

    # Update stats
    mastery.total_attempts += 1
    if is_correct:
        mastery.correct_attempts += 1
    mastery.hints_used += hints_used
    mastery.last_practiced = datetime.now(timezone.utc)

    # Recompute score
    mastery.mastery_score = _compute_mastery_score(
        mastery.correct_attempts, mastery.total_attempts, mastery.hints_used
    )
    mastery.level = _score_to_level(mastery.mastery_score)

    # Schedule next review (spaced repetition-inspired)
    if mastery.mastery_score >= 0.85:
        mastery.next_review = datetime.now(timezone.utc) + timedelta(days=7)
    elif mastery.mastery_score >= 0.5:
        mastery.next_review = datetime.now(timezone.utc) + timedelta(days=3)
    else:
        mastery.next_review = datetime.now(timezone.utc) + timedelta(days=1)

    store.insert("mastery", concept_id, mastery.model_dump())
    return mastery


def get_learning_progress() -> dict:
    """Get overall learning progress across all concepts."""
    _init_concepts()
    store = get_local_store()

    all_mastery = store.get_all("mastery")
    all_concepts = store.get_all("concepts")

    total_attempted = sum(m.get("total_attempts", 0) for m in all_mastery)
    total_correct = sum(m.get("correct_attempts", 0) for m in all_mastery)

    # Find weak concepts (below 0.4 mastery)
    weak = [m for m in all_mastery if m.get("mastery_score", 0) < 0.4 and m.get("total_attempts", 0) > 0]

    # Overall mastery
    scores = [m.get("mastery_score", 0) for m in all_mastery if m.get("total_attempts", 0) > 0]
    overall = sum(scores) / len(scores) if scores else 0.0

    # Revision suggestions
    now = datetime.now(timezone.utc)
    suggestions = []
    for m in all_mastery:
        next_review = m.get("next_review")
        if next_review:
            try:
                review_dt = datetime.fromisoformat(str(next_review))
                if review_dt <= now:
                    suggestions.append({
                        "concept_id": m["concept_id"],
                        "concept_name": m["concept_name"],
                        "mastery_score": m["mastery_score"],
                        "reason": "Due for review",
                    })
            except (ValueError, TypeError):
                pass

    return {
        "concepts": [ConceptMastery(**m) for m in all_mastery],
        "overall_mastery": round(overall, 3),
        "total_questions_attempted": total_attempted,
        "total_correct": total_correct,
        "weak_concepts": [m.get("concept_name", "") for m in weak],
        "revision_suggestions": suggestions,
    }


def get_revision_plan() -> dict:
    """Generate a revision plan based on mastery levels and prerequisites."""
    _init_concepts()
    store = get_local_store()

    all_concepts = store.get_all("concepts")
    all_mastery = {m["concept_id"]: m for m in store.get_all("mastery")}

    plan = []
    for concept in all_concepts:
        cid = concept["concept_id"]
        mastery = all_mastery.get(cid, {})
        score = mastery.get("mastery_score", 0)
        level = mastery.get("level", "not_started")

        # Check if prerequisites are met
        prereqs_met = True
        for prereq_id in concept.get("prerequisites", []):
            prereq_mastery = all_mastery.get(prereq_id, {})
            if prereq_mastery.get("mastery_score", 0) < 0.4:
                prereqs_met = False
                break

        action = "skip"
        if level == "not_started" and prereqs_met:
            action = "start"
        elif level in ("beginner", "developing"):
            action = "practice" if prereqs_met else "learn prerequisites first"
        elif level == "proficient":
            action = "review for mastery"

        plan.append({
            "concept_id": cid,
            "concept_name": concept["name"],
            "domain": concept.get("domain", ""),
            "current_level": level,
            "mastery_score": score,
            "prerequisites": concept.get("prerequisites", []),
            "prerequisites_met": prereqs_met,
            "recommended_action": action,
        })

    # Sort: incomplete prerequisites first, then by mastery score ascending
    plan.sort(key=lambda x: (x["prerequisites_met"], x["mastery_score"]))

    return {
        "plan": plan,
        "next_review_date": None,
    }
