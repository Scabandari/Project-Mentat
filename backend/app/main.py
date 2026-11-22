from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.schemas.errors import ErrorBody, ErrorOut


def _error(status: int, code: str, message: str, details: object = None) -> JSONResponse:
    body = ErrorOut(error=ErrorBody(code=code, message=message, details=details))
    return JSONResponse(status_code=status, content=body.model_dump(mode="json"))


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title="Project Mentat API",
        version=__version__,
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _error(exc.status_code, f"http_{exc.status_code}", str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return _error(422, "validation_error", "Request validation failed", exc.errors())

    app.include_router(api_router)
    return app


app = create_app()
