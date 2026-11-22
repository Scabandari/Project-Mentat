"""Section 4: Pot odds."""

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
from app.generators.poker.s3_outs import DRAWS, _draw_spot


def required_equity(spot: Spot, extra_callers: int = 0) -> float:
    """Call ÷ final pot. Pot excludes villain's bet."""
    return spot.bet / (spot.pot + spot.bet * (2 + extra_callers))


def _setup(spot: Spot) -> str:
    if spot.fmt == "live":
        return f"{spot.stake_label} live. Pot is **{spot.money(spot.pot)}**. "
    return f"Online. Pot is **{spot.money(spot.pot)}**. "


def _scene(spot: Spot, **cards: Any) -> dict[str, Any]:
    return {"pot": spot.pot, "bet": spot.bet, **cards}


@register("pot_odds_required")
def pot_odds_required(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    spot = make_spot(rng, ctx)
    req = required_equity(spot)
    buckets, cid = make_buckets(rng, req * 100, percent_width(ctx.level), "percent", 0, 100)
    final = spot.pot + 2 * spot.bet
    return Instance(
        prompt=_setup(spot) + f"Villain {spot.bet_phrase()}. What equity do you need to call?",
        answer_type="bucket",
        unit="percent",
        buckets=buckets,
        correct=cid,
        exact=round(req * 100, 1),
        scene=_scene(spot),
        shortcut="Call ÷ (pot + bet + call). Standard sizes: use the table.",
        explanation_md=(
            f"You call {spot.money(spot.bet)} to win a final pot of "
            f"{spot.money(spot.pot)} + {spot.money(spot.bet)} + {spot.money(spot.bet)} = {spot.money(final)}.\n\n"
            f"{spot.money(spot.bet)} ÷ {spot.money(final)} = **{pct(req)}**."
        ),
    )


@register("pot_odds_multiway")
def pot_odds_multiway(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    spot = make_spot(rng, ctx)
    req = required_equity(spot, extra_callers=1)
    buckets, cid = make_buckets(rng, req * 100, percent_width(ctx.level), "percent", 0, 100)
    final = spot.pot + 3 * spot.bet
    return Instance(
        prompt=_setup(spot)
        + f"Villain {spot.bet_phrase()} and another player calls. What equity do you need to call?",
        answer_type="bucket",
        unit="percent",
        buckets=buckets,
        correct=cid,
        exact=round(req * 100, 1),
        scene=_scene(spot),
        shortcut="Each caller ahead of you adds a bet to the pot, so your price improves.",
        explanation_md=(
            f"Final pot: {spot.money(spot.pot)} + 3 × {spot.money(spot.bet)} = {spot.money(final)}. "
            f"{spot.money(spot.bet)} ÷ {spot.money(final)} = **{pct(req)}** (heads-up it would be "
            f"{pct(required_equity(spot))})."
        ),
    )


VERDICTS = ["Call is +EV", "Roughly breakeven", "Call is −EV"]


def _draw_vs_price(rng: Random, ctx: GenContext, min_gap: float) -> Any:
    """A real draw on the flop or turn plus a bet, where equity and price clearly differ.

    The right answer is decided first (50/50), then spots are sampled until one matches.
    Most one-card draws lack the price, so without this "always fold" would score ~75%.
    """
    want_call = rng.random() < 0.5

    def attempt(r: Random) -> Any:
        street = r.choice([3, 4])
        hero, board, outs = _draw_spot(r, street, {4, 8, 9, 12, 15})
        spot = make_spot(r, ctx, 0.25, 1.5)
        unseen = 47 if street == 3 else 46
        eq = len(outs) / unseen  # one card to come: villain can bet again
        req = required_equity(spot)
        if abs(eq - req) < min_gap or (eq >= req) != want_call:
            return None
        return hero, board, outs, spot, eq, req, street

    return retry(rng, attempt, tries=5000)


def _draw_explanation(outs: list[str], eq: float, req: float, unseen: int, spot: Spot) -> str:
    n = len(outs)
    name = DRAWS.get(n, f"{n}-out draw")
    return (
        f"- **Your equity** (one card): {n} outs ({name}) ÷ {unseen} unseen = **{pct(eq)}** "
        f"(≈ {n} × 2 = {n * 2}%)\n"
        f"- **Required**: {spot.money(spot.bet)} ÷ {spot.money(spot.pot + 2 * spot.bet)} = **{pct(req)}**"
    )


@register("pot_odds_vs_draw")
def pot_odds_vs_draw(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    hero, board, outs, spot, eq, req, street = _draw_vs_price(rng, ctx, 0.04)
    verdict = VERDICTS[0] if eq > req else VERDICTS[2]
    choices, cid = ordered_choices(VERDICTS, verdict)
    return Instance(
        prompt=_setup(spot)
        + f"Villain {spot.bet_phrase()}. On direct odds alone, is calling with your draw profitable?",
        answer_type="choice",
        choices=choices,
        correct=cid,
        exact=verdict,
        scene=_scene(spot, hero=hero, board=board, street="flop" if street == 3 else "turn"),
        shortcut="Compare outs × 2 to the price for one card.",
        explanation_md=f"**{verdict}.**\n\n"
        + _draw_explanation(outs, eq, req, 47 if street == 3 else 46, spot),
    )


@register("call_or_fold_draw")
def call_or_fold_draw(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    hero, board, outs, spot, eq, req, street = _draw_vs_price(rng, ctx, 0.03)
    action = "call" if eq >= req else "fold"
    return Instance(
        prompt=_setup(spot) + f"Villain {spot.bet_phrase()}. Ignoring implied odds: call or fold?",
        answer_type="action",
        actions=["fold", "call"],
        correct=action,
        exact=action,
        scene=_scene(spot, hero=hero, board=board, street="flop" if street == 3 else "turn"),
        shortcut="Count outs → × 2 → compare with call ÷ final pot.",
        explanation_md=f"**{action.capitalize()}.**\n\n"
        + _draw_explanation(outs, eq, req, 47 if street == 3 else 46, spot),
    )
