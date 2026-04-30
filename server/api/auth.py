import os
import sys

from fastapi import APIRouter, Depends, HTTPException, Response, status

# from app.core.config import settings
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
from typing import List

# from app.services.auth_service import AuthService
from core.dependencies import (
    get_auth_service,
    get_current_active_user,
    get_user_service,
    is_admin,
)
from services.auth_service import AuthService
from services.user_service import UserService
from utils.jwt import create_access_token

from schemas.auth import (
    AdminUserResponse,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)

router = APIRouter(tags=["authentication"])


# роутер регистрации
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate, user_service: UserService = Depends(get_user_service)
):
    """Регистрация нового пользователя"""

    existing_user = await user_service.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует",
        )
    existing_user = await user_service.get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="такой username уже занят"
        )
    user = await user_service.create_user(user_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось создать пользователя",
        )
    token = create_access_token(data={"user_id": str(user.id)})
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            username=user.username,
            email=user.email,
            role=user.role_info.name,
        ),
    )


@router.post("/login", status_code=status.HTTP_201_CREATED)
async def login(
    user_data: UserLogin,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service),
):
    """Вход пользователя"""
    user = await auth_service.login_user(user_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )
    token = create_access_token(data={"user_id": str(user.id)})
    # Возвращаем Pydantic-объект
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            username=user.username, email=user.email, role=user.role_info.name
        ),
    )


@router.get("/me", response_model=UserResponse)
async def verify_token_and_get_user(current_user=Depends(get_current_active_user)):
    """
    Эндпоинт для проверки токена при запуске приложения.
    Возвращает актуальные данные пользователя.
    """

    return UserResponse(
        username=current_user.username,
        email=current_user.email,
        role=current_user.role_info.name,
    )


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    update_data: UserUpdate,
    current_user=Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service),
):
    """Обновление данных текущего пользователя"""
    # Проверка уникальности email, если он меняется
    if update_data.email and update_data.email != current_user.email:
        if await user_service.get_user_by_email(update_data.email):
            raise HTTPException(status_code=400, detail="Этот email уже занят")

    # Проверка уникальности username
    if update_data.username and update_data.username != current_user.username:
        if await user_service.get_user_by_username(update_data.username):
            raise HTTPException(status_code=400, detail="Этот логин уже занят")

    updated_user = await user_service.update_user(current_user.id, update_data)
    if not updated_user:
        raise HTTPException(status_code=400, detail="Не удалось обновить данные")

    return UserResponse(
        username=updated_user.username,
        email=updated_user.email,
        role=updated_user.role_info.name,
    )


# Не забудь импортировать свою зависимость!
# from core.dependencies import is_admin


@router.get("/users", response_model=List[AdminUserResponse])
async def get_all_users_for_admin(
    # Внедряем зависимость админа. Если юзер не админ, FastAPI отбросит его
    # с ошибкой еще ДО входа в тело функции!
    current_admin=Depends(is_admin),
    user_service: UserService = Depends(get_user_service),
):
    """Получение списка всех пользователей. Доступно только администратору."""
    users = await user_service.get_all_users()

    return [
        AdminUserResponse(
            id=u.id,
            username=u.username,
            email=u.email,
            role=u.role_info.name if u.role_info else "пользователь",
            is_active=u.is_active,
        )
        for u in users
    ]


@router.patch("/users/{user_id}/status", response_model=AdminUserResponse)
async def toggle_user_status(
    user_id: int,
    current_admin=Depends(is_admin),
    user_service: UserService = Depends(get_user_service),
):
    """Инвертировать статус активности пользователя"""
    user = await user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    new_status = not user.is_active
    updated_user = await user_service.update_user(
        user_id, UserUpdate(is_active=new_status)
    )

    return AdminUserResponse(
        id=updated_user.id,
        username=updated_user.username,
        email=updated_user.email,
        role=updated_user.role_info.name if updated_user.role_info else "пользователь",
        is_active=updated_user.is_active,
    )


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
async def update_user_by_admin(
    user_id: int,
    update_data: UserUpdate,
    current_admin=Depends(is_admin),
    user_service: UserService = Depends(get_user_service),
):
    """Редактирование данных пользователя"""
    user_to_update = await user_service.get_user_by_id(user_id)
    if not user_to_update:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    if update_data.email and update_data.email != user_to_update.email:
        if await user_service.get_user_by_email(update_data.email):
            raise HTTPException(status_code=400, detail="Этот email уже занят!")

    if update_data.username and update_data.username != user_to_update.username:
        if await user_service.get_user_by_username(update_data.username):
            raise HTTPException(status_code=400, detail="Этот логин уже занят!")

    updated_user = await user_service.update_user(user_id, update_data)

    return AdminUserResponse(
        id=updated_user.id,
        username=updated_user.username,
        email=updated_user.email,
        role=updated_user.role_info.name if updated_user.role_info else "пользователь",
        is_active=updated_user.is_active,
    )
