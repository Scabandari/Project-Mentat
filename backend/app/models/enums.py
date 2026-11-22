from enum import StrEnum

from sqlalchemy import Enum


class CardKind(StrEnum):
    static = "static"
    generator = "generator"


class AnswerType(StrEnum):
    bucket = "bucket"
    choice = "choice"
    action = "action"
    flip = "flip"


class CardState(StrEnum):
    learning = "learning"
    review = "review"
    relearning = "relearning"


class StudyMode(StrEnum):
    review = "review"
    drill = "drill"
    learn = "learn"


def str_enum(enum_cls: type[StrEnum], name: str) -> Enum:
    """VARCHAR + CHECK constraint. Avoids native PG enums, which are painful to alter in Alembic."""
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=20,
        values_callable=lambda e: [m.value for m in e],
    )
