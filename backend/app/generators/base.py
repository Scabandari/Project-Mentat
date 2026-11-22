"""Generator contract, registry and answer builders.

A generator is a pure function of (rng, params, ctx) → Instance. Same seed + params + ctx
gives the same instance, so any bug report is reproducible from the stored seed.
"""

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from random import Random
from typing import Any, Literal

from app.generators.registry import REGISTRY

AnswerType = Literal["bucket", "choice", "action"]
Unit = Literal["percent", "count", "ratio", "chips"]
StakesFormat = Literal["live", "online"]


class GenerationError(RuntimeError):
    """A generator couldn't produce a valid instance (e.g. rejection sampling ran out)."""


@dataclass(frozen=True)
class GenContext:
    stakes_format: StakesFormat = "online"
    level: int = 1  # 1-3, from FSRS stability


@dataclass
class Instance:
    prompt: str
    answer_type: AnswerType
    correct: int | str  # bucket/choice id, or action
    explanation_md: str
    shortcut: str
    exact: float | str | None = None
    scene: dict[str, Any] | None = None
    unit: Unit | None = None
    buckets: list[dict[str, Any]] | None = None
    choices: list[dict[str, Any]] | None = None
    actions: list[str] | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.answer_type == "bucket":
            assert self.buckets and len(self.buckets) == 5 and self.unit
            assert any(b["id"] == self.correct for b in self.buckets)
        elif self.answer_type == "choice":
            assert self.choices and any(c["id"] == self.correct for c in self.choices)
            labels = [c["label"] for c in self.choices]
            assert len(labels) == len(set(labels)), f"duplicate choices: {labels}"
        else:
            assert self.actions and self.correct in self.actions


GeneratorFn = Callable[[Random, dict[str, Any], GenContext], Instance]


def register(key: str) -> Callable[[GeneratorFn], GeneratorFn]:
    def deco(fn: GeneratorFn) -> GeneratorFn:
        if key in REGISTRY:
            raise ValueError(f"generator '{key}' registered twice")
        REGISTRY[key] = fn
        return fn

    return deco


def generate(key: str, seed: int, params: dict[str, Any], ctx: GenContext) -> Instance:
    fn: GeneratorFn = REGISTRY[key]
    return fn(Random(seed), params, ctx)


def retry[T](rng: Random, attempt: Callable[[Random], T | None], tries: int = 2000) -> T:
    """Rejection sampling helper."""
    for _ in range(tries):
        out = attempt(rng)
        if out is not None:
            return out
    raise GenerationError("rejection sampling exhausted")


# ---------------------------------------------------------------- buckets
def make_buckets(
    rng: Random,
    exact: float,
    width: int,
    unit: Unit,
    lo_bound: float | None = None,
    hi_bound: float | None = None,
    label_fn: Callable[[int, int], str] | None = None,
    aligned: bool = False,
) -> tuple[list[dict[str, Any]], int]:
    """Five contiguous, equal-width buckets.

    width == 1: exact integer values (counts like outs or combos).
    width >= 2 (use even widths): the correct bucket is centred on round(exact), so the
    tolerance is ±width/2 and boundaries stay integers. The correct bucket lands in a random
    slot so position is never a tell; the set is then shifted to respect domain bounds and
    the correct id recomputed by containment.
    aligned=True puts boundaries on multiples of width instead (for money amounts).
    """
    c = round(exact)

    def first_for(slot: int) -> int:
        if width == 1:
            return c - slot
        if aligned:  # boundaries on multiples of width: cleaner labels for money amounts
            return math.floor(exact / width) * width - slot * width
        return c - width // 2 - slot * width

    def fits(first: int) -> bool:
        last_hi = first + 5 * width - (1 if width == 1 else 0)
        return (lo_bound is None or first >= lo_bound) and (hi_bound is None or last_hi <= hi_bound)

    # Pick uniformly among slots that keep all buckets in bounds, so no slot is favoured.
    feasible = [s for s in range(5) if fits(first_for(s))]
    if feasible:
        first = first_for(rng.choice(feasible))
    else:  # near a domain edge: pin the whole set against that edge
        span = 5 * width - (1 if width == 1 else 0)
        first = first_for(2)
        if hi_bound is not None:
            first = min(first, int(hi_bound - span))
        if lo_bound is not None:
            first = max(first, int(lo_bound))

    buckets: list[dict[str, Any]] = []
    correct_id = -1
    for i in range(5):
        lo = first + i * width
        hi = lo + width
        if width == 1:
            label, contains = str(lo), c == lo
        else:
            if label_fn:
                label = label_fn(lo, hi)
            else:
                label = f"{lo}–{hi}%" if unit == "percent" else f"{lo}–{hi}"
            contains = lo <= exact < hi or (i == 4 and exact == hi)
        if contains:
            correct_id = i
        buckets.append({"id": i, "label": label, "lo": lo, "hi": hi})
    if correct_id < 0:
        raise GenerationError(f"exact {exact} outside buckets {buckets}")
    return buckets, correct_id


def percent_width(level: int) -> int:
    return {1: 10, 2: 6}.get(level, 4)


# ---------------------------------------------------------------- choices
def make_choices(
    rng: Random, correct: str, distractors: Sequence[str], n: int = 5, shuffle: bool = True
) -> tuple[list[dict[str, Any]], int]:
    pool = [d for d in dict.fromkeys(distractors) if d != correct]
    picked = rng.sample(pool, min(n - 1, len(pool)))
    labels = [correct, *picked]
    if shuffle:
        rng.shuffle(labels)
    return [{"id": i, "label": lbl} for i, lbl in enumerate(labels)], labels.index(correct)


def ordered_choices(labels: Sequence[str], correct: str) -> tuple[list[dict[str, Any]], int]:
    """Fixed-order options (e.g. Hero / Villain / Split, Yes / No)."""
    return [{"id": i, "label": lbl} for i, lbl in enumerate(labels)], list(labels).index(correct)


def pct(x: float, digits: int = 1) -> str:
    return f"{x * 100:.{digits}f}".rstrip("0").rstrip(".") + "%"
