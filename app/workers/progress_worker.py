import json
import os
import sys

from PyQt6.QtCore import QUrl, pyqtSignal, QObject, QTimer
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from schemas.profile_stats import ProfileStatsResponse
from loader import settings

# Таймауты для сетевых запросов (в миллисекундах)
REQUEST_TIMEOUT_MS = 10000  # 10 секунд


class ProgressWorker(QObject):
    completed_lessons_loaded_signal = pyqtSignal(list)
    lesson_completed_signal = pyqtSignal(int)
    profile_stats_loaded_signal = pyqtSignal(object)
    error_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.manager = QNetworkAccessManager()
        self.timeout_timers = {}  # Словарь для отслеживания таймаутов

    def get_completed_lessons_for_topic(self, topic_id: int) -> None:
        try:
            url = QUrl(f"http://localhost:8000/progress/topic/{topic_id}")
            request = QNetworkRequest(url)
            token = settings.value("token")
            if token:
                request.setRawHeader(b"Authorization", f"Bearer {token}".encode("utf-8"))
            request.setTransferTimeoutAttribute(REQUEST_TIMEOUT_MS)  # Таймаут

            reply = self.manager.get(request)
            self._setup_timeout(reply, "Ошибка загрузки прогресса: превышено время ожидания сервера")
            reply.finished.connect(lambda: self._on_get_completed_reply(reply))
        except Exception as e:
            self.error_signal.emit(f"Ошибка при загрузке прогресса: {str(e)}")

    def complete_lesson(self, lesson_id: int) -> None:
        try:
            url = QUrl(f"http://localhost:8000/progress/lesson/{lesson_id}/complete")
            request = QNetworkRequest(url)
            token = settings.value("token")
            if token:
                request.setRawHeader(b"Authorization", f"Bearer {token}".encode("utf-8"))
            request.setTransferTimeoutAttribute(REQUEST_TIMEOUT_MS)  # Таймаут

            reply = self.manager.post(request, b"")
            self._setup_timeout(reply, "Ошибка отметки урока: превышено время ожидания сервера")
            reply.finished.connect(lambda: self._on_complete_reply(reply, lesson_id))
        except Exception as e:
            self.error_signal.emit(f"Ошибка при отметке урока: {str(e)}")

    def get_profile_stats(self) -> None:
        try:
            url = QUrl("http://localhost:8000/progress/profile/stats")
            request = QNetworkRequest(url)
            token = settings.value("token")
            if token:
                request.setRawHeader(b"Authorization", f"Bearer {token}".encode("utf-8"))
            request.setTransferTimeoutAttribute(REQUEST_TIMEOUT_MS)  # Таймаут

            reply = self.manager.get(request)
            self._setup_timeout(reply, "Ошибка загрузки статистики профиля: превышено время ожидания сервера")
            reply.finished.connect(lambda: self._on_profile_stats_reply(reply))
        except Exception as e:
            self.error_signal.emit(f"Ошибка при загрузке статистики: {str(e)}")

    def _on_get_completed_reply(self, reply: QNetworkReply) -> None:
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                try:
                    data = json.loads(reply.readAll().data().decode("utf-8"))
                    self.completed_lessons_loaded_signal.emit(data)
                except json.JSONDecodeError as e:
                    self.error_signal.emit(f"Ошибка парсинга прогресса: {str(e)}")
            else:
                self._handle_error(reply, "Ошибка загрузки прогресса")
        except Exception as e:
            self.error_signal.emit(f"Критическая ошибка при загрузке прогресса: {str(e)}")
        finally:
            reply.deleteLater()
            self._cleanup_timeout(reply)

    def _on_complete_reply(self, reply: QNetworkReply, lesson_id: int) -> None:
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                self.lesson_completed_signal.emit(lesson_id)
            else:
                self._handle_error(reply, "Ошибка отметки урока")
        except Exception as e:
            self.error_signal.emit(f"Критическая ошибка при отметке урока: {str(e)}")
        finally:
            reply.deleteLater()
            self._cleanup_timeout(reply)

    def _on_profile_stats_reply(self, reply: QNetworkReply) -> None:
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                try:
                    data = json.loads(reply.readAll().data().decode("utf-8"))
                    self.profile_stats_loaded_signal.emit(ProfileStatsResponse.model_validate(data))
                except (json.JSONDecodeError, ValueError) as e:
                    self.error_signal.emit(f"Ошибка парсинга статистики: {str(e)}")
            else:
                self._handle_error(reply, "Ошибка загрузки статистики профиля")
        except Exception as e:
            self.error_signal.emit(f"Критическая ошибка при загрузке статистики: {str(e)}")
        finally:
            reply.deleteLater()
            self._cleanup_timeout(reply)

    def _handle_error(self, reply: QNetworkReply, default_msg: str) -> None:
        try:
            data = json.loads(reply.readAll().data().decode("utf-8"))
            self.error_signal.emit(data.get("detail", default_msg))
        except json.JSONDecodeError:
            error_str = reply.readAll().data().decode("utf-8", errors="ignore") or "Ошибка связи с сервером"
            self.error_signal.emit(error_str)
        except Exception as e:
            self.error_signal.emit(f"Ошибка обработки ошибки: {str(e)}")

    def _setup_timeout(self, reply: QNetworkReply, timeout_msg: str) -> None:
        """Установить таймаут для сетевого запроса"""
        try:
            timer = QTimer()
            timer.setSingleShot(True)
            self.timeout_timers[id(reply)] = (timer, timeout_msg)
            
            def on_timeout():
                if not reply.isFinished():
                    reply.abort()
                    self.error_signal.emit(timeout_msg)
            
            timer.timeout.connect(on_timeout)
            timer.start(REQUEST_TIMEOUT_MS)
        except Exception as e:
            print(f"Ошибка при установке таймаута: {str(e)}")

    def _cleanup_timeout(self, reply: QNetworkReply) -> None:
        """Очистить таймаут после завершения запроса"""
        try:
            reply_id = id(reply)
            if reply_id in self.timeout_timers:
                timer, _ = self.timeout_timers[reply_id]
                timer.stop()
                del self.timeout_timers[reply_id]
        except Exception as e:
            print(f"Ошибка при очистке таймаута: {str(e)}")
