from fastapi import APIRouter, Depends
from typing import List

from schemas.topic import TopicCreate, TopicResponse
from services.topic_service import TopicService
from core.dependencies import get_topic_service

# Создаем роутер с префиксом
router = APIRouter(prefix="/topics", tags=["Topics"])


@router.get("/", response_model=List[TopicResponse])
async def get_topics(topic_service: TopicService = Depends(get_topic_service)):
    """Получить список всех тем с количеством уроков в каждой"""
    # Сервис возвращает список ORM-объектов, а FastAPI сам превратит их в List[TopicResponse]
    return await topic_service.get_all_topics_with_counts()


@router.post("/", response_model=TopicResponse)
async def create_topic(topic: TopicCreate,
                       topic_service: TopicService = Depends(get_topic_service)):
    """Создать новую тему"""
    # Сервис возвращает новый ORM-объект, FastAPI превратит его в TopicResponse
    return await topic_service.create_topic(topic)


@router.put("/{topic_id}", response_model=TopicResponse)
async def update_topic(topic_id: int, 
                       topic: TopicCreate,
                       topic_service: TopicService = Depends(get_topic_service)):
    """Обновить существующую тему"""
    # Сервис возвращает обновленный ORM-объект, FastAPI превратит его в TopicResponse
    return await topic_service.update_topic(topic_id, topic)

@router.delete("/{topic_id}")
async def delete_topic(topic_id: int, 
                       topic_service: TopicService = Depends(get_topic_service)):
    """Удалить тему (и все связанные с ней уроки)"""
    return await topic_service.delete_topic(topic_id)