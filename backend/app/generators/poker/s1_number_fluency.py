"""Section 1: Number fluency. Ratios, percentages and the bet-size table."""

from random import Random
from typing import Any

from app.generators.base import (
    GenContext,
    Instance,
    make_buckets,
    make_choices,
    pct,
    percent_width,
    register,
    retry,
)
from app.generators.money import make_spot

# (label, fraction of pot)
SIZES = [("⅓ pot", 1 / 3), ("½ pot", 1 / 2), ("⅔ pot", 2 / 3), ("¾ pot", 3 / 4), ("pot", 1.0), ("2× pot", 2.0)]  # fmt: skip
FRACTION_LABELS = [("⅓", 1 / 3), ("½", 1 / 2), ("⅔", 2 / 3), ("¾", 3 / 4), ("Pot", 1.0), ("1½×", 1.5), ("2×", 2.0)]  # fmt: skip


def call_equity(f: float) -> float:
    return f / (1 + 2 * f)


def bluff_breakeven(f: float) -> float:
    return f / (1 + f)


def mdf(f: float) -> float:
    return 1 / (1 + f)


def _ratio_label(a: float) -> str:
    return f"{a:g}:1"


@register("ratio_to_pct")
def ratio_to_pct(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    pool = [1, 2, 3, 4, 5] if ctx.level == 1 else [1, 1.5, 2, 2.5, 3, 3.5, 4, 5, 6, 7, 9, 11]
    a = rng.choice(pool)
    exact = 100 / (a + 1)
    buckets, cid = make_buckets(rng, exact, percent_width(ctx.level), "percent", 0, 100)
    return Instance(
        prompt=f"Convert odds of **{_ratio_label(a)}** against to a percentage.",
        answer_type="bucket",
        unit="percent",
        buckets=buckets,
        correct=cid,
        exact=round(exact, 1),
        shortcut="a:1 against → 1 / (a + 1).",
        explanation_md=f"{_ratio_label(a)} means 1 win per {a:g} losses: 1 / ({a:g} + 1) = **{exact:.1f}%**.",
    )


RATIO_TABLE = [(1, "50%"), (1.5, "40%"), (2, "33%"), (3, "25%"), (4, "20%"), (5, "17%"), (9, "10%")]


@register("pct_to_ratio")
def pct_to_ratio(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    a, p = rng.choice(RATIO_TABLE)
    correct = _ratio_label(a)
    choices, cid = make_choices(rng, correct, [_ratio_label(x) for x, _ in RATIO_TABLE])
    return Instance(
        prompt=f"**{p}** equity is what odds against?",
        answer_type="choice",
        choices=choices,
        correct=cid,
        exact=correct,
        shortcut="p% → (100 − p) : p, reduced to x:1.",
        explanation_md=f"{p} wins, so losses : wins = (100 − {p.rstrip('%')}) : {p.rstrip('%')} ≈ **{correct}**.",
    )


@register("bet_as_fraction")
def bet_as_fraction(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    def attempt(r: Random) -> Any:
        spot = make_spot(r, ctx, 0.3, 2.0)
        label, f = min(FRACTION_LABELS, key=lambda x: abs(x[1] - spot.fraction))
        return (spot, label, f) if abs(f - spot.fraction) <= 0.04 else None

    spot, label, _ = retry(rng, attempt)
    choices, cid = make_choices(rng, label, [lbl for lbl, _ in FRACTION_LABELS])
    return Instance(
        prompt=f"Villain bets **{spot.money(spot.bet)}** into **{spot.money(spot.pot)}**. "
        "Roughly what fraction of the pot is that?",
        answer_type="choice",
        choices=choices,
        correct=cid,
        exact=label,
        scene={"pot": spot.pot, "bet": spot.bet},
        shortcut="Bet ÷ pot, then snap to the nearest standard size.",
        explanation_md=f"{spot.money(spot.bet)} ÷ {spot.money(spot.pot)} = {spot.fraction:.2f} ≈ **{label}**.",
    )


def _table_card(rng: Random, title: str, fn: Any, verb: str, formula: str) -> Instance:
    label, f = rng.choice(SIZES)
    correct = pct(fn(f), 0)
    distractors = [pct(fn(g), 0) for _, g in SIZES]
    choices, cid = make_choices(rng, correct, distractors)
    rows = "\n".join(
        f"| {lbl} | {'**' if lbl == label else ''}{pct(fn(g), 0)}{'**' if lbl == label else ''} |"
        for lbl, g in SIZES
    )
    return Instance(
        prompt=f"{verb} **{label}**: {title}?",
        answer_type="choice",
        choices=choices,
        correct=cid,
        exact=correct,
        shortcut=formula,
        explanation_md=f"**{correct}**: {formula}\n\n| Bet | {title.capitalize()} |\n|---|---|\n{rows}",
    )


@register("table_call_equity")
def table_call_equity(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    return _table_card(
        rng, "equity needed to call", call_equity, "Facing", "B / (P + 2B): call ÷ final pot."
    )


@register("table_bluff_breakeven")
def table_bluff_breakeven(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    return _table_card(
        rng,
        "how often must it work",
        bluff_breakeven,
        "You bluff",
        "B / (P + B): risk ÷ (risk + reward).",
    )


@register("table_mdf")
def table_mdf(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    return _table_card(
        rng, "minimum defense frequency", mdf, "Facing", "P / (P + B) = 1 − bluff breakeven."
    )
