from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Lesson
from schemas.lesson import LessonCreate, LessonUpdate


class LessonService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_lesson_by_id(self, lesson_id: int):
        return await self.db.get(Lesson, lesson_id)

    async def get_lesson_by_name(self, name: str):
        result = await self.db.execute(select(Lesson).where(Lesson.name == name))
        return result.scalar_one_or_none()

    async def get_lesson_by_notes(self, notes: dict):
        result = await self.db.execute(select(Lesson).where(Lesson.notes == notes))
        return result.scalar_one_or_none()

    async def create_lesson(self, lesson_data: LessonCreate) -> Optional[Lesson]:
        db_lesson = Lesson(
            name=lesson_data.name,
            description=lesson_data.description,
            difficult=lesson_data.difficult,
            rhythm=lesson_data.rhythm,
            notes=lesson_data.notes,
            topic=lesson_data.topic,
            topic_id=lesson_data.topic,
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

        lesson.name = lesson_data.name
        lesson.description = lesson_data.description
        lesson.difficult = lesson_data.difficult
        lesson.rhythm = lesson_data.rhythm
        lesson.notes = lesson_data.notes
        lesson.topic = lesson_data.topic
        lesson.topic_id = lesson_data.topic

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
        result = await self.db.execute(select(Lesson).where(Lesson.topic == topic_id))
        return result.scalars().all()
