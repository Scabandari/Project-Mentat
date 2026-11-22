# Project Mentat — Spec (v0.2 draft)

> A learning app built to learn anything, starting with **poker mathematics (No-Limit Texas Hold'em)**.
> The goal is fluency: getting the right number in your head, quickly, at the table.

---

## 1. Principles

1. **Generic engine, domain packs.** The core (cards, decks, scheduling, review, stats) knows nothing about poker. Poker is the first *content pack*.
2. **Generated problems beat static cards.** Static cards are fine for facts ("How many combos of AK?"). Computation skills need *procedurally generated* problems: new numbers every time, so you learn the method instead of memorising answers.
3. **Speed is part of correctness.** Every review records latency, and mastery requires accuracy *and* speed.
4. **Approximate answers are valid.** Mental math is about estimates. The default numeric answer is a **5-choice bucket** (e.g. "30–35%"), not typed input.
5. **Deterministic answer keys.** Every math answer comes from tested code. LLMs never compute or grade answers.
6. **Server is the source of truth.** Problems are generated and graded server-side; the client never sees the answer key before answering.

---

## 2. Decisions

| Area | Decision |
|---|---|
| Game scope | NLHE only (cash + generic). No ICM/PLO in v1. |
| Users | Single user in v1. **Every user-owned row has `user_id`** (one seeded default user), so adding logins later is additive, not a migration nightmare. |
| Answer input | 5 buckets by default; `choice`, `action`, `flip` also supported. |
| Player level | Beginner. Every deck has a **lesson** (Learn mode), and each card has a **difficulty ramp** (L1–L3) that rises with FSRS stability. |
| Stakes format | **User toggle: `live` / `online`**, stored in `users.settings.stakes_format`. Generators render $ amounts with chip-rounded, uneven sizes (live) or bb + pot-% sizes (online). Same math, different presentation. |
| Preflop ranges | **Separate pack** (`preflop-ranges`), v2, needs the `range` answer type. |
| Offline | Not in v1. PWA shell + offline queue can come later. |
| Hosting | Self-hosted on Ryan's home server via `make prod-up`. v1 served on `http://localhost:8473` (nginx; override with `HTTP_PORT`). Subdomain + TLS is a follow-up (see §3 Infra). |

---

## 3. Stack

### Backend
| Concern | Choice |
|---|---|
| Runtime / deps | Python 3.12, **uv** |
| API | **FastAPI** |
| Validation / settings | **Pydantic v2**, `pydantic-settings` |
| ORM | **SQLAlchemy 2.0 (async)** + `asyncpg` |
| Migrations | **Alembic** (autogenerate) |
| DB | **Postgres 16** |
| Scheduling | `fsrs` (py-fsrs) |
| Poker eval | `eval7` (Cython, fast exact enumeration / Monte Carlo) |
| LLM | **LangChain** (`langchain-anthropic`), isolated in `app/llm/` |
| Quality | `ruff` (lint + format), `mypy`, `pytest` + `pytest-asyncio`, `httpx` test client |
| Logging | `structlog`, JSON in prod |

### Frontend
| Concern | Choice |
|---|---|
| Build / deps | **Vite**, **pnpm** |
| UI | **React 19 + TypeScript 7 (strict)** |
| Components | **shadcn/ui** (Radix primitives) |
| Styling | **Tailwind CSS**. shadcn is built on Tailwind; adding runtime CSS-in-JS (styled-components/emotion) would fight it. Use `cva` + `cn()` for variants. |
| State | **Redux Toolkit slices** for client/UI state (session flow, timer, settings) |
| Server state | **RTK Query**, with endpoints **generated from FastAPI's OpenAPI** (`@rtk-query/codegen-openapi`). No hand-written API types. |
| Routing | React Router |
| Quality | oxlint, Prettier (+ tailwind plugin), Vitest + Testing Library |

### Infra
| Concern | Choice |
|---|---|
| Orchestration | **Docker Compose**: `docker-compose.yml` (dev) + `docker-compose.prod.yml` (override) |
| Dev | `db`, `api` (uvicorn `--reload`, source mounted), `web` (Vite dev server, proxies `/api` → `api`) |
| Prod | `db`, `api` (uvicorn workers), `nginx` (serves built SPA, proxies `/api`, gzip, cache headers). Runs on the home server, bound to `localhost:8473`; Postgres not exposed outside the compose network. `restart: unless-stopped` on all services. |
| Public access (follow-up) | **Cloudflare Tunnel** (`cloudflared` service in prod compose) → subdomain. No port forwarding, no exposed home IP, TLS handled by Cloudflare. Alternative: Caddy with auto Let's Encrypt + router port-forward. Auth must ship before exposing publicly. |
| Backups | Nightly `pg_dump` to a mounted host dir (`make backup` / `make restore f=`), keep 14 days. |
| Config | `.env` (gitignored) + `.env.example` |
| Tasks | **Makefile** (`make help`) |
| CI | GitHub Actions: backend (ruff, mypy, pytest vs Postgres, OpenAPI drift check), frontend (oxlint, prettier, tsc, vitest, build), prod-stack smoke test |
| Hooks | `pre-commit` (ruff, prettier, oxlint) |

### Repo layout
```
.
├── backend/
│   ├── app/
│   │   ├── api/v1/          # routers
│   │   ├── core/            # settings, db session, logging
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic request/response models
│   │   ├── services/        # scheduling, grading, sessions
│   │   ├── generators/      # generator registry + poker generators
│   │   ├── content/         # pack definitions (YAML + md explanations)
│   │   ├── llm/             # LangChain chains (tutor, deck builder)
│   │   └── scripts/         # seed, export_openapi
│   ├── alembic/
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/{app,features,components/ui,api,lib}
│   ├── package.json
│   └── Dockerfile
├── nginx/nginx.conf
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
└── Makefile
```

---

## 4. Core Engine

### 4.1 Concepts
- **Pack**: a domain (`poker-math`).
- **Deck**: a skill/topic within a pack ("Pot Odds").
- **Card**: the unit of scheduling.
  - **Static**: fixed front/back.
  - **Generator**: references a registered generator (`generator_key`) plus difficulty `params`. Produces a fresh **problem instance** each review. FSRS schedules the card (the skill), not the instance.
- **Problem instance**: one rendered problem, with its seed, prompt payload and hidden answer key.
- **Review**: one graded attempt on an instance.
- **Session**: a sitting (Review / Drill / Learn).

### 4.2 Generators
```python
@register("pot_odds_required_equity")
class PotOddsRequiredEquity(Generator):
    answer_type = "bucket"
    def generate(self, rng: Random, params: Params, ctx: GenContext) -> Instance: ...
    # ctx.stakes_format: "live" | "online";  ctx.level: 1–3
```
- Pure, seeded, deterministic: same seed + params → same instance (reproducible bugs, testable).
- Each generator ships property tests that check the answer key against an independent brute-force computation where possible.
- Each generator provides a `shortcut` (one-liner) and an `explanation_md` (worked solution) built from the instance.

### 4.3 Answer types & grading
| Type | Input | Grading |
|---|---|---|
| `bucket` | 5 contiguous buckets | Correct bucket only |
| `choice` | N options | Exact |
| `action` | Fold / Call / Raise | Against EV-maximising action |
| `flip` | Reveal → self-rate | User picks Again/Hard/Good/Easy |

**Bucket construction:** width set per card (e.g. 5 pts for equity, 1 for outs), boundaries on round numbers, half-open `[lo, hi)`. The correct bucket's position is randomised across slots 0–4 so position is never a tell; clamp at domain edges (0%/100%).

**Rating (auto-graded types):**
| Result | Rating |
|---|---|
| Wrong | Again |
| Correct, latency > 2× target | Hard |
| Correct, latency ≤ 2× target | Good |
| Correct, latency ≤ 0.5× target | Easy |

### 4.4 Study modes
- **Review**: FSRS due queue + capped new cards per day.
- **Drill**: rapid-fire on chosen decks, timer visible, **logged but does not update FSRS** (prevents cramming from distorting intervals).
- **Learn**: introduces new cards with the worked example first.

### 4.5 LLM usage (LangChain)
Scoped and optional; the app works fully without it.
- **Tutor** (M2): "Explain differently" on a result. The chain receives the deterministic solution + user's answer and only *rephrases or teaches*; it never recomputes.
- **Deck builder** (M4): turn pasted notes/URL into static cards for non-poker topics, then a review screen before saving.

---

## 5. Data Model (Postgres)

All PKs `uuid` (v7 via `uuid-utils` for index locality). All tables have `created_at`; mutable ones have `updated_at`. JSONB for polymorphic payloads, validated by Pydantic at the boundary.

```
users
  id PK, email NULL UNIQUE, display_name, settings JSONB, created_at

packs
  id PK, slug UNIQUE, name, description, version, created_at, updated_at

decks
  id PK, pack_id FK→packs, slug, name, description, lesson_md,
  section SMALLINT, position SMALLINT, unlock_after_deck_id FK NULL
  UNIQUE(pack_id, slug)

cards
  id PK, deck_id FK→decks, slug, kind ENUM(static, generator),
  answer_type ENUM(bucket, choice, action, flip),
  generator_key NULL, params JSONB,          -- generator cards
  front_md NULL, back_md NULL,               -- static cards
  target_ms INT, is_active BOOL, position SMALLINT
  UNIQUE(deck_id, slug)

user_card_states                              -- FSRS state per user×card
  user_id FK, card_id FK, PK(user_id, card_id)
  state ENUM(new, learning, review, relearning), stability FLOAT, difficulty FLOAT,
  due TIMESTAMPTZ, last_review TIMESTAMPTZ NULL, reps INT, lapses INT,
  level SMALLINT DEFAULT 1                    -- difficulty ramp L1–L3
  INDEX(user_id, due)

study_sessions
  id PK, user_id FK, mode ENUM(review, drill, learn), deck_ids UUID[],
  started_at, ended_at NULL

problem_instances
  id PK, user_id FK, card_id FK, session_id FK, seed BIGINT,
  prompt JSONB,          -- what the client renders
  answer_key JSONB,      -- never serialised to client before answer
  choices JSONB NULL, answered_at NULL, created_at

reviews
  id PK, user_id FK, card_id FK, instance_id FK UNIQUE, session_id FK,
  response JSONB, is_correct BOOL, rating SMALLINT(1–4),
  latency_ms INT, counted_for_srs BOOL,
  state_before JSONB, state_after JSONB,     -- FSRS snapshots, allows optimiser + undo
  created_at
  INDEX(user_id, created_at), INDEX(card_id, created_at)
```

Content (packs/decks/cards) is **seeded idempotently** from `app/content/` via upsert on slug (`make seed`), so content lives in git, not hand-edited in the DB.

---

## 6. REST API (`/api/v1`)

Conventions: plain resources (no success envelope); errors are `{"error": {"code", "message", "details"}}`; cursor pagination `{"items": [...], "next_cursor"}` only on history endpoints; timestamps ISO-8601 UTC.

| Method | Path | Returns |
|---|---|---|
| GET | `/health` | `{status, db}` |
| GET | `/me/settings` | `SettingsOut` |
| PATCH | `/me/settings` | `SettingsOut`. Body: `SettingsIn` (partial) |
| GET | `/packs` | `PackOut[]` |
| GET | `/packs/{slug}` | `PackDetailOut` (with decks) |
| GET | `/decks/{id}` | `DeckOut` |
| POST | `/sessions` | `SessionOut`. Body: `{mode, deck_ids?, new_limit?}` |
| POST | `/sessions/{id}/next` | `ProblemOut`, or `204` when queue empty |
| POST | `/instances/{id}/answer` | `GradeOut`. Body: `AnswerIn` |
| POST | `/sessions/{id}/end` | `SessionSummaryOut` |
| GET | `/stats/overview` | `StatsOverviewOut` |
| GET | `/stats/decks/{id}` | `DeckStatsOut` |
| GET | `/reviews?cursor=` | `Page[ReviewOut]` |
| POST | `/instances/{id}/tutor` | `TutorOut` (LLM, M2) |

`next` is a POST because it creates an instance.

### Response models (Pydantic)
```python
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, Field

Rating = Literal["again", "hard", "good", "easy"]
Mode = Literal["review", "drill", "learn"]
Action = Literal["fold", "call", "raise"]

class DeckOut(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str
    section: int
    locked: bool
    card_count: int
    due_count: int
    new_count: int
    mastery: float  # 0–1, share of cards in review state with stability > threshold

class SettingsOut(BaseModel):
    stakes_format: Literal["live", "online"] = "online"
    daily_new_limit: int = 10
    show_timer: bool = True

class SettingsIn(BaseModel):
    stakes_format: Literal["live", "online"] | None = None
    daily_new_limit: int | None = Field(default=None, ge=0, le=100)
    show_timer: bool | None = None

class PackOut(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str
    deck_count: int

class PackDetailOut(PackOut):
    decks: list[DeckOut]

class SessionOut(BaseModel):
    id: UUID
    mode: Mode
    deck_ids: list[UUID]
    started_at: datetime
    due_count: int
    new_count: int

# --- Problems: discriminated on answer_type ---
class Scene(BaseModel):
    hero: list[str] = []          # ["Ah", "Kd"]
    board: list[str] = []         # ["Qs", "Jh", "2c"]
    pot: float | None = None
    bet: float | None = None
    hero_stack: float | None = None
    villain_stack: float | None = None
    street: Literal["preflop", "flop", "turn", "river"] | None = None

class ProblemBase(BaseModel):
    instance_id: UUID
    card_id: UUID
    deck_slug: str
    prompt: str                   # short markdown question
    scene: Scene | None = None    # rendered visually when present
    target_ms: int
    is_new: bool

class Bucket(BaseModel):
    id: int                       # 0–4
    label: str                    # "30–35%"
    lo: float
    hi: float

class Choice(BaseModel):
    id: int
    label: str

class BucketProblem(ProblemBase):
    answer_type: Literal["bucket"]
    unit: Literal["percent", "count", "ratio", "chips"]
    buckets: list[Bucket] = Field(min_length=5, max_length=5)

class ChoiceProblem(ProblemBase):
    answer_type: Literal["choice"]
    choices: list[Choice]

class ActionProblem(ProblemBase):
    answer_type: Literal["action"]
    actions: list[Action]

class FlipProblem(ProblemBase):
    answer_type: Literal["flip"]

ProblemOut = Annotated[
    BucketProblem | ChoiceProblem | ActionProblem | FlipProblem,
    Field(discriminator="answer_type"),
]

# --- Answering ---
class AnswerIn(BaseModel):
    response: int | Action | None = None  # bucket/choice id, action; None for flip
    self_rating: Rating | None = None      # flip only
    latency_ms: int = Field(ge=0)

class GradeOut(BaseModel):
    instance_id: UUID
    is_correct: bool | None               # None for flip
    rating: Rating
    correct_response: int | Action | None
    exact_answer: float | str | None      # e.g. 31.8 (shown alongside bucket)
    back_md: str | None                   # flip cards
    shortcut: str
    explanation_md: str
    latency_ms: int
    target_ms: int
    next_due: datetime | None             # None in drill mode

# --- Stats ---
class DeckStat(BaseModel):
    deck_id: UUID
    deck_name: str
    reviews: int
    accuracy: float
    median_latency_ms: int

class SessionSummaryOut(BaseModel):
    session_id: UUID
    reviewed: int
    correct: int
    accuracy: float
    median_latency_ms: int
    by_deck: list[DeckStat]

class StatsOverviewOut(BaseModel):
    streak_days: int
    reviews_today: int
    due_now: int
    accuracy_7d: float
    median_latency_ms_7d: int
    weakest: list[DeckStat]               # feeds Drill suggestions

class TutorOut(BaseModel):
    message_md: str
```

---

## 7. Poker Math Pack (v1 content)

Full card-by-card curriculum in **[CURRICULUM.md](CURRICULUM.md)**: 11 sections (hand basics → number fluency → combinatorics → outs → pot odds → preflop → betting math → implied odds → stack geometry → EV → range vs. range) plus a mixed-spot capstone. 58 cards, ~45 generated.

## 8. UI (mobile-first)
- **Home**: due count, streak, Review / Drill, weakest decks, **Live / Online toggle**.
- **Card**: rendered cards + board, pot/bet chips, **5 large bucket buttons** (thumb-reachable), timer bar against target.
- **Result**: correct bucket highlighted, exact value, time, shortcut, expandable explanation, "Explain differently" (tutor).
- **Decks**, **Stats**.
- Dark mode default.

---

## 9. Milestones

| Milestone | Scope |
|---|---|
| **M0: Infra** ✅ | Compose (db/api/web), Makefile, Alembic baseline, health check, OpenAPI → RTK Query codegen, CI. |
| **M1: Engine** | Models, seeding, FSRS, sessions, static `flip` cards end-to-end. |
| **M2: Generators** | Generator registry, `bucket` grading, live/online rendering, sections 0–4, lessons, result/explain screen, tutor chain. |
| **M3: Betting math** | Sections 5–9, capstone, Drill mode, stats. |
| **M4: Generic learning** | LLM deck builder, CSV import, user-created decks. |
| **v2** | Auth → subdomain via Cloudflare Tunnel, PWA/offline, section 10, `preflop-ranges` pack. |

---

## 10. Open Questions
1. LLM provider for the tutor: Anthropic by default?
2. Daily new-card limit default (proposal: 10).
