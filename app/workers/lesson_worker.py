import sys
from PyQt6.QtCore import QUrl, pyqtSignal, QObject
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
import json
import sys
import os
from typing import TypeVar
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schemas.auth import UserCreate, UserLogin
from schemas.lesson import LessonCreate, LessonResponse
from pydantic import BaseModel, ValidationError

from loader import settings

T = TypeVar('T', bound=BaseModel)

class LessonWorker(QObject):
    """Типизированный API клиент с Pydantic моделями"""
    lesson_created_sygnal = pyqtSignal()
    lesson_error_sygnal = pyqtSignal(str)
    lesson_get_signal = pyqtSignal(LessonResponse)
    lessons_by_topic_loaded_signal = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.manager = QNetworkAccessManager()    


    def create_lesson(self, lesson_data:LessonCreate) -> None:
        url = QUrl("http://localhost:8000/lesson/create")
        request = QNetworkRequest(url)
        token =  settings.value("token")
        request.setRawHeader(b"Authorization", f"Bearer {token}".encode('utf-8'))
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, 
                         "application/json")
        json_bytes = json.dumps(lesson_data.model_dump()).encode('utf-8')
        reply = self.manager.post(request, json_bytes)
        reply.finished.connect(lambda: self._lesson_reply(reply))


    def get_lesson(self) -> None:
        url = QUrl("http://localhost:8000/lesson/get")
        request = QNetworkRequest(url)
        token =  settings.value("token")
        request.setRawHeader(b"Authorization", f"Bearer {token}".encode('utf-8'))
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, 
                         "application/json")
        reply = self.manager.get(request)
        reply.finished.connect(lambda: self._lesson_get(reply))
    

    def _lesson_reply(self, reply: QNetworkReply) -> None:
        data = json.loads(reply.readAll().data().decode("utf-8"))
        """Универсальная обработка ответа с валидацией"""
        if reply.error() == QNetworkReply.NetworkError.NoError:
            self.lesson_created_sygnal.emit()
        else:
            self.lesson_error_sygnal.emit(data["detail"])
        reply.deleteLater()


    def _lesson_get(self, reply: QNetworkReply) -> None:
        data = json.loads(reply.readAll().data().decode("utf-8"))
        if reply.error() == QNetworkReply.NetworkError.NoError:
            lesson = LessonResponse.model_validate(data)
            self.lesson_get_signal.emit(lesson)
        else:
            self.lesson_error_sygnal.emit(data["detail"])
        reply.deleteLater()


    def get_lessons_by_topic(self, topic_id: int) -> None:
        """Получает список уроков для конкретной темы через QNetworkAccessManager"""
        url = QUrl(f"http://localhost:8000/lesson/topic/{topic_id}")
        request = QNetworkRequest(url)
        
        # Добавляем токен авторизации
        token = settings.value("token")
        if token:
            request.setRawHeader(b"Authorization", f"Bearer {token}".encode('utf-8'))
        
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        
        reply = self.manager.get(request)
        reply.finished.connect(lambda: self._on_get_lessons_by_topic_reply(reply))


    def _on_get_lessons_by_topic_reply(self, reply: QNetworkReply) -> None:
        """Обрабатывает ответ со списком уроков"""
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = json.loads(reply.readAll().data().decode("utf-8"))
            # Валидируем каждый элемент списка через Pydantic
            lessons = [LessonResponse.model_validate(item) for item in data]
            self.lessons_by_topic_loaded_signal.emit(lessons)
        else:
            # Обработка ошибки
            try:
                data = json.loads(reply.readAll().data().decode("utf-8"))
                self.lesson_error_sygnal.emit(data.get("detail", "Ошибка загрузки уроков"))
            except:
                self.lesson_error_sygnal.emit("Ошибка связи с сервером")
                
        reply.deleteLater()