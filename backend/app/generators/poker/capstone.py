"""Mixed spots: real hands that chain two or three sections, the way the table asks."""

from random import Random
from typing import Any

from app.generators.base import (
    GenContext,
    Instance,
    ordered_choices,
    pct,
    register,
    retry,
)
from app.generators.cards import RANKS, SUITS, combos_matching, deal, pretty
from app.generators.money import Spot, make_spot, make_stacks
from app.generators.poker.s3_outs import _draw_spot, describe_outs, flop_equity
from app.generators.poker.s4_pot_odds import _setup
from app.generators.poker.s5_preflop import _set_mining_instance, set_mining_spot
from app.generators.poker.s8_stacks import spr_band


@register("spot_draw_call")
def spot_draw_call(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    """Outs (3) → equity with two cards (3) → price (4) → decision."""
    want_call = rng.random() < 0.5

    def attempt(r: Random) -> Any:
        hero, board, outs = _draw_spot(r, 3, {4, 8, 9, 12, 15})
        spot = make_spot(r, ctx)
        shove = make_stacks(r, ctx, spot, 0.5, 2.5)
        eq = flop_equity(len(outs))
        need = shove / (spot.pot + 2 * shove)
        if abs(eq - need) < 0.04 or (eq >= need) != want_call:
            return None
        return hero, board, outs, spot, shove, eq, need

    hero, board, outs, spot, shove, eq, need = retry(rng, attempt, tries=1000)
    action = "call" if want_call else "fold"
    m = spot.money
    return Instance(
        prompt=_setup(spot)
        + f"Villain shoves **{m(shove)}** on the flop. You're covered. Call or fold?",
        answer_type="action",
        actions=["fold", "call"],
        correct=action,
        exact=action,
        scene={"pot": spot.pot, "bet": shove, "hero": hero, "board": board, "street": "flop"},
        shortcut="All-in on the flop → two cards to come → outs × 4.",
        explanation_md=(
            f"**{action.capitalize()}.**\n\n1. **Outs: {len(outs)}**\n{describe_outs(outs)}\n"
            f"2. **Equity** (two cards): ≈ {len(outs)} × 4 → exact **{pct(eq)}**\n"
            f"3. **Price**: {m(shove)} ÷ {m(spot.pot + 2 * shove)} = **{pct(need)}**"
        ),
    )


def _rank_classes(board: list[str], hero: list[str]) -> tuple[list[str], list[str]]:
    """A polarised river range on this board: sets/two pair for value, unpaired
    suited broadways and connectors (missed draws) as bluffs."""
    ranks = sorted({c[0] for c in board}, key=RANKS.index, reverse=True)
    value = [r + r for r in ranks[:3]] + [ranks[0] + ranks[1] + "s", ranks[0] + ranks[1] + "o"]
    bluff_pool = [
        "QJs",
        "JTs",
        "T9s",
        "98s",
        "87s",
        "76s",
        "65s",
        "KQs",
        "KJs",
        "QTs",
        "A5s",
        "A4s",
    ]
    bluffs = [b for b in bluff_pool if b[0] not in ranks and b[1] not in ranks]
    return value, bluffs


def _combos(classes: list[str], dead: list[str]) -> dict[str, int]:
    return {c: len(combos_matching(c, dead)) for c in classes}


@register("spot_river_bluffcatch")
def spot_river_bluffcatch(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    """Combos with card removal (2) → bluff share → price (1/4) → decision."""
    want_call = rng.random() < 0.5

    def attempt(r: Random) -> Any:
        board = deal(r, 5)
        if len({c[0] for c in board}) < 5:
            return None
        top = max(board, key=lambda c: RANKS.index(c[0]))
        kicker = r.choice([x for x in RANKS if x not in {c[0] for c in board}])
        hero = [
            top[0] + r.choice([s for s in SUITS if top[0] + s not in board]),
            kicker + r.choice(SUITS),
        ]
        if len(set(hero + board)) < 7:
            return None
        value_cls, bluff_cls = _rank_classes(board, hero)
        # Range shape follows the target answer, otherwise bluff-heavy reads dominate.
        n_value = r.choice([2, 3]) if want_call else r.choice([4, 5])
        n_bluff = r.choice([2, 3, 4]) if want_call else r.choice([1, 2])
        if len(bluff_cls) < n_bluff:
            return None
        value = _combos(r.sample(value_cls, n_value), board + hero)
        bluffs = _combos(r.sample(bluff_cls, n_bluff), board + hero)
        v, b = sum(value.values()), sum(bluffs.values())
        if not v or not b:
            return None
        spot = make_spot(r, ctx, 0.5, 1.5)
        share = b / (v + b)
        need = spot.bet / (spot.pot + 2 * spot.bet)
        if abs(share - need) < 0.05 or (share >= need) != want_call:
            return None
        return board, hero, value, bluffs, v, b, spot, share, need

    board, hero, value, bluffs, v, b, spot, share, need = retry(rng, attempt, tries=5000)
    action = "call" if want_call else "fold"
    m = spot.money

    def fmt_range(d: dict[str, int]) -> str:
        return ", ".join(d)

    def counted(d: dict[str, int]) -> str:
        return " + ".join(f"{k} {n}" for k, n in d.items())

    return Instance(
        prompt=(
            _setup(spot)
            + f"River. Villain bets **{m(spot.bet)}**. You read his range as value **{{{fmt_range(value)}}}** "
            f"and bluffs **{{{fmt_range(bluffs)}}}**. Your top pair beats only the bluffs. Call or fold?"
        ),
        answer_type="action",
        actions=["fold", "call"],
        correct=action,
        exact=action,
        scene={"pot": spot.pot, "bet": spot.bet, "hero": hero, "board": board, "street": "river"},
        shortcut="Bluff share of his range vs the price: call if bluffs ÷ total ≥ B / (P + 2B).",
        explanation_md=(
            f"**{action.capitalize()}.**\n\n"
            f"1. **Value combos** (card removal from board and your hand): {counted(value)} = **{v}**\n"
            f"2. **Bluff combos**: {counted(bluffs)} = **{b}**\n"
            f"3. **You win** {b} ÷ {v + b} = **{pct(share)}**\n"
            f"4. **Price**: {m(spot.bet)} ÷ {m(spot.pot + 2 * spot.bet)} = **{pct(need)}**"
        ),
    )


COMMIT = ["Get it in", "Keep the pot small"]


@register("spot_flop_commit")
def spot_flop_commit(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    """Effective stack (8) → SPR (8) → plan with top pair."""
    want_commit = rng.random() < 0.5

    def attempt(r: Random) -> tuple[Spot, float, float] | None:
        spot = make_spot(r, ctx)
        eff = make_stacks(r, ctx, spot, 1.0, 18.0)
        spr = eff / spot.pot
        if (want_commit and spr >= 3.5) or (not want_commit and spr <= 11):
            return None
        other = make_stacks(r, ctx, spot, spr * 1.2, spr * 3)
        return spot, eff, other

    spot, eff, other = retry(rng, attempt)
    hero_deep = rng.random() < 0.5
    hero_stack, villain_stack = (other, eff) if hero_deep else (eff, other)
    spr = eff / spot.pot

    def board_and_hand(r: Random) -> tuple[list[str], list[str]] | None:
        board = deal(r, 3)
        top = max(board, key=lambda c: RANKS.index(c[0]))
        if top[0] in "2345" or len({c[0] for c in board}) < 3:
            return None
        kicker = r.choice([x for x in "AKQJT" if x not in {c[0] for c in board}] or ["9"])
        hero = [
            top[0] + r.choice([s for s in SUITS if top[0] + s not in board]),
            kicker + r.choice(SUITS),
        ]
        return (board, hero) if len(set(board + hero)) == 5 else None

    board, hero = retry(rng, board_and_hand)
    answer = COMMIT[0] if want_commit else COMMIT[1]
    choices, cid = ordered_choices(COMMIT, answer)
    m = spot.money
    return Instance(
        prompt=(
            _setup(spot) + f"Your stack **{m(hero_stack)}**, villain's **{m(villain_stack)}**. "
            f"You flop top pair, good kicker ({pretty(hero)}). What's your plan?"
        ),
        answer_type="choice",
        choices=choices,
        correct=cid,
        exact=answer,
        scene={
            "pot": spot.pot,
            "hero": hero,
            "board": board,
            "hero_stack": hero_stack,
            "villain_stack": villain_stack,
            "street": "flop",
        },
        shortcut="Effective stack ÷ pot. Under ~4: commit with top pair. Over ~10: pot control.",
        explanation_md=(
            f"**{answer}.** Effective stack is the smaller one, {m(eff)}; SPR = {m(eff)} ÷ {m(spot.pot)} "
            f"= **{spr:.1f}** ({spr_band(spr).lower()}). "
            + (
                "With so little behind, top pair good kicker is strong enough to stack off."
                if want_commit
                else "This deep, one pair rarely wants to play for stacks; keep the pot manageable."
            )
        ),
    )


@register("spot_set_mine")
def spot_set_mine(rng: Random, params: dict[str, Any], ctx: GenContext) -> Instance:
    """Effective stack (8) → implied odds (7) → set-mining rule (5)."""
    s = set_mining_spot(rng, ctx, short_villain=True)
    return _set_mining_instance(
        s,
        "",
        "Implied odds come from villain's stack, not yours: use the effective stack.",
    )
