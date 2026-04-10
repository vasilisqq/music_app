from fastapi import APIRouter, Depends
from typing import List

from schemas.topic import TopicCreate, TopicResponse
from server.services.topic_service import TopicService
from core.dependencies import get_topic_service

router = APIRouter(prefix="/topics", tags=["Topics"])

@router.get("/", response_model=List[TopicResponse])
async def get_topics(topic_serivce: TopicService = Depends(get_topic_service)):
    """Получить список всех тем с количеством уроков в каждой"""
    return await topic_serivce.get_all_topics_with_counts()


@router.post("/", response_model=TopicResponse)
async def create_topic(topic: TopicCreate,
                 topic_serivce: TopicService = Depends(get_topic_service)):
    """Создать новую тему"""
    return await topic_serivce.create_topic(topic)