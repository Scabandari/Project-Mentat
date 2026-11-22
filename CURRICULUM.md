# Poker Math Curriculum (pack: `poker-math`)

Audience: **beginner**, NLHE. Goal: compute or recall every number you need at the table, fast.

## How it's structured

- **11 sections** (0–10) plus a **capstone**, ordered by dependency.
- Each section opens with a short **lesson** (Learn mode): concept, formula, one worked example, the mental shortcut.
- Card kinds:
  - **Fact**: memorise it (`choice`, sometimes `flip`). Static.
  - **Calc**: compute a number (`bucket`, 5 choices). Generated.
  - **Decision**: full spot → `action` (fold/call/raise). Generated.
- **Soft gating:** next section unlocks at ~70% mastery of the previous one; you can always skip ahead.
- **Difficulty ramp (per card, automatic):** L1 round numbers, single concept → L2 realistic numbers → L3 awkward numbers, combined concepts. Level rises as FSRS stability grows.
- **Target times** below are beginner defaults; they tighten as the card's level rises.

### Live vs. online (user toggle)

The math is identical; presentation changes. Every generator renders in the active format.

| | Live | Online |
|---|---|---|
| Units | Dollars (`$85 into $140`) | Big blinds (`6.5bb into 11bb`) |
| Stakes | $1/2, $2/5, $5/10 | 100bb-deep blind levels |
| Bet sizes | Rounded to $5/$25 chips, often "uneven" (`$65 into $110`) | Pot fractions (33%, 50%, 75%, 125%) |
| Stacks | $200–$1,500, often uneven effective stacks | 100bb standard, 40–250bb variants |
| Prompt style | "Villain bets $60 into $95" | "Villain bets 75% pot" |

Online cards train **fractions → %** (table lookup); live cards train **dollars → fraction → %** (division first). Both are worth drilling; the toggle picks your default.

---

## 0. Hand Basics

Prerequisite for everything else. A beginner cannot count outs without reading boards.

**Lesson:** hand rankings, kickers, best-5-of-7, what "the nuts" means.

| Card | Kind | Asks | Target |
|---|---|---|---|
| `rankings-order` | Fact | Which hand ranks higher? (e.g. flush vs. straight) | 5s |
| `winner-showdown` | Calc→choice | Board + two hands → who wins / split | 12s |
| `best-five` | Calc→choice | Hole cards + board → your hand's name | 10s |
| `kicker-plays` | Calc→choice | Same pair, different kickers → winner or split | 12s |
| `board-possible` | Calc→choice | Is a flush / straight / full house possible on this board? | 8s |
| `the-nuts` | Calc→choice | What is the nuts on this board? | 15s |

---

## 1. Number Fluency

The highest-ROI section. Most table math is a lookup from these tables.

**Lesson:** ratio ↔ % ↔ fraction; why bet size as a fraction of pot is the only thing that matters.

| Card | Kind | Asks | Target |
|---|---|---|---|
| `ratio-to-pct` | Calc | `3:1` → `25%` | 5s |
| `pct-to-ratio` | Calc | `20%` → `4:1` | 5s |
| `bet-as-fraction` | Calc | `$65 into $100` → ≈⅔ pot (live) / skipped online | 6s |
| `table-call-equity` | Fact | Bet size → required call equity | 5s |
| `table-bluff-breakeven` | Fact | Bet size → how often the bluff must work | 5s |
| `table-mdf` | Fact | Bet size → minimum defense frequency | 5s |

**The table to memorise:**

| Bet (× pot) | Call needs equity | Bluff must work | MDF |
|---|---|---|---|
| ⅓ | 20% | 25% | 75% |
| ½ | 25% | 33% | 67% |
| ⅔ | 29% | 40% | 60% |
| ¾ | 30% | 43% | 57% |
| Pot | 33% | 50% | 50% |
| 2× | 40% | 67% | 33% |

Formulas (bet `B`, pot before bet `P`): call equity `B / (P + 2B)` · bluff breakeven `B / (P + B)` · MDF `P / (P + B)`.

---

## 2. Combinatorics

