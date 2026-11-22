"""Generator correctness. A wrong answer key trains wrong instincts, so these are strict."""

from itertools import combinations
from math import comb
from random import Random

import pytest

from app.generators.base import GenContext, Instance, generate, make_buckets
from app.generators.cards import combos_matching, evaluate, remaining
from app.generators.money import Spot
from app.generators.poker.s1_number_fluency import bluff_breakeven, call_equity, mdf
from app.generators.poker.s3_outs import flop_equity, outs_to, turn_equity
from app.generators.poker.s4_pot_odds import required_equity
from app.generators.registry import REGISTRY

CONTEXTS = [GenContext(fmt, lvl) for fmt in ("live", "online") for lvl in (1, 2, 3)]
SEEDS = range(40)


@pytest.mark.parametrize("key", sorted(REGISTRY))
def test_every_generator_produces_valid_deterministic_instances(key: str) -> None:
    for ctx in CONTEXTS:
        for seed in SEEDS:
            a = generate(key, seed, {}, ctx)
            b = generate(key, seed, {}, ctx)
            assert isinstance(a, Instance)
            assert a == b, f"{key} not deterministic for seed {seed}"
            assert a.prompt and a.explanation_md and a.shortcut
            if a.answer_type == "bucket" and isinstance(a.exact, (int, float)):
                bucket = a.buckets[a.correct]  # type: ignore[index]
                if a.unit == "count":
                    assert bucket["lo"] == round(a.exact)
                else:
                    assert bucket["lo"] <= a.exact < bucket["hi"], (key, seed, a.exact, bucket)
            if a.scene:
                cards = [
                    *a.scene.get("hero", []),
                    *a.scene.get("villain", []),
                    *a.scene.get("board", []),
                ]
                assert len(cards) == len(set(cards)), f"{key}: duplicate cards {cards}"


def test_correct_slot_is_uniform_when_bounds_allow() -> None:
    rng = Random(1)
    slots = [make_buckets(rng, 50, 6, "percent", 0, 100)[1] for _ in range(1000)]
    assert all(150 < slots.count(i) < 250 for i in range(5))


# ---------------------------------------------------------------- buckets
@pytest.mark.parametrize("width", [1, 4, 6, 10])
def test_buckets_contain_exact_and_respect_bounds(width: int) -> None:
    rng = Random(0)
    for _ in range(2000):
        exact = rng.uniform(0, 100) if width > 1 else rng.randint(0, 60)
        buckets, cid = make_buckets(rng, exact, width, "percent" if width > 1 else "count", 0, 100)
        assert len(buckets) == 5
        assert all(b["lo"] >= 0 and b["hi"] <= 100 + width for b in buckets)
        assert all(buckets[i + 1]["lo"] == buckets[i]["hi"] for i in range(4))
        b = buckets[cid]
        assert (b["lo"] == round(exact)) if width == 1 else (b["lo"] <= exact < b["hi"])


# ---------------------------------------------------------------- math, checked independently
def test_table_values() -> None:
    expected = {
        1 / 3: (20, 25, 75),
        0.5: (25, 33, 67),
        0.75: (30, 43, 57),
        1: (33, 50, 50),
        2: (40, 67, 33),
    }
    for f, (c, b, m) in expected.items():
        assert round(call_equity(f) * 100) == c
        assert round(bluff_breakeven(f) * 100) == b
        assert round(mdf(f) * 100) == m


def test_pot_odds_matches_definition() -> None:
    spot = Spot(pot=100, bet=50, fmt="online")
    assert required_equity(spot) == pytest.approx(50 / 200)
    assert required_equity(spot, extra_callers=1) == pytest.approx(50 / 250)


@pytest.mark.parametrize("outs", [4, 8, 9, 12, 15])
def test_flop_equity_matches_enumeration(outs: int) -> None:
    unseen = list(range(47))
    hits = sum(1 for a, b in combinations(unseen, 2) if a < outs or b < outs)
    assert flop_equity(outs) == pytest.approx(hits / comb(47, 2))
    assert turn_equity(outs) == pytest.approx(outs / 46)


def test_outs_known_draws() -> None:
    assert len(outs_to(["Ah", "Kh"], ["Qh", "7h", "2c"])) == 9  # nut flush draw
    assert len(outs_to(["9c", "8d"], ["7h", "6s", "2c"])) == 8  # open-ender
    assert len(outs_to(["9c", "8d"], ["Jh", "7s", "2c"])) == 4  # gutshot (T)
    assert len(outs_to(["9h", "8h"], ["7h", "6h", "2c"])) == 15  # flush + open-ender
    # board makes the straight on its own → hero's cards don't play, not outs
    assert "9d" not in outs_to(["2c", "2d"], ["8h", "7s", "6c", "5d"])


def test_combos_with_card_removal() -> None:
    assert len(combos_matching("AK", ["Ah", "7c", "2d"])) == 12
    assert len(combos_matching("AA", ["Ah", "7c", "2d"])) == 3
    assert len(combos_matching("AKs", ["Ah", "7c", "2d"])) == 3
    assert len(combos_matching("AKo", [])) == 12


def test_nuts_cannot_be_beaten() -> None:
    for seed in range(15):
        inst = generate("the_nuts", seed, {}, GenContext(level=3))
        board = inst.scene["board"]  # type: ignore[index]
        label = inst.choices[inst.correct]["label"]  # type: ignore[index]
        sym = {"♣": "c", "♦": "d", "♥": "h", "♠": "s"}
        nut = [c[0] + sym[c[1]] for c in label.split()]
        nut_value = evaluate([*nut, *board])
        best = max(evaluate([a, b, *board]) for a, b in combinations(remaining(board), 2))
        assert nut_value == best


def test_dirty_outs_recount() -> None:
    for seed in range(10):
        inst = generate("outs_dirty", seed, {}, GenContext())
        s = inst.scene
        assert s is not None
        hero, villain, board = s["hero"], s["villain"], s["board"]
        wins = sum(
            1
            for c in remaining(hero, villain, board)
            if evaluate([*hero, *board, c]) > evaluate([*villain, *board, c])
        )
        assert wins == inst.exact


def test_draw_decisions_are_balanced() -> None:
    """Neither 'always fold' nor 'always call' should score well."""
    for key, call_value in (("call_or_fold_draw", "call"), ("pot_odds_vs_draw", 0)):
        for ctx in (GenContext("live", 1), GenContext("online", 2)):
            picks = [generate(key, s, {}, ctx).correct for s in range(200)]
            share = picks.count(call_value) / len(picks)
            assert 0.35 < share < 0.65, (key, ctx, share)
