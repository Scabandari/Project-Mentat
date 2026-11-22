from fastapi import APIRouter

from app.api.v1 import catalog, health, me, stats, study

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(me.router)
api_router.include_router(catalog.router)
api_router.include_router(study.router)
api_router.include_router(stats.router)
