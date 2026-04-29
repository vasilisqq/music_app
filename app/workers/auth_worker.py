import sys
import os
import json
from PyQt6.QtCore import QUrl, pyqtSignal, QObject, QTimer
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from typing import TypeVar

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from schemas.auth import UserCreate, UserLogin
from pydantic import BaseModel
from loader import settings

# Таймауты для сетевых запросов (в миллисекундах)
REQUEST_TIMEOUT_MS = 10000  # 10 секунд

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
        self.timeout_timers = {}  # Словарь для отслеживания таймаутов    
    
    def create_user(self, user_data: UserCreate) -> None:
        try:
            url = QUrl("http://localhost:8000/register/")
            request = QNetworkRequest(url)
            request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
            request.setTransferTimeoutAttribute(REQUEST_TIMEOUT_MS)  # Таймаут
            json_bytes = json.dumps(user_data.model_dump()).encode('utf-8')
            reply = self.manager.post(request, json_bytes)
            self._setup_timeout(reply, "Ошибка регистрации: превышено время ожидания сервера")
            reply.finished.connect(lambda: self._user_reply(reply))
        except Exception as e:
            self.error_occurred_signal.emit(f"Ошибка при подготовке запроса регистрации: {str(e)}")
    
    def login_user(self, user_data: UserLogin) -> None:
        try:
            url = QUrl("http://localhost:8000/login")
            request = QNetworkRequest(url)
            request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
            request.setTransferTimeoutAttribute(REQUEST_TIMEOUT_MS)  # Таймаут
            json_bytes = json.dumps(user_data.model_dump()).encode('utf-8')
            reply = self.manager.post(request, json_bytes)
            self._setup_timeout(reply, "Ошибка входа: превышено время ожидания сервера")
            reply.finished.connect(lambda: self._user_reply(reply))
        except Exception as e:
            self.error_occurred_signal.emit(f"Ошибка при подготовке запроса входа: {str(e)}")
        
    def verify_token(self, token: str) -> None:
        """GET /me для проверки валидности токена"""
        try:
            url = QUrl("http://localhost:8000/me")
            request = QNetworkRequest(url)
            # Добавляем токен в заголовок Authorization
            request.setRawHeader(b"Authorization", f"Bearer {token}".encode("utf-8"))
            request.setTransferTimeoutAttribute(REQUEST_TIMEOUT_MS)  # Таймаут
            reply = self.manager.get(request)
            self._setup_timeout(reply, "Ошибка проверки токена: превышено время ожидания сервера")
            reply.finished.connect(lambda: self._verify_reply(reply))
        except Exception as e:
            self.error_occurred_signal.emit(f"Ошибка при проверке токена: {str(e)}")

    def _user_reply(self, reply: QNetworkReply) -> None:
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                try:
                    data = json.loads(reply.readAll().data().decode("utf-8"))
                    self.user_received_signal.emit(data)
                except json.JSONDecodeError as e:
                    self.error_occurred_signal.emit(f"Ошибка парсинга ответа сервера: {str(e)}")
            else:
                try:
                    data = json.loads(reply.readAll().data().decode("utf-8"))
                    self.error_occurred_signal.emit(data.get("detail", "Неизвестная ошибка"))
                except json.JSONDecodeError:
                    error_str = reply.readAll().data().decode("utf-8", errors="ignore") or "Неизвестная ошибка"
                    self.error_occurred_signal.emit(error_str)
        except Exception as e:
            self.error_occurred_signal.emit(f"Критическая ошибка обработки ответа: {str(e)}")
        finally:
            reply.deleteLater()
            self._cleanup_timeout(reply)
        
    def _verify_reply(self, reply: QNetworkReply) -> None:
        """Обработка ответа на проверку токена"""
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                try:
                    data = json.loads(reply.readAll().data().decode("utf-8"))
                    self.token_valid_signal.emit(data)
                except json.JSONDecodeError as e:
                    self.error_occurred_signal.emit(f"Ошибка парсинга ответа: {str(e)}")
                    self.token_invalid_signal.emit()
            else:
                self.token_invalid_signal.emit()
        except Exception as e:
            self.error_occurred_signal.emit(f"Ошибка при проверке токена: {str(e)}")
            self.token_invalid_signal.emit()
        finally:
            reply.deleteLater()
            self._cleanup_timeout(reply)

    def update_profile(self, token: str, update_data: dict) -> None:
        """PATCH /me для обновления профиля"""
        try:
            url = QUrl("http://localhost:8000/me")
            request = QNetworkRequest(url)
            request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
            request.setRawHeader(b"Authorization", f"Bearer {token}".encode("utf-8"))
            request.setTransferTimeoutAttribute(REQUEST_TIMEOUT_MS)  # Таймаут
            
            json_bytes = json.dumps(update_data).encode('utf-8')
            
            # Вместо .patch() используем .sendCustomRequest()
            # Второй аргумент — это глагол в виде байтовой строки: b"PATCH"
            reply = self.manager.sendCustomRequest(request, b"PATCH", json_bytes)
            self._setup_timeout(reply, "Ошибка обновления профиля: превышено время ожидания сервера")
            reply.finished.connect(lambda: self._update_reply(reply))
        except Exception as e:
            self.error_occurred_signal.emit(f"Ошибка при обновлении профиля: {str(e)}")

    def _update_reply(self, reply: QNetworkReply) -> None:
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                try:
                    data = json.loads(reply.readAll().data().decode("utf-8"))
                    self.update_finished_signal.emit(data)
                except json.JSONDecodeError as e:
                    self.error_occurred_signal.emit(f"Ошибка парсинга ответа: {str(e)}")
            else:
                try:
                    error_data = json.loads(reply.readAll().data().decode("utf-8"))
                    self.error_occurred_signal.emit(error_data.get("detail", "Ошибка обновления"))
                except json.JSONDecodeError:
                    error_str = reply.readAll().data().decode("utf-8", errors="ignore") or "Ошибка связи с сервером"
                    self.error_occurred_signal.emit(error_str)
        except Exception as e:
            self.error_occurred_signal.emit(f"Критическая ошибка при обновлении: {str(e)}")
        finally:
            reply.deleteLater()
            self._cleanup_timeout(reply)


    def get_all_users(self):
        """Запрос списка всех пользователей для админа"""
        try:
            url = QUrl("http://localhost:8000/users")
            request = QNetworkRequest(url)
            token = settings.value("token")
            request.setRawHeader(b"Authorization", f"Bearer {token}".encode())
            request.setTransferTimeoutAttribute(REQUEST_TIMEOUT_MS)  # Таймаут
            
            reply = self.manager.get(request)
            self._setup_timeout(reply, "Ошибка загрузки пользователей: превышено время ожидания сервера")
            reply.finished.connect(lambda: self._on_users_loaded(reply))
        except Exception as e:
            self.error_occurred_signal.emit(f"Ошибка при загрузке пользователей: {str(e)}")

    def toggle_user_status(self, user_id: int):
        """Запрос на изменение статуса пользователя"""
        try:
            url = QUrl(f"http://localhost:8000/users/{user_id}/status")
            request = QNetworkRequest(url)
            token = settings.value("token")
            request.setRawHeader(b"Authorization", f"Bearer {token}".encode())
            request.setTransferTimeoutAttribute(REQUEST_TIMEOUT_MS)  # Таймаут
            
            # PATCH запрос без тела (логика инверсии на сервере)
            reply = self.manager.sendCustomRequest(request, b"PATCH")
            self._setup_timeout(reply, "Ошибка изменения статуса: превышено время ожидания сервера")
            reply.finished.connect(lambda: self._on_status_updated(reply))
        except Exception as e:
            self.error_occurred_signal.emit(f"Ошибка при изменении статуса пользователя: {str(e)}")

    def _on_users_loaded(self, reply):
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                try:
                    data = json.loads(reply.readAll().data().decode())
                    self.users_loaded_signal.emit(data)
                except json.JSONDecodeError as e:
                    self.error_occurred_signal.emit(f"Ошибка парсинга списка пользователей: {str(e)}")
            else:
                error_str = reply.readAll().data().decode("utf-8", errors="ignore") or "Ошибка загрузки пользователей"
                self.error_occurred_signal.emit(error_str)
        except Exception as e:
            self.error_occurred_signal.emit(f"Критическая ошибка при загрузке пользователей: {str(e)}")
        finally:
            reply.deleteLater()
            self._cleanup_timeout(reply)

    def _on_status_updated(self, reply):
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                try:
                    data = json.loads(reply.readAll().data().decode())
                    self.user_status_updated_signal.emit(data)
                except json.JSONDecodeError as e:
                    self.error_occurred_signal.emit(f"Ошибка парсинга ответа: {str(e)}")
            else:
                error_str = reply.readAll().data().decode("utf-8", errors="ignore") or "Ошибка изменения статуса"
                self.error_occurred_signal.emit(error_str)
        except Exception as e:
            self.error_occurred_signal.emit(f"Критическая ошибка при изменении статуса: {str(e)}")
        finally:
            reply.deleteLater()
            self._cleanup_timeout(reply)


    def edit_user(self, user_id: int, update_data: dict) -> None:
        """PATCH запрос на редактирование пользователя"""
        try:
            url = QUrl(f"http://localhost:8000/users/{user_id}")
            request = QNetworkRequest(url)
            request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
            token = settings.value("token")
            if token:
                request.setRawHeader(b"Authorization", f"Bearer {token}".encode("utf-8"))
            request.setTransferTimeoutAttribute(REQUEST_TIMEOUT_MS)  # Таймаут
            
            json_bytes = json.dumps(update_data).encode('utf-8')
            reply = self.manager.sendCustomRequest(request, b"PATCH", json_bytes)
            self._setup_timeout(reply, "Ошибка редактирования пользователя: превышено время ожидания сервера")
            reply.finished.connect(lambda: self._on_user_edited(reply))
        except Exception as e:
            self.error_occurred_signal.emit(f"Ошибка при редактировании пользователя: {str(e)}")

    def _on_user_edited(self, reply: QNetworkReply) -> None:
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                try:
                    data = json.loads(reply.readAll().data().decode("utf-8"))
                    self.user_edited_signal.emit(data)
                except json.JSONDecodeError as e:
                    self.error_occurred_signal.emit(f"Ошибка парсинга ответа: {str(e)}")
            else:
                try:
                    # Пытаемся достать текст ошибки из ответа FastAPI (detail)
                    error_data = json.loads(reply.readAll().data().decode("utf-8"))
                    self.error_occurred_signal.emit(error_data.get("detail", "Ошибка обновления"))
                except json.JSONDecodeError:
                    error_str = reply.readAll().data().decode("utf-8", errors="ignore") or "Ошибка связи с сервером"
                    self.error_occurred_signal.emit(error_str)
        except Exception as e:
            self.error_occurred_signal.emit(f"Критическая ошибка при редактировании пользователя: {str(e)}")
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
                    self.error_occurred_signal.emit(timeout_msg)
            
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