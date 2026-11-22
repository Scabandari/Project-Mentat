"""Section 8: Stack geometry. SPR, effective stacks, geometric sizing."""

from random import Random
from typing import Any

from app.generators.base import (
    GenContext,
    Instance,
    make_buckets,
    ordered_choices,
    register,
    retry,
)
from app.generators.money import Spot, make_spot, make_stacks, money_buckets


def _two_stacks(
    rng: Random, ctx: GenContext, spot: Spot, lo: float, hi: float
) -> tuple[float, float]:
    eff = make_stacks(rng, ctx, spot, lo, hi)
    other = make_stacks(rng, ctx, spot, eff / spot.pot * 1.1, eff / spot.pot * 3)
    return (eff, other) if rng.random() < 0.5 else (other, eff)


def _flop_setup(spot: Spot, hero: float, villain: float) -> str:
    m = spot.money
    where = f"{spot.stake_label} live" if spot.fmt == "live" else "Online"
    return f"{where}. Flop pot **{m(spot.pot)}**. Your stack **{m(hero)}**, villain's **{m(villain)}**."


@register("spr_calc")
def spr_calc(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    spot = make_spot(rng, ctx)
    hero, villain = _two_stacks(rng, ctx, spot, 1.0, 15.0)
    eff = min(hero, villain)
    spr = eff / spot.pot
    buckets, cid = make_buckets(rng, spr, 2, "ratio", 0)
    m = spot.money
    return Instance(
        prompt=_flop_setup(spot, hero, villain) + " What's the SPR?",
        answer_type="bucket",
        unit="ratio",
        buckets=buckets,
        correct=cid,
        exact=round(spr, 1),
        scene={"pot": spot.pot, "hero_stack": hero, "villain_stack": villain, "street": "flop"},
        shortcut="Effective (smaller) stack ÷ pot.",
        explanation_md=f"Effective stack {m(eff)} ÷ pot {m(spot.pot)} = **{spr:.1f}**.",
    )


@register("effective_stack")
def effective_stack(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    spot = make_spot(rng, ctx)
    hero, villain = _two_stacks(rng, ctx, spot, 2.0, 12.0)
    eff = min(hero, villain)
    buckets, cid = money_buckets(rng, eff, spot.pot, ctx, lo_bound=0)
    m = spot.money
    return Instance(
        prompt=_flop_setup(spot, hero, villain) + " What's the effective stack?",
        answer_type="bucket",
        unit="chips",
        buckets=buckets,
        correct=cid,
        exact=eff,
        scene={"pot": spot.pot, "hero_stack": hero, "villain_stack": villain, "street": "flop"},
        shortcut="The smaller stack: nobody can win more than that.",
        explanation_md=f"min({m(hero)}, {m(villain)}) = **{m(eff)}**. The bigger stack's extra chips can't be won.",
    )


SPR_BANDS = ["Low (under 4)", "Medium (4–10)", "High (over 10)"]
SPR_MEANING = {
    SPR_BANDS[0]: "top pair or better is usually committed: get it in",
    SPR_BANDS[1]: "top pair depends on board and opponent",
    SPR_BANDS[2]: "one pair is a bluff-catcher for big pots; you need strong hands to stack off",
}


def spr_band(spr: float) -> str:
    return SPR_BANDS[0] if spr < 4 else SPR_BANDS[1] if spr <= 10 else SPR_BANDS[2]


@register("spr_classify")
def spr_classify(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    band = rng.choice(SPR_BANDS)

    def attempt(r: Random) -> tuple[Spot, float, float, float] | None:
        spot = make_spot(r, ctx)
        hero, villain = _two_stacks(r, ctx, spot, 0.8, 20.0)
        spr = min(hero, villain) / spot.pot
        if spr_band(spr) != band or min(abs(spr - 4), abs(spr - 10)) < 0.5:
            return None
        return spot, hero, villain, spr

    spot, hero, villain, spr = retry(rng, attempt)
    choices, cid = ordered_choices(SPR_BANDS, band)
    return Instance(
        prompt=_flop_setup(spot, hero, villain) + " How deep is this pot?",
        answer_type="choice",
        choices=choices,
        correct=cid,
        exact=band,
        scene={"pot": spot.pot, "hero_stack": hero, "villain_stack": villain, "street": "flop"},
        shortcut="SPR < 4 commit · 4–10 it depends · > 10 be careful with one pair.",
        explanation_md=f"SPR = {spr:.1f} → **{band}**: {SPR_MEANING[band]}.",
    )


def geometric_fraction(pot: float, stack: float, streets: int) -> float:
    """Bet fraction f per street so that, with calls, stacks go in on the last street:
    pot grows ×(1 + 2f) per street, so (1 + 2f)^n = (P + 2S) / P."""
    return float(((pot + 2 * stack) / pot) ** (1 / streets) - 1) / 2


@register("geometric_sizing")
def geometric_sizing(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    streets = rng.choice([2, 3])
    spot = make_spot(rng, ctx)
    stack = make_stacks(rng, ctx, spot, 1.5, 12.0)
    f = geometric_fraction(spot.pot, stack, streets)
    width = {1: 20, 2: 12}.get(ctx.level, 8)
    buckets, cid = make_buckets(rng, f * 100, width, "percent", 0)
    m = spot.money
    street_names = {3: "flop, turn and river", 2: "turn and river"}[streets]
    growth = (spot.pot + 2 * stack) / spot.pot
    return Instance(
        prompt=(
            f"Pot **{m(spot.pot)}**, effective stack **{m(stack)}**. You want to bet the same "
            f"fraction of the pot on the {street_names} and be all-in by the river. What size?"
        ),
        answer_type="bucket",
        unit="percent",
        buckets=buckets,
        correct=cid,
        exact=round(f * 100, 1),
        scene={"pot": spot.pot, "hero_stack": stack},
        shortcut="Each called bet of f × pot multiplies the pot by (1 + 2f).",
        explanation_md=(
            f"All-in means the final pot is {m(spot.pot)} + 2 × {m(stack)} = {m(spot.pot + 2 * stack)}, "
            f"{growth:.2f}× today's. Over {streets} streets: (1 + 2f)^{streets} = {growth:.2f} → "
            f"f = **{f * 100:.0f}% pot** per street."
        ),
    )
