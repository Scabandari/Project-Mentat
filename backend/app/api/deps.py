from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models import DEFAULT_USER_ID


def get_user_id() -> UUID:
    """Single-user mode. Replaced by real auth later; every route already depends on this."""
    return DEFAULT_USER_ID


def get_now() -> datetime:
    """Injectable clock so tests can time-travel."""
    return datetime.now(UTC)


DB = Annotated[AsyncSession, Depends(get_session)]
UserId = Annotated[UUID, Depends(get_user_id)]
Now = Annotated[datetime, Depends(get_now)]
