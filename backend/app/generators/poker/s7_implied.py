"""Section 7: Implied and reverse implied odds."""

from random import Random
from typing import Any

from app.generators.base import (
    GenContext,
    Instance,
    make_choices,
    pct,
    register,
    retry,
)
from app.generators.cards import SUIT_SYMBOL, SUITS, pretty
from app.generators.money import Spot, make_spot, make_stacks, money_buckets
from app.generators.poker.s3_outs import _draw_spot
from app.generators.poker.s4_pot_odds import _setup, required_equity


def implied_needed(spot: Spot, equity: float) -> float:
    """Extra you must win later: call / equity − (pot incl. villain's bet + call)."""
    return spot.bet / equity - (spot.pot + 2 * spot.bet)


def _implied_spot(
    rng: Random, ctx: GenContext
) -> tuple[list[str], list[str], list[str], Spot, float, float]:
    def attempt(r: Random) -> Any:
        hero, board, outs = _draw_spot(r, 3, {4, 8, 9})
        spot = make_spot(r, ctx, 0.4, 1.25)
        eq = len(outs) / 47
        need = implied_needed(spot, eq)
        if eq >= required_equity(spot) or need < spot.pot * 0.2:
            return None  # only draws that lack direct odds, by a meaningful margin
        return hero, board, outs, spot, eq, need

    return retry(rng, attempt, tries=500)  # type: ignore[no-any-return]


def _implied_working(spot: Spot, outs: list[str], eq: float, need: float) -> str:
    m = spot.money
    return (
        f"- Equity, one card: {len(outs)} ÷ 47 = **{pct(eq)}** "
        f"(you need {pct(required_equity(spot))} on direct odds)\n"
        f"- Extra needed = call ÷ equity − (pot + bet + call) = "
        f"{m(spot.bet)} ÷ {eq:.3f} − {m(spot.pot + 2 * spot.bet)} = **{m(round(need))}**"
    )


@register("implied_required")
def implied_required(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    hero, board, outs, spot, eq, need = _implied_spot(rng, ctx)
    buckets, cid = money_buckets(rng, need, spot.pot, ctx, lo_bound=0)
    return Instance(
        prompt=_setup(spot)
        + f"Villain {spot.bet_phrase()}. You have **{len(outs)} outs**. How much more must you win "
        "when you hit to make calling break even?",
        answer_type="bucket",
        unit="chips",
        buckets=buckets,
        correct=cid,
        exact=round(need, 1),
        scene={"pot": spot.pot, "bet": spot.bet, "hero": hero, "board": board, "street": "flop"},
        shortcut="call ÷ equity − (pot + bet + call).",
        explanation_md=_implied_working(spot, outs, eq, need),
    )


@register("implied_call")
def implied_call(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    """Implied odds are capped by what villain has left: the payoff never exceeds his stack."""
    want_call = rng.random() < 0.5

    def attempt(r: Random) -> Any:
        hero, board, outs, spot, eq, need = _implied_spot(r, ctx)
        behind = make_stacks(r, ctx, spot, 2.0, 15.0)  # villain's stack after calling the bet
        factor = r.uniform(1.3, 2.2) if want_call else r.uniform(0.3, 0.75)
        step = 0.5 if spot.fmt == "online" else 5
        payoff = max(step, round(need * factor / step) * step)
        if payoff > behind:
            return None
        return hero, board, outs, spot, eq, need, behind, payoff

    hero, board, outs, spot, eq, need, behind, payoff = retry(rng, attempt, tries=500)
    action = "call" if payoff >= need else "fold"
    m = spot.money
    return Instance(
        prompt=_setup(spot)
        + f"Villain {spot.bet_phrase()} and has **{m(behind)}** left. When you hit, you expect to win "
        f"about **{m(payoff)}** more. Call or fold?",
        answer_type="action",
        actions=["fold", "call"],
        correct=action,
        exact=action,
        scene={
            "pot": spot.pot,
            "bet": spot.bet,
            "villain_stack": behind,
            "hero": hero,
            "board": board,
            "street": "flop",
        },
        shortcut="Call if what you'll win later ≥ call ÷ equity − (pot + bet + call).",
        explanation_md=f"**{action.capitalize()}.** Expected extra {m(payoff)} vs needed {m(round(need))}.\n\n"
        + _implied_working(spot, outs, eq, need),
    )


@register("reverse_implied")
def reverse_implied(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    """Which draw is most likely to hit and still lose? A low flush draw."""
    suit = rng.choice(SUITS)
    other = [s for s in SUITS if s != suit]
    sym = SUIT_SYMBOL[suit]
    # Board: two of the flush suit (high cards) + one offsuit card; no ace on board.
    hi = rng.sample("KQJT9", 2)
    off_rank = rng.choice([r for r in "8765432" if r not in hi])
    board = [hi[0] + suit, hi[1] + suit, off_rank + rng.choice(other)]
    used = set(board)

    def pick(ranks: str, suits: list[str]) -> list[str] | None:
        cards = [r + s for r, s in zip(ranks, suits, strict=True)]
        return None if any(c in used for c in cards) else cards

    low = retry(rng, lambda r: pick("".join(r.sample("65432", 2)), [suit, suit]))
    used.update(low)
    nut = retry(
        rng, lambda r: pick("A" + r.choice([x for x in "8765432" if x != off_rank]), [suit, suit])
    )
    used.update(nut)
    pair_hand = retry(
        rng,
        lambda r: pick(
            hi[0] + r.choice([k for k in "A87" if k != off_rank]),
            [r.choice(other), r.choice(other)],
        ),
    )
    used.update(pair_hand)
    set_hand = retry(rng, lambda r: pick(off_rank * 2, r.sample(other, 2)))

    options = {
        f"{pretty(low)}: low flush draw": True,
        f"{pretty(nut)}: nut flush draw": False,
        f"{pretty(pair_hand)}: top pair": False,
        f"{pretty(set_hand)}: bottom set": False,
    }
    correct = next(k for k, v in options.items() if v)
    choices, cid = make_choices(rng, correct, [k for k in options if k != correct], n=4)
    return Instance(
        prompt="Which hand has the worst **reverse implied odds** (it improves, but still loses a big pot)?",
        answer_type="choice",
        choices=choices,
        correct=cid,
        exact=correct,
        scene={"board": board, "street": "flop"},
        shortcut="Non-nut draws hit and still lose: low flushes, the ignorant end of straights.",
        explanation_md=(
            f"**{correct}.** When a third {sym} comes, every higher flush beats you, and those are "
            "exactly the hands that pay you off big. The nut flush draw can't be outdrawn by another flush."
        ),
    )
