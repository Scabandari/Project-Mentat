import logging

import structlog

from app.core.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    level = logging.getLevelNamesMapping().get(settings.log_level.upper(), logging.INFO)
    renderer: structlog.typing.Processor = (
        structlog.processors.JSONRenderer()
        if settings.app_env == "prod"
        else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
    )
