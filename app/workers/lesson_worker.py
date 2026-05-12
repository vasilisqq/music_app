import os
import sys

from PyQt6.QtCore import pyqtSignal

# Импортируем наш новый базовый класс
from workers.base_worker import BaseAPIWorker

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schemas.lesson import LessonCreate, LessonResponse, LessonUpdate


class LessonWorker(BaseAPIWorker):
    lesson_created_sygnal = pyqtSignal(LessonResponse)
    lesson_updated_signal = pyqtSignal(LessonResponse)
    lesson_deleted_signal = pyqtSignal(int)
    lesson_error_sygnal = pyqtSignal(
        str
    )
    lesson_get_signal = pyqtSignal(LessonResponse)
    lessons_by_topic_loaded_signal = pyqtSignal(list)
    lessons_reordered_signal = pyqtSignal()

    def __init__(self):
        super().__init__()  # Инициализирует QNetworkAccessManager из базового класса

    def create_lesson(self, lesson_data: LessonCreate) -> None:
        self._make_request(
            method="POST",
            endpoint="/lesson/create",
            data=lesson_data,
            success_callback=lambda d: self.lesson_created_sygnal.emit(
                LessonResponse.model_validate(d)
            ),
            error_callback=self.lesson_error_sygnal.emit,
        )

    def get_lesson_by_id(self, lesson_id: int) -> None:
        self._make_request(
            method="GET",
            endpoint=f"/lesson/{lesson_id}",
            success_callback=lambda d: self.lesson_get_signal.emit(
                LessonResponse.model_validate(d)
            ),
            error_callback=self.lesson_error_sygnal.emit,
        )

    def update_lesson(self, lesson_id: int, lesson_data: LessonUpdate) -> None:
        self._make_request(
            method="PUT",
            endpoint=f"/lesson/{lesson_id}",
            data=lesson_data,
            success_callback=lambda d: self.lesson_updated_signal.emit(
                LessonResponse.model_validate(d)
            ),
            error_callback=self.lesson_error_sygnal.emit,
        )

    def delete_lesson(self, lesson_id: int) -> None:
        self._make_request(
            method="DELETE",
            endpoint=f"/lesson/{lesson_id}",
            success_callback=lambda _: self.lesson_deleted_signal.emit(lesson_id),
            error_callback=self.lesson_error_sygnal.emit,
        )

    def get_lessons_by_topic(self, topic_id: int) -> None:
        self._make_request(
            method="GET",
            endpoint=f"/lesson/topic/{topic_id}",
            success_callback=lambda d: self.lessons_by_topic_loaded_signal.emit(
                [LessonResponse.model_validate(item) for item in d]
            ),
            error_callback=self.lesson_error_sygnal.emit,
        )

    def reorder_lessons(self, topic_id: int, lesson_ids: list[int]) -> None:
        """Отправляет запрос на изменение порядка уроков в теме"""
        self._make_request(
            method="POST",
            endpoint=f"/lesson/topic/{topic_id}/reorder",
            data={"lesson_ids": lesson_ids},
            success_callback=lambda _: self.lessons_reordered_signal.emit(),
            error_callback=self.lesson_error_sygnal.emit,
        )
