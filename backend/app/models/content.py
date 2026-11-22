from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, Timestamped, UUIDPk
from app.models.enums import AnswerType, CardKind, str_enum


class Updated:
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Pack(UUIDPk, Timestamped, Updated, Base):
    __tablename__ = "packs"

    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, server_default="")
    version: Mapped[int] = mapped_column(Integer, server_default="1")

    decks: Mapped[list["Deck"]] = relationship(
        back_populates="pack", order_by="Deck.position", cascade="all, delete-orphan"
    )


class Deck(UUIDPk, Timestamped, Updated, Base):
    __tablename__ = "decks"
    __table_args__ = (UniqueConstraint("pack_id", "slug"),)

    pack_id: Mapped[UUID] = mapped_column(ForeignKey("packs.id", ondelete="CASCADE"), index=True)
    slug: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, server_default="")
    lesson_md: Mapped[str | None] = mapped_column(Text)
    section: Mapped[int] = mapped_column(SmallInteger)
    position: Mapped[int] = mapped_column(SmallInteger)
    unlock_after_deck_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("decks.id", ondelete="SET NULL")
    )

    pack: Mapped[Pack] = relationship(back_populates="decks")
    cards: Mapped[list["Card"]] = relationship(
        back_populates="deck", order_by="Card.position", cascade="all, delete-orphan"
    )


class Card(UUIDPk, Timestamped, Updated, Base):
    __tablename__ = "cards"
    __table_args__ = (UniqueConstraint("deck_id", "slug"),)

    deck_id: Mapped[UUID] = mapped_column(ForeignKey("decks.id", ondelete="CASCADE"), index=True)
    slug: Mapped[str] = mapped_column(String(64))
    kind: Mapped[CardKind] = mapped_column(str_enum(CardKind, "card_kind"))
    answer_type: Mapped[AnswerType] = mapped_column(str_enum(AnswerType, "answer_type"))
    generator_key: Mapped[str | None] = mapped_column(String(64))
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    front_md: Mapped[str | None] = mapped_column(Text)
    back_md: Mapped[str | None] = mapped_column(Text)
    target_ms: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")
    position: Mapped[int] = mapped_column(SmallInteger)

    deck: Mapped[Deck] = relationship(back_populates="cards")
