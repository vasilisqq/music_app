from fastapi import APIRouter, Depends, HTTPException, status, Response
import sys
import os
# from app.core.config import settings
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from schemas.auth import UserCreate, UserLogin, TokenResponse, UserResponse
from services.user_service import UserService
from services.auth_service import AuthService
# from app.services.auth_service import AuthService
from core.dependencies import get_user_service, get_auth_service, get_current_active_user
from utils.jwt import create_access_token

router = APIRouter(tags=["authentication"])

#роутер регистрации
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    """Регистрация нового пользователя"""
    
    existing_user = await user_service.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует"
        )
    existing_user = await user_service.get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="такой username уже занят"
        )
    user = await user_service.create_user(user_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось создать пользователя"
        )
    token = create_access_token(data = {"user_id": str(user.id)})
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            username=user.username,
            email=user.email,
            role = user.role_info.name,
        )
    )

@router.post("/login", status_code=status.HTTP_201_CREATED)
async def login(
    user_data: UserLogin,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service)
):
    """Вход пользователя"""
    user = await auth_service.login_user(user_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )
    token = create_access_token(data = {"user_id": str(user.id)})
    # Возвращаем Pydantic-объект
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            username=user.username,
            email=user.email,
            role = user.role_info.name
        )
    )

@router.get("/me", response_model=UserResponse)
async def verify_token_and_get_user(
    current_user = Depends(get_current_active_user)
):
    """
    Эндпоинт для проверки токена при запуске приложения.
    Возвращает актуальные данные пользователя.
    """ 
    
    return UserResponse(
        username=current_user.username,
        email=current_user.email,
        role=current_user.role_info.name
    )
