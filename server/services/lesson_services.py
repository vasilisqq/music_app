from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict
from schemas.lesson import LessonCreate
from models import Lesson
from services.user_service import UserService
from server.core.config import settings
from sqlalchemy import select, insert

class LessonService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_lesson_by_name(self, name:str):
        result = await self.db.execute(
            select(Lesson).where(Lesson.name == name)
            )
        return result.scalar_one_or_none()
    
    async def get_lesson_by_notes(self, notes:dict):
        result = await self.db.execute(
            select(Lesson.id).where(Lesson.notes == notes)
            )
        return result.scalar_one_or_none()


    async def create_lesson(self, lesson_data: LessonCreate) -> Optional[bool]:
        db_lesson = Lesson(
                name=lesson_data.name,
                difficult=lesson_data.difficult,
                rhythm=lesson_data.rhythm,
                notes=lesson_data.notes,
                topic=lesson_data.topic
            )
        self.db.add(db_lesson)
        await self.db.commit()
        await self.db.refresh(db_lesson)
        return db_lesson

    async def get_lessons_by_topic(self, topic_id: int):
        """Получает список всех уроков для указанной темы."""
        result = await self.db.execute(
            select(Lesson).where(Lesson.topic == topic_id) # Используем поле topic, как в create_lesson
        )
        # Получаем список всех найденных записей
        return result.scalars().all()
        
        
        

