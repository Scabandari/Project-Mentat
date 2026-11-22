from uuid import UUID

from fastapi import APIRouter

from app.api.deps import DB, Now, UserId
from app.schemas.study import DeckDetailOut, PackDetailOut, PackOut
from app.services import catalog as svc

router = APIRouter(tags=["catalog"])


@router.get("/packs", operation_id="listPacks")
async def list_packs(db: DB, user_id: UserId, now: Now) -> list[PackOut]:
    return await svc.list_packs(db, user_id, now)


@router.get("/packs/{slug}", operation_id="getPack")
async def get_pack(slug: str, db: DB, user_id: UserId, now: Now) -> PackDetailOut:
    return await svc.get_pack(db, user_id, now, slug)


@router.get("/decks/{deck_id}", operation_id="getDeck")
async def get_deck(deck_id: UUID, db: DB, user_id: UserId, now: Now) -> DeckDetailOut:
    return await svc.get_deck(db, user_id, now, deck_id)
