import json
import os
import sys

from PyQt6.QtCore import QUrl, pyqtSignal, QObject
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from schemas.profile_stats import ProfileStatsResponse
from loader import settings


class ProgressWorker(QObject):
    completed_lessons_loaded_signal = pyqtSignal(list)
    lesson_completed_signal = pyqtSignal(int)
    profile_stats_loaded_signal = pyqtSignal(object)
    error_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.manager = QNetworkAccessManager()

    def get_completed_lessons_for_topic(self, topic_id: int) -> None:
        url = QUrl(f"http://localhost:8000/progress/topic/{topic_id}")
        request = QNetworkRequest(url)
        token = settings.value("token")
        if token:
            request.setRawHeader(b"Authorization", f"Bearer {token}".encode("utf-8"))

        reply = self.manager.get(request)
        reply.finished.connect(lambda: self._on_get_completed_reply(reply))

    def complete_lesson(self, lesson_id: int) -> None:
        url = QUrl(f"http://localhost:8000/progress/lesson/{lesson_id}/complete")
        request = QNetworkRequest(url)
        token = settings.value("token")
        if token:
            request.setRawHeader(b"Authorization", f"Bearer {token}".encode("utf-8"))

        reply = self.manager.post(request, b"")
        reply.finished.connect(lambda: self._on_complete_reply(reply, lesson_id))

    def get_profile_stats(self) -> None:
        url = QUrl("http://localhost:8000/progress/profile/stats")
        request = QNetworkRequest(url)
        token = settings.value("token")
        if token:
            request.setRawHeader(b"Authorization", f"Bearer {token}".encode("utf-8"))

        reply = self.manager.get(request)
        reply.finished.connect(lambda: self._on_profile_stats_reply(reply))

    def _on_get_completed_reply(self, reply: QNetworkReply) -> None:
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = json.loads(reply.readAll().data().decode("utf-8"))
            self.completed_lessons_loaded_signal.emit(data)
        else:
            self._handle_error(reply, "Ошибка загрузки прогресса")
        reply.deleteLater()

    def _on_complete_reply(self, reply: QNetworkReply, lesson_id: int) -> None:
        if reply.error() == QNetworkReply.NetworkError.NoError:
            self.lesson_completed_signal.emit(lesson_id)
        else:
            self._handle_error(reply, "Ошибка отметки урока")
        reply.deleteLater()

    def _on_profile_stats_reply(self, reply: QNetworkReply) -> None:
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = json.loads(reply.readAll().data().decode("utf-8"))
            self.profile_stats_loaded_signal.emit(ProfileStatsResponse.model_validate(data))
        else:
            self._handle_error(reply, "Ошибка загрузки статистики профиля")
        reply.deleteLater()

    def _handle_error(self, reply: QNetworkReply, default_msg: str) -> None:
        try:
            data = json.loads(reply.readAll().data().decode("utf-8"))
            self.error_signal.emit(data.get("detail", default_msg))
        except:
            self.error_signal.emit("Ошибка связи с сервером")
