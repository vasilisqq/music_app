from pydantic import BaseModel, EmailStr,ConfigDict
from typing import Optional


class UserLogin(BaseModel):
    """Схема для входа пользователя"""
    email: EmailStr
    password: str


class UserCreate(UserLogin):
    """Схема для создания пользователя"""
    username: str


# class UserResponse(BaseModel):
#     """Схема для ответа с данными пользователя"""
#     id: int
#     email: str
#     username: str
#     is_active: bool
#     role: int

#     model_config = ConfigDict(from_attributes=True)
