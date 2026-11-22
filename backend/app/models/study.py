from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamped, UUIDPk
from app.models.enums import CardState, StudyMode, str_enum


class UserCardState(Base):
    """FSRS state per user x card. No row = the card is new to this user."""

    __tablename__ = "user_card_states"
    __table_args__ = (Index("ix_user_card_states_user_due", "user_id", "due"),)

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    card_id: Mapped[UUID] = mapped_column(
        ForeignKey("cards.id", ondelete="CASCADE"), primary_key=True
    )
    state: Mapped[CardState] = mapped_column(str_enum(CardState, "card_state"))
    step: Mapped[int | None] = mapped_column(SmallInteger)
    stability: Mapped[float | None] = mapped_column(Float)
    difficulty: Mapped[float | None] = mapped_column(Float)
    due: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_review: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reps: Mapped[int] = mapped_column(Integer, server_default="0")
    lapses: Mapped[int] = mapped_column(Integer, server_default="0")
    level: Mapped[int] = mapped_column(SmallInteger, server_default="1")


class StudySession(UUIDPk, Base):
    __tablename__ = "study_sessions"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    mode: Mapped[StudyMode] = mapped_column(str_enum(StudyMode, "study_mode"))
    deck_ids: Mapped[list[UUID]] = mapped_column(ARRAY(PG_UUID(as_uuid=True)))
    new_limit: Mapped[int] = mapped_column(SmallInteger)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProblemInstance(UUIDPk, Timestamped, Base):
    __tablename__ = "problem_instances"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    card_id: Mapped[UUID] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("study_sessions.id", ondelete="CASCADE"), index=True
    )
    seed: Mapped[int] = mapped_column(BigInteger)
    is_new: Mapped[bool] = mapped_column(Boolean)
    prompt: Mapped[dict[str, Any]] = mapped_column(JSONB)
    answer_key: Mapped[dict[str, Any]] = mapped_column(JSONB)
    choices: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB(none_as_null=True))
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Review(UUIDPk, Timestamped, Base):
    __tablename__ = "reviews"
    __table_args__ = (
        Index("ix_reviews_user_created", "user_id", "created_at"),
        Index("ix_reviews_card_created", "card_id", "created_at"),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    card_id: Mapped[UUID] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"))
    instance_id: Mapped[UUID] = mapped_column(
        ForeignKey("problem_instances.id", ondelete="CASCADE"), unique=True
    )
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("study_sessions.id", ondelete="CASCADE"), index=True
    )
    response: Mapped[dict[str, Any]] = mapped_column(JSONB)
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    rating: Mapped[int] = mapped_column(SmallInteger)
    latency_ms: Mapped[int] = mapped_column(Integer)
    counted_for_srs: Mapped[bool] = mapped_column(Boolean)
    # none_as_null: store Python None as SQL NULL (not JSON 'null') so IS NULL works.
    state_before: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    state_after: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
