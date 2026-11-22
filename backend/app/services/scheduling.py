"""FSRS wrapper. The only module that knows about the `fsrs` library."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

import fsrs

from app.models import CardState, UserCardState

RatingName = Literal["again", "hard", "good", "easy"]
RATING_VALUE: dict[RatingName, int] = {"again": 1, "hard": 2, "good": 3, "easy": 4}
RATING_NAME: dict[int, RatingName] = {v: k for k, v in RATING_VALUE.items()}

# A card counts as "mastered" once FSRS expects to retain it for at least this many days.
MASTERY_STABILITY_DAYS = 7.0
# In review mode, learning cards due within this window are shown early instead of ending.
LEARN_AHEAD_SECONDS = 20 * 60

SCHEDULER = fsrs.Scheduler(desired_retention=0.9, enable_fuzzing=True)

_TO_FSRS = {
    CardState.learning: fsrs.State.Learning,
    CardState.review: fsrs.State.Review,
    CardState.relearning: fsrs.State.Relearning,
}
_FROM_FSRS = {v: k for k, v in _TO_FSRS.items()}


@dataclass(frozen=True)
class ScheduleResult:
    state: CardState
    step: int | None
    stability: float | None
    difficulty: float | None
    due: datetime
    last_review: datetime | None


def snapshot(row: UserCardState | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "state": row.state.value,
        "step": row.step,
        "stability": row.stability,
        "difficulty": row.difficulty,
        "due": row.due.isoformat(),
        "last_review": row.last_review.isoformat() if row.last_review else None,
        "reps": row.reps,
        "lapses": row.lapses,
    }


def schedule(row: UserCardState | None, rating: RatingName, now: datetime) -> ScheduleResult:
    if row is None:
        card = fsrs.Card(due=now)
    else:
        card = fsrs.Card(
            state=_TO_FSRS[row.state],
            step=row.step,
            stability=row.stability,
            difficulty=row.difficulty,
            due=row.due,
            last_review=row.last_review,
        )
    updated, _ = SCHEDULER.review_card(card, fsrs.Rating(RATING_VALUE[rating]), now)
    return ScheduleResult(
        state=_FROM_FSRS[updated.state],
        step=updated.step,
        stability=updated.stability,
        difficulty=updated.difficulty,
        due=updated.due,
        last_review=updated.last_review,
    )


def auto_rating(is_correct: bool, latency_ms: int, target_ms: int) -> RatingName:
    """Rating for auto-graded answers: wrong → again; speed decides hard/good/easy."""
    if not is_correct:
        return "again"
    if latency_ms <= target_ms * 0.5:
        return "easy"
    if latency_ms <= target_ms * 2:
        return "good"
    return "hard"
