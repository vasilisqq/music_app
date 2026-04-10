from sqlalchemy import select, func
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from models import Topic, Lesson
from schemas.topic import TopicCreate

class TopicService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_topics_with_counts(self):
        """Асинхронно возвращает список всех тем вместе с количеством уроков."""
        # 1. Формируем запрос через select()
        stmt = (
            select(Topic, func.count(Lesson.id).label('lessons_count'))
            .outerjoin(Lesson)
            .group_by(Topic.id)
        )
        
        # 2. Асинхронно выполняем запрос
        result = await self.db.execute(stmt)
        
        # 3. Получаем все строки
        topics = result.all()
        
        # 4. Формируем результат (лучше собирать словарь руками, 
        # чтобы избежать внутренних скрытых полей SQLAlchemy вроде _sa_instance_state)
        res_list = []
        for topic, count in topics:
            res_list.append({
                "id": topic.id,
                "name": topic.name,
                "description": topic.description,
                "lessons_count": count
            })
        return res_list

    async def create_topic(self, topic_data: TopicCreate):
        """Асинхронно создает новую тему."""
        # Проверяем уникальность
        stmt = select(Topic).where(Topic.name == topic_data.name)
        
        # Используем await self.db.scalar(stmt) — он сам выполнит запрос 
        # и вернет первый объект Topic или None
        existing_topic = await self.db.scalar(stmt) # Берем первый результат или None
        
        if existing_topic:
            raise HTTPException(status_code=400, detail="Тема с таким названием уже существует")
            
        # Создаем
        new_topic = Topic(name=topic_data.name, description=topic_data.description)
        self.db.add(new_topic)
        await self.db.commit()        # Обязательно await!
        await self.db.refresh(new_topic) # Обязательно await!
        
        return {
            "id": new_topic.id,
            "name": new_topic.name,
            "description": new_topic.description,
            "lessons_count": 0
        }