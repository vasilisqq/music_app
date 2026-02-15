from fastapi import APIRouter
from .auth import router as auth_router
from .lesson import router as lesson_router
# from .users import router as users_router

api_router = APIRouter()

# Подключаем роутеры
api_router.include_router(auth_router)
api_router.include_router(lesson_router)

