import json
import os
import sys

from PyQt6.QtCore import QUrl, pyqtSignal, QObject, QTimer
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schemas.lesson import LessonCreate, LessonUpdate, LessonResponse
from loader import settings

# Таймауты для сетевых запросов (в миллисекундах)
REQUEST_TIMEOUT_MS = 10000  # 10 секунд


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
        self.timeout_timers = {}  # Словарь для отслеживания таймаутов

    def create_lesson(self, lesson_data: LessonCreate) -> None:
        try:
            url = QUrl("http://localhost:8000/lesson/create")
            request = self._build_json_request(url)
            request.setTransferTimeoutAttribute(REQUEST_TIMEOUT_MS)  # Таймаут
            json_bytes = lesson_data.model_dump_json().encode("utf-8")
            reply = self.manager.post(request, json_bytes)
            self._setup_timeout(reply, "Ошибка создания урока: превышено время ожидания сервера")
            reply.finished.connect(lambda: self._on_create_reply(reply))
        except Exception as e:
            self.lesson_error_sygnal.emit(f"Ошибка при создании урока: {str(e)}")

    def get_lesson_by_id(self, lesson_id: int) -> None:
        try:
            url = QUrl(f"http://localhost:8000/lesson/{lesson_id}")
            request = self._build_json_request(url)
            request.setTransferTimeoutAttribute(REQUEST_TIMEOUT_MS)  # Таймаут
            reply = self.manager.get(request)
            self._setup_timeout(reply, "Ошибка загрузки урока: превышено время ожидания сервера")
            reply.finished.connect(lambda: self._on_get_lesson_reply(reply))
        except Exception as e:
            self.lesson_error_sygnal.emit(f"Ошибка при загрузке урока: {str(e)}")

    def update_lesson(self, lesson_id: int, lesson_data: LessonUpdate) -> None:
        try:
            url = QUrl(f"http://localhost:8000/lesson/{lesson_id}")
            request = self._build_json_request(url)
            request.setTransferTimeoutAttribute(REQUEST_TIMEOUT_MS)  # Таймаут
            json_bytes = lesson_data.model_dump_json().encode("utf-8")
            reply = self.manager.put(request, json_bytes)
            self._setup_timeout(reply, "Ошибка обновления урока: превышено время ожидания сервера")
            reply.finished.connect(lambda: self._on_update_reply(reply))
        except Exception as e:
            self.lesson_error_sygnal.emit(f"Ошибка при обновлении урока: {str(e)}")

    def delete_lesson(self, lesson_id: int) -> None:
        try:
            url = QUrl(f"http://localhost:8000/lesson/{lesson_id}")
            request = self._build_json_request(url)
            request.setTransferTimeoutAttribute(REQUEST_TIMEOUT_MS)  # Таймаут
            reply = self.manager.deleteResource(request)
            self._setup_timeout(reply, "Ошибка удаления урока: превышено время ожидания сервера")
            reply.finished.connect(lambda: self._on_delete_reply(reply, lesson_id))
        except Exception as e:
            self.lesson_error_sygnal.emit(f"Ошибка при удалении урока: {str(e)}")

    def get_lessons_by_topic(self, topic_id: int) -> None:
        try:
            url = QUrl(f"http://localhost:8000/lesson/topic/{topic_id}")
            request = self._build_json_request(url)
            request.setTransferTimeoutAttribute(REQUEST_TIMEOUT_MS)  # Таймаут
            reply = self.manager.get(request)
            self._setup_timeout(reply, "Ошибка загрузки уроков: превышено время ожидания сервера")
            reply.finished.connect(lambda: self._on_get_lessons_by_topic_reply(reply))
        except Exception as e:
            self.lesson_error_sygnal.emit(f"Ошибка при загрузке уроков: {str(e)}")

    def _build_json_request(self, url: QUrl) -> QNetworkRequest:
        request = QNetworkRequest(url)
        token = settings.value("token")
        if token:
            request.setRawHeader(b"Authorization", f"Bearer {token}".encode("utf-8"))
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        request.setTransferTimeoutAttribute(REQUEST_TIMEOUT_MS)  # Таймаут для всех запросов
        return request

    def _on_create_reply(self, reply: QNetworkReply) -> None:
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                try:
                    data = json.loads(reply.readAll().data().decode("utf-8"))
                    self.lesson_created_sygnal.emit(LessonResponse.model_validate(data))
                except (json.JSONDecodeError, ValueError) as e:
                    self.lesson_error_sygnal.emit(f"Ошибка парсинга ответа: {str(e)}")
            else:
                self._handle_error(reply, "Ошибка при создании урока")
        except Exception as e:
            self.lesson_error_sygnal.emit(f"Критическая ошибка при создании урока: {str(e)}")
        finally:
            reply.deleteLater()
            self._cleanup_timeout(reply)

    def _on_get_lesson_reply(self, reply: QNetworkReply) -> None:
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                try:
                    data = json.loads(reply.readAll().data().decode("utf-8"))
                    self.lesson_get_signal.emit(LessonResponse.model_validate(data))
                except (json.JSONDecodeError, ValueError) as e:
                    self.lesson_error_sygnal.emit(f"Ошибка парсинга урока: {str(e)}")
            else:
                self._handle_error(reply, "Ошибка загрузки урока")
        except Exception as e:
            self.lesson_error_sygnal.emit(f"Критическая ошибка при загрузке урока: {str(e)}")
        finally:
            reply.deleteLater()
            self._cleanup_timeout(reply)

    def _on_update_reply(self, reply: QNetworkReply) -> None:
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                try:
                    data = json.loads(reply.readAll().data().decode("utf-8"))
                    self.lesson_updated_signal.emit(LessonResponse.model_validate(data))
                except (json.JSONDecodeError, ValueError) as e:
                    self.lesson_error_sygnal.emit(f"Ошибка парсинга ответа: {str(e)}")
            else:
                self._handle_error(reply, "Ошибка при обновлении урока")
        except Exception as e:
            self.lesson_error_sygnal.emit(f"Критическая ошибка при обновлении урока: {str(e)}")
        finally:
            reply.deleteLater()
            self._cleanup_timeout(reply)

    def _on_delete_reply(self, reply: QNetworkReply, lesson_id: int) -> None:
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                self.lesson_deleted_signal.emit(lesson_id)
            else:
                self._handle_error(reply, "Ошибка при удалении урока")
        except Exception as e:
            self.lesson_error_sygnal.emit(f"Критическая ошибка при удалении урока: {str(e)}")
        finally:
            reply.deleteLater()
            self._cleanup_timeout(reply)

    def _on_get_lessons_by_topic_reply(self, reply: QNetworkReply) -> None:
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                try:
                    data = json.loads(reply.readAll().data().decode("utf-8"))
                    lessons = [LessonResponse.model_validate(item) for item in data]
                    self.lessons_by_topic_loaded_signal.emit(lessons)
                except (json.JSONDecodeError, ValueError) as e:
                    self.lesson_error_sygnal.emit(f"Ошибка парсинга уроков: {str(e)}")
            else:
                self._handle_error(reply, "Ошибка загрузки уроков")
        except Exception as e:
            self.lesson_error_sygnal.emit(f"Критическая ошибка при загрузке уроков: {str(e)}")
        finally:
            reply.deleteLater()
            self._cleanup_timeout(reply)

    def _handle_error(self, reply: QNetworkReply, default_msg: str) -> None:
        try:
            data = json.loads(reply.readAll().data().decode("utf-8"))
            self.lesson_error_sygnal.emit(data.get("detail", default_msg))
        except json.JSONDecodeError:
            error_str = reply.readAll().data().decode("utf-8", errors="ignore") or "Ошибка связи с сервером"
            self.lesson_error_sygnal.emit(error_str)
        except Exception as e:
            self.lesson_error_sygnal.emit(f"Ошибка обработки ошибки: {str(e)}")

    def _setup_timeout(self, reply: QNetworkReply, timeout_msg: str) -> None:
        """Установить таймаут для сетевого запроса"""
        try:
            timer = QTimer()
            timer.setSingleShot(True)
            self.timeout_timers[id(reply)] = (timer, timeout_msg)
            
            def on_timeout():
                if not reply.isFinished():
                    reply.abort()
                    self.lesson_error_sygnal.emit(timeout_msg)
            
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
