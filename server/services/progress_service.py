from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Lesson, LessonProgress


class ProgressService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_completed_lesson_ids_for_topic(self, *, user_id: int, topic_id: int) -> list[int]:
        result = await self.db.execute(
            select(LessonProgress.lesson_id)
            .join(Lesson, Lesson.id == LessonProgress.lesson_id)
            .where(LessonProgress.user_id == user_id)
            .where(Lesson.topic_id == topic_id)
            .where(LessonProgress.completed_at.is_not(None))
        )
        return list(result.scalars().all())

    async def mark_lesson_completed(self, *, user_id: int, lesson_id: int) -> None:
        lesson = await self.db.get(Lesson, lesson_id)
        if not lesson:
            raise HTTPException(status_code=404, detail="Урок не найден")

        result = await self.db.execute(
            select(LessonProgress)
            .where(LessonProgress.user_id == user_id)
            .where(LessonProgress.lesson_id == lesson_id)
        )
        progress = result.scalar_one_or_none()

        if progress is None:
            progress = LessonProgress(user_id=user_id, lesson_id=lesson_id)
            self.db.add(progress)

        if progress.completed_at is None:
            progress.completed_at = datetime.now(timezone.utc)

        await self.db.commit()
