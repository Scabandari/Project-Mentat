"""Study sessions: queue selection, problem instances, grading, FSRS updates, summaries."""

import random
import statistics
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from pydantic import TypeAdapter
from sqlalchemy import Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AnswerType,
    Card,
    CardState,
    Deck,
    ProblemInstance,
    Review,
    StudyMode,
    StudySession,
    UserCardState,
)
from app.schemas.study import (
    AnswerIn,
    DeckStat,
    GradeOut,
    NextOut,
    ProblemOut,
    QueueCounts,
    SessionIn,
    SessionOut,
    SessionSummaryOut,
)
from app.services.scheduling import (
    LEARN_AHEAD_SECONDS,
    RATING_VALUE,
    RatingName,
    auto_rating,
    schedule,
    snapshot,
)
from app.services.settings import get_settings

LEARN_DEFAULT_NEW = 5
_problem_adapter: TypeAdapter[Any] = TypeAdapter(ProblemOut)


# ---------------------------------------------------------------- helpers
def _start_of_day_utc(now: datetime, tz: str) -> datetime:
    local = now.astimezone(ZoneInfo(tz))
    return local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(now.tzinfo)


async def daily_new_remaining(session: AsyncSession, user_id: UUID, now: datetime) -> int:
    settings = await get_settings(session, user_id)
    introduced = await session.scalar(
        select(func.count(Review.id)).where(
            Review.user_id == user_id,
            Review.counted_for_srs.is_(True),
            Review.state_before.is_(None),
            Review.created_at >= _start_of_day_utc(now, settings.timezone),
        )
    )
    return max(0, settings.daily_new_limit - (introduced or 0))


def _active_cards(deck_ids: list[UUID]) -> Select[Card]:
    return select(Card).where(Card.deck_id.in_(deck_ids), Card.is_active.is_(True))


def _with_state(q: Select[Card], user_id: UUID) -> Select[Card]:
    return q.join(
        UserCardState, and_(UserCardState.card_id == Card.id, UserCardState.user_id == user_id)
    )


def _without_state(q: Select[Card], user_id: UUID) -> Select[Card]:
    return q.outerjoin(
        UserCardState, and_(UserCardState.card_id == Card.id, UserCardState.user_id == user_id)
    ).where(UserCardState.card_id.is_(None))


async def _count(session: AsyncSession, q: Select[Card]) -> int:
    return (await session.scalar(select(func.count()).select_from(q.subquery()))) or 0


async def _get_session(session: AsyncSession, user_id: UUID, session_id: UUID) -> StudySession:
    s = await session.get(StudySession, session_id)
    if s is None or s.user_id != user_id:
        raise HTTPException(404, "Session not found")
    return s


async def _new_served(session: AsyncSession, s: StudySession) -> int:
    """New cards already *answered* in this session. The pending card still counts as
    remaining, so queue counts include the card on screen."""
    n = await session.scalar(
        select(func.count(ProblemInstance.id)).where(
            ProblemInstance.session_id == s.id,
            ProblemInstance.is_new.is_(True),
            ProblemInstance.answered_at.is_not(None),
        )
    )
    return n or 0


# ---------------------------------------------------------------- create
async def create_session(
    session: AsyncSession, user_id: UUID, now: datetime, body: SessionIn
) -> SessionOut:
    if body.deck_ids:
        found = set(await session.scalars(select(Deck.id).where(Deck.id.in_(body.deck_ids))))
        missing = set(body.deck_ids) - found
        if missing:
            raise HTTPException(404, f"Unknown deck ids: {sorted(map(str, missing))}")
        deck_ids = list(body.deck_ids)
    else:
        deck_ids = list(await session.scalars(select(Deck.id).order_by(Deck.position)))

    mode = StudyMode(body.mode)
    if mode is StudyMode.review:
        allowance = await daily_new_remaining(session, user_id, now)
        new_limit = min(body.new_limit if body.new_limit is not None else allowance, allowance)
    elif mode is StudyMode.learn:
        new_limit = body.new_limit if body.new_limit is not None else LEARN_DEFAULT_NEW
    else:
        new_limit = 0

    s = StudySession(
        user_id=user_id, mode=mode, deck_ids=deck_ids, new_limit=new_limit, started_at=now
    )
    session.add(s)
    await session.commit()
    q = await _queue_counts(session, user_id, now, s)
    return SessionOut(
        id=s.id,
        mode=s.mode.value,
        deck_ids=deck_ids,
        started_at=now,
        due_count=q.due,
        new_count=q.new,
    )


