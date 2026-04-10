import json
from PyQt6.QtCore import QUrl, pyqtSignal, QObject
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from loader import settings

class TopicWorker(QObject):
    """Сетевой воркер для работы с темами (нативный PyQt-подход)"""
    
    # Сигналы для связи с интерфейсом
    topics_loaded_signal = pyqtSignal(list)
    topic_added_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.manager = QNetworkAccessManager()

    def get_topics(self) -> None:
        """GET запрос для получения списка тем"""
        # Убедись, что URL совпадает с твоим FastAPI роутером!
        url = QUrl("http://localhost:8000/topics/") 
        request = QNetworkRequest(url)
        
        # Добавляем токен, если нужно
        token = settings.value("token")
        if token:
            request.setRawHeader(b"Authorization", f"Bearer {token}".encode("utf-8"))
            
        reply = self.manager.get(request)
        reply.finished.connect(lambda: self._on_get_reply(reply))

    def create_topic(self, topic_data: dict) -> None:
        """POST запрос для создания новой темы"""
        url = QUrl("http://localhost:8000/topics/")
        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        
        token = settings.value("token")
        if token:
            request.setRawHeader(b"Authorization", f"Bearer {token}".encode("utf-8"))

        json_bytes = json.dumps(topic_data).encode('utf-8')
        reply = self.manager.post(request, json_bytes)
        reply.finished.connect(lambda: self._on_create_reply(reply))

    def _on_get_reply(self, reply: QNetworkReply) -> None:
        """Обработка ответа со списком тем"""
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = json.loads(reply.readAll().data().decode("utf-8"))
            self.topics_loaded_signal.emit(data)
        else:
            try:
                data = json.loads(reply.readAll().data().decode("utf-8"))
                self.error_signal.emit(data.get("detail", "Ошибка загрузки тем"))
            except:
                self.error_signal.emit("Ошибка связи с сервером")
        reply.deleteLater()

    def _on_create_reply(self, reply: QNetworkReply) -> None:
        """Обработка ответа после создания темы"""
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = json.loads(reply.readAll().data().decode("utf-8"))
            self.topic_added_signal.emit(data)
        else:
            try:
                data = json.loads(reply.readAll().data().decode("utf-8"))
                self.error_signal.emit(data.get("detail", "Ошибка при создании темы"))
            except:
                self.error_signal.emit("Ошибка связи с сервером")
        reply.deleteLater()