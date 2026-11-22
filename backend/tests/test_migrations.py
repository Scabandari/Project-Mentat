import asyncio

from alembic import command
from alembic.config import Config

from tests.conftest import ALEMBIC_INI, _seed


def test_migrations_roundtrip() -> None:
    cfg = Config(str(ALEMBIC_INI))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    asyncio.run(_seed())  # restore content for tests that run after this one