# ---------------------------------------------------------------- queue
async def _queue_counts(
    session: AsyncSession, user_id: UUID, now: datetime, s: StudySession
) -> QueueCounts:
    reviewed = (
        await session.scalar(select(func.count(Review.id)).where(Review.session_id == s.id))
    ) or 0
    if s.mode is StudyMode.drill:
        return QueueCounts(due=0, new=0, reviewed=reviewed)
    due = 0
    if s.mode is StudyMode.review:
        due = await _count(
            session,
            _with_state(_active_cards(s.deck_ids), user_id).where(UserCardState.due <= now),
        )
    available_new = await _count(session, _without_state(_active_cards(s.deck_ids), user_id))
    new = max(0, min(s.new_limit - await _new_served(session, s), available_new))
    return QueueCounts(due=due, new=new, reviewed=reviewed)


async def _pick_card(
    session: AsyncSession, user_id: UUID, now: datetime, s: StudySession
) -> tuple[Card, bool] | None:
    base = _active_cards(s.deck_ids)

    if s.mode is StudyMode.drill:
        last = await session.scalar(
            select(ProblemInstance.card_id)
            .where(ProblemInstance.session_id == s.id)
            .order_by(ProblemInstance.created_at.desc())
            .limit(1)
        )
        q = base.where(Card.id != last) if last else base
        card = await session.scalar(q.order_by(func.random()).limit(1))
        card = card or await session.scalar(base.limit(1))
        return (card, False) if card else None

    if s.mode is StudyMode.review:
        due = await session.scalar(
            _with_state(base, user_id)
            .where(UserCardState.due <= now)
            .order_by(UserCardState.due)
            .limit(1)
        )
        if due:
            return due, False

    if await _new_served(session, s) < s.new_limit:
        new = await session.scalar(
            _without_state(base, user_id)
            .join(Deck, Deck.id == Card.deck_id)
            .order_by(Deck.position, Card.position)
            .limit(1)
        )
        if new:
            return new, True

    ahead = await session.scalar(
        _with_state(base, user_id)
        .where(
            UserCardState.state.in_([CardState.learning, CardState.relearning]),
            UserCardState.due <= now + timedelta(seconds=LEARN_AHEAD_SECONDS),
        )
        .order_by(UserCardState.due)
        .limit(1)
    )
    return (ahead, False) if ahead else None


def _render_static(card: Card) -> tuple[dict[str, Any], dict[str, Any]]:
    return {"prompt": card.front_md or ""}, {"back_md": card.back_md or ""}


def _problem_out(inst: ProblemInstance, card: Card, deck_slug: str) -> Any:
    payload: dict[str, Any] = {
        "answer_type": card.answer_type.value,
        "instance_id": inst.id,
        "card_id": card.id,
        "deck_slug": deck_slug,
        "target_ms": card.target_ms,
        "is_new": inst.is_new,
        **inst.prompt,
    }
    if card.answer_type is AnswerType.flip:
        payload["back_md"] = inst.answer_key.get("back_md", "")
    if inst.choices is not None:
        payload["choices" if card.answer_type is AnswerType.choice else "buckets"] = inst.choices
    return _problem_adapter.validate_python(payload)


async def next_problem(
    session: AsyncSession, user_id: UUID, now: datetime, session_id: UUID
) -> NextOut:
    s = await _get_session(session, user_id, session_id)
    if s.ended_at is not None:
        raise HTTPException(409, "Session has ended")

    pending = await session.scalar(
        select(ProblemInstance).where(
            ProblemInstance.session_id == s.id, ProblemInstance.answered_at.is_(None)
        )
    )
    if pending is None:
        picked = await _pick_card(session, user_id, now, s)
        if picked is None:
            return NextOut(problem=None, queue=await _queue_counts(session, user_id, now, s))
        card, is_new = picked
        if card.kind.value != "static":
            raise HTTPException(501, f"Generator '{card.generator_key}' not implemented")
        prompt, key = _render_static(card)
        pending = ProblemInstance(
            created_at=now,
            user_id=user_id,
            card_id=card.id,
            session_id=s.id,
            seed=random.getrandbits(62),
            is_new=is_new,
            prompt=prompt,
            answer_key=key,
            choices=None,
        )
        session.add(pending)
        await session.commit()

    card = await session.get_one(Card, pending.card_id)
    deck = await session.get_one(Deck, card.deck_id)
    queue = await _queue_counts(session, user_id, now, s)
    return NextOut(problem=_problem_out(pending, card, deck.slug), queue=queue)


