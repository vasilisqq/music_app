import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import QUrl, pyqtSignal, QObject
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt6.QtCore import QJsonDocument
from PyQt6.QtGui import QFont
import json
import sys
import os
from typing import TypeVar
# from app.core.config import settings
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schemas.auth import UserCreate, UserLogin, UserResponse
from pydantic import BaseModel, EmailStr, ConfigDict, ValidationError

T = TypeVar('T', bound=BaseModel)

class ApiWorker(QObject):
    """Типизированный API клиент с Pydantic моделями"""
    user_received = pyqtSignal(UserResponse)
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.manager = QNetworkAccessManager()
    
    def get_user(self, user_id: int) -> None:
        """GET /users/{id} → UserResponse"""
        url = QUrl(f"http://localhost:8000/users/{user_id}")
        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")
        
        reply = self.manager.get(request)
        reply.finished.connect(lambda: self._handle_reply(reply, UserResponse))
    
    def create_user(self, user_data: UserCreate) -> None:
        """POST /users/ → UserResponse"""
        url = QUrl("http://localhost:8000/register/")
        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        
        # Pydantic → JSON bytes автоматически
        json_bytes = json.dumps(user_data.model_dump()).encode('utf-8')
        reply = self.manager.post(request, json_bytes)
        reply.finished.connect(lambda: self._handle_reply(reply, UserResponse))
    
    def login_user(self, user_data: UserLogin) -> None:
        """POST /auth/login → UserResponse (или TokenResponse)"""
        url = QUrl("http://localhost:8000/auth/login")
        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")
        
        json_data = QJsonDocument(user_data.model_dump().encode()).toJson()
        reply = self.manager.post(request, json_data)
        reply.finished.connect(lambda: self._handle_reply(reply, UserResponse))
    
    def _handle_reply(self, reply: QNetworkReply, model_type: type[T]) -> None:
        """Универсальная обработка ответа с валидацией"""
        if reply.error() == QNetworkReply.NetworkError.NoError:
            try:
                # JSON → Pydantic модель с валидацией
                data = json.loads(reply.readAll().data().decode())
                validated_model = model_type.model_validate(data)
                self.user_received.emit(validated_model)  # UserResponse!
            except ValidationError as e:
                self.error_occurred.emit(f"Ошибка валидации ответа: {e}")
            except json.JSONDecodeError as e:
                self.error_occurred.emit(f"Неверный JSON: {e}")
        else:
            self.error_occurred.emit(reply.errorString())
        reply.deleteLater()