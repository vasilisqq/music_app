from sqlalchemy import select, func
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from models import Topic, Lesson # Убедись в правильных импортах
from schemas.topic import TopicCreate

class TopicService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_topics_with_counts(self):
        """Возвращаем записи БД, эндпоинт сам превратит их в TopicResponse"""
        stmt = (
            select(Topic, func.count(Lesson.id).label('lessons_count'))
            .outerjoin(Lesson)
            .group_by(Topic.id)
            .order_by(Topic.id)
        )
        
        result = await self.db.execute(stmt)
        topics_with_counts = result.all()
        
        res_list = []
        for topic_obj, count in topics_with_counts:
            # Магия здесь! Динамически добавляем атрибут к объекту SQLAlchemy.
            # Pydantic (в эндпоинте) легко его прочитает благодаря from_attributes=True
            topic_obj.lessons_count = count
            res_list.append(topic_obj) 
            
        return res_list # Возвращаем чистые ORM объекты!

    async def create_topic(self, topic_data: TopicCreate):
        stmt = select(Topic).where(Topic.name == topic_data.name)
        existing_topic = await self.db.scalar(stmt)
        
        if existing_topic:
            raise HTTPException(status_code=400, detail="Тема с таким названием уже существует")
            
        new_topic = Topic(name=topic_data.name, description=topic_data.description)
        self.db.add(new_topic)
        await self.db.commit()
        await self.db.refresh(new_topic)
        
        # Для Pydantic указываем, что уроков пока 0
        new_topic.lessons_count = 0 
        
        return new_topic # Снова возвращаем ORM объект!

    async def update_topic(self, topic_id: int, topic_data: TopicCreate):
        topic = await self.db.get(Topic, topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Тема не найдена")

        if topic.name != topic_data.name:
            stmt = select(Topic).where(Topic.name == topic_data.name)
            existing_topic = await self.db.scalar(stmt)
            if existing_topic:
                raise HTTPException(status_code=400, detail="Тема с таким названием уже существует")

        topic.name = topic_data.name
        topic.description = topic_data.description
        await self.db.commit()
        await self.db.refresh(topic)

        # Считаем количество уроков для корректного ответа
        stmt_count = select(func.count(Lesson.id)).where(Lesson.topic_id == topic_id)
        l_count = await self.db.scalar(stmt_count) or 0
        
        topic.lessons_count = l_count

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