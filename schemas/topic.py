# schemas/topic.py
from pydantic import BaseModel, ConfigDict
from typing import Optional

class TopicCreate(BaseModel):
    name: str
    description: Optional[str] = None

class TopicResponse(TopicCreate):
    id: int
    lessons_count: int = 0
    progress: float = 0.0

    model_config = ConfigDict(from_attributes=True)