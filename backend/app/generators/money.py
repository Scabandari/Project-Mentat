"""Live vs. online presentation of pots and bets. Same math, different numbers on screen.

Live: dollars at a real stake, rounded to $5 chips, deliberately uneven sizes.
Online: big blinds, bets as standard pot fractions.
"""

from dataclasses import dataclass
from random import Random
from typing import Any

from app.generators.base import GenContext, make_buckets

ONLINE_FRACTIONS = (0.33, 0.5, 0.66, 0.75, 1.0, 1.25, 1.5, 2.0)
ONLINE_FRACTIONS_L1 = (0.33, 0.5, 0.75, 1.0)
LIVE_STAKES = ((1, 2), (2, 5), (5, 10))


@dataclass(frozen=True)
class Spot:
    pot: float  # before the bet
    bet: float
    fmt: str  # "live" | "online"
    stake: tuple[int, int] | None = None

    def money(self, x: float) -> str:
        if self.fmt == "live":
            return f"${x:,.0f}"
        return f"{x:g}bb"

    @property
    def stake_label(self) -> str:
        return f"${self.stake[0]}/{self.stake[1]}" if self.stake else "100bb deep"

    @property
    def fraction(self) -> float:
        return self.bet / self.pot

    def bet_phrase(self) -> str:
        if self.fmt == "online":
            return f"bets {round(self.fraction * 100)}% pot ({self.money(self.bet)})"
        return f"bets {self.money(self.bet)}"


def _round_to(x: float, step: float) -> float:
    return max(step, round(x / step) * step)


def make_spot(rng: Random, ctx: GenContext, min_frac: float = 0.25, max_frac: float = 1.5) -> Spot:
    if ctx.stakes_format == "online":
        fracs = [f for f in (ONLINE_FRACTIONS_L1 if ctx.level == 1 else ONLINE_FRACTIONS)
                 if min_frac <= f <= max_frac] or [0.5]  # fmt: skip
        frac = rng.choice(fracs)
        pot = (
            rng.choice([4, 6, 8, 10, 12, 15, 20, 24, 30, 40])
            if ctx.level == 1
            else _round_to(rng.uniform(4, 60), 0.5)
        )
        bet = _round_to(pot * frac, 0.5)
        return Spot(pot=pot, bet=bet, fmt="online")

    sb, bb = rng.choice(LIVE_STAKES)
    step = 5 if bb <= 5 else 10
    pot = _round_to(rng.uniform(10, 60) * bb / 2, step)
    if ctx.level == 1:
        frac = rng.choice([1 / 3, 0.5, 0.75, 1.0])
        frac = min(max(frac, min_frac), max_frac)
    else:
        frac = rng.uniform(min_frac, max_frac)
    bet = _round_to(pot * frac, step)
    return Spot(pot=pot, bet=bet, fmt="live", stake=(sb, bb))


NICE_STEPS = (1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 5000)


def fmt_money(x: float, fmt: str) -> str:
    sign = "−" if x < 0 else ""
    if fmt == "live":
        return f"{sign}${abs(x):,.0f}"
    return f"{sign}{abs(x):g}bb"


def money_buckets(
    rng: Random, exact: float, scale: float, ctx: GenContext, lo_bound: float | None = None
) -> tuple[list[dict[str, Any]], int]:
    """Buckets for amounts ($ or bb). Width is a 'nice' step sized to the problem: about
    25% / 15% / 10% of max(|answer|, scale) by level. `scale` (usually the pot) keeps
    answers near zero, like a breakeven EV, from getting absurdly narrow buckets."""
    exact = round(exact, 1)  # bucket the value we display, so the two always agree
    frac = {1: 0.25, 2: 0.15}.get(ctx.level, 0.1)
    target = max(abs(exact), scale) * frac
    # Never width 1: make_buckets reserves that for exact integer counts.
    width = next((n for n in NICE_STEPS if n >= target and n > 1), NICE_STEPS[-1])
    fmt = ctx.stakes_format

    def label(lo: int, hi: int) -> str:
        if lo < 0 < hi or hi <= 0:
            return f"{fmt_money(lo, fmt)} to {fmt_money(hi, fmt)}"
        if fmt == "live":
            return f"${lo:,}–{hi:,}"
        return f"{lo}–{hi}bb"

    return make_buckets(rng, exact, width, "chips", lo_bound=lo_bound, label_fn=label, aligned=True)


def make_stacks(rng: Random, ctx: GenContext, spot: Spot, lo_mult: float, hi_mult: float) -> float:
    """An effective stack behind, as a multiple of the pot, rounded like the spot's money."""
    raw = spot.pot * rng.uniform(lo_mult, hi_mult)
    step = 0.5 if spot.fmt == "online" else (5 if (spot.stake and spot.stake[1] <= 5) else 10)
    return _round_to(raw, step)
