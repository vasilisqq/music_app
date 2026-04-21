import json
import os
import sys

from PyQt6.QtCore import QUrl, pyqtSignal, QObject
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schemas.lesson import LessonCreate, LessonUpdate, LessonResponse
from loader import settings


class LessonWorker(QObject):
    lesson_created_sygnal = pyqtSignal(LessonResponse)
    lesson_updated_signal = pyqtSignal(LessonResponse)
    lesson_deleted_signal = pyqtSignal(int)
    lesson_error_sygnal = pyqtSignal(str)
    lesson_get_signal = pyqtSignal(LessonResponse)
    lessons_by_topic_loaded_signal = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.manager = QNetworkAccessManager()

    def create_lesson(self, lesson_data: LessonCreate) -> None:
        url = QUrl("http://localhost:8000/lesson/create")
        request = self._build_json_request(url)
        json_bytes = lesson_data.model_dump_json().encode("utf-8")
        reply = self.manager.post(request, json_bytes)
        reply.finished.connect(lambda: self._on_create_reply(reply))

    def get_lesson_by_id(self, lesson_id: int) -> None:
        url = QUrl(f"http://localhost:8000/lesson/{lesson_id}")
        request = self._build_json_request(url)
        reply = self.manager.get(request)
        reply.finished.connect(lambda: self._on_get_lesson_reply(reply))

    def update_lesson(self, lesson_id: int, lesson_data: LessonUpdate) -> None:
        url = QUrl(f"http://localhost:8000/lesson/{lesson_id}")
        request = self._build_json_request(url)
        json_bytes = lesson_data.model_dump_json().encode("utf-8")
        reply = self.manager.put(request, json_bytes)
        reply.finished.connect(lambda: self._on_update_reply(reply))

    def delete_lesson(self, lesson_id: int) -> None:
        url = QUrl(f"http://localhost:8000/lesson/{lesson_id}")
        request = self._build_json_request(url)
        reply = self.manager.deleteResource(request)
        reply.finished.connect(lambda: self._on_delete_reply(reply, lesson_id))

    def get_lessons_by_topic(self, topic_id: int) -> None:
        url = QUrl(f"http://localhost:8000/lesson/topic/{topic_id}")
        request = self._build_json_request(url)
        reply = self.manager.get(request)
        reply.finished.connect(lambda: self._on_get_lessons_by_topic_reply(reply))

    def _build_json_request(self, url: QUrl) -> QNetworkRequest:
        request = QNetworkRequest(url)
        token = settings.value("token")
        if token:
            request.setRawHeader(b"Authorization", f"Bearer {token}".encode("utf-8"))
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        return request

    def _on_create_reply(self, reply: QNetworkReply) -> None:
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = json.loads(reply.readAll().data().decode("utf-8"))
            self.lesson_created_sygnal.emit(LessonResponse.model_validate(data))
        else:
            self._handle_error(reply, "Ошибка при создании урока")
        reply.deleteLater()

    def _on_get_lesson_reply(self, reply: QNetworkReply) -> None:
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = json.loads(reply.readAll().data().decode("utf-8"))
            self.lesson_get_signal.emit(LessonResponse.model_validate(data))
        else:
            self._handle_error(reply, "Ошибка загрузки урока")
        reply.deleteLater()

    def _on_update_reply(self, reply: QNetworkReply) -> None:
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = json.loads(reply.readAll().data().decode("utf-8"))
            self.lesson_updated_signal.emit(LessonResponse.model_validate(data))
        else:
            self._handle_error(reply, "Ошибка при обновлении урока")
        reply.deleteLater()

    def _on_delete_reply(self, reply: QNetworkReply, lesson_id: int) -> None:
        if reply.error() == QNetworkReply.NetworkError.NoError:
            self.lesson_deleted_signal.emit(lesson_id)
        else:
            self._handle_error(reply, "Ошибка при удалении урока")
        reply.deleteLater()

    def _on_get_lessons_by_topic_reply(self, reply: QNetworkReply) -> None:
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = json.loads(reply.readAll().data().decode("utf-8"))
            lessons = [LessonResponse.model_validate(item) for item in data]
            self.lessons_by_topic_loaded_signal.emit(lessons)
        else:
            self._handle_error(reply, "Ошибка загрузки уроков")
        reply.deleteLater()

    def _handle_error(self, reply: QNetworkReply, default_msg: str) -> None:
        try:
            data = json.loads(reply.readAll().data().decode("utf-8"))
            self.lesson_error_sygnal.emit(data.get("detail", default_msg))
        except:
            self.lesson_error_sygnal.emit("Ошибка связи с сервером")
