"""Generator registry. Generators register themselves here; cards whose generator_key is not
registered are seeded inactive. Populated in M2."""

from typing import Any

REGISTRY: dict[str, Any] = {}


def is_registered(key: str) -> bool:
    return key in REGISTRY
