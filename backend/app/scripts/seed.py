"""Idempotently seed the DB. M0: default user only. Content packs arrive in M1."""

import asyncio

from sqlalchemy.dialects.postgresql import insert

from app.core.db import SessionLocal, engine
from app.models import DEFAULT_USER_ID, User


async def seed() -> None:
    async with SessionLocal() as session:
        stmt = (
            insert(User)
            .values(id=DEFAULT_USER_ID, display_name="Ryan")
            .on_conflict_do_nothing(index_elements=[User.id])
        )
        await session.execute(stmt)
        await session.commit()
    await engine.dispose()
    print("seed: ok")


if __name__ == "__main__":
    asyncio.run(seed())
