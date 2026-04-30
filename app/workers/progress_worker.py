import os
import sys

from PyQt6.QtCore import pyqtSignal

# Импортируем наш базовый класс
from workers.base_worker import BaseAPIWorker

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
from schemas.profile_stats import ProfileStatsResponse


class ProgressWorker(BaseAPIWorker):
    """
    Воркер для работы с прогрессом пользователя (статистика, пройденные уроки).
    """

    # Сигналы остаются без изменений, чтобы не сломать UI
    completed_lessons_loaded_signal = pyqtSignal(list)
    lesson_completed_signal = pyqtSignal(int)
    profile_stats_loaded_signal = pyqtSignal(object)
    error_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def get_completed_lessons_for_topic(self, topic_id: int) -> None:
        """
        Получает список ID пройденных уроков для конкретной темы.
        """
        self._make_request(
            method="GET",
            endpoint=f"/progress/topic/{topic_id}",
            success_callback=self.completed_lessons_loaded_signal.emit,
            error_callback=self.error_signal.emit,
        )

    def complete_lesson(self, lesson_id: int) -> None:
        """
        Отправляет запрос на завершение урока.
        """
        self._make_request(
            method="POST",
            endpoint=f"/progress/lesson/{lesson_id}/complete",
            # Передаем lambda _, чтобы проигнорировать ответ от сервера
            # и просто прокинуть lesson_id дальше в интерфейс
            success_callback=lambda _: self.lesson_completed_signal.emit(lesson_id),
            error_callback=self.error_signal.emit,
        )

    def get_profile_stats(self) -> None:
        """
        Запрашивает статистику профиля пользователя и валидирует ее через Pydantic.
        """
        self._make_request(
            method="GET",
            endpoint="/progress/profile/stats",
            # Парсим полученный словарь в Pydantic модель перед отправкой в сигнал
            success_callback=lambda data: self.profile_stats_loaded_signal.emit(
                ProfileStatsResponse.model_validate(data)
            ),
            error_callback=self.error_signal.emit,
        )
