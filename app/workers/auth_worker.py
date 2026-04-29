import sys
import os
from PyQt6.QtCore import pyqtSignal
from typing import TypeVar
from pydantic import BaseModel

# Импортируем базовый класс
from workers.base_worker import BaseAPIWorker

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from schemas.auth import UserCreate, UserLogin
from loader import settings

T = TypeVar('T', bound=BaseModel)

class AuthWorker(BaseAPIWorker):
    """Типизированный API клиент с Pydantic моделями"""
    
    # Сигналы
    user_received_signal = pyqtSignal(dict)
    error_occurred_signal = pyqtSignal(str)
    users_loaded_signal = pyqtSignal(list) # Список AdminUserResponse
    user_status_updated_signal = pyqtSignal(dict) # Изменил object на dict, так как из сети приходит JSON
    user_edited_signal = pyqtSignal(dict) # Сигнал успешного редактирования
    
    # Новые сигналы для проверки токена
    token_valid_signal = pyqtSignal(dict)
    token_invalid_signal = pyqtSignal()
    update_finished_signal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
    
    def create_user(self, user_data: UserCreate) -> None:
        self._make_request(
            method="POST",
            endpoint="/register/",
            data=user_data,
            success_callback=self.user_received_signal.emit,
            error_callback=self.error_occurred_signal.emit
        )
    
    def login_user(self, user_data: UserLogin) -> None:
        self._make_request(
            method="POST",
            endpoint="/login",
            data=user_data,
            success_callback=self.user_received_signal.emit,
            error_callback=self.error_occurred_signal.emit
        )
        
    def verify_token(self, token: str) -> None:
        """GET /me для проверки валидности токена"""
        self._make_request(
            method="GET",
            endpoint="/me",
            success_callback=self.token_valid_signal.emit,
            error_callback=lambda _: self.token_invalid_signal.emit()
        )

    def update_profile(self, token: str, update_data: dict) -> None:
        """PATCH /me для обновления профиля"""
        self._make_request(
            method="PATCH",
            endpoint="/me",
            data=update_data,
            success_callback=self.update_finished_signal.emit,
            error_callback=self.error_occurred_signal.emit
        )

    def get_all_users(self):
        """Запрос списка всех пользователей для админа"""
        self._make_request(
            method="GET",
            endpoint="/users",
            success_callback=self.users_loaded_signal.emit,
            error_callback=self.error_occurred_signal.emit
        )

    def toggle_user_status(self, user_id: int):
        """Запрос на изменение статуса пользователя"""
        # PATCH запрос без тела
        self._make_request(
            method="PATCH",
            endpoint=f"/users/{user_id}/status",
            success_callback=self.user_status_updated_signal.emit,
            error_callback=self.error_occurred_signal.emit
        )

    def edit_user(self, user_id: int, update_data: dict) -> None:
        """PATCH запрос на редактирование пользователя"""
        self._make_request(
            method="PATCH",
            endpoint=f"/users/{user_id}",
            data=update_data,
            success_callback=self.user_edited_signal.emit,
            error_callback=self.error_occurred_signal.emit
        )