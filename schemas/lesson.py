from pydantic import BaseModel, Json,ConfigDict
from typing import Dict, Any

class LessonCreate(BaseModel):
    name:str
    difficult: str
    rhythm:float
    notes:dict
    topic:int

    model_config = ConfigDict(from_attributes=True)


class LessonResponse(LessonCreate):
    id:int

    model_config = ConfigDict(from_attributes=True)