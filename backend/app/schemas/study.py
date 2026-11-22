from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field

Rating = Literal["again", "hard", "good", "easy"]
Mode = Literal["review", "drill", "learn"]
Action = Literal["fold", "call", "raise"]
StakesFormat = Literal["live", "online"]


# ---------- Settings ----------
class SettingsOut(BaseModel):
    stakes_format: StakesFormat = "online"
    daily_new_limit: int = 10
    show_timer: bool = True
    timezone: str = "America/Toronto"


class SettingsIn(BaseModel):
    stakes_format: StakesFormat | None = None
    daily_new_limit: int | None = Field(default=None, ge=0, le=100)
    show_timer: bool | None = None
    timezone: str | None = None


# ---------- Content ----------
class DeckOut(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str
    section: int
    card_count: int
    due_count: int
    new_count: int
    mastery: float  # 0-1: share of cards with FSRS stability ≥ mastery threshold
    locked: bool  # advisory: previous deck < 70% mastery. Never enforced.
    has_lesson: bool


class PackOut(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str
    deck_count: int
    due_count: int
    new_count: int  # unseen cards in the pack
    new_today: int  # new cards a review session would introduce today (daily limit applied)


class PackDetailOut(PackOut):
    decks: list[DeckOut]


class DeckDetailOut(DeckOut):
    lesson_md: str | None


# ---------- Sessions ----------
class SessionIn(BaseModel):
    mode: Mode = "review"
    deck_ids: list[UUID] | None = None  # None = all decks
    new_limit: int | None = Field(default=None, ge=0, le=100)  # None = remaining daily allowance


class SessionOut(BaseModel):
    id: UUID
    mode: Mode
    deck_ids: list[UUID]
    started_at: datetime
    due_count: int
    new_count: int


# ---------- Problems (discriminated on answer_type) ----------
class Scene(BaseModel):
    hero: list[str] = []
    villain: list[str] = []
    board: list[str] = []
    pot: float | None = None
    bet: float | None = None
    hero_stack: float | None = None
    villain_stack: float | None = None
    street: Literal["preflop", "flop", "turn", "river"] | None = None
    money_format: StakesFormat | None = None  # how to label pot/bet: $ (live) or bb (online)


class ProblemBase(BaseModel):
    instance_id: UUID
    card_id: UUID
    deck_slug: str
    prompt: str
    scene: Scene | None = None
    target_ms: int
    is_new: bool


class Bucket(BaseModel):
    id: int
    label: str
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
    # Self-graded, so nothing to hide: the client needs the back to reveal before rating.
    back_md: str


ProblemOut = Annotated[
    BucketProblem | ChoiceProblem | ActionProblem | FlipProblem,
    Field(discriminator="answer_type"),
]


class QueueCounts(BaseModel):
    due: int
    new: int
    reviewed: int


class NextOut(BaseModel):
    problem: ProblemOut | None  # None = session queue is empty
    queue: QueueCounts


# ---------- Answering ----------
class AnswerIn(BaseModel):
    response: int | Action | None = None  # bucket/choice id or action; None for flip
    self_rating: Rating | None = None  # flip only
    latency_ms: int = Field(ge=0, le=3_600_000)


class GradeOut(BaseModel):
    instance_id: UUID
    is_correct: bool | None  # None for self-graded flip cards
    rating: Rating
    correct_response: int | Action | None
    exact_answer: float | str | None
    back_md: str | None
    shortcut: str
    explanation_md: str
    latency_ms: int
    target_ms: int
    next_due: datetime | None  # None when the review didn't touch the schedule (drill)


# ---------- Summary ----------
class DeckStat(BaseModel):
    deck_id: UUID
    deck_name: str
    reviews: int
    accuracy: float
    median_latency_ms: int


class SessionSummaryOut(BaseModel):
    session_id: UUID
    mode: Mode
    reviewed: int
    correct: int
    accuracy: float
    median_latency_ms: int
    duration_s: int
    by_deck: list[DeckStat]


# ---------- Tutor / config ----------
class TutorIn(BaseModel):
    question: str | None = Field(default=None, max_length=500)


class TutorOut(BaseModel):
    message_md: str


class ConfigOut(BaseModel):
    tutor_enabled: bool


# ---------- Stats ----------
class DayStat(BaseModel):
    date: str  # YYYY-MM-DD in the user's timezone
    reviews: int
    correct: int


class DeckStatRow(BaseModel):
    deck_id: UUID
    deck_name: str
    section: int
    reviews: int
    accuracy: float
    median_latency_ms: int
    on_time: float  # share of reviews answered within the card's target time
    mastery: float


class StatsOverviewOut(BaseModel):
    streak_days: int
    reviews_today: int
    due_now: int
    reviews_7d: int
    accuracy_7d: float | None
    median_latency_ms_7d: int | None
    daily: list[DayStat]  # last 14 days, oldest first
    decks: list[DeckStatRow]  # decks with reviews in the last 30 days
    weakest: list[DeckStatRow]  # up to 3, worst first (min 5 reviews)


class CardStatRow(BaseModel):
    card_id: UUID
    slug: str
    label: str
    answer_type: str
    reviews: int
    accuracy: float | None
    median_latency_ms: int | None
    target_ms: int
    state: str  # new | learning | review | relearning
    due: datetime | None
    stability_days: float | None


class DeckStatsOut(BaseModel):
    deck_id: UUID
    deck_name: str
    cards: list[CardStatRow]
