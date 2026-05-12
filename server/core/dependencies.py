from db import get_db
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from models import User
from services.auth_service import AuthService
from services.lesson_services import LessonService
from services.topic_service import TopicService
from services.user_service import UserService
from sqlalchemy.ext.asyncio import AsyncSession
from utils.jwt import verify_token

# from app.services.auth_service import AuthService

# # Схема безопасности для Bearer токенов (остается для документации OpenAPI)
security = HTTPBearer()


async def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    """Зависимость, предоставляющая UserService."""
    return UserService(db)


async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Зависимость, предоставляющая AuthService."""
    return AuthService(db)


async def get_lesson_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Зависимость, предоставляющая AuthService."""
    return LessonService(db)


async def get_topic_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Зависимость, предоставляющая AuthService."""
    return TopicService(db)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user_service: UserService = Depends(get_user_service),
) -> User:
    """Получение текущего пользователя по JWT токену из cookie"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось валидировать учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = verify_token(credentials.credentials)
    if payload is None:
        raise credentials_exception
    user = await user_service.get_user_by_id(payload)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user=Depends(get_current_user)):
    """Получение текущего активного пользователя"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Неактивный пользователь"
        )
    return current_user


async def is_admin(
    current_user=Depends(get_current_active_user),
    user_service=Depends(get_user_service),
):
    if not current_user.role_info or current_user.role_info.name != "администратор":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав. Доступно только администраторам.",
        )

    return current_user


# async def get_current_admin(
#     current_user: User = Depends(get_current_user)
# ) -> User:
#     """Получение текущего суперпользователя"""
#     if not current_user.is_superuser:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Недостаточно прав доступа"
#         )
#      return current_user
