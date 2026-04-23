from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Lesson, LessonProgress
from schemas.lesson import LessonCreate, LessonUpdate


class LessonService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_next_order_in_topic(self, topic_id: int) -> int:
        result = await self.db.execute(
            select(func.max(Lesson.order_in_topic)).where(Lesson.topic_id == topic_id)
        )
        max_order = result.scalar_one_or_none()
        return (max_order or 0) + 1

    async def _maybe_assign_order_for_new_topic(self, lesson: Lesson, *, new_topic_id: int, topic_changed: bool):
        if topic_changed:
            lesson.order_in_topic = await self._get_next_order_in_topic(new_topic_id)
            return

        if getattr(lesson, "order_in_topic", None) is None:
            lesson.order_in_topic = await self._get_next_order_in_topic(new_topic_id)



    async def get_lesson_by_id(self, lesson_id: int):
        return await self.db.get(Lesson, lesson_id)

    async def get_lesson_by_name(self, name: str):
        result = await self.db.execute(select(Lesson).where(Lesson.name == name))
        return result.scalar_one_or_none()

    async def get_lesson_by_notes(self, notes: dict):
        result = await self.db.execute(select(Lesson).where(Lesson.notes == notes))
        return result.scalar_one_or_none()

    async def create_lesson(self, lesson_data: LessonCreate) -> Optional[Lesson]:
        topic_id = lesson_data.topic
        db_lesson = Lesson(
            name=lesson_data.name,
            description=lesson_data.description,
            difficult=lesson_data.difficult,
            rhythm=lesson_data.rhythm,
            notes=lesson_data.notes,
            topic=topic_id,
            topic_id=topic_id,
            order_in_topic=lesson_data.order_in_topic or await self._get_next_order_in_topic(topic_id),
        )
        self.db.add(db_lesson)
        await self.db.commit()
        await self.db.refresh(db_lesson)
        return db_lesson

    async def update_lesson(self, lesson_id: int, lesson_data: LessonUpdate):
        lesson = await self.get_lesson_by_id(lesson_id)
        if not lesson:
            raise HTTPException(status_code=404, detail="Урок не найден")

        if lesson.name != lesson_data.name:
            existing_lesson = await self.get_lesson_by_name(lesson_data.name)
            if existing_lesson and existing_lesson.id != lesson_id:
                raise HTTPException(status_code=400, detail="Упражнение с таким названием уже существует")

        existing_notes_lesson = await self.get_lesson_by_notes(lesson_data.notes)
        if existing_notes_lesson and existing_notes_lesson.id != lesson_id:
            raise HTTPException(status_code=400, detail="упражнение с такими нотами уже существует")

        old_topic_id = lesson.topic_id
        new_topic_id = lesson_data.topic
        topic_changed = old_topic_id != new_topic_id

        lesson.name = lesson_data.name
        lesson.description = lesson_data.description
        lesson.difficult = lesson_data.difficult
        lesson.rhythm = lesson_data.rhythm
        lesson.notes = lesson_data.notes
        lesson.topic = new_topic_id
        lesson.topic_id = new_topic_id

        if lesson_data.order_in_topic is not None and not topic_changed:
            lesson.order_in_topic = lesson_data.order_in_topic
        else:
            await self._maybe_assign_order_for_new_topic(
                lesson, new_topic_id=new_topic_id, topic_changed=topic_changed
            )

        await self.db.commit()
        await self.db.refresh(lesson)
        return lesson

    async def delete_lesson(self, lesson_id: int):
        lesson = await self.get_lesson_by_id(lesson_id)
        if not lesson:
            raise HTTPException(status_code=404, detail="Урок не найден")

        await self.db.delete(lesson)
        await self.db.commit()
        return {"id": lesson_id, "message": "Урок успешно удален"}

    async def get_lessons_by_topic(self, topic_id: int):
        result = await self.db.execute(
            select(Lesson)
            .where(Lesson.topic_id == topic_id)
            .order_by(Lesson.order_in_topic.asc())
        )
        return result.scalars().all()
    

    async def get_lessons_with_status_by_topic(self, topic_id: int, user_id: int):
        # 1. Получаем все уроки темы, отсортированные по порядку
        result = await self.db.execute(
            select(Lesson)
            .where(Lesson.topic_id == topic_id)
            .order_by(Lesson.order_in_topic.asc())
        )
        lessons = result.scalars().all()

        if not lessons:
            return []

        # 2. Получаем ID всех пройденных уроков пользователя в этой теме
        progress_result = await self.db.execute(
            select(LessonProgress.lesson_id)
            .join(Lesson, Lesson.id == LessonProgress.lesson_id)
            .where(LessonProgress.user_id == user_id)
            .where(Lesson.topic_id == topic_id)
            .where(LessonProgress.completed_at.is_not(None))
        )
        completed_lesson_ids = set(progress_result.scalars().all())

        # 3. Находим максимальный order_in_topic среди пройденных уроков
        max_completed_order = 0
        for lesson in lessons:
            if lesson.id in completed_lesson_ids:
                if lesson.order_in_topic > max_completed_order:
                    max_completed_order = lesson.order_in_topic

        # 4. Присваиваем статусы "на лету"
        for lesson in lessons:
            if lesson.id in completed_lesson_ids:
                lesson.status = "completed"
            elif lesson.order_in_topic <= max_completed_order + 1:
                lesson.status = "available"
            else:
                lesson.status = "locked"

        return lessons
