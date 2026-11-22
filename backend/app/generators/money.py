"""Live vs. online presentation of pots and bets. Same math, different numbers on screen.

Live: dollars at a real stake, rounded to $5 chips, deliberately uneven sizes.
Online: big blinds, bets as standard pot fractions.
"""

from dataclasses import dataclass
from random import Random

from app.generators.base import GenContext

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
