from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_db
from services.user_service import UserService
from services.auth_service import AuthService
from services.lesson_services import LessonService
# from app.utils.jwt import verify_token
# from app.models.user import User
# from app.services.auth_service import AuthService

# # Схема безопасности для Bearer токенов (остается для документации OpenAPI)
# security = HTTPBearer()

# async def get_current_user(
#     request: Request, # Получаем Request для доступа к cookie
#     db: AsyncSession = Depends(get_db)
# ) -> User:
#     """Получение текущего пользователя по JWT токену из cookie"""
    
#     credentials_exception = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="Не удалось валидировать учетные данные",
#         headers={"WWW-Authenticate": "Bearer"},
#     )
    
#     # Извлекаем access_token из cookie
#     token = request.cookies.get("access_token")
#     if not token:
#         raise credentials_exception
    
#     # Проверяем токен
#     payload = verify_token(token, token_type="access")
#     if not payload:
#         raise credentials_exception
    
#     user_id = payload.get("sub")
#     if user_id is None:
#         raise credentials_exception
    
#     # Получаем пользователя из базы данных
#     user_service = UserService(db)
#     user = await user_service.get_user_by_id(int(user_id))
#     if user is None:
#         raise credentials_exception
    
#     return user

# async def get_current_active_user(
#     current_user: User = Depends(get_current_user)
# ) -> User:
#     """Получение текущего активного пользователя"""
#     if not current_user.is_active:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST, 
#             detail="Неактивный пользователь"
#         )
#     return current_user

# async def get_current_superuser(
#     current_user: User = Depends(get_current_user)
# ) -> User:
#     """Получение текущего суперпользователя"""
#     if not current_user.is_superuser:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Недостаточно прав доступа"
#         )
#     return current_user

async def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    """Зависимость, предоставляющая UserService."""
    return UserService(db)

async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Зависимость, предоставляющая AuthService."""
    return AuthService(db)

async def get_lesson_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Зависимость, предоставляющая AuthService."""
    return LessonService(db)