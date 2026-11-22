from datetime import UTC, datetime

from app.models import CardState, UserCardState
from app.services.scheduling import auto_rating, schedule

NOW = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)


def test_auto_rating_bands() -> None:
    assert auto_rating(False, 100, 10_000) == "again"
    assert auto_rating(True, 4_000, 10_000) == "easy"
    assert auto_rating(True, 10_000, 10_000) == "good"
    assert auto_rating(True, 20_000, 10_000) == "good"
    assert auto_rating(True, 20_001, 10_000) == "hard"


def test_new_card_again_stays_in_learning_soon() -> None:
    r = schedule(None, "again", NOW)
    assert r.state is CardState.learning
    assert (r.due - NOW).total_seconds() <= 600


def test_new_card_easy_graduates() -> None:
    r = schedule(None, "easy", NOW)
    assert r.state is CardState.review
    assert (r.due - NOW).days >= 1


def test_lapse_from_review_goes_to_relearning() -> None:
    first = schedule(None, "easy", NOW)
    row = UserCardState(
        state=first.state,
        step=first.step,
        stability=first.stability,
        difficulty=first.difficulty,
        due=first.due,
        last_review=first.last_review,
    )
    r = schedule(row, "again", first.due)
    assert r.state is CardState.relearning
