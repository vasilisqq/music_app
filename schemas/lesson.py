from typing import Literal

from pydantic import BaseModel, ConfigDict


class LessonBase(BaseModel):
    name: str
    description: str
    difficult: int
    rhythm: float
    notes: dict
    topic: int
    hand: str = "right"
    order_in_topic: int | None = None

    model_config = ConfigDict(from_attributes=True)


class LessonCreate(LessonBase):
    pass


class LessonUpdate(LessonBase):
    pass


class LessonResponse(LessonBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# ДОБАВИТЬ ЭТОТ КЛАСС:
class LessonWithStatusResponse(LessonResponse):
    status: Literal["completed", "available", "locked"]
