from pydantic import BaseModel, ConfigDict


class LessonBase(BaseModel):
    name: str
    description: str
    difficult: int
    rhythm: float
    notes: dict
    topic: int

    model_config = ConfigDict(from_attributes=True)


class LessonCreate(LessonBase):
    pass


class LessonUpdate(LessonBase):
    pass


class LessonResponse(LessonBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
