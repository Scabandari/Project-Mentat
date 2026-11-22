"""Load and validate content packs from YAML, and upsert them into the DB by slug."""

from pathlib import Path
from typing import Any, Literal, Self

import yaml
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.generators.registry import is_registered
from app.models import AnswerType, Card, CardKind, Deck, Pack

CONTENT_DIR = Path(__file__).parent
Slug = str


class CardDef(BaseModel):
    slug: Slug = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    kind: Literal["static", "generator"]
    answer_type: Literal["bucket", "choice", "action", "flip"] = "flip"
    generator_key: str | None = None
    params: dict[str, Any] = {}
    front_md: str | None = None
    back_md: str | None = None
    target_ms: int = Field(gt=0, le=120_000)

    @model_validator(mode="after")
    def check_kind(self) -> Self:
        if self.kind == "static":
            if not (self.front_md and self.back_md):
                raise ValueError(f"{self.slug}: static cards need front_md and back_md")
            if self.answer_type != "flip":
                raise ValueError(f"{self.slug}: static cards are flip-only for now")
        elif not self.generator_key:
            raise ValueError(f"{self.slug}: generator cards need generator_key")
        return self


class DeckDef(BaseModel):
    slug: Slug
    section: int = Field(ge=0)
    name: str
    description: str = ""
    lesson_md: str | None = None
    cards: list[CardDef]

    @model_validator(mode="after")
    def unique_cards(self) -> Self:
        slugs = [c.slug for c in self.cards]
        dupes = {s for s in slugs if slugs.count(s) > 1}
        if dupes:
            raise ValueError(f"deck {self.slug}: duplicate card slugs {sorted(dupes)}")
        return self


class PackDef(BaseModel):
    slug: Slug
    name: str
    description: str = ""
    version: int = 1
    decks: list[DeckDef]

    @model_validator(mode="after")
    def unique_decks(self) -> Self:
        slugs = [d.slug for d in self.decks]
        if len(slugs) != len(set(slugs)):
            raise ValueError(f"pack {self.slug}: duplicate deck slugs")
        return self


def load_packs(root: Path = CONTENT_DIR) -> list[PackDef]:
    return [
        PackDef.model_validate(yaml.safe_load(p.read_text()))
        for p in sorted(root.glob("*/pack.yaml"))
    ]


async def upsert_pack(session: AsyncSession, pdef: PackDef) -> Pack:
    """Idempotent: match on slugs, update in place. Cards removed from YAML are deactivated,
    never deleted, so review history survives."""
    pack = await session.scalar(
        select(Pack)
        .where(Pack.slug == pdef.slug)
        .options(selectinload(Pack.decks).selectinload(Deck.cards))
    )
    if pack is None:
        pack = Pack(slug=pdef.slug, name=pdef.name, decks=[])
        session.add(pack)
    pack.name, pack.description, pack.version = pdef.name, pdef.description, pdef.version

    decks_by_slug = {d.slug: d for d in pack.decks}
    prev: Deck | None = None
    for pos, ddef in enumerate(pdef.decks):
        deck = decks_by_slug.get(ddef.slug)
        if deck is None:
            deck = Deck(
                slug=ddef.slug, section=ddef.section, position=pos, name=ddef.name, cards=[]
            )
            pack.decks.append(deck)
        deck.name, deck.description, deck.lesson_md = ddef.name, ddef.description, ddef.lesson_md
        deck.section, deck.position = ddef.section, pos
        await session.flush()
        deck.unlock_after_deck_id = prev.id if prev else None
        prev = deck

        cards_by_slug = {c.slug: c for c in deck.cards}
        seen: set[str] = set()
        for cpos, cdef in enumerate(ddef.cards):
            seen.add(cdef.slug)
            card = cards_by_slug.get(cdef.slug)
            if card is None:
                card = Card(slug=cdef.slug)
                deck.cards.append(card)
            card.kind = CardKind(cdef.kind)
            card.answer_type = AnswerType(cdef.answer_type)
            card.generator_key = cdef.generator_key
            card.params = cdef.params
            card.front_md, card.back_md = cdef.front_md, cdef.back_md
            card.target_ms = cdef.target_ms
            card.position = cpos
            card.is_active = cdef.kind == "static" or is_registered(cdef.generator_key or "")
        for slug, card in cards_by_slug.items():
            if slug not in seen:
                card.is_active = False

    await session.flush()
    return pack