**Lesson:** 52 cards → 1,326 starting hands (169 distinct). Card removal.

| Card | Kind | Asks | Target |
|---|---|---|---|
| `combos-basic` | Fact | Combos of a pair / suited / offsuit / any unpaired hand (6 / 4 / 12 / 16) | 5s |
| `combos-total` | Fact | Total starting hands; distinct hands (1,326 / 169) | 5s |
| `combos-card-removal` | Calc | Combos of AK when an A is on the board (12) | 12s |
| `combos-pairs-on-board` | Calc | Combos of a set / two pair given the board | 15s |
| `combos-range-count` | Calc | Count combos in a small range given the board (e.g. `{AA, KK, AK}` on `K72`) | 25s |
| `blockers` | Calc | Holding the A♠ on a three-spade board: how many nut flush combos can villain have? | 15s |

---

## 3. Outs & Draws

**Lesson:** an out is a card that makes you the likely winner. Clean vs. dirty outs. Rule of 2 and 4.

| Card | Kind | Asks | Target |
|---|---|---|---|
| `outs-draw-types` | Fact | Outs for flush draw 9, OESD 8, gutshot 4, two overs 6, pair→two pair/trips 5, set→boat 7 (on flop) | 6s |
| `outs-count` | Calc | Hero + board → clean outs | 15s |
| `outs-combo` | Calc | Combo draws, no double-counting (FD + OESD = 15, FD + gutshot = 12) | 20s |
| `outs-dirty` | Calc | Discount outs that give villain a better hand | 25s |
| `outs-to-equity-flop` | Calc | Outs on flop → equity by river (×4; subtract `outs − 8` if > 8 outs) | 8s |
| `outs-to-equity-turn` | Calc | Outs on turn → equity on river (×2) | 6s |
| `draw-odds-facts` | Fact | FD ≈ 35% flop→river / 19% one card; OESD ≈ 32% / 17%; gutshot ≈ 17% / 9%; backdoor flush ≈ 4% | 6s |

---

## 4. Pot Odds

**Lesson:** compare the equity you have to the equity you need.

| Card | Kind | Asks | Target |
|---|---|---|---|
| `pot-odds-required` | Calc | Pot + bet → required equity | 10s |
| `pot-odds-vs-draw` | Calc→choice | Required vs. actual equity: "+EV / −EV / roughly breakeven" | 15s |
| `call-or-fold-draw` | Decision | Hero draw + villain bet → call / fold | 25s |
| `pot-odds-multiway` | Calc | Required equity with a bet and a caller ahead of you | 20s |

---

## 5. Preflop Equities & Probabilities

**Lesson:** a handful of matchups cover most all-ins.

| Card | Kind | Asks | Target |
|---|---|---|---|
| `matchup-archetypes` | Fact | Pair vs. two overs ≈ 55/45 · pair vs. one over one under ≈ 70/30 · overpair vs. underpair ≈ 80/20 · dominated (AK vs AQ) ≈ 70–75/25–30 · two overs vs. two unders ≈ 60/40 · AA vs. random ≈ 85/15 | 8s |
| `matchup-classify` | Calc→choice | Two hands → which archetype? | 8s |
| `matchup-equity` | Calc | Two hands → equity (exact via enumeration, bucketed) | 12s |
| `suited-bonus` | Fact | Suitedness adds ≈ 2–3% equity | 5s |
| `deal-probabilities` | Fact | Dealt any pair 1 in 17 (5.9%) · AA 1 in 221 · suited 23.5% | 6s |
| `flop-probabilities` | Fact | Pair flops a set or better ≈ 12% (1 in 8.5) · suited flops a flush draw ≈ 11%, a flush ≈ 0.8% · unpaired hand pairs on the flop ≈ 32% | 6s |
| `set-mining` | Decision | Call a raise with a small pair given stacks (implied odds ≥ 15–20× the call)? | 25s |

---

## 6. Betting Math

**Lesson:** the other side of pot odds: what *your* bets require.

