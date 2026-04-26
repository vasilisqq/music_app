from fastapi import APIRouter
from .auth import router as auth_router
from .lesson import router as lesson_router
from .topic import router as topic_router
from .progress import router as progress_router
from .admin_stats import router as admin_stats_router
# from .users import router as users_router

api_router = APIRouter()

# Подключаем роутеры
api_router.include_router(auth_router)
api_router.include_router(lesson_router)
api_router.include_router(topic_router)
api_router.include_router(progress_router)
api_router.include_router(admin_stats_router)

