"""Section 2: Combinatorics."""

from collections import Counter
from itertools import combinations
from math import comb
from random import Random
from typing import Any

from app.generators.base import GenContext, Instance, make_buckets, register, retry
from app.generators.cards import (
    RANKS,
    SUIT_SYMBOL,
    SUITS,
    combos_matching,
    deal,
    plural_rank,
    pretty,
)

BROADWAY = "AKQJT"


def class_label(cls: str) -> str:
    if cls[0] == cls[1]:
        return cls
    suffix = {"s": " suited", "o": " offsuit"}.get(cls[2:], " (any suits)")
    return cls[:2] + suffix


def _rand_class(rng: Random, ranks: str) -> str:
    r1, r2 = rng.sample(ranks, 2)
    hi, lo = sorted((r1, r2), key=RANKS.index, reverse=True)
    kind = rng.choice(["pair", "s", "o", ""])
    return hi + hi if kind == "pair" else hi + lo + kind


def _unblocked(cls: str) -> int:
    if cls[0] == cls[1]:
        return 6
    return {"s": 4, "o": 12}.get(cls[2:], 16)


@register("combos_card_removal")
def combos_card_removal(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    ranks = BROADWAY if ctx.level == 1 else RANKS[4:]

    def attempt(r: Random) -> tuple[str, list[str]] | None:
        cls = _rand_class(r, ranks)
        board = deal(r, 3)
        # Make card removal actually matter most of the time.
        hits = sum(c[0] in cls[:2] for c in board)
        return (cls, board) if hits >= 1 or r.random() < 0.2 else None

    cls, board = retry(rng, attempt)
    live = len(combos_matching(cls, board))
    buckets, cid = make_buckets(rng, live, 1, "count", 0)
    full = _unblocked(cls)
    seen = Counter(c[0] for c in board if c[0] in cls[:2])
    seen_txt = ", ".join(f"{n} {r}" for r, n in seen.items()) or "none"
    return Instance(
        prompt=f"How many combos of **{class_label(cls)}** are possible on this board?",
        answer_type="bucket",
        unit="count",
        buckets=buckets,
        correct=cid,
        exact=live,
        scene={"board": board, "street": "flop"},
        shortcut="Pairs: C(n,2). Unpaired: n₁ × n₂ (suited: count matching suits only).",
        explanation_md=(
            f"Unblocked, {class_label(cls)} has {full} combos. "
            f"Board cards of those ranks: {seen_txt}. **{live} combos** remain."
        ),
    )


def _live(rank: str, dead: list[str]) -> int:
    return sum(1 for s in SUITS if rank + s not in dead)


@register("combos_pairs_on_board")
def combos_pairs_on_board(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    n = 3 if ctx.level == 1 else rng.choice([3, 4])

    def unpaired(r: Random) -> list[str] | None:
        b = deal(r, n)
        return b if len({c[0] for c in b}) == n else None

    board = retry(rng, unpaired)
    hero = [] if ctx.level == 1 else deal(rng, 2, board) if rng.random() < 0.6 else []
    dead = board + hero
    ranks = sorted({c[0] for c in board}, key=RANKS.index, reverse=True)
    what = rng.choice(["sets", "two pair", "top two pair"])
    if what == "sets":
        parts = {r: comb(_live(r, dead), 2) for r in ranks}
        detail = " + ".join(f"{plural_rank(r)} {v}" for r, v in parts.items())
    elif what == "two pair":
        parts = {f"{a}{b}": _live(a, dead) * _live(b, dead) for a, b in combinations(ranks, 2)}
        detail = " + ".join(f"{k} {v}" for k, v in parts.items())
    else:
        a, b = ranks[0], ranks[1]
        parts = {f"{a}{b}": _live(a, dead) * _live(b, dead)}
        detail = f"{a}{b}: {_live(a, dead)} × {_live(b, dead)}"
    total = sum(parts.values())
    buckets, cid = make_buckets(rng, total, 1, "count", 0)
    hero_txt = f" You hold {pretty(hero)}." if hero else ""
    return Instance(
        prompt=f"How many combos of **{what}** (using both hole cards) can villain have?{hero_txt}",
        answer_type="bucket",
        unit="count",
        buckets=buckets,
        correct=cid,
        exact=total,
        scene={"board": board, "hero": hero, "street": "flop" if n == 3 else "turn"},
        shortcut="Set of an unpaired board card: C(3,2) = 3. Two pair: 3 × 3 = 9.",
        explanation_md=f"{detail} = **{total}**. Cards you can see (board, your hand) are removed.",
    )


RANGE_POOL = [
    "AA",
    "KK",
    "QQ",
    "JJ",
    "TT",
    "99",
    "AK",
    "AKs",
    "AQ",
    "AQs",
    "KQ",
    "KQs",
    "AJs",
    "QJs",
]


@register("combos_range_count")
def combos_range_count(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    k = 2 if ctx.level == 1 else rng.choice([3, 4])

    def attempt(r: Random) -> list[str] | None:
        picks = r.sample(RANGE_POOL, k)
        keys = [p[:2] for p in picks]
        return picks if len(set(keys)) == len(keys) else None  # no overlapping classes

    rng_range = retry(rng, attempt)
    board = deal(rng, 3)
    parts = {cls: len(combos_matching(cls, board)) for cls in rng_range}
    total = sum(parts.values())
    buckets, cid = make_buckets(rng, total, 1, "count", 0)
    detail = " + ".join(f"{cls} {n}" for cls, n in parts.items())
    return Instance(
        prompt=f"Villain's range is **{{{', '.join(rng_range)}}}**. How many combos on this board?",
        answer_type="bucket",
        unit="count",
        buckets=buckets,
        correct=cid,
        exact=total,
        scene={"board": board, "street": "flop"},
        shortcut="Count each hand separately with card removal, then add.",
        explanation_md=f"{detail} = **{total}**. (`AK` = any suits, `AKs` = suited only.)",
    )


@register("blockers")
def blockers(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    suit = rng.choice(SUITS)
    sym = SUIT_SYMBOL[suit]
    others = [r for r in RANKS if r != "A"]
    board_ranks = rng.sample(others, 3)
    board = [r + suit for r in board_ranks]
    if ctx.level > 1 and rng.random() < 0.5:
        filler = retry(rng, lambda r: c if (c := deal(r, 1, board)[0])[1] != suit else None)
        board.append(filler)
    hero_spade = rng.random() < 0.6
    if hero_spade:
        candidates = [r + suit for r in "AKQJT98" if r + suit not in board]
        hero = [rng.choice(candidates)]
        hero.append(
            retry(rng, lambda r: c if (c := deal(r, 1, board, hero)[0])[1] != suit else None)
        )
    else:

        def offsuit_hand(r: Random) -> list[str] | None:
            h = deal(r, 2, board)
            return h if all(c[1] != suit for c in h) else None

        hero = retry(rng, offsuit_hand)
    left = 13 - 3 - sum(c[1] == suit for c in hero)
    holds_ace = ("A" + suit) in hero
    if holds_ace or rng.random() < 0.5:
        question = f"flush combos (two {sym} cards)"
        total = comb(left, 2)
        detail = f"{sym} left: 13 − 3 on board{' − 1 in your hand' if hero_spade else ''} = {left}. C({left}, 2) = **{total}**."
    else:
        question = f"nut flush combos (A{sym} + another {sym})"
        total = left - 1
        detail = (
            f"Villain needs A{sym} plus one of the other {sym}: {left} {sym} left, minus the ace = **{total}**."
            + (" Your card in the suit is one fewer for villain." if hero_spade else "")
        )
    buckets, cid = make_buckets(rng, total, 1, "count", 0)
    return Instance(
        prompt=f"How many **{question}** can villain have?",
        answer_type="bucket",
        unit="count",
        buckets=buckets,
        correct=cid,
        exact=total,
        scene={"hero": hero, "board": board, "street": "flop" if len(board) == 3 else "turn"},
        shortcut="Count the suit's cards you can't see; your own suited card is a blocker.",
        explanation_md=detail,
    )
