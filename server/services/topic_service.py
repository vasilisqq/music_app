from fastapi import HTTPException
from models import Lesson, LessonProgress, Topic
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.topic import TopicCreate


class TopicService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_topics_with_counts(self, user_id: int):
        """Возвращаем темы с количеством уроков и прогрессом пользователя"""
        completed_lessons = func.count(
            case((LessonProgress.completed_at.is_not(None), Lesson.id))
        ).label("completed_lessons_count")

        stmt = (
            select(
                Topic,
                func.count(Lesson.id).label("lessons_count"),
                completed_lessons,
            )
            .outerjoin(Lesson, Lesson.topic_id == Topic.id)
            .outerjoin(
                LessonProgress,
                (LessonProgress.lesson_id == Lesson.id)
                & (LessonProgress.user_id == user_id),
            )
            .group_by(Topic.id)
            .order_by(Topic.id)
        )

        result = await self.db.execute(stmt)
        topics_with_counts = result.all()

        res_list = []
        for topic_obj, lessons_count, completed_count in topics_with_counts:
            topic_obj.lessons_count = int(lessons_count or 0)
            topic_obj.progress = (
                float(completed_count) / topic_obj.lessons_count
                if topic_obj.lessons_count > 0
                else 0.0
            )
            res_list.append(topic_obj)

        return res_list

    async def create_topic(self, topic_data: TopicCreate):
        stmt = select(Topic).where(Topic.name == topic_data.name)
        existing_topic = await self.db.scalar(stmt)

        if existing_topic:
            raise HTTPException(
                status_code=400, detail="Тема с таким названием уже существует"
            )

        new_topic = Topic(name=topic_data.name, description=topic_data.description)
        self.db.add(new_topic)
        await self.db.commit()
        await self.db.refresh(new_topic)

        new_topic.lessons_count = 0
        new_topic.progress = 0.0

        return new_topic

    async def update_topic(self, topic_id: int, topic_data: TopicCreate):
        topic = await self.db.get(Topic, topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Тема не найдена")

        if topic.name != topic_data.name:
            stmt = select(Topic).where(Topic.name == topic_data.name)
            existing_topic = await self.db.scalar(stmt)
            if existing_topic:
                raise HTTPException(
                    status_code=400, detail="Тема с таким названием уже существует"
                )

        topic.name = topic_data.name
        topic.description = topic_data.description
        await self.db.commit()
        await self.db.refresh(topic)

        stmt_count = select(func.count(Lesson.id)).where(Lesson.topic_id == topic_id)
        l_count = await self.db.scalar(stmt_count) or 0

        topic.lessons_count = l_count
        topic.progress = 0.0

        return topic

    async def delete_topic(self, topic_id: int):
        """Удаляет тему (каскадно удалятся и все её уроки благодаря настройкам ORM)"""
        topic = await self.db.get(Topic, topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Тема не найдена")

        # Удаляем объект
        await self.db.delete(topic)
        await self.db.commit()

        # Возвращаем ID удаленной темы, чтобы клиент знал, что убирать из таблицы
        return {"id": topic_id, "message": "Тема успешно удалена"}
