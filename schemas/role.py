from pydantic import BaseModel

class RoleCreate(BaseModel):
    name:str


class RoleResponse(RoleCreate):
    """Схема для создания пользователя"""
    id: int

