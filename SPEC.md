# Project Mentat — Spec (v0.1 draft)

> A learning app built to learn anything, starting with **poker mathematics**.
> The goal is fluency: getting the right number in your head, quickly, at the table.

---

## 1. Principles

1. **Generic engine, domain packs.** The core (cards, decks, scheduling, review, stats) knows nothing about poker. Poker is the first *content pack*.
2. **Generated problems beat static cards.** Static cards are fine for facts ("How many combos of AK?"). Computation skills need *procedurally generated* problems: new numbers every time, so you learn the method instead of memorising answers.
3. **Speed is part of correctness.** At the table, a right answer that takes 40 s is a wrong answer. Every review records latency, and mastery requires accuracy *and* speed.
4. **Approximate answers are valid.** Mental math is about estimates. Numeric answers are graded with tolerance bands, not exact match.
5. **Local-first, mobile-first.** Study happens on a phone in spare minutes. It works offline, and sync comes later.

---

## 2. Platform & Stack (decision)

| Concern | Choice | Why |
|---|---|---|
| App | **React + TypeScript + Vite, as a PWA** | Runs on phone and desktop, installable, offline. One codebase. |
| Storage | **IndexedDB via Dexie** | Local-first, no backend needed for v1. |
| Scheduling | **FSRS** (`ts-fsrs`) | Current best-in-class spaced-repetition algorithm, better than SM-2/Anki defaults. |
| Poker eval | TS hand evaluator + Monte Carlo/exact enumeration in a Web Worker | Equity for generated problems computed client-side. |
| Tests | Vitest | Generator correctness is critical, because a wrong answer key trains wrong instincts. |
| Sync (later) | Supabase or a tiny API + Postgres | Deferred to v2. |

Alternatives considered: React Native/Expo (better native feel, slower to iterate, overkill for v1); Python CLI (fast to build, but you won't study on it on the metro).

---

## 3. Core Engine

### 3.1 Concepts
- **Pack**: a domain (e.g. `poker-math`). Contains decks and generators.
- **Deck**: an ordered set of skills/topics (e.g. "Pot Odds").
- **Card**: the unit of scheduling. Either:
  - **Static card**: fixed prompt/answer.
  - **Generator card**: a *template* that produces a fresh **problem instance** on each review. FSRS schedules the template (the skill), not the instance.
- **Review**: one attempt. Stores card id, instance seed, user answer, correct answer, grade, latency, timestamp.

### 3.2 Answer types
| Type | Grading |
|---|---|
| `flip` | Self-graded (Again / Hard / Good / Easy), classic flashcard |
| `numeric` | Auto-graded with tolerance (e.g. ±3 percentage points = Good, ±6 = Hard, else Again) |
| `choice` | Multiple choice, auto-graded |
| `action` | Choose Call / Fold / Raise, graded against EV |
| `range` (v2) | Select hands on a 13×13 grid |

Auto-grade → FSRS rating mapping also factors in latency against a per-card **target time** (e.g. correct but more than 2× target time downgrades Good to Hard).

### 3.3 Study modes
- **Review**: FSRS due queue (default daily mode).
- **Drill**: unscheduled rapid-fire on one deck, with a timer. Doesn't affect scheduling, or affects it lightly (configurable).
- **Learn**: introduces new cards with an explanation/worked example first.
- **Explain**: every card has an "Explain" view showing the worked solution and the mental shortcut, not just the answer.

### 3.4 Content authoring
- Packs defined as **TypeScript modules** (generators) + **YAML/Markdown** (static cards, explanations).
- Import CSV/Anki (`.apkg`) for non-poker decks (v2).

### 3.5 Stats
- Per-deck accuracy, median latency, retention, streak.
- **Calibration chart** for numeric cards: your estimate vs. truth (shows whether you overestimate equity, etc.).
- Weakest-skills list feeding Drill mode.

---

## 4. Poker Math Pack (v1 content)

Ordered roughly by dependency. Each item = one or more generator cards.

### Tier 1 — Foundations
1. **Outs counting**: show hero hand + board, count clean outs (flush draws, OESD, gutshot, overcards, combo draws, discounted/dirty outs).
2. **Outs → equity**: rule of 2 and 4 (and the "4x minus (outs − 8)" correction for big draws) vs. exact.
3. **Pot odds**: pot + bet → required equity % (`call / (pot + bet + call)`).
4. **Ratio ↔ percentage conversions**: 3:1 ↔ 25%, etc. (pure speed drill).
5. **Call/fold decisions**: given draw + pot odds → action.

### Tier 2 — Betting math
6. **Bluff breakeven / fold equity**: bet B into pot P → required fold % (`B / (P + B)`).
7. **Minimum Defense Frequency (MDF)**: `P / (P + B)`.
8. **Implied odds**: how much more must you win on later streets to justify a call.
9. **Reverse implied odds** (conceptual + numeric).
10. **SPR**: compute and classify (low/medium/high commitment).
11. **Geometric bet sizing**: size per street to get stacks in by the river.
12. **Semi-bluff EV**: fold equity + equity when called.

### Tier 3 — Combinatorics & ranges
13. **Hand combos**: pairs (6), suited (4), offsuit (12), and with card removal.
14. **Blockers**: combos remaining given board/hero cards.
15. **Range composition**: value:bluff ratio in a given range.
16. **Preflop matchups**: memorise common equities (pair vs. overcards ≈ 55/45, dominated hands ≈ 70/30, etc.).
17. **Hand vs. range equity estimation** (v2, heavier compute).

### Tier 4 — EV & advanced (v2+)
18. **EV calculations**: full EV of a call/bet with multiple outcomes.
19. **Bet-to-value ratios / polarised river sizing**.
20. **ICM basics**: tournament chip vs. $ value.
21. **Variance / bankroll**: standard deviation, risk of ruin (conceptual).

Each generator specifies: inputs, answer formula, tolerance, target time, explanation template, and difficulty knobs (e.g. round numbers → awkward numbers, single draw → combo draw).

---

## 5. UI (mobile-first)

- **Home**: due count, streak, "Review" / "Drill" buttons, weakest skills.
- **Card screen**: rendered cards and board (visual, not "Ah Kd" text), pot/bet chips, numeric keypad for answers, visible timer.
- **Result**: correct answer, your error, time, one-line shortcut, "Explain" expansion.
- **Deck browser** and **stats** screens.
- Dark mode default (it's a poker app).

---

## 6. Milestones

| Milestone | Scope |
|---|---|
| **M0: Skeleton** | Vite/React/TS PWA, Dexie schema, FSRS wired, static `flip` cards working end-to-end. |
| **M1: Generators** | Generator card type, `numeric` grading with tolerance + latency, Tier 1 poker decks. |
| **M2: Betting math** | Tier 2 decks, Drill mode, Explain view, basic stats. |
| **M3: Combinatorics** | Tier 3 decks, card-removal engine, calibration chart. |
| **M4: Generic learning** | YAML/CSV/Anki import, user-created decks. |
| **v2** | Sync, range-grid answers, hand-vs-range equity, Tier 4. |

---

## 7. Open Questions

1. Phone-first PWA OK, or do you want a native app from day one?
2. Single user (you) for now, or plan for multiple users / ReportNote-style SaaS later? (Affects whether we design for auth/sync early.)
3. Game focus: NLHE cash only, or include tournaments (ICM) and PLO?
4. Should Drill mode results feed FSRS, or stay separate?
5. Answer input for equity: type a number, or tap a slider/bucket (faster, coarser)?