# ---------------------------------------------------------------- answer
async def answer(
    session: AsyncSession, user_id: UUID, now: datetime, instance_id: UUID, body: AnswerIn
) -> GradeOut:
    inst = await session.scalar(
        select(ProblemInstance).where(ProblemInstance.id == instance_id).with_for_update()
    )
    if inst is None or inst.user_id != user_id:
        raise HTTPException(404, "Problem not found")
    if inst.answered_at is not None:
        raise HTTPException(409, "Problem already answered")
    s = await _get_session(session, user_id, inst.session_id)
    if s.ended_at is not None:
        raise HTTPException(409, "Session has ended")
    card = await session.get_one(Card, inst.card_id)

    rating: RatingName
    is_correct: bool | None
    correct_response = inst.answer_key.get("response")
    if card.answer_type is AnswerType.flip:
        if body.self_rating is None:
            raise HTTPException(422, "Flip cards require self_rating")
        rating, is_correct = body.self_rating, None
    else:
        if body.response is None:
            raise HTTPException(422, "This card requires a response")
        is_correct = body.response == correct_response
        rating = auto_rating(is_correct, body.latency_ms, card.target_ms)

    counted = s.mode is not StudyMode.drill
    row = await session.scalar(
        select(UserCardState)
        .where(UserCardState.user_id == user_id, UserCardState.card_id == card.id)
        .with_for_update()
    )
    before = snapshot(row)
    next_due: datetime | None = None
    if counted:
        result = schedule(row, rating, now)
        if row is None:
            row = UserCardState(user_id=user_id, card_id=card.id, reps=0, lapses=0, level=1)
            session.add(row)
        elif row.state is CardState.review and rating == "again":
            row.lapses += 1
        row.state, row.step = result.state, result.step
        row.stability, row.difficulty = result.stability, result.difficulty
        row.due, row.last_review = result.due, result.last_review
        row.reps += 1
        next_due = result.due

    session.add(
        Review(
            user_id=user_id,
            card_id=card.id,
            instance_id=inst.id,
            session_id=s.id,
            response={"response": body.response, "self_rating": body.self_rating},
            is_correct=is_correct if is_correct is not None else rating != "again",
            rating=RATING_VALUE[rating],
            latency_ms=body.latency_ms,
            counted_for_srs=counted,
            state_before=before,
            state_after=snapshot(row) if counted else before,
            created_at=now,
        )
    )
    inst.answered_at = now
    await session.commit()

    return GradeOut(
        instance_id=inst.id,
        is_correct=is_correct,
        rating=rating,
        correct_response=correct_response,
        exact_answer=inst.answer_key.get("exact"),
        back_md=inst.answer_key.get("back_md"),
        shortcut=inst.answer_key.get("shortcut", ""),
        explanation_md=inst.answer_key.get("explanation_md", ""),
        latency_ms=body.latency_ms,
        target_ms=card.target_ms,
        next_due=next_due,
    )


# ---------------------------------------------------------------- end
async def end_session(
    session: AsyncSession, user_id: UUID, now: datetime, session_id: UUID
) -> SessionSummaryOut:
    s = await _get_session(session, user_id, session_id)
    if s.ended_at is None:
        s.ended_at = now
        await session.commit()

    rows = (
        await session.execute(
            select(Deck.id, Deck.name, Review.is_correct, Review.latency_ms)
            .join(Card, Card.id == Review.card_id)
            .join(Deck, Deck.id == Card.deck_id)
            .where(Review.session_id == s.id)
            .order_by(Deck.position)
        )
    ).all()

    by_deck: dict[UUID, list[tuple[str, bool, int]]] = {}
    for deck_id, name, ok, lat in rows:
        by_deck.setdefault(deck_id, []).append((name, bool(ok), lat))

    def stat(items: list[tuple[str, bool, int]]) -> tuple[int, int, float, int]:
        n = len(items)
        correct = sum(1 for _, ok, _ in items if ok)
        median = int(statistics.median(lat for *_, lat in items)) if items else 0
        return n, correct, (correct / n if n else 0.0), median

    all_items = [i for items in by_deck.values() for i in items]
    n, correct, acc, median = stat(all_items)
    return SessionSummaryOut(
        session_id=s.id,
        mode=s.mode.value,
        reviewed=n,
        correct=correct,
        accuracy=round(acc, 3),
        median_latency_ms=median,
        duration_s=int(((s.ended_at or now) - s.started_at).total_seconds()),
        by_deck=[
            DeckStat(
                deck_id=deck_id,
                deck_name=items[0][0],
                reviews=stat(items)[0],
                accuracy=round(stat(items)[2], 3),
                median_latency_ms=stat(items)[3],
            )
            for deck_id, items in by_deck.items()
        ],
    )
