from typing import List

from core.dependencies import get_current_active_user, get_topic_service
from fastapi import APIRouter, Depends
from services.topic_service import TopicService

from schemas.topic import TopicCreate, TopicResponse

# Создаем роутер с префиксом
router = APIRouter(prefix="/topics", tags=["Topics"])


@router.get("/", response_model=List[TopicResponse])
async def get_topics(
    topic_service: TopicService = Depends(get_topic_service),
    current_user=Depends(get_current_active_user),
):
    """Получить список всех тем с количеством уроков и прогрессом пользователя"""
    return await topic_service.get_all_topics_with_counts(current_user.id)


@router.post("/", response_model=TopicResponse)
async def create_topic(
    topic: TopicCreate, topic_service: TopicService = Depends(get_topic_service)
):
    """Создать новую тему"""
    # Сервис возвращает новый ORM-объект, FastAPI превратит его в TopicResponse
    return await topic_service.create_topic(topic)


@router.put("/{topic_id}", response_model=TopicResponse)
async def update_topic(
    topic_id: int,
    topic: TopicCreate,
    topic_service: TopicService = Depends(get_topic_service),
):
    """Обновить существующую тему"""
    # Сервис возвращает обновленный ORM-объект, FastAPI превратит его в TopicResponse
    return await topic_service.update_topic(topic_id, topic)


@router.delete("/{topic_id}")
async def delete_topic(
    topic_id: int, topic_service: TopicService = Depends(get_topic_service)
):
    """Удалить тему (и все связанные с ней уроки)"""
    return await topic_service.delete_topic(topic_id)
