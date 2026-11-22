from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.schemas.study import SettingsIn, SettingsOut


async def _user(session: AsyncSession, user_id: UUID) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    return user


async def get_settings(session: AsyncSession, user_id: UUID) -> SettingsOut:
    user = await _user(session, user_id)
    return SettingsOut.model_validate({**SettingsOut().model_dump(), **(user.settings or {})})


async def update_settings(session: AsyncSession, user_id: UUID, patch: SettingsIn) -> SettingsOut:
    if patch.timezone is not None:
        try:
            ZoneInfo(patch.timezone)
        except (ZoneInfoNotFoundError, ValueError) as e:
            raise HTTPException(422, f"Unknown timezone: {patch.timezone}") from e
    user = await _user(session, user_id)
    current = await get_settings(session, user_id)
    merged = current.model_copy(update=patch.model_dump(exclude_none=True))
    user.settings = merged.model_dump()
    await session.commit()
    return merged
