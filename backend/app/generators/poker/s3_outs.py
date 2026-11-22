"""Section 3: Outs and draws. Outs are counted by enumerating every unseen card."""

from collections import Counter
from math import comb
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
from app.generators.cards import (
    CATEGORIES,
    RANKS,
    SUIT_SYMBOL,
    category_index,
    deal,
    evaluate,
    pretty,
    rank_of,
    remaining,
)

STRAIGHT = CATEGORIES.index("Straight")

DRAWS = {
    4: "gutshot",
    6: "two overcards",
    8: "open-ended straight draw",
    9: "flush draw",
    12: "flush draw + gutshot",
    15: "flush draw + open-ender",
}


def outs_to(hero: list[str], board: list[str], threshold: int = STRAIGHT) -> list[str]:
    """Unseen cards that lift hero to `threshold` or better, using at least one hole card."""
    out = []
    for c in remaining(hero, board):
        if category_index([*hero, *board, c]) < threshold:
            continue
        if len(board) == 4 and category_index([*board, c]) >= threshold:
            continue  # the board alone makes it: hero's cards don't play
        out.append(c)
    return out


def describe_outs(outs: list[str]) -> str:
    suits = Counter(c[1] for c in outs)
    lines = []
    if suits and suits.most_common(1)[0][1] >= 7:
        s, n = suits.most_common(1)[0]
        lines.append(f"- {n} × {SUIT_SYMBOL[s]} (flush)")
        rest = [c for c in outs if c[1] != s]
    else:
        rest = list(outs)
    by_rank = Counter(c[0] for c in rest)
    for r, n in sorted(by_rank.items(), key=lambda x: RANKS.index(x[0]), reverse=True):
        cards = pretty(sorted((c for c in rest if c[0] == r), key=lambda c: c[1]))
        lines.append(f"- {n} × {r} ({cards})")
    return "\n".join(lines)


def _draw_spot(
    rng: Random, street_cards: int, accept: set[int]
) -> tuple[list[str], list[str], list[str]]:
    def attempt(r: Random) -> tuple[list[str], list[str], list[str]] | None:
        hero = deal(r, 2)
        board = deal(r, street_cards, hero)
        if category_index(hero + board) >= STRAIGHT:
            return None
        outs = outs_to(hero, board)
        return (hero, board, outs) if len(outs) in accept else None

    return retry(rng, attempt, tries=50_000)


@register("outs_count")
def outs_count(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    street = 3 if ctx.level == 1 else rng.choice([3, 4])
    hero, board, outs = _draw_spot(rng, street, {4, 8, 9})
    n = len(outs)
    buckets, cid = make_buckets(rng, n, 1, "count", 0)
    return Instance(
        prompt="How many cards give you **a straight or better** on the next card?",
        answer_type="bucket",
        unit="count",
        buckets=buckets,
        correct=cid,
        exact=n,
        scene={"hero": hero, "board": board, "street": "flop" if street == 3 else "turn"},
        shortcut="Flush draw 9 · open-ender 8 · gutshot 4.",
        explanation_md=f"**{n} outs**:\n\n{describe_outs(outs)}",
    )


@register("outs_combo")
def outs_combo(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    hero, board, outs = _draw_spot(rng, 3, {12, 15})
    n = len(outs)
    buckets, cid = make_buckets(rng, n, 1, "count", 0)
    return Instance(
        prompt="Combo draw: how many cards give you **a straight or better**?",
        answer_type="bucket",
        unit="count",
        buckets=buckets,
        correct=cid,
        exact=n,
        scene={"hero": hero, "board": board, "street": "flop"},
        shortcut="Add the draws, subtract cards counted twice (the straight cards of your suit).",
        explanation_md=f"**{n} outs**:\n\n{describe_outs(outs)}\n\nStraight cards in your suit are already in the flush count.",
    )


@register("outs_dirty")
def outs_dirty(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    def attempt(r: Random) -> Any:
        villain = deal(r, 2)
        if villain[0][0] != villain[1][0]:
            return None  # villain holds a pocket pair, to make sets
        board = deal(r, 4, villain)
        if category_index(villain + board) != CATEGORIES.index("Trips"):
            return None
        hero = deal(r, 2, villain, board)
        if evaluate(hero + board) >= evaluate(villain + board):
            return None
        naive = outs_to(hero, board)
        if len(naive) < 4:
            return None
        wins = [
            c
            for c in remaining(hero, board, villain)
            if evaluate([*hero, *board, c]) > evaluate([*villain, *board, c])
        ]
        dirty = [c for c in naive if c not in wins]
        return (hero, villain, board, naive, wins, dirty) if dirty else None

    hero, villain, board, naive, wins, dirty = retry(rng, attempt, tries=200_000)
    n = len(wins)
    buckets, cid = make_buckets(rng, n, 1, "count", 0)
    return Instance(
        prompt="Villain shows a **set**. How many river cards win for you?",
        answer_type="bucket",
        unit="count",
        buckets=buckets,
        correct=cid,
        exact=n,
        scene={"hero": hero, "villain": villain, "board": board, "street": "turn"},
        shortcut="Against a set, any out that pairs the board gives villain a full house.",
        explanation_md=(
            f"Your draw has {len(naive)} outs, but {len(dirty)} of them also improve villain to a "
            f"better hand, usually by pairing the board ({pretty(sorted(dirty, key=rank_of))}).\n\n"
            f"**{n} clean outs**:\n\n{describe_outs(wins)}"
        ),
    )


def flop_equity(outs: int) -> float:
    """Exact probability of hitting by the river with two cards to come (47 unseen)."""
    return 1 - comb(47 - outs, 2) / comb(47, 2)


def turn_equity(outs: int) -> float:
    return outs / 46


@register("outs_to_equity_flop")
def outs_to_equity_flop(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    outs = rng.choice(list(DRAWS))
    exact = flop_equity(outs) * 100
    estimate = outs * 4 - max(0, outs - 8)
    buckets, cid = make_buckets(rng, exact, percent_width(ctx.level), "percent", 0, 100)
    return Instance(
        prompt=f"Flop. You have a **{DRAWS[outs]}** ({outs} outs) and you're all-in. "
        "Equity by the river?",
        answer_type="bucket",
        unit="percent",
        buckets=buckets,
        correct=cid,
        exact=round(exact, 1),
        shortcut="Outs × 4. Over 8 outs, subtract (outs − 8).",
        explanation_md=(
            f"Rule of 4: {outs} × 4{f' − {outs - 8}' if outs > 8 else ''} ≈ **{estimate}%**. "
            f"Exact: 1 − C({47 - outs},2)/C(47,2) = **{pct(exact / 100)}**."
        ),
    )


@register("outs_to_equity_turn")
def outs_to_equity_turn(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    outs = rng.choice(list(DRAWS))
    exact = turn_equity(outs) * 100
    buckets, cid = make_buckets(rng, exact, percent_width(ctx.level), "percent", 0, 100)
    return Instance(
        prompt=f"Turn. You have a **{DRAWS[outs]}** ({outs} outs). Equity on the river?",
        answer_type="bucket",
        unit="percent",
        buckets=buckets,
        correct=cid,
        exact=round(exact, 1),
        shortcut="Outs × 2, plus 1–2 for big draws.",
        explanation_md=(
            f"Rule of 2: {outs} × 2 ≈ **{outs * 2}%**. Exact: {outs}/46 = **{pct(exact / 100)}**."
        ),
    )
