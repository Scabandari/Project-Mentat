from fastapi import APIRouter

from app.api.deps import DB, UserId
from app.schemas.study import SettingsIn, SettingsOut
from app.services import settings as svc

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/settings", operation_id="getSettings")
async def get_settings(db: DB, user_id: UserId) -> SettingsOut:
    return await svc.get_settings(db, user_id)


@router.patch("/settings", operation_id="updateSettings")
async def update_settings(body: SettingsIn, db: DB, user_id: UserId) -> SettingsOut:
    return await svc.update_settings(db, user_id, body)
