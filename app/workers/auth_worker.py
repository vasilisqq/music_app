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
    users_loaded_signal = pyqtSignal(list) # Список AdminUserResponse
    user_status_updated_signal = pyqtSignal(object) # Один обновленный AdminUserResponse
    user_edited_signal = pyqtSignal(dict) # Сигнал успешного редактирования
    # Новые сигналы для проверки токена
    token_valid_signal = pyqtSignal(dict)
    token_invalid_signal = pyqtSignal()
    update_finished_signal = pyqtSignal(dict)

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

    def update_profile(self, token: str, update_data: dict) -> None:
        """PATCH /me для обновления профиля"""
        url = QUrl("http://localhost:8000/me")
        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        request.setRawHeader(b"Authorization", f"Bearer {token}".encode("utf-8"))
        
        json_bytes = json.dumps(update_data).encode('utf-8')
        
        # Вместо .patch() используем .sendCustomRequest()
        # Второй аргумент — это глагол в виде байтовой строки: b"PATCH"
        reply = self.manager.sendCustomRequest(request, b"PATCH", json_bytes)
        reply.finished.connect(lambda: self._update_reply(reply))

    def _update_reply(self, reply: QNetworkReply) -> None:
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = json.loads(reply.readAll().data().decode("utf-8"))
            self.update_finished_signal.emit(data)
        else:
            try:
                error_data = json.loads(reply.readAll().data().decode("utf-8"))
                self.error_occurred_signal.emit(error_data.get("detail", "Ошибка обновления"))
            except:
                self.error_occurred_signal.emit("Ошибка связи с сервером")
        reply.deleteLater()


    def get_all_users(self):
        """Запрос списка всех пользователей для админа"""
        url = QUrl("http://localhost:8000/users")
        request = QNetworkRequest(url)
        token = settings.value("token")
        request.setRawHeader(b"Authorization", f"Bearer {token}".encode())
        
        reply = self.manager.get(request)
        reply.finished.connect(lambda: self._on_users_loaded(reply))

    def toggle_user_status(self, user_id: int):
        """Запрос на изменение статуса пользователя"""
        url = QUrl(f"http://localhost:8000/users/{user_id}/status")
        request = QNetworkRequest(url)
        token = settings.value("token")
        request.setRawHeader(b"Authorization", f"Bearer {token}".encode())
        
        # PATCH запрос без тела (логика инверсии на сервере)
        reply = self.manager.sendCustomRequest(request, b"PATCH")
        reply.finished.connect(lambda: self._on_status_updated(reply))

    def _on_users_loaded(self, reply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = json.loads(reply.readAll().data().decode())
            self.users_loaded_signal.emit(data)
        reply.deleteLater()

    def _on_status_updated(self, reply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = json.loads(reply.readAll().data().decode())
            self.user_status_updated_signal.emit(data)
        reply.deleteLater()


    def edit_user(self, user_id: int, update_data: dict) -> None:
        """PATCH запрос на редактирование пользователя"""
        url = QUrl(f"http://localhost:8000/users/{user_id}")
        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        token = settings.value("token")
        if token:
            request.setRawHeader(b"Authorization", f"Bearer {token}".encode("utf-8"))
        
        json_bytes = json.dumps(update_data).encode('utf-8')
        reply = self.manager.sendCustomRequest(request, b"PATCH", json_bytes)
        reply.finished.connect(lambda: self._on_user_edited(reply))

    def _on_user_edited(self, reply: QNetworkReply) -> None:
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = json.loads(reply.readAll().data().decode("utf-8"))
            self.user_edited_signal.emit(data)
        else:
            try:
                # Пытаемся достать текст ошибки из ответа FastAPI (detail)
                error_data = json.loads(reply.readAll().data().decode("utf-8"))
                self.error_occurred_signal.emit(error_data.get("detail", "Ошибка обновления"))
            except:
                self.error_occurred_signal.emit("Ошибка связи с сервером")
        reply.deleteLater()