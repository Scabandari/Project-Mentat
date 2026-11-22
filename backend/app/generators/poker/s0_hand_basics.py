"""Section 0: Hand basics."""

from collections import Counter
from collections.abc import Sequence
from itertools import combinations
from random import Random
from typing import Any

from app.generators.base import GenContext, Instance, make_choices, ordered_choices, register, retry
from app.generators.cards import (
    CATEGORIES,
    CATEGORY_LABEL,
    board_paired,
    category,
    deal,
    evaluate,
    flush_possible,
    pretty,
    rank_of,
    remaining,
    straight_possible,
)


def best_five(cards: Sequence[str]) -> list[str]:
    best = max(combinations(cards, 5), key=evaluate)
    return sorted(best, key=rank_of, reverse=True)


def describe(cards: Sequence[str]) -> str:
    five = best_five(cards)
    return f"{CATEGORY_LABEL[category(five)]} ({pretty(five)})"


@register("rankings_order")
def rankings_order(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    span = 2 if ctx.level == 1 else 8
    a = rng.randrange(1, len(CATEGORIES))
    b = rng.choice([x for x in range(1, len(CATEGORIES)) if 0 < abs(x - a) <= span])
    hi, lo = max(a, b), min(a, b)
    la, lb = CATEGORY_LABEL[CATEGORIES[a]], CATEGORY_LABEL[CATEGORIES[b]]
    correct = CATEGORY_LABEL[CATEGORIES[hi]]
    choices, cid = ordered_choices([la, lb], correct)
    order = " > ".join(CATEGORY_LABEL[c] for c in reversed(CATEGORIES[lo : hi + 1]))
    return Instance(
        prompt=f"Which ranks higher: **{la}** or **{lb}**?",
        answer_type="choice",
        choices=choices,
        correct=cid,
        exact=correct,
        shortcut="Rarer hands rank higher.",
        explanation_md=f"**{correct}** wins.\n\n{order}",
    )


@register("best_five")
def best_five_gen(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    def attempt(r: Random) -> tuple[list[str], list[str]] | None:
        hero = deal(r, 2)
        board = deal(r, 5, hero)
        # skew away from high card / one pair, which random deals produce most of the time
        idx = CATEGORIES.index(category(hero + board))
        return (hero, board) if idx >= 2 or r.random() < 0.25 else None

    hero, board = retry(rng, attempt)
    cat = category(hero + board)
    idx = CATEGORIES.index(cat)
    near = [CATEGORY_LABEL[c] for i, c in enumerate(CATEGORIES) if 0 < abs(i - idx) <= 3]
    choices, cid = make_choices(rng, CATEGORY_LABEL[cat], near)
    five = best_five(hero + board)
    return Instance(
        prompt="What's your best five-card hand?",
        answer_type="choice",
        choices=choices,
        correct=cid,
        exact=CATEGORY_LABEL[cat],
        scene={"hero": hero, "board": board, "street": "river"},
        shortcut="Best 5 of 7. Check flush and straight first, then pairs.",
        explanation_md=f"**{CATEGORY_LABEL[cat]}**: {pretty(five)}",
    )


def _showdown(rng: Random, want_same_category: bool) -> tuple[list[str], list[str], list[str]]:
    def attempt(r: Random) -> tuple[list[str], list[str], list[str]] | None:
        hero = deal(r, 2)
        villain = deal(r, 2, hero)
        board = deal(r, 5, hero, villain)
        same = category(hero + board) == category(villain + board)
        return (hero, villain, board) if same == want_same_category else None

    return retry(rng, attempt)


def _result(hero: list[str], villain: list[str], board: list[str]) -> str:
    h, v = evaluate(hero + board), evaluate(villain + board)
    return "Hero" if h > v else "Villain" if v > h else "Split"


@register("winner_showdown")
def winner_showdown(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    hero, villain, board = _showdown(rng, want_same_category=rng.random() < 0.4)
    result = _result(hero, villain, board)
    choices, cid = ordered_choices(["Hero", "Villain", "Split"], result)
    return Instance(
        prompt="Who wins at showdown?",
        answer_type="choice",
        choices=choices,
        correct=cid,
        exact=result,
        scene={"hero": hero, "villain": villain, "board": board, "street": "river"},
        shortcut="Name both best-five hands, compare category, then ranks, then kickers.",
        explanation_md=(
            f"**{result}{'' if result == 'Split' else ' wins'}.**\n\n"
            f"- Hero: {describe(hero + board)}\n- Villain: {describe(villain + board)}"
        ),
    )


def _pair_rank(cards: Sequence[str]) -> str | None:
    counts = Counter(c[0] for c in cards)
    pairs = [r for r, n in counts.items() if n == 2]
    return pairs[0] if len(pairs) == 1 else None


@register("kicker_plays")
def kicker_plays(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    def attempt(r: Random) -> tuple[list[str], list[str], list[str]] | None:
        hero = deal(r, 2)
        villain = deal(r, 2, hero)
        board = deal(r, 5, hero, villain)
        if category(hero + board) != "Pair" or category(villain + board) != "Pair":
            return None
        hp, vp = _pair_rank(best_five(hero + board)), _pair_rank(best_five(villain + board))
        return (hero, villain, board) if hp and hp == vp else None

    hero, villain, board = retry(rng, attempt, tries=20_000)
    result = _result(hero, villain, board)
    choices, cid = ordered_choices(["Hero", "Villain", "Split"], result)
    note = (
        "The board's kickers are higher than both hands' side cards, so the board plays."
        if result == "Split"
        else "Same pair, so the highest kicker in each best five decides."
    )
    return Instance(
        prompt="Both players have the same pair. Who wins?",
        answer_type="choice",
        choices=choices,
        correct=cid,
        exact=result,
        scene={"hero": hero, "villain": villain, "board": board, "street": "river"},
        shortcut="Only five cards play. Compare kickers in order, top down.",
        explanation_md=(
            f"**{result}{'' if result == 'Split' else ' wins'}.** {note}\n\n"
            f"- Hero: {describe(hero + board)}\n- Villain: {describe(villain + board)}"
        ),
    )


_PROPERTIES = {
    "a flush": (flush_possible, "a flush needs three cards of one suit on the board"),
    "a straight": (
        straight_possible,
        "a straight needs three board cards that fit within five consecutive ranks",
    ),
    "a full house": (board_paired, "a full house needs a paired board"),
}


@register("board_possible")
def board_possible(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    name = rng.choice(list(_PROPERTIES))
    check, rule = _PROPERTIES[name]
    want = rng.random() < 0.5
    n = rng.choice([3, 4, 5]) if ctx.level > 1 else 3
    board = retry(rng, lambda r: b if check(b := deal(r, n)) == want else None)
    answer = "Yes" if want else "No"
    choices, cid = ordered_choices(["Yes", "No"], answer)
    return Instance(
        prompt=f"Could any player hold **{name}** on this board?",
        answer_type="choice",
        choices=choices,
        correct=cid,
        exact=answer,
        scene={"board": board},
        shortcut="Flush: 3 suited. Straight: 3 within a 5-rank window. Boat: paired board.",
        explanation_md=f"**{answer}**: {rule}.",
    )


@register("the_nuts")
def the_nuts(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    n = 3 if ctx.level == 1 else rng.choice([3, 4, 5])
    board = deal(rng, n)
    best: dict[int, tuple[str, str]] = {}
    for a, b in combinations(remaining(board), 2):
        v = evaluate([a, b, *board])
        pair = tuple(sorted((a, b), key=rank_of, reverse=True))
        cur = best.get(v)
        if cur is None or [rank_of(c) for c in pair] > [rank_of(c) for c in cur]:
            best[v] = pair  # type: ignore[assignment]
    values = sorted(best, reverse=True)
    nut = pretty(best[values[0]])
    # Distractors: the best hand of each weaker category first (variety), then near-nuts.
    by_cat: dict[str, int] = {}
    for v in values[1:]:
        by_cat.setdefault(category([*best[v], *board]), v)
    ordered = [v for v in values[1:] if v in by_cat.values()] + values[1:]
    labels = [nut]
    for v in ordered:
        label = pretty(best[v])
        if label not in labels:
            labels.append(label)
        if len(labels) == 5:
            break
    choices, cid = make_choices(rng, nut, labels[1:])
    nut_desc = describe([*best[values[0]], *board])
    return Instance(
        prompt="Which hand is **the nuts** on this board?",
        answer_type="choice",
        choices=choices,
        correct=cid,
        exact=nut,
        scene={"board": board, "street": {3: "flop", 4: "turn", 5: "river"}[n]},
        shortcut="Check straight flush → quads → full house → flush → straight, top down.",
        explanation_md=f"**{nut}** makes {nut_desc}. Nothing can beat it on this board.",
    )
