from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    """Схема для создания пользователя"""
    email: EmailStr
    username: str
    password: str

class UserLogin(BaseModel):
    """Схема для входа пользователя"""
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    """Схема для ответа с данными пользователя"""
    id: int
    email: str
    username: str
    is_active: bool
    is_superuser: bool