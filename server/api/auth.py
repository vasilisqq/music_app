from fastapi import APIRouter, Depends, HTTPException, status, Response
import sys
import os
# from app.core.config import settings
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from schemas.auth import UserCreate, UserLogin
from services.user_service import UserService
from services.auth_service import AuthService
# from app.services.auth_service import AuthService
from core.dependencies import get_user_service, get_auth_service


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
    token = await user_service.create_user(user_data)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось создать пользователя"
        )
    
    return token

@router.post("/login", status_code=status.HTTP_201_CREATED)
async def login(
    user_data: UserLogin,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Вход пользователя"""
    token = await auth_service.login_user(user_data)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )
    return token


# @router.post("/logout")
# async def logout(
#     response: Response, # Добавляем Response для удаления cookie
#     token_data: TokenRefresh,
#     auth_service: AuthService = Depends(get_auth_service)
# ):
#     """Выход пользователя (удаление refresh токена и access токена из cookie)"""
#     is_unloginned = auth_service.logout_user(token_data.refresh_token)
#     if not is_unloginned:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Недействительный refresh токен",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     # Проверяем refresh токен
#     response.delete_cookie(key="access_token")
#     return {"message": "Успешный выход"}