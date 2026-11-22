"""Section 9: Expected value."""

from random import Random
from typing import Any

from app.generators.base import (
    GenContext,
    Instance,
    make_buckets,
    pct,
    percent_width,
    register,
    retry,
)
from app.generators.money import Spot, make_spot, make_stacks, money_buckets
from app.generators.poker.s3_outs import DRAWS, flop_equity
from app.generators.poker.s4_pot_odds import _setup


def ev_call(pot_with_bet: float, call: float, equity: float) -> float:
    """All-in call, no future action. pot_with_bet already includes villain's bet."""
    return equity * (pot_with_bet + call) - call


def ev_bluff(pot: float, bet: float, fold: float) -> float:
    return fold * pot - (1 - fold) * bet


def shove_ev(pot: float, stack: float, fold: float, equity: float) -> float:
    """Shove `stack` into `pot`; villain folds `fold` of the time or calls `stack`."""
    called = equity * (pot + 2 * stack) - stack
    return fold * pot + (1 - fold) * called


def required_fold_equity(pot: float, stack: float, equity: float) -> float:
    """Fold frequency that makes a shove break even (0 if it's +EV even when called)."""
    called = equity * (pot + 2 * stack) - stack
    return 0.0 if called >= 0 else -called / (pot - called)


@register("ev_call")
def ev_call_gen(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    spot = make_spot(rng, ctx, 0.5, 2.0)
    eq = round(rng.uniform(0.15, 0.6), 2)
    pot_with_bet = spot.pot + spot.bet
    ev = ev_call(pot_with_bet, spot.bet, eq)
    buckets, cid = money_buckets(rng, ev, spot.pot, ctx)
    m = spot.money
    return Instance(
        prompt=_setup(spot)
        + f"Villain shoves **{m(spot.bet)}** and you can call all-in. Your equity is **{eq * 100:.0f}%**. "
        "What's the EV of calling?",
        answer_type="bucket",
        unit="chips",
        buckets=buckets,
        correct=cid,
        exact=round(ev, 1),
        scene={"pot": spot.pot, "bet": spot.bet},
        shortcut="EV = equity × final pot − call.",
        explanation_md=(
            f"Final pot {m(spot.pot)} + {m(spot.bet)} + {m(spot.bet)} = {m(pot_with_bet + spot.bet)}.\n\n"
            f"EV = {eq:.2f} × {m(pot_with_bet + spot.bet)} − {m(spot.bet)} = **{m(round(ev, 1))}**."
        ),
    )


@register("ev_bluff")
def ev_bluff_gen(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    spot = make_spot(rng, ctx, 0.33, 1.5)
    fold = round(rng.uniform(0.2, 0.7), 2)
    ev = ev_bluff(spot.pot, spot.bet, fold)
    buckets, cid = money_buckets(rng, ev, spot.pot, ctx)
    m = spot.money
    return Instance(
        prompt=_setup(spot)
        + f"You bluff **{m(spot.bet)}** with no equity. Villain folds **{fold * 100:.0f}%**. EV of the bluff?",
        answer_type="bucket",
        unit="chips",
        buckets=buckets,
        correct=cid,
        exact=round(ev, 1),
        scene={"pot": spot.pot, "bet": spot.bet, "street": "river"},
        shortcut="EV = fold% × pot − call% × bet.",
        explanation_md=(
            f"EV = {fold:.2f} × {m(spot.pot)} − {1 - fold:.2f} × {m(spot.bet)} = **{m(round(ev, 1))}**."
        ),
    )


def _semi_bluff_spot(rng: Random, ctx: GenContext) -> tuple[Spot, float, int, float]:
    def attempt(r: Random) -> tuple[Spot, float, int, float] | None:
        spot = make_spot(r, ctx)
        stack = make_stacks(r, ctx, spot, 1.0, 3.5)
        outs = r.choice([8, 9, 12, 15])
        eq = flop_equity(outs)
        if required_fold_equity(spot.pot, stack, eq) < 0.05:
            return None  # +EV even when called: nothing to compute
        return spot, stack, outs, eq

    return retry(rng, attempt)


@register("semi_bluff_fold_equity")
def semi_bluff_fold_equity(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    spot, stack, outs, eq = _semi_bluff_spot(rng, ctx)
    need = required_fold_equity(spot.pot, stack, eq)
    buckets, cid = make_buckets(rng, need * 100, percent_width(ctx.level), "percent", 0, 100)
    m = spot.money
    called = eq * (spot.pot + 2 * stack) - stack
    return Instance(
        prompt=(
            f"Flop. Pot **{m(spot.pot)}**. You shove **{m(stack)}** with a {DRAWS[outs]} "
            f"({pct(eq)} when called). How often must villain fold for the shove to break even?"
        ),
        answer_type="bucket",
        unit="percent",
        buckets=buckets,
        correct=cid,
        exact=round(need * 100, 1),
        scene={"pot": spot.pot, "bet": stack, "street": "flop"},
        shortcut="Fold% = −EV(called) ÷ (pot − EV(called)).",
        explanation_md=(
            f"When called: {eq:.3f} × {m(spot.pot + 2 * stack)} − {m(stack)} = {m(round(called, 1))}. "
            f"When villain folds you win {m(spot.pot)}.\n\n"
            f"Break even: F × {m(spot.pot)} + (1 − F) × {m(round(called, 1))} = 0 → F = **{pct(need)}**."
        ),
    )


@register("ev_shove")
def ev_shove(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    want_shove = rng.random() < 0.5

    def attempt(r: Random) -> Any:
        spot, stack, outs, eq = _semi_bluff_spot(r, ctx)
        need = required_fold_equity(spot.pot, stack, eq)
        fold = round(r.uniform(0.05, 0.8), 2)
        if abs(fold - need) < 0.07 or (fold > need) != want_shove:
            return None
        return spot, stack, outs, eq, need, fold

    spot, stack, outs, eq, need, fold = retry(rng, attempt)
    action = "raise" if want_shove else "fold"
    ev = shove_ev(spot.pot, stack, fold, eq)
    m = spot.money
    return Instance(
        prompt=(
            f"Flop. Pot **{m(spot.pot)}**, {m(stack)} behind. You have a {DRAWS[outs]} ({pct(eq)} when called). "
            f"Villain folds to a shove about **{fold * 100:.0f}%**. Shove (raise) or fold?"
        ),
        answer_type="action",
        actions=["fold", "raise"],
        correct=action,
        exact="shove" if want_shove else "fold",
        scene={"pot": spot.pot, "hero_stack": stack, "street": "flop"},
        shortcut="Shove if villain's fold% beats the break-even fold%.",
        explanation_md=(
            f"**{'Shove' if want_shove else 'Fold'}.** Break-even fold% = {pct(need)}; villain folds {fold * 100:.0f}%.\n\n"
            f"EV(shove) = {fold:.2f} × {m(spot.pot)} + {1 - fold:.2f} × EV(called) = **{m(round(ev, 1))}** "
            "(folding is 0)."
        ),
    )
