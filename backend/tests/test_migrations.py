from alembic import command
from alembic.config import Config

from tests.conftest import ALEMBIC_INI


def test_migrations_roundtrip() -> None:
    cfg = Config(str(ALEMBIC_INI))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
