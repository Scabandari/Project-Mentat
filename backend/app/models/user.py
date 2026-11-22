from typing import Any
from uuid import UUID

from sqlalchemy import String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamped, UUIDPk

# Single-user mode (v1): every user-owned row points at this user until auth ships.
DEFAULT_USER_ID = UUID("00000000-0000-7000-8000-000000000001")


class User(UUIDPk, Timestamped, Base):
    __tablename__ = "users"

    email: Mapped[str | None] = mapped_column(String(320), unique=True)
    display_name: Mapped[str] = mapped_column(String(100))
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
