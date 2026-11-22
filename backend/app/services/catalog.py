"""Packs and decks with per-user counts (due, new, mastery)."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Card, CardState, Deck, Pack, UserCardState
from app.schemas.study import DeckDetailOut, DeckOut, PackDetailOut, PackOut
from app.services.scheduling import MASTERY_STABILITY_DAYS
from app.services.study import daily_new_remaining

UNLOCK_MASTERY = 0.7


@dataclass
class _Counts:
    cards: int = 0
    due: int = 0
    new: int = 0
    mastered: int = 0


async def _deck_counts(
    session: AsyncSession, user_id: UUID, now: datetime, deck_ids: list[UUID]
) -> dict[UUID, _Counts]:
    s = UserCardState
    rows = await session.execute(
        select(
            Card.deck_id,
            func.count(Card.id),
            func.count(s.card_id).filter(s.due <= now),
            func.count(Card.id).filter(s.card_id.is_(None)),
            func.count(s.card_id).filter(
                and_(s.state == CardState.review, s.stability >= MASTERY_STABILITY_DAYS)
            ),
        )
        .outerjoin(s, and_(s.card_id == Card.id, s.user_id == user_id))
        .where(Card.deck_id.in_(deck_ids), Card.is_active.is_(True))
        .group_by(Card.deck_id)
    )
    return {deck_id: _Counts(*vals) for deck_id, *vals in rows.all()}


def _deck_out(deck: Deck, c: _Counts, prev_mastery: float | None) -> DeckOut:
    mastery = c.mastered / c.cards if c.cards else 0.0
    return DeckOut(
        id=deck.id,
        slug=deck.slug,
        name=deck.name,
        description=deck.description,
        section=deck.section,
        card_count=c.cards,
        due_count=c.due,
        new_count=c.new,
        mastery=round(mastery, 3),
        locked=prev_mastery is not None and prev_mastery < UNLOCK_MASTERY,
        has_lesson=bool(deck.lesson_md),
    )


async def _decks_out(
    session: AsyncSession, user_id: UUID, now: datetime, decks: list[Deck]
) -> list[DeckOut]:
    counts = await _deck_counts(session, user_id, now, [d.id for d in decks])
    by_id = {d.id: d for d in decks}
    out: list[DeckOut] = []
    mastery: dict[UUID, float] = {}
    for d in decks:
        c = counts.get(d.id, _Counts())
        mastery[d.id] = c.mastered / c.cards if c.cards else 0.0
    for d in decks:
        prev = mastery.get(d.unlock_after_deck_id) if d.unlock_after_deck_id in by_id else None
        out.append(_deck_out(d, counts.get(d.id, _Counts()), prev))
    return out


def _pack_out(pack: Pack, decks: list[DeckOut], new_remaining: int) -> PackOut:
    return PackOut(
        id=pack.id,
        slug=pack.slug,
        name=pack.name,
        description=pack.description,
        deck_count=len(decks),
        due_count=sum(d.due_count for d in decks),
        new_count=sum(d.new_count for d in decks),
        new_today=min(new_remaining, sum(d.new_count for d in decks)),
    )


async def _pack_decks(session: AsyncSession, pack_id: UUID) -> list[Deck]:
    return list(
        await session.scalars(select(Deck).where(Deck.pack_id == pack_id).order_by(Deck.position))
    )


async def list_packs(session: AsyncSession, user_id: UUID, now: datetime) -> list[PackOut]:
    packs = await session.scalars(select(Pack).order_by(Pack.name))
    remaining = await daily_new_remaining(session, user_id, now)
    return [
        _pack_out(
            p,
            await _decks_out(session, user_id, now, await _pack_decks(session, p.id)),
            remaining,
        )
        for p in packs
    ]


async def get_pack(session: AsyncSession, user_id: UUID, now: datetime, slug: str) -> PackDetailOut:
    pack = await session.scalar(select(Pack).where(Pack.slug == slug))
    if pack is None:
        raise HTTPException(404, f"Pack '{slug}' not found")
    decks = await _decks_out(session, user_id, now, await _pack_decks(session, pack.id))
    remaining = await daily_new_remaining(session, user_id, now)
    return PackDetailOut(**_pack_out(pack, decks, remaining).model_dump(), decks=decks)


async def get_deck(
    session: AsyncSession, user_id: UUID, now: datetime, deck_id: UUID
) -> DeckDetailOut:
    deck = await session.get(Deck, deck_id)
    if deck is None:
        raise HTTPException(404, "Deck not found")
    siblings = await _pack_decks(session, deck.pack_id)
    out = next(d for d in await _decks_out(session, user_id, now, siblings) if d.id == deck_id)
    return DeckDetailOut(**out.model_dump(), lesson_md=deck.lesson_md)
