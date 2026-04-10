import sys
import os
import json
from PyQt6.QtCore import QUrl, pyqtSignal, QObject
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from typing import TypeVar

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from schemas.auth import UserCreate, UserLogin
from pydantic import BaseModel
from loader import settings

T = TypeVar('T', bound=BaseModel)

class AuthWorker(QObject):
    """Типизированный API клиент с Pydantic моделями"""
    user_received_signal = pyqtSignal(dict)
    error_occurred_signal = pyqtSignal(str)
    
    # Новые сигналы для проверки токена
    token_valid_signal = pyqtSignal(dict)
    token_invalid_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.manager = QNetworkAccessManager()    
    
    def create_user(self, user_data: UserCreate) -> None:
        url = QUrl("http://localhost:8000/register/")
        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        json_bytes = json.dumps(user_data.model_dump()).encode('utf-8')
        reply = self.manager.post(request, json_bytes)
        reply.finished.connect(lambda: self._user_reply(reply))
    
    def login_user(self, user_data: UserLogin) -> None:
        url = QUrl("http://localhost:8000/login")
        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        json_bytes = json.dumps(user_data.model_dump()).encode('utf-8')
        reply = self.manager.post(request, json_bytes)
        reply.finished.connect(lambda: self._user_reply(reply))
        
    def verify_token(self, token: str) -> None:
        """GET /me для проверки валидности токена"""
        url = QUrl("http://localhost:8000/me")
        request = QNetworkRequest(url)
        # Добавляем токен в заголовок Authorization
        request.setRawHeader(b"Authorization", f"Bearer {token}".encode("utf-8"))
        reply = self.manager.get(request)
        reply.finished.connect(lambda: self._verify_reply(reply))

    def _user_reply(self, reply: QNetworkReply) -> None:
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = json.loads(reply.readAll().data().decode("utf-8"))
            self.user_received_signal.emit(data) 
        else:
            data = json.loads(reply.readAll().data().decode("utf-8"))
            self.error_occurred_signal.emit(data.get("detail", "Неизвестная ошибка"))
        reply.deleteLater()
        
    def _verify_reply(self, reply: QNetworkReply) -> None:
        """Обработка ответа на проверку токена"""
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = json.loads(reply.readAll().data().decode("utf-8"))
            self.token_valid_signal.emit(data)
        else:
            self.token_invalid_signal.emit()
        reply.deleteLater()