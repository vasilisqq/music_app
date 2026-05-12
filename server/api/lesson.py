import os
import sys

from core.dependencies import get_current_active_user, get_lesson_service, is_admin
from fastapi import APIRouter, Depends, HTTPException, status
from services.lesson_services import LessonService

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
from schemas.lesson import (
    LessonCreate,
    LessonResponse,
    LessonUpdate,
    LessonWithStatusResponse,
    LessonReorderRequest
)

router = APIRouter(tags=["lessons"], prefix="/lesson")


@router.post(
    "/create", response_model=LessonResponse, status_code=status.HTTP_201_CREATED
)
async def create_lesson(
    lesson_data: LessonCreate,
    lesson_service: LessonService = Depends(get_lesson_service),
    is_admin=Depends(is_admin),
):
    existing_lesson = await lesson_service.get_lesson_by_name(lesson_data.name)
    if existing_lesson:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Упражнение с таким названием уже существует",
        )

    existing_lesson = await lesson_service.get_lesson_by_notes(lesson_data.notes)
    if existing_lesson:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="упражнение с такими нотами уже существует",
        )

    lesson = await lesson_service.create_lesson(lesson_data)
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось создать упражнение",
        )

    return lesson


@router.get("/{lesson_id}", response_model=LessonResponse)
async def get_lesson(
    lesson_id: int,
    lesson_service: LessonService = Depends(get_lesson_service),
    current_user=Depends(get_current_active_user),
):
    lesson = await lesson_service.get_lesson_by_id(lesson_id)
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Такого упражнения не существует",
        )
    return lesson


@router.put("/{lesson_id}", response_model=LessonResponse)
async def update_lesson(
    lesson_id: int,
    lesson_data: LessonUpdate,
    lesson_service: LessonService = Depends(get_lesson_service),
    is_admin=Depends(is_admin),
):
    return await lesson_service.update_lesson(lesson_id, lesson_data)


@router.delete("/{lesson_id}")
async def delete_lesson(
    lesson_id: int,
    lesson_service: LessonService = Depends(get_lesson_service),
    is_admin=Depends(is_admin),
):
    return await lesson_service.delete_lesson(lesson_id)


@router.get("/topic/{topic_id}", response_model=list[LessonWithStatusResponse])
async def get_lessons_by_topic(
    topic_id: int,
    lesson_service: LessonService = Depends(get_lesson_service),
    current_user=Depends(get_current_active_user),
):
    # Теперь используем новый метод и передаем ID текущего пользователя
    lessons = await lesson_service.get_lessons_with_status_by_topic(
        topic_id, current_user.id
    )
    return lessons


@router.post("/topic/{topic_id}/reorder")
async def reorder_lessons_in_topic(
    topic_id: int,
    request: LessonReorderRequest,
    current_user = Depends(get_current_active_user), # Или Depends(is_admin)
    lesson_service: LessonService = Depends(get_lesson_service)
):
    """
    Изменяет порядок уроков в теме.
    Принимает список ID уроков в том порядке, в котором они должны отображаться.
    """
    try:
        await lesson_service.reorder_lessons(topic_id, request)
        return {"message": "Порядок уроков успешно обновлен"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")