| Card | Kind | Asks | Target |
|---|---|---|---|
| `bluff-breakeven` | Calc | Bet size → required fold % | 10s |
| `mdf` | Calc | Facing bet → how often you must continue | 10s |
| `value-bluff-ratio` | Calc | River bet size → max bluff share of a polarised range (= call equity number) | 12s |
| `bluff-or-check` | Decision | Estimated fold % vs. breakeven → bluff / give up | 20s |

---

## 7. Implied & Reverse Implied Odds

**Lesson:** calling now for money you'll win later; when hitting still loses.

| Card | Kind | Asks | Target |
|---|---|---|---|
| `implied-required` | Calc | Extra you must win later: `call / equity − (pot + call)` | 25s |
| `implied-call` | Decision | Draw without direct odds; stacks + villain tendency → call / fold | 30s |
| `reverse-implied` | Calc→choice | Which draws are dirty here? (non-nut flush, one-end straight) | 15s |

---

## 8. Stack Geometry

**Lesson:** stack-to-pot ratio decides how committed you are before you act.

| Card | Kind | Asks | Target |
|---|---|---|---|
| `spr-calc` | Calc | Effective stack / flop pot | 8s |
| `spr-classify` | Calc→choice | Low (< 4) / medium (4–10) / deep (> 10) → what that means for top pair | 8s |
| `geometric-sizing` | Calc | Pot fraction per street to get stacks in over N streets | 25s |
| `effective-stack` | Calc | Effective stack with uneven stacks (live-heavy) | 8s |

---

## 9. Expected Value

**Lesson:** EV = Σ (probability × outcome). Everything above is a special case.

| Card | Kind | Asks | Target |
|---|---|---|---|
| `ev-call` | Calc | `EV = equity × (pot + call) − call`, where pot already includes villain's bet | 25s |
| `ev-bluff` | Calc | `EV = fold% × pot − (1 − fold%) × bet` | 20s |
| `semi-bluff-fold-equity` | Calc | Required fold equity for a semi-bluff given draw equity | 30s |
| `ev-shove` | Decision | Shove vs. fold with fold equity + equity when called | 35s |

---

## 10. Range vs. Range (v2)

**Lesson:** equity distributions, board texture, who the board favours. More concept, less arithmetic.

| Card | Kind | Asks | Target |
|---|---|---|---|
| `board-favours` | Calc→choice | Which preflop range (raiser / caller) does this flop favour? | 15s |
| `hand-vs-range` | Calc | Hero hand vs. a simple range → equity bucket | 30s |
| `range-nut-advantage` | Calc→choice | Who has more nut combos on this board? | 20s |

---

## Capstone: Mixed Spots

Real hands chaining 2–3 sections, the way the table asks.

| Card | Chains | Asks | Target |
|---|---|---|---|
| `spot-draw-call` | 3 → 4 | Count outs, convert to equity, compare to pot odds → call / fold | 30s |
| `spot-river-bluffcatch` | 1 → 6 | Villain's sizing → required equity vs. his likely value:bluff → call / fold | 30s |
| `spot-flop-commit` | 8 → 9 | SPR + hand strength → bet / check / shove | 35s |
| `spot-set-mine` | 5 → 7 | Preflop raise, stacks → set-mine or fold | 25s |

---

## Separate Packs (not this curriculum)

- **`preflop-ranges`**: opening, 3-bet and defense ranges by position. Memorisation on a 13×13 grid; needs the `range` answer type (v2).
- **`tournament-math`**: push/fold, ICM (later).
- **`variance-bankroll`**: winrate, standard deviation, downswing sizing (later).

---

## Card count

| Section | Cards |
|---|---|
| 0 Hand basics | 6 |
| 1 Number fluency | 6 |
| 2 Combinatorics | 6 |
| 3 Outs & draws | 7 |
| 4 Pot odds | 4 |
| 5 Preflop | 7 |
| 6 Betting math | 4 |
| 7 Implied odds | 3 |
| 8 Stack geometry | 4 |
| 9 EV | 4 |
| 10 Range vs. range (v2) | 3 |
| Capstone | 4 |
| **Total** | **58** (~45 generators, ~13 static) |
