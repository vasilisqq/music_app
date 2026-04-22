from fastapi import APIRouter, Depends, status

from core.dependencies import get_current_active_user
from services.progress_service import ProgressService
from db import get_db
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter(tags=["progress"], prefix="/progress")


async def get_progress_service(db: AsyncSession = Depends(get_db)) -> ProgressService:
    return ProgressService(db)


@router.get("/topic/{topic_id}", response_model=list[int])
async def get_completed_lessons_for_topic(
    topic_id: int,
    progress_service: ProgressService = Depends(get_progress_service),
    current_user=Depends(get_current_active_user),
):
    return await progress_service.get_completed_lesson_ids_for_topic(
        user_id=current_user.id, topic_id=topic_id
    )


@router.post("/lesson/{lesson_id}/complete", status_code=status.HTTP_204_NO_CONTENT)
async def complete_lesson(
    lesson_id: int,
    progress_service: ProgressService = Depends(get_progress_service),
    current_user=Depends(get_current_active_user),
):
    await progress_service.mark_lesson_completed(user_id=current_user.id, lesson_id=lesson_id)
    return None
