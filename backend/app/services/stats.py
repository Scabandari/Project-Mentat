"""Progress stats. All day boundaries are in the user's timezone."""

import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Card, CardKind, CardState, Deck, Review, UserCardState
from app.schemas.study import (
    CardStatRow,
    DayStat,
    DeckStatRow,
    DeckStatsOut,
    StatsOverviewOut,
)
from app.services.scheduling import MASTERY_STABILITY_DAYS
from app.services.settings import get_settings

WEAK_MIN_REVIEWS = 5


def _median(xs: list[int]) -> int | None:
    return int(statistics.median(xs)) if xs else None


async def overview(session: AsyncSession, user_id: UUID, now: datetime) -> StatsOverviewOut:
    tz = ZoneInfo((await get_settings(session, user_id)).timezone)
    today = now.astimezone(tz).date()
    since = datetime.combine(today - timedelta(days=29), datetime.min.time(), tz)

    rows = (
        await session.execute(
            select(
                Review.created_at,
                Review.is_correct,
                Review.latency_ms,
                Card.target_ms,
                Deck.id,
                Deck.name,
                Deck.section,
            )
            .join(Card, Card.id == Review.card_id)
            .join(Deck, Deck.id == Card.deck_id)
            .where(Review.user_id == user_id, Review.created_at >= since)
        )
    ).all()

    by_day: dict[str, list[bool]] = defaultdict(list)
    last7: list[tuple[bool, int]] = []
    by_deck: dict[UUID, list[tuple[bool, int, int]]] = defaultdict(list)
    names: dict[UUID, tuple[str, int]] = {}
    for created, ok, latency, target, deck_id, deck_name, section in rows:
        day = created.astimezone(tz).date()
        by_day[day.isoformat()].append(bool(ok))
        if (today - day).days < 7:
            last7.append((bool(ok), latency))
        by_deck[deck_id].append((bool(ok), latency, target))
        names[deck_id] = (deck_name, section)

    # Streak: consecutive days with reviews, ending today (or yesterday if none yet today).
    streak, day = 0, today if by_day.get(today.isoformat()) else today - timedelta(days=1)
    while by_day.get(day.isoformat()):
        streak += 1
        day -= timedelta(days=1)

    daily = [
        DayStat(date=d, reviews=len(by_day.get(d, [])), correct=sum(by_day.get(d, [])))
        for d in ((today - timedelta(days=i)).isoformat() for i in range(13, -1, -1))
    ]

    mastery = await _deck_mastery(session, user_id, list(by_deck))
    decks = sorted(
        (
            DeckStatRow(
                deck_id=deck_id,
                deck_name=names[deck_id][0],
                section=names[deck_id][1],
                reviews=len(items),
                accuracy=round(sum(ok for ok, _, _ in items) / len(items), 3),
                median_latency_ms=_median([lat for _, lat, _ in items]) or 0,
                on_time=round(sum(lat <= tgt for _, lat, tgt in items) / len(items), 3),
                mastery=mastery.get(deck_id, 0.0),
            )
            for deck_id, items in by_deck.items()
        ),
        key=lambda d: d.section,
    )
    weakest = sorted(
        (d for d in decks if d.reviews >= WEAK_MIN_REVIEWS),
        key=lambda d: d.accuracy * 0.7 + d.on_time * 0.3,
    )[:3]

    due_now = await session.scalar(
        select(func.count())
        .select_from(UserCardState)
        .join(Card, Card.id == UserCardState.card_id)
        .where(UserCardState.user_id == user_id, UserCardState.due <= now, Card.is_active.is_(True))
    )
    return StatsOverviewOut(
        streak_days=streak,
        reviews_today=len(by_day.get(today.isoformat(), [])),
        due_now=due_now or 0,
        reviews_7d=len(last7),
        accuracy_7d=round(sum(ok for ok, _ in last7) / len(last7), 3) if last7 else None,
        median_latency_ms_7d=_median([lat for _, lat in last7]),
        daily=daily,
        decks=decks,
        weakest=weakest,
    )


async def _deck_mastery(
    session: AsyncSession, user_id: UUID, deck_ids: list[UUID]
) -> dict[UUID, float]:
    if not deck_ids:
        return {}
    s = UserCardState
    rows = await session.execute(
        select(
            Card.deck_id,
            func.count(Card.id),
            func.count(s.card_id).filter(
                and_(s.state == CardState.review, s.stability >= MASTERY_STABILITY_DAYS)
            ),
        )
        .outerjoin(s, and_(s.card_id == Card.id, s.user_id == user_id))
        .where(Card.deck_id.in_(deck_ids), Card.is_active.is_(True))
        .group_by(Card.deck_id)
    )
    return {d: round(m / n, 3) if n else 0.0 for d, n, m in rows.all()}


def _card_label(card: Card) -> str:
    if card.kind is CardKind.static and card.front_md:
        text = card.front_md.replace("**", "").strip()
        return text if len(text) <= 80 else text[:77] + "…"
    return card.slug.replace("-", " ").capitalize()


async def deck_stats(session: AsyncSession, user_id: UUID, deck_id: UUID) -> DeckStatsOut:
    deck = await session.get(Deck, deck_id)
    if deck is None:
        raise HTTPException(404, "Deck not found")
    cards = list(
        await session.scalars(
            select(Card)
            .where(Card.deck_id == deck_id, Card.is_active.is_(True))
            .order_by(Card.position)
        )
    )
    states = {
        st.card_id: st
        for st in await session.scalars(
            select(UserCardState).where(
                UserCardState.user_id == user_id,
                UserCardState.card_id.in_([c.id for c in cards]),
            )
        )
    }
    reviews: dict[UUID, list[tuple[bool, int]]] = defaultdict(list)
    for card_id, ok, lat in await session.execute(
        select(Review.card_id, Review.is_correct, Review.latency_ms).where(
            Review.user_id == user_id, Review.card_id.in_([c.id for c in cards])
        )
    ):
        reviews[card_id].append((bool(ok), lat))

    rows = []
    for c in cards:
        items = reviews.get(c.id, [])
        st = states.get(c.id)
        rows.append(
            CardStatRow(
                card_id=c.id,
                slug=c.slug,
                label=_card_label(c),
                answer_type=c.answer_type.value,
                reviews=len(items),
                accuracy=round(sum(ok for ok, _ in items) / len(items), 3) if items else None,
                median_latency_ms=_median([lat for _, lat in items]),
                target_ms=c.target_ms,
                state=st.state.value if st else "new",
                due=st.due if st else None,
                stability_days=round(st.stability, 1) if st and st.stability else None,
            )
        )
    return DeckStatsOut(deck_id=deck.id, deck_name=deck.name, cards=rows)
