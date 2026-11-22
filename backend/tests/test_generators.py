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


# ---------------------------------------------------------------- M3 math
from app.generators.poker.capstone import _combos  # noqa: E402
from app.generators.poker.s5_preflop import preflop_equity  # noqa: E402
from app.generators.poker.s6_betting import bluff_share, breakeven, mdf_of  # noqa: E402
from app.generators.poker.s7_implied import implied_needed  # noqa: E402
from app.generators.poker.s8_stacks import geometric_fraction  # noqa: E402
from app.generators.poker.s9_ev import (  # noqa: E402
    ev_bluff,
    ev_call,
    required_fold_equity,
    shove_ev,
)


def test_preflop_equity_known_matchups() -> None:
    assert preflop_equity(("As", "Ad"), ("Kh", "Kc")) == pytest.approx(0.82, abs=0.01)
    assert preflop_equity(("As", "Kd"), ("Qh", "Qc")) == pytest.approx(0.43, abs=0.01)
    assert preflop_equity(("2s", "2d"), ("Ah", "Kc")) == pytest.approx(0.53, abs=0.01)
    assert preflop_equity(("As", "Kd"), ("Ah", "Qc")) == pytest.approx(0.74, abs=0.015)


def test_betting_identities() -> None:
    spot = Spot(pot=100, bet=75, fmt="online")
    assert breakeven(spot) + mdf_of(spot) == pytest.approx(1)
    assert bluff_share(spot) == pytest.approx(required_equity(spot))
    # A bluff at exactly breakeven fold% has zero EV.
    assert ev_bluff(100, 75, breakeven(spot)) == pytest.approx(0)


def test_geometric_sizing_gets_stacks_in() -> None:
    for pot, stack, n in [(100, 400, 3), (60, 90, 2), (10, 95, 3)]:
        f = geometric_fraction(pot, stack, n)
        p, behind = float(pot), float(stack)
        for _ in range(n):
            bet = f * p
            p += 2 * bet
            behind -= bet
        assert behind == pytest.approx(0, abs=1e-6)


def test_ev_formulas() -> None:
    # Call 50 into 150 (incl. bet) with 25% equity: exactly breakeven.
    assert ev_call(150, 50, 0.25) == pytest.approx(0)
    # Shove at the break-even fold frequency has zero EV.
    for pot, stack, eq in [(100, 300, 0.35), (40, 90, 0.32), (200, 420, 0.35)]:
        f = required_fold_equity(pot, stack, eq)
        assert 0 < f < 1
        assert shove_ev(pot, stack, f, eq) == pytest.approx(0, abs=1e-9)


def test_implied_odds_makes_call_break_even() -> None:
    spot = Spot(pot=100, bet=50, fmt="online")
    eq = 9 / 47
    extra = implied_needed(spot, eq)
    assert eq * (spot.pot + 2 * spot.bet + extra) - spot.bet == pytest.approx(0)


def test_bluffcatch_recount() -> None:
    assert _combos(["KK", "AKs"], ["Kh", "7c", "2d", "9s", "3h"]) == {"KK": 3, "AKs": 3}


@pytest.mark.parametrize(
    ("key", "positive"),
    [
        ("set_mining", "call"),
        ("spot_set_mine", "call"),
        ("implied_call", "call"),
        ("ev_shove", "raise"),
        ("spot_draw_call", "call"),
        ("spot_river_bluffcatch", "call"),
    ],
)
def test_m3_decisions_are_balanced(key: str, positive: str) -> None:
    picks = [generate(key, s, {}, GenContext("live", 2)).correct for s in range(150)]
    assert 0.3 < picks.count(positive) / len(picks) < 0.7


@pytest.mark.parametrize("key", ["bluff_or_check", "spot_flop_commit", "spr_classify"])
def test_m3_choices_are_balanced(key: str) -> None:
    picks = [generate(key, s, {}, GenContext("online", 1)).correct for s in range(150)]
    n = len(set(picks))
    assert all(picks.count(c) / len(picks) > 0.5 / n for c in set(picks))


def test_implied_payoff_never_exceeds_villains_stack() -> None:
    for s in range(100):
        inst = generate("implied_call", s, {}, GenContext("online", 2))
        assert inst.scene is not None
        assert "left" in inst.prompt and inst.scene["villain_stack"] > 0
