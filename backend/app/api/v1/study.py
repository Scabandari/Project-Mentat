from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from langchain_core.language_models import BaseChatModel

from app.api.deps import DB, Now, UserId
from app.llm.tutor import get_tutor_model
from app.schemas.errors import ErrorOut
from app.schemas.study import (
    AnswerIn,
    ConfigOut,
    GradeOut,
    NextOut,
    SessionIn,
    SessionOut,
    SessionSummaryOut,
    TutorIn,
    TutorOut,
)
from app.services import study as svc
from app.services import tutor as tutor_svc

Tutor = Annotated[BaseChatModel | None, Depends(get_tutor_model)]

router = APIRouter(tags=["study"])
ERRORS: dict[int | str, dict[str, object]] = {
    404: {"model": ErrorOut},
    409: {"model": ErrorOut},
}


@router.post(
    "/sessions",
    operation_id="createSession",
    status_code=status.HTTP_201_CREATED,
    responses=ERRORS,
)
async def create_session(body: SessionIn, db: DB, user_id: UserId, now: Now) -> SessionOut:
    return await svc.create_session(db, user_id, now, body)


@router.post("/sessions/{session_id}/next", operation_id="nextProblem", responses=ERRORS)
async def next_problem(session_id: UUID, db: DB, user_id: UserId, now: Now) -> NextOut:
    return await svc.next_problem(db, user_id, now, session_id)


@router.post("/sessions/{session_id}/end", operation_id="endSession", responses=ERRORS)
async def end_session(session_id: UUID, db: DB, user_id: UserId, now: Now) -> SessionSummaryOut:
    return await svc.end_session(db, user_id, now, session_id)


@router.post("/instances/{instance_id}/answer", operation_id="answerProblem", responses=ERRORS)
async def answer(instance_id: UUID, body: AnswerIn, db: DB, user_id: UserId, now: Now) -> GradeOut:
    return await svc.answer(db, user_id, now, instance_id, body)


@router.post(
    "/instances/{instance_id}/tutor",
    operation_id="tutorExplain",
    responses={**ERRORS, 502: {"model": ErrorOut}, 503: {"model": ErrorOut}},
)
async def tutor(
    instance_id: UUID, body: TutorIn, db: DB, user_id: UserId, model: Tutor
) -> TutorOut:
    return await tutor_svc.tutor(db, model, user_id, instance_id, body)


@router.get("/config", operation_id="getConfig", tags=["meta"])
async def config(model: Tutor) -> ConfigOut:
    return ConfigOut(tutor_enabled=model is not None)
