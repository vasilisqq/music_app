import json
from PyQt6.QtCore import QUrl, pyqtSignal, QObject, QTimer
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from loader import settings
from schemas.topic import TopicCreate, TopicResponse # Импортируем наши схемы

# Таймауты для сетевых запросов (в миллисекундах)
REQUEST_TIMEOUT_MS = 10000  # 10 секунд

class TopicWorker(QObject):
    """Сетевой воркер для работы с темами (Pydantic Edition)"""
    
    # Теперь сигналы строго типизированы нашими моделями!
    topics_loaded_signal = pyqtSignal(list) # Здесь будет list[TopicResponse]
    topic_added_signal = pyqtSignal(TopicResponse)
    topic_updated_signal = pyqtSignal(TopicResponse)
    error_signal = pyqtSignal(str)
    topic_deleted_signal = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.manager = QNetworkAccessManager()
        self.timeout_timers = {}  # Словарь для отслеживания таймаутов

    def get_topics(self) -> None:
        try:
            url = QUrl("http://localhost:8000/topics/") 
            request = QNetworkRequest(url)
            token = settings.value("token")
            if token:
                request.setRawHeader(b"Authorization", f"Bearer {token}".encode("utf-8"))
            request.setTransferTimeoutAttribute(REQUEST_TIMEOUT_MS)  # Таймаут
                
            reply = self.manager.get(request)
            self._setup_timeout(reply, "Ошибка загрузки тем: превышено время ожидания сервера")
            reply.finished.connect(lambda: self._on_get_reply(reply))
        except Exception as e:
            self.error_signal.emit(f"Ошибка при загрузке тем: {str(e)}")

    def create_topic(self, topic_data: TopicCreate) -> None:
        """Принимает Pydantic модель TopicCreate"""
        try:
            url = QUrl("http://localhost:8000/topics/")
            request = QNetworkRequest(url)
            request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
            request.setTransferTimeoutAttribute(REQUEST_TIMEOUT_MS)  # Таймаут
            
            token = settings.value("token")
            if token:
                request.setRawHeader(b"Authorization", f"Bearer {token}".encode("utf-8"))

            # Pydantic v2 сам корректно соберет JSON
            json_bytes = topic_data.model_dump_json().encode('utf-8')
            reply = self.manager.post(request, json_bytes)
            self._setup_timeout(reply, "Ошибка создания темы: превышено время ожидания сервера")
            reply.finished.connect(lambda: self._on_create_reply(reply))
        except Exception as e:
            self.error_signal.emit(f"Ошибка при создании темы: {str(e)}")

    def edit_topic(self, topic_id: int, topic_data: TopicCreate) -> None:
        """Принимает Pydantic модель TopicCreate"""
        try:
            url = QUrl(f"http://localhost:8000/topics/{topic_id}")
            request = QNetworkRequest(url)
            request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
            request.setTransferTimeoutAttribute(REQUEST_TIMEOUT_MS)  # Таймаут
            
            token = settings.value("token")
            if token:
                request.setRawHeader(b"Authorization", f"Bearer {token}".encode("utf-8"))

            json_bytes = topic_data.model_dump_json().encode('utf-8')
            reply = self.manager.put(request, json_bytes)
            self._setup_timeout(reply, "Ошибка обновления темы: превышено время ожидания сервера")
            reply.finished.connect(lambda: self._on_update_reply(reply))
        except Exception as e:
            self.error_signal.emit(f"Ошибка при обновлении темы: {str(e)}")

    def _on_get_reply(self, reply: QNetworkReply) -> None:
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                try:
                    data = json.loads(reply.readAll().data().decode("utf-8"))
                    # Превращаем каждый словарь в объект TopicResponse
                    topics = [TopicResponse(**item) for item in data]
                    self.topics_loaded_signal.emit(topics)
                except (json.JSONDecodeError, TypeError) as e:
                    self.error_signal.emit(f"Ошибка парсинга тем: {str(e)}")
            else:
                self._handle_error(reply, "Ошибка загрузки тем")
        except Exception as e:
            self.error_signal.emit(f"Критическая ошибка при загрузке тем: {str(e)}")
        finally:
            reply.deleteLater()
            self._cleanup_timeout(reply)

    def _on_create_reply(self, reply: QNetworkReply) -> None:
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                try:
                    data = json.loads(reply.readAll().data().decode("utf-8"))
                    # Упаковываем ответ в модель
                    self.topic_added_signal.emit(TopicResponse(**data))
                except (json.JSONDecodeError, TypeError) as e:
                    self.error_signal.emit(f"Ошибка парсинга ответа при создании темы: {str(e)}")
            else:
                self._handle_error(reply, "Ошибка при создании темы")
        except Exception as e:
            self.error_signal.emit(f"Критическая ошибка при создании темы: {str(e)}")
        finally:
            reply.deleteLater()
            self._cleanup_timeout(reply)

    def _on_update_reply(self, reply: QNetworkReply) -> None:
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                try:
                    data = json.loads(reply.readAll().data().decode("utf-8"))
                    # Упаковываем ответ в модель
                    self.topic_updated_signal.emit(TopicResponse(**data))
                except (json.JSONDecodeError, TypeError) as e:
                    self.error_signal.emit(f"Ошибка парсинга ответа при обновлении темы: {str(e)}")
            else:
                self._handle_error(reply, "Ошибка при обновлении темы")
        except Exception as e:
            self.error_signal.emit(f"Критическая ошибка при обновлении темы: {str(e)}")
        finally:
            reply.deleteLater()
            self._cleanup_timeout(reply)

    def _handle_error(self, reply: QNetworkReply, default_msg: str):
        """Вспомогательный метод для обработки ошибок без дублирования кода"""
        try:
            data = json.loads(reply.readAll().data().decode("utf-8"))
            self.error_signal.emit(data.get("detail", default_msg))
        except json.JSONDecodeError:
            error_str = reply.readAll().data().decode("utf-8", errors="ignore") or "Ошибка связи с сервером"
            self.error_signal.emit(error_str)
        except Exception as e:
            self.error_signal.emit(f"Ошибка обработки ошибки: {str(e)}")


    def delete_topic(self, topic_id: int) -> None:
        """DELETE запрос для удаления темы"""
        try:
            url = QUrl(f"http://localhost:8000/topics/{topic_id}")
            request = QNetworkRequest(url)
            request.setTransferTimeoutAttribute(REQUEST_TIMEOUT_MS)  # Таймаут
            
            token = settings.value("token")
            if token:
                request.setRawHeader(b"Authorization", f"Bearer {token}".encode("utf-8"))

            # В PyQt метод называется deleteResource
            reply = self.manager.deleteResource(request)
            self._setup_timeout(reply, "Ошибка удаления темы: превышено время ожидания сервера")
            reply.finished.connect(lambda: self._on_delete_reply(reply, topic_id))
        except Exception as e:
            self.error_signal.emit(f"Ошибка при удалении темы: {str(e)}")

    def _on_delete_reply(self, reply: QNetworkReply, topic_id: int) -> None:
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                # Если успешно, посылаем сигнал с ID удаленной темы
                self.topic_deleted_signal.emit(topic_id)
            else:
                self._handle_error(reply, "Ошибка при удалении темы")
        except Exception as e:
            self.error_signal.emit(f"Критическая ошибка при удалении темы: {str(e)}")
        finally:
            reply.deleteLater()
            self._cleanup_timeout(reply)

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