"""Section 5: Preflop equities and set mining."""

from functools import lru_cache
from random import Random
from typing import Any

import eval7  # type: ignore[import-untyped]

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
from app.generators.cards import RANKS, SUITS, pretty

MC_ITERATIONS = 500_000  # ±0.1% at 1 s.e.; buckets are several points wide


@lru_cache(maxsize=4096)
def preflop_equity(hero: tuple[str, str], villain: tuple[str, str]) -> float:
    """Hero's all-in preflop equity (ties count half), via eval7 Monte Carlo in C.
    Cached so a given matchup always returns the same number within a process."""
    eq = eval7.py_hand_vs_range_monte_carlo(
        [eval7.Card(c) for c in hero], eval7.HandRange("".join(villain)), [], MC_ITERATIONS
    )
    return round(float(eq), 3)


ARCHETYPES = {
    "pair_vs_overs": ("Pair vs two overcards", "≈ 55/45 for the pair"),
    "pair_vs_over_under": ("Pair vs one over, one under", "≈ 70/30 for the pair"),
    "overpair": ("Overpair vs underpair", "≈ 80/20 for the higher pair"),
    "dominated": ("Dominated (shared card)", "≈ 70–75/25–30 for the better kicker"),
    "overs_vs_unders": ("Two overcards vs two undercards", "≈ 60/40 for the overcards"),
}


def _hand(rng: Random, r1: str, r2: str, used: set[str]) -> tuple[str, str]:
    for _ in range(100):
        s1, s2 = rng.choice(SUITS), rng.choice(SUITS)
        if r1 == r2 and s1 == s2:
            continue
        a, b = r1 + s1, r2 + s2
        if a not in used and b not in used:
            used.update((a, b))
            return a, b
    raise RuntimeError("could not place cards")


def _ranks(rng: Random, n: int) -> list[str]:
    return sorted(rng.sample(RANKS, n), key=RANKS.index, reverse=True)


def build_matchup(rng: Random, kind: str) -> tuple[tuple[str, str], tuple[str, str]]:
    """Returns (stronger-or-pair side, other side) for an archetype."""
    used: set[str] = set()
    if kind == "pair_vs_overs":
        hi1, hi2, p = _ranks(rng, 3)
        return _hand(rng, p, p, used), _hand(rng, hi1, hi2, used)
    if kind == "pair_vs_over_under":
        o, p, u = _ranks(rng, 3)
        return _hand(rng, p, p, used), _hand(rng, o, u, used)
    if kind == "overpair":
        p1, p2 = _ranks(rng, 2)
        return _hand(rng, p1, p1, used), _hand(rng, p2, p2, used)
    if kind == "dominated":
        shared, k1, k2 = rng.sample(RANKS, 3)
        k1, k2 = sorted((k1, k2), key=RANKS.index, reverse=True)
        return _hand(rng, shared, k1, used), _hand(rng, shared, k2, used)
    a, b, c, d = _ranks(rng, 4)
    return _hand(rng, a, b, used), _hand(rng, c, d, used)


def _seat(
    rng: Random, a: tuple[str, str], b: tuple[str, str]
) -> tuple[tuple[str, str], tuple[str, str]]:
    return (a, b) if rng.random() < 0.5 else (b, a)


@register("matchup_classify")
def matchup_classify(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    kind = rng.choice(list(ARCHETYPES))
    hero, villain = _seat(rng, *build_matchup(rng, kind))
    label, approx = ARCHETYPES[kind]
    choices, cid = make_choices(rng, label, [v[0] for v in ARCHETYPES.values()])
    eq = preflop_equity(hero, villain)
    return Instance(
        prompt="All-in preflop. Which matchup is this?",
        answer_type="choice",
        choices=choices,
        correct=cid,
        exact=label,
        scene={"hero": list(hero), "villain": list(villain), "street": "preflop"},
        shortcut="Pairs first, then compare high cards; a shared card means domination.",
        explanation_md=f"**{label}**: {approx}. Here: you **{pct(eq)}**, villain {pct(1 - eq)}.",
    )


@register("matchup_equity")
def matchup_equity(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    kind = rng.choice(list(ARCHETYPES))
    hero, villain = _seat(rng, *build_matchup(rng, kind))
    eq = preflop_equity(hero, villain) * 100
    label, approx = ARCHETYPES[kind]
    buckets, cid = make_buckets(rng, eq, percent_width(ctx.level), "percent", 0, 100)
    suited = [h for h in (hero, villain) if h[0][1] == h[1][1] and h[0][0] != h[1][0]]
    suited_note = " Suited hands gain ≈ 2–3%." if suited else ""
    return Instance(
        prompt="All-in preflop. What's your equity?",
        answer_type="bucket",
        unit="percent",
        buckets=buckets,
        correct=cid,
        exact=round(eq, 1),
        scene={"hero": list(hero), "villain": list(villain), "street": "preflop"},
        shortcut="Classify the matchup, then adjust a few points for suits and connectedness.",
        explanation_md=f"{label}: {approx}.{suited_note}\n\n{pretty(hero)} vs {pretty(villain)}: **{eq:.1f}%**.",
    )


SMALL_PAIRS = "23456789"


def _preflop_amounts(rng: Random, ctx: GenContext) -> tuple[float, str, Any]:
    """(raise size, unit label fn, money formatter)."""
    if ctx.stakes_format == "online":
        raise_to = rng.choice([2.5, 3, 3.5, 4]) if ctx.level > 1 else 3

        def fmt(x: float) -> str:
            return f"{x:g}bb"

        return raise_to, "100bb online", fmt
    bb = rng.choice([2, 5])
    raise_to = rng.choice([6, 8, 10, 12, 15]) * bb // 2 if bb == 2 else rng.choice([15, 20, 25, 30])

    def fmt_live(x: float) -> str:
        return f"${x:,.0f}"

    return float(raise_to), f"${1 if bb == 2 else 2}/{bb} live", fmt_live


def set_mining_spot(rng: Random, ctx: GenContext, short_villain: bool) -> dict[str, Any]:
    """Call if effective stack ≥ 20× the call, fold if ≤ 10×. The grey zone is excluded."""
    want_call = rng.random() < 0.5
    raise_to, stake, fmt = _preflop_amounts(rng, ctx)

    live = ctx.stakes_format == "live"

    def rnd(x: float) -> float:
        return float(round(x / 5) * 5) if live else float(round(x))

    def attempt(r: Random) -> dict[str, Any] | None:
        mult = r.uniform(22, 60) if want_call else r.uniform(4, 9.5)
        eff = rnd(raise_to * mult)
        if short_villain:  # the twist: you're deep, but villain isn't
            hero_stack, villain_stack = rnd(eff * r.uniform(2, 4)), eff
        else:
            hero_stack, villain_stack = eff, rnd(eff * r.uniform(1, 3))
        eff = min(hero_stack, villain_stack)
        ratio = eff / raise_to
        if (ratio >= 20) != want_call or 10 < ratio < 20:
            return None
        return {
            "eff": eff,
            "hero_stack": hero_stack,
            "villain_stack": villain_stack,
            "ratio": ratio,
        }

    out = retry(rng, attempt)
    pair = rng.choice(SMALL_PAIRS)
    used: set[str] = set()
    hero = _hand(rng, pair, pair, used)
    return {
        **out,
        "hero": list(hero),
        "raise_to": raise_to,
        "stake": stake,
        "fmt": fmt,
        "call": want_call,
    }


def _set_mining_instance(s: dict[str, Any], prompt_extra: str, shortcut: str) -> Instance:
    fmt = s["fmt"]
    action = "call" if s["call"] else "fold"
    return Instance(
        prompt=(
            f"{s['stake']}. Villain raises to **{fmt(s['raise_to'])}**. You have {pretty(s['hero'])}. "
            f"Your stack {fmt(s['hero_stack'])}, villain's {fmt(s['villain_stack'])}.{prompt_extra} "
            "Call to set-mine, or fold?"
        ),
        answer_type="action",
        actions=["fold", "call"],
        correct=action,
        exact=action,
        scene={"hero": s["hero"], "street": "preflop"},
        shortcut=shortcut,
        explanation_md=(
            f"**{action.capitalize()}.** Effective stack {fmt(s['eff'])} is **{s['ratio']:.0f}×** the call. "
            "You flop a set ≈ 12% (1 in 8.5), so you need roughly **15–20×** to win enough when you hit."
        ),
    )


@register("set_mining")
def set_mining(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    s = set_mining_spot(rng, ctx, short_villain=False)
    return _set_mining_instance(s, "", "Set mine with ≥ 15–20× the call behind (effective stack).")
