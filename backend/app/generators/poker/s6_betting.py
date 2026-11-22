"""Section 6: Betting math. What your bets require, and how often you must defend."""

from random import Random
from typing import Any

from app.generators.base import (
    GenContext,
    Instance,
    make_buckets,
    ordered_choices,
    pct,
    percent_width,
    register,
    retry,
)
from app.generators.money import Spot, make_spot
from app.generators.poker.s4_pot_odds import _setup


def breakeven(spot: Spot) -> float:
    return spot.bet / (spot.pot + spot.bet)


def mdf_of(spot: Spot) -> float:
    return spot.pot / (spot.pot + spot.bet)


def bluff_share(spot: Spot) -> float:
    """Max share of bluffs in a polarised river betting range (makes villain indifferent)."""
    return spot.bet / (spot.pot + 2 * spot.bet)


def _pct_bucket(rng: Random, ctx: GenContext, x: float) -> tuple[list[dict[str, Any]], int]:
    return make_buckets(rng, x * 100, percent_width(ctx.level), "percent", 0, 100)


@register("bluff_breakeven")
def bluff_breakeven_gen(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    spot = make_spot(rng, ctx, 0.25, 2.0)
    x = breakeven(spot)
    buckets, cid = _pct_bucket(rng, ctx, x)
    m = spot.money
    return Instance(
        prompt=_setup(spot)
        + f"You bluff **{m(spot.bet)}**. How often must villain fold for it to break even?",
        answer_type="bucket",
        unit="percent",
        buckets=buckets,
        correct=cid,
        exact=round(x * 100, 1),
        scene={"pot": spot.pot, "bet": spot.bet},
        shortcut="Risk ÷ (risk + reward) = B / (P + B).",
        explanation_md=f"You risk {m(spot.bet)} to win {m(spot.pot)}: {m(spot.bet)} ÷ {m(spot.pot + spot.bet)} = **{pct(x)}**.",
    )


@register("mdf")
def mdf_gen(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    spot = make_spot(rng, ctx, 0.25, 2.0)
    x = mdf_of(spot)
    buckets, cid = _pct_bucket(rng, ctx, x)
    m = spot.money
    return Instance(
        prompt=_setup(spot)
        + f"Villain {spot.bet_phrase()}. What's your minimum defense frequency?",
        answer_type="bucket",
        unit="percent",
        buckets=buckets,
        correct=cid,
        exact=round(x * 100, 1),
        scene={"pot": spot.pot, "bet": spot.bet},
        shortcut="MDF = P / (P + B) = 1 − bluff breakeven.",
        explanation_md=(
            f"{m(spot.pot)} ÷ ({m(spot.pot)} + {m(spot.bet)}) = **{pct(x)}**. Fold more than "
            f"{pct(1 - x)} and villain profits by betting any two cards."
        ),
    )


@register("value_bluff_ratio")
def value_bluff_ratio(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    spot = make_spot(rng, ctx, 0.33, 2.0)
    x = bluff_share(spot)
    buckets, cid = _pct_bucket(rng, ctx, x)
    m = spot.money
    value_per_bluff = (1 - x) / x
    return Instance(
        prompt=_setup(spot)
        + f"River. You bet **{m(spot.bet)}** with a polarised range (nuts or air). "
        "What share of your bets can be bluffs?",
        answer_type="bucket",
        unit="percent",
        buckets=buckets,
        correct=cid,
        exact=round(x * 100, 1),
        scene={"pot": spot.pot, "bet": spot.bet, "street": "river"},
        shortcut="Bluff share = villain's call equity = B / (P + 2B).",
        explanation_md=(
            f"Make villain's call break even: bluffs ÷ all bets = his required equity = "
            f"{m(spot.bet)} ÷ {m(spot.pot + 2 * spot.bet)} = **{pct(x)}**, "
            f"about {value_per_bluff:.1f} value bets per bluff."
        ),
    )


BLUFF_CHOICES = ["Bluff", "Give up"]


@register("bluff_or_check")
def bluff_or_check(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    want_bluff = rng.random() < 0.5

    def attempt(r: Random) -> tuple[Spot, float, float] | None:
        spot = make_spot(r, ctx, 0.33, 1.5)
        need = breakeven(spot)
        fold = round(r.uniform(0.15, 0.75), 2)
        if abs(fold - need) < 0.06 or (fold > need) != want_bluff:
            return None
        return spot, need, fold

    spot, need, fold = retry(rng, attempt)
    answer = BLUFF_CHOICES[0] if want_bluff else BLUFF_CHOICES[1]
    choices, cid = ordered_choices(BLUFF_CHOICES, answer)
    m = spot.money
    ev = fold * spot.pot - (1 - fold) * spot.bet
    return Instance(
        prompt=_setup(spot)
        + f"River, you missed. You could bet **{m(spot.bet)}**. You think villain folds about **{fold * 100:.0f}%**. Bluff or give up?",
        answer_type="choice",
        choices=choices,
        correct=cid,
        exact=answer,
        scene={"pot": spot.pot, "bet": spot.bet, "street": "river"},
        shortcut="Bluff when villain folds more often than B / (P + B).",
        explanation_md=(
            f"**{answer}.** Needed folds: {pct(need)}; expected: {fold * 100:.0f}%.\n\n"
            f"EV = {fold:.2f} × {m(spot.pot)} − {1 - fold:.2f} × {m(spot.bet)} = **{m(round(ev, 1))}**."
        ),
    )
