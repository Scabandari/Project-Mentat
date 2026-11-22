"""Card helpers on top of eval7. Cards travel as 2-char strings like 'Ah', 'Td'."""

from collections.abc import Iterable, Sequence
from itertools import combinations
from random import Random

import eval7  # type: ignore[import-untyped]

RANKS = "23456789TJQKA"
SUITS = "cdhs"
DECK: tuple[str, ...] = tuple(r + s for r in RANKS for s in SUITS)
SUIT_SYMBOL = {"c": "♣", "d": "♦", "h": "♥", "s": "♠"}
RANK_NAME = {
    "2": "Two", "3": "Three", "4": "Four", "5": "Five", "6": "Six", "7": "Seven",
    "8": "Eight", "9": "Nine", "T": "Ten", "J": "Jack", "Q": "Queen", "K": "King", "A": "Ace",
}  # fmt: skip
PLURAL = {"Six": "Sixes"}

# Weakest → strongest, as eval7.handtype names them.
CATEGORIES = (
    "High Card", "Pair", "Two Pair", "Trips", "Straight",
    "Flush", "Full House", "Quads", "Straight Flush",
)  # fmt: skip
CATEGORY_LABEL = {
    "High Card": "High card", "Pair": "One pair", "Two Pair": "Two pair",
    "Trips": "Three of a kind", "Straight": "Straight", "Flush": "Flush",
    "Full House": "Full house", "Quads": "Four of a kind", "Straight Flush": "Straight flush",
}  # fmt: skip

_CACHE: dict[str, eval7.Card] = {c: eval7.Card(c) for c in DECK}


def rank_of(card: str) -> int:
    return RANKS.index(card[0])


def pretty(cards: Iterable[str]) -> str:
    return " ".join(c[0] + SUIT_SYMBOL[c[1]] for c in cards)


def plural_rank(r: str) -> str:
    name = RANK_NAME[r]
    return PLURAL.get(name, name + "s")


def evaluate(cards: Sequence[str]) -> int:
    return int(eval7.evaluate([_CACHE[c] for c in cards]))


def category(cards: Sequence[str]) -> str:
    return str(eval7.handtype(evaluate(cards)))


def category_index(cards: Sequence[str]) -> int:
    return CATEGORIES.index(category(cards))


def remaining(*known: Iterable[str]) -> list[str]:
    seen = {c for group in known for c in group}
    return [c for c in DECK if c not in seen]


def deal(rng: Random, n: int, *exclude: Iterable[str]) -> list[str]:
    return rng.sample(remaining(*exclude), n)


def combos_matching(hand_class: str, dead: Iterable[str] = ()) -> list[tuple[str, str]]:
    """Live combos of a hand class like 'AA', 'AKs', 'AKo', 'AK' given dead cards."""
    dead_set = set(dead)
    r1, r2 = hand_class[0], hand_class[1]
    kind = hand_class[2] if len(hand_class) == 3 else ""
    live1 = [r1 + s for s in SUITS if r1 + s not in dead_set]
    if r1 == r2:
        return list(combinations(live1, 2))
    live2 = [r2 + s for s in SUITS if r2 + s not in dead_set]
    out = []
    for a in live1:
        for b in live2:
            suited = a[1] == b[1]
            if (kind == "s" and not suited) or (kind == "o" and suited):
                continue
            out.append((a, b))
    return out


def straight_possible(board: Sequence[str]) -> bool:
    """Can two hole cards complete a straight with this board?"""
    ranks = {rank_of(c) for c in board}
    if 12 in ranks:
        ranks.add(-1)  # ace plays low
    return any(len(ranks & set(range(lo, lo + 5))) >= 3 for lo in range(-1, 9))


def flush_possible(board: Sequence[str]) -> bool:
    return any(sum(c[1] == s for c in board) >= 3 for s in SUITS)


def board_paired(board: Sequence[str]) -> bool:
    ranks = [c[0] for c in board]
    return len(set(ranks)) < len(ranks)
