# from app.core.dependencies import get_current_active_user, get_current_superuser
# from app.schemas.auth import UserResponse
# from app.models.user import User
# from app.services.user_service import UserService
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.auth import *
from server.db import get_db
from server.models import Role

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("/roles", response_model=UserResponse)
async def get_all_roles(current_user: Role = Depends(get_current_active_user)):
    """Получение информации о текущем пользователе"""
    return UserResponse.model_validate(current_user)


@router.get("/", response_model=List[UserResponse])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """Получение списка всех пользователей (только для суперпользователей)"""
    user_service = UserService(db)
    # Здесь можно добавить метод для получения списка пользователей
    # Пока возвращаем пустой список
    return []


@router.get("/{user_id}", response_model=UserResponse)
async def read_user(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """Получение информации о пользователе по ID (только для суперпользователей)"""
    user_service = UserService(db)
    user = await user_service.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден"
        )
    return UserResponse.model_validate(user)


@router.put("/me", response_model=UserResponse)
async def update_user_me(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Обновление информации о текущем пользователе"""
    # Здесь можно добавить логику обновления пользователя
    # Пока просто возвращаем текущего пользователя
    return UserResponse.model_validate(current_user)
