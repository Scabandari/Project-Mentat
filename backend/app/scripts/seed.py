"""Idempotently seed the DB: default user + all content packs."""

import asyncio

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.content.loader import load_packs, upsert_pack
from app.core.db import SessionLocal, engine
from app.models import DEFAULT_USER_ID, User


async def seed_all(session: AsyncSession) -> None:
    await session.execute(
        insert(User)
        .values(id=DEFAULT_USER_ID, display_name="Ryan")
        .on_conflict_do_nothing(index_elements=[User.id])
    )
    for pdef in load_packs():
        await upsert_pack(session, pdef)
    await session.commit()


async def main() -> None:
    async with SessionLocal() as session:
        await seed_all(session)
    await engine.dispose()
    print("seed: ok")


if __name__ == "__main__":
    asyncio.run(main())
