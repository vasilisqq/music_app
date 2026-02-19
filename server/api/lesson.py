from fastapi import APIRouter, Depends, HTTPException, status, Response
import sys
import os
# from app.core.config import settings
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from schemas.lesson import LessonCreate
from services.lesson_services import LessonService
from services.auth_service import AuthService
# from app.services.auth_service import AuthService
from core.dependencies import get_lesson_service
from core.dependencies import is_admin

router = APIRouter(tags=["lessons"],prefix="/lesson")

@router.post("/create", status_code=status.HTTP_201_CREATED)
async def register(
    lesson_data: LessonCreate,
    lesson_service: LessonService = Depends(get_lesson_service),
    is_admin = Depends(is_admin)
):
    """Регистрация нового пользователя"""
    existing_lesson = await lesson_service.get_lesson_by_name(lesson_data.name)
    if existing_lesson:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Упражнение с таким названием уже существует"
        )
    existing_lesson = await lesson_service.get_lesson_by_notes(lesson_data.notes)
    if existing_lesson:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="упражнение с такими нотами уже существует"
        )
    lesson = await lesson_service.create_lesson(lesson_data)
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось создать упражнение"
        )

