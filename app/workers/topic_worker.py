import json
from PyQt6.QtCore import QUrl, pyqtSignal, QObject
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from loader import settings
from schemas.topic import TopicCreate, TopicResponse # Импортируем наши схемы

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

    def get_topics(self) -> None:
        url = QUrl("http://localhost:8000/topics/") 
        request = QNetworkRequest(url)
        token = settings.value("token")
        if token:
            request.setRawHeader(b"Authorization", f"Bearer {token}".encode("utf-8"))
            
        reply = self.manager.get(request)
        reply.finished.connect(lambda: self._on_get_reply(reply))

    def create_topic(self, topic_data: TopicCreate) -> None:
        """Принимает Pydantic модель TopicCreate"""
        url = QUrl("http://localhost:8000/topics/")
        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        
        token = settings.value("token")
        if token:
            request.setRawHeader(b"Authorization", f"Bearer {token}".encode("utf-8"))

        # Pydantic v2 сам корректно соберет JSON
        json_bytes = topic_data.model_dump_json().encode('utf-8')
        reply = self.manager.post(request, json_bytes)
        reply.finished.connect(lambda: self._on_create_reply(reply))

    def edit_topic(self, topic_id: int, topic_data: TopicCreate) -> None:
        """Принимает Pydantic модель TopicCreate"""
        url = QUrl(f"http://localhost:8000/topics/{topic_id}")
        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        
        token = settings.value("token")
        if token:
            request.setRawHeader(b"Authorization", f"Bearer {token}".encode("utf-8"))

        json_bytes = topic_data.model_dump_json().encode('utf-8')
        reply = self.manager.put(request, json_bytes)
        reply.finished.connect(lambda: self._on_update_reply(reply))

    def _on_get_reply(self, reply: QNetworkReply) -> None:
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = json.loads(reply.readAll().data().decode("utf-8"))
            # Превращаем каждый словарь в объект TopicResponse
            topics = [TopicResponse(**item) for item in data]
            self.topics_loaded_signal.emit(topics)
        else:
            self._handle_error(reply, "Ошибка загрузки тем")
        reply.deleteLater()

    def _on_create_reply(self, reply: QNetworkReply) -> None:
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = json.loads(reply.readAll().data().decode("utf-8"))
            # Упаковываем ответ в модель
            self.topic_added_signal.emit(TopicResponse(**data))
        else:
            self._handle_error(reply, "Ошибка при создании темы")
        reply.deleteLater()

    def _on_update_reply(self, reply: QNetworkReply) -> None:
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = json.loads(reply.readAll().data().decode("utf-8"))
            # Упаковываем ответ в модель
            self.topic_updated_signal.emit(TopicResponse(**data))
        else:
            self._handle_error(reply, "Ошибка при обновлении темы")
        reply.deleteLater()

    def _handle_error(self, reply: QNetworkReply, default_msg: str):
        """Вспомогательный метод для обработки ошибок без дублирования кода"""
        try:
            data = json.loads(reply.readAll().data().decode("utf-8"))
            self.error_signal.emit(data.get("detail", default_msg))
        except:
            self.error_signal.emit("Ошибка связи с сервером")


    def delete_topic(self, topic_id: int) -> None:
        """DELETE запрос для удаления темы"""
        url = QUrl(f"http://localhost:8000/topics/{topic_id}")
        request = QNetworkRequest(url)
        
        token = settings.value("token")
        if token:
            request.setRawHeader(b"Authorization", f"Bearer {token}".encode("utf-8"))

        # В PyQt метод называется deleteResource
        reply = self.manager.deleteResource(request)
        reply.finished.connect(lambda: self._on_delete_reply(reply, topic_id))

    def _on_delete_reply(self, reply: QNetworkReply, topic_id: int) -> None:
        if reply.error() == QNetworkReply.NetworkError.NoError:
            # Если успешно, посылаем сигнал с ID удаленной темы
            self.topic_deleted_signal.emit(topic_id)
        else:
            self._handle_error(reply, "Ошибка при удалении темы")
        reply.deleteLater()