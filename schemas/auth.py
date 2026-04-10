from pydantic import BaseModel, EmailStr,ConfigDict
from typing import Optional


class UserLogin(BaseModel):
    """Схема для входа пользователя"""
    email: EmailStr
    password: str


class UserCreate(UserLogin):
    """Схема для создания пользователя"""
    username: str


class UserResponse(BaseModel):
    username: str
    email: EmailStr
    role: str
# Итоговая модель ответа при логине/регистрации
class TokenResponse(BaseModel):
    access_token: str
    user: UserResponse
    token_type: str = "bearer"


class UserUpdate(BaseModel):
    """Схема для обновления данных профиля"""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None