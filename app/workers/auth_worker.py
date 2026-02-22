import sys
from PyQt6.QtCore import QUrl, pyqtSignal, QObject
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
import json
import sys
import os
from typing import TypeVar
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from schemas.auth import UserCreate, UserLogin
from schemas.lesson import LessonCreate, LessonResponse
from pydantic import BaseModel

from loader import settings

T = TypeVar('T', bound=BaseModel)

class AuthWorker(QObject):
    """Типизированный API клиент с Pydantic моделями"""
    user_received_signal = pyqtSignal(str)
    error_occurred_signal = pyqtSignal(str)


    def __init__(self):
        super().__init__()
        self.manager = QNetworkAccessManager()    
    

    def create_user(self, user_data: UserCreate) -> None:
        """POST /users/ → UserResponse"""
        url = QUrl("http://localhost:8000/register/")
        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        json_bytes = json.dumps(user_data.model_dump()).encode('utf-8')
        reply = self.manager.post(request, json_bytes)
        reply.finished.connect(lambda: self._user_reply(reply))
    

    def login_user(self, user_data: UserLogin) -> None:
        """POST /auth/login → UserResponse (или TokenResponse)"""
        url = QUrl("http://localhost:8000/login")
        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        json_bytes = json.dumps(user_data.model_dump()).encode('utf-8')
        reply = self.manager.post(request, json_bytes)
        reply.finished.connect(lambda: self._user_reply(reply))
    

    def _user_reply(self, reply: QNetworkReply) -> None:
        data = json.loads(reply.readAll().data().decode("utf-8"))
        """Универсальная обработка ответа с валидацией"""
        if reply.error() == QNetworkReply.NetworkError.NoError:
            self.user_received.emit(data) 
        else:
            self.error_occurred.emit(data["detail"])
        reply.deleteLater()