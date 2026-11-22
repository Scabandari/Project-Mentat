"""Test setup: points the app at `<db>_test`, creates it if needed, migrates to head."""

import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import asyncpg  # type: ignore[import-untyped]
import httpx
import pytest
from sqlalchemy.engine import make_url

BASE_URL = make_url(
    os.environ.get("DATABASE_URL", "postgresql+asyncpg://mentat:mentat@localhost:5432/mentat")
)
_DB = BASE_URL.database or "mentat"
TEST_DB = _DB if _DB.endswith("_test") else f"{_DB}_test"
TEST_URL = BASE_URL.set(database=TEST_DB)

os.environ["DATABASE_URL"] = TEST_URL.render_as_string(hide_password=False)
os.environ["APP_ENV"] = "test"

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


async def _ensure_database() -> None:
    conn = await asyncpg.connect(
        user=BASE_URL.username,
        password=BASE_URL.password,
        host=BASE_URL.host,
        port=BASE_URL.port or 5432,
        database="postgres",
    )
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", TEST_DB)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{TEST_DB}"')
    finally:
        await conn.close()


def _alembic(*args: str) -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(ALEMBIC_INI))
    getattr(command, args[0])(cfg, *args[1:])


async def _seed() -> None:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.scripts.seed import seed_all

    # Own engine: this runs outside the test event loop.
    engine = create_async_engine(os.environ["DATABASE_URL"])
    async with async_sessionmaker(engine)() as session:
        await seed_all(session)
    await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def database() -> Iterator[None]:
    asyncio.run(_ensure_database())
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")
    asyncio.run(_seed())
    yield


@pytest.fixture(autouse=True)
async def clean_user_data() -> AsyncIterator[None]:
    from sqlalchemy import text

    from app.core.db import SessionLocal

    async with SessionLocal() as session:
        await session.execute(
            text("TRUNCATE reviews, problem_instances, study_sessions, user_card_states CASCADE")
        )
        await session.execute(text("UPDATE users SET settings = '{}'::jsonb"))
        await session.commit()
    yield


@dataclass
class Clock:
    now: datetime = field(default_factory=lambda: datetime(2026, 11, 21, 15, 0, tzinfo=UTC))

    def advance(self, **kw: float) -> None:
        self.now += timedelta(**kw)


@pytest.fixture
def clock() -> Iterator[Clock]:
    from app.api.deps import get_now
    from app.main import app

    c = Clock()
    app.dependency_overrides[get_now] = lambda: c.now
    yield c
    app.dependency_overrides.pop(get_now, None)


@pytest.fixture
async def client(clock: Clock) -> AsyncIterator[httpx.AsyncClient]:
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
