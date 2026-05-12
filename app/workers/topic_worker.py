import os
import sys

from PyQt6.QtCore import pyqtSignal

# Импортируем наш базовый класс
from workers.base_worker import BaseAPIWorker

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schemas.topic import TopicCreate, TopicResponse


class TopicWorker(BaseAPIWorker):
    """Сетевой воркер для работы с темами (Pydantic Edition)"""

    # Сигналы строго типизированы нашими моделями
    topics_loaded_signal = pyqtSignal(list)  # Ожидает list[TopicResponse]
    topic_added_signal = pyqtSignal(TopicResponse)
    topic_updated_signal = pyqtSignal(TopicResponse)
    topic_deleted_signal = pyqtSignal(int)
    error_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def get_topics(self) -> None:
        """Запрашивает список всех тем."""
        self._make_request(
            method="GET",
            endpoint="/topics/",
            success_callback=lambda data: self.topics_loaded_signal.emit(
                [TopicResponse.model_validate(item) for item in data]
            ),
            error_callback=self.error_signal.emit,
        )

    def create_topic(self, topic_data: TopicCreate) -> None:
        """Создает новую тему (принимает Pydantic модель TopicCreate)."""
        self._make_request(
            method="POST",
            endpoint="/topics/",
            data=topic_data,
            success_callback=lambda data: self.topic_added_signal.emit(
                TopicResponse.model_validate(data)
            ),
            error_callback=self.error_signal.emit,
        )

    def edit_topic(self, topic_id: int, topic_data: TopicCreate) -> None:
        """Обновляет существующую тему (принимает Pydantic модель TopicCreate)."""
        self._make_request(
            method="PUT",  # В оригинале у тебя был PUT
            endpoint=f"/topics/{topic_id}",
            data=topic_data,
            success_callback=lambda data: self.topic_updated_signal.emit(
                TopicResponse.model_validate(data)
            ),
            error_callback=self.error_signal.emit,
        )

    def delete_topic(self, topic_id: int) -> None:
        """Удаляет тему по её ID."""
        self._make_request(
            method="DELETE",
            endpoint=f"/topics/{topic_id}",
            # При успешном удалении сервер может вернуть просто {"detail": "success"}
            # Игнорируем ответ (_) и просто прокидываем ID удаленной темы в интерфейс
            success_callback=lambda _: self.topic_deleted_signal.emit(topic_id),
            error_callback=self.error_signal.emit,
        )
