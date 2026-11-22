from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.core.db import get_session
from app.schemas.health import HealthOut

router = APIRouter(tags=["health"])


@router.get("/health", operation_id="getHealth")
async def health(
    response: Response, session: Annotated[AsyncSession, Depends(get_session)]
) -> HealthOut:
    try:
        await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthOut(
        status="ok" if db_ok else "degraded",
        db="ok" if db_ok else "down",
        version=__version__,
    )
