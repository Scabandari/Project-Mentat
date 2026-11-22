from uuid import UUID

from fastapi import APIRouter

from app.api.deps import DB, Now, UserId
from app.schemas.study import DeckStatsOut, StatsOverviewOut
from app.services import stats as svc

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview", operation_id="getStatsOverview")
async def overview(db: DB, user_id: UserId, now: Now) -> StatsOverviewOut:
    return await svc.overview(db, user_id, now)


@router.get("/decks/{deck_id}", operation_id="getDeckStats")
async def deck_stats(deck_id: UUID, db: DB, user_id: UserId) -> DeckStatsOut:
    return await svc.deck_stats(db, user_id, deck_id)
