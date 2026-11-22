from typing import Any
from uuid import UUID

from fastapi import HTTPException
from langchain_core.language_models import BaseChatModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.generators.cards import pretty
from app.llm.tutor import explain
from app.models import ProblemInstance, Review
from app.schemas.study import TutorIn, TutorOut


def _label(choices: list[dict[str, Any]] | None, value: Any) -> str:
    if value is None:
        return "(no answer)"
    if choices:
        for c in choices:
            if c["id"] == value:
                return str(c["label"])
    return str(value)


def _scene_text(scene: dict[str, Any] | None) -> str:
    if not scene:
        return ""
    parts = []
    for key, name in (("hero", "Hero"), ("villain", "Villain"), ("board", "Board")):
        if scene.get(key):
            parts.append(f"{name}: {pretty(scene[key])}")
    return "Cards: " + "; ".join(parts) if parts else ""


async def tutor(
    session: AsyncSession,
    model: BaseChatModel | None,
    user_id: UUID,
    instance_id: UUID,
    body: TutorIn,
) -> TutorOut:
    if model is None:
        raise HTTPException(503, "Tutor is not configured (set ANTHROPIC_API_KEY)")
    inst = await session.get(ProblemInstance, instance_id)
    if inst is None or inst.user_id != user_id:
        raise HTTPException(404, "Problem not found")
    review = await session.scalar(select(Review).where(Review.instance_id == inst.id))
    if review is None:
        # Never explain before the answer: it would leak the key.
        raise HTTPException(409, "Answer the problem first")

    key = inst.answer_key
    if "back_md" in key:  # flip card
        correct, student = key["back_md"], "(self-graded)"
        verdict = "self-graded flashcard"
    else:
        correct = _label(inst.choices, key.get("response"))
        student = _label(inst.choices, review.response.get("response"))
        verdict = "student was correct" if review.is_correct else "student was wrong"
    try:
        text = await explain(
            model,
            prompt=str(inst.prompt.get("prompt", "")),
            scene=_scene_text(inst.prompt.get("scene")),
            student_answer=student,
            correct_answer=correct,
            verdict=verdict,
            explanation=str(key.get("explanation_md") or key.get("back_md") or ""),
            question=body.question,
        )
    except Exception as e:  # provider errors shouldn't 500 the study flow
        raise HTTPException(502, f"Tutor unavailable: {type(e).__name__}") from e
    return TutorOut(message_md=text.strip())
