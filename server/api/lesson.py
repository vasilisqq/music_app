from fastapi import APIRouter, Depends, HTTPException, status

from services.lesson_services import LessonService

from core.dependencies import get_lesson_service, is_admin, get_current_active_user

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from schemas.lesson import LessonCreate, LessonResponse


router = APIRouter(tags=["lessons"],prefix="/lesson")


@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_lesson(
    lesson_data: LessonCreate,
    lesson_service: LessonService = Depends(get_lesson_service),
    is_admin = Depends(is_admin)
):
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
    

@router.get("/get", status_code=status.HTTP_201_CREATED)
async def get_lesson(
    # lesson_data: LessonCreate,
    lesson_service: LessonService = Depends(get_lesson_service),
    current_user = Depends(get_current_active_user)
):
    lesson =  await lesson_service.get_lesson_by_name("ыдловрап")
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Такого упражнения не существует"
        )
    return LessonResponse.model_validate(lesson)


@router.get("/topic/{topic_id}", response_model=list[LessonResponse])
async def get_lessons_by_topic(
    topic_id: int,
    lesson_service: LessonService = Depends(get_lesson_service),
    current_user = Depends(get_current_active_user) # Защищаем роут авторизацией
):
    """
    Эндпоинт для получения списка уроков по ID темы.
    """
    lessons = await lesson_service.get_lessons_by_topic(topic_id)
    
    # Возвращаем список уроков (FastAPI сам преобразует их в Pydantic схемы)
    return lessons
