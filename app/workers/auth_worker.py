"""
Authentication Worker Module

Обеспечивает асинхронное взаимодействие с API аутентификации
через PyQt6 сигналы.
"""

import logging

from PyQt6.QtCore import pyqtSignal
from workers.base_worker import BaseAPIWorker

from schemas.auth import UserCreate, UserLogin

# Настройка логирования
logger = logging.getLogger(__name__)


class AuthWorker(BaseAPIWorker):
    """
    Воркер для работы с API аутентификации.

    Обеспечивает:
    - Регистрацию пользователей
    - Вход пользователей
    - Проверку токенов
    - Управление профилем
    - Операции администратора с пользователями

    Атрибуты (сигналы):
        user_received_signal: Пользователь успешно создан/залогирован
        error_occurred_signal: Произошла ошибка
        users_loaded_signal: Загружен список пользователей
        user_status_updated_signal: Статус пользователя изменён
        user_edited_signal: Пользователь отредактирован
        token_valid_signal: Токен валиден
        token_invalid_signal: Токен невалиден
        update_finished_signal: Профиль обновлён
    """

    # Сигналы для аутентификации
    user_received_signal = pyqtSignal(dict)
    """Сигнал при успешной регистрации или входе"""

    error_occurred_signal = pyqtSignal(str)
    """Сигнал при возникновении ошибки"""

    # Сигналы для администратора
    users_loaded_signal = pyqtSignal(list)
    """Сигнал при загрузке списка пользователей"""

    user_status_updated_signal = pyqtSignal(dict)
    """Сигнал при изменении статуса пользователя"""

    user_edited_signal = pyqtSignal(dict)
    """Сигнал при успешном редактировании пользователя"""

    # Сигналы для проверки токена
    token_valid_signal = pyqtSignal(dict)
    """Сигнал при валидном токене"""

    token_invalid_signal = pyqtSignal()
    """Сигнал при невалидном токене"""

    # Сигналы для обновления профиля
    update_finished_signal = pyqtSignal(dict)
    """Сигнал при завершении обновления профиля"""

    def __init__(self) -> None:
        """Инициализация AuthWorker"""
        super().__init__()
        logger.debug("AuthWorker инициализирован")

    def create_user(self, user_data: UserCreate) -> None:
        """
        Отправляет запрос на регистрацию пользователя.

        Аргументы:
            user_data: Данные для регистрации (Pydantic модель UserCreate)
        """
        logger.info(f"Запрос регистрации для пользователя: {user_data.email}")
        self._make_request(
            method="POST",
            endpoint="/register/",
            data=user_data,
            success_callback=self.user_received_signal.emit,
            error_callback=self.error_occurred_signal.emit,
        )

    def login_user(self, user_data: UserLogin) -> None:
        """
        Отправляет запрос на вход пользователя.

        Аргументы:
            user_data: Данные для входа (Pydantic модель UserLogin)
        """
        logger.info(f"Запрос входа для пользователя: {user_data.email}")
        self._make_request(
            method="POST",
            endpoint="/login",
            data=user_data,
            success_callback=self.user_received_signal.emit,
            error_callback=self.error_occurred_signal.emit,
        )

    def verify_token(self, token: str) -> None:
        """
        Проверяет валидность токена.

        Отправляет GET запрос на /me для верификации токена.

        Аргументы:
            token: JWT токен для проверки
        """
        logger.debug("Проверка валидности токена")
        self._make_request(
            method="GET",
            endpoint="/me",
            success_callback=self.token_valid_signal.emit,
            error_callback=lambda _: self.token_invalid_signal.emit(),
        )

    def update_profile(self, update_data: dict) -> None:
        """
        Обновляет профиль текущего пользователя.

        Отправляет PATCH запрос на /me с данными для обновления.

        Аргументы:
            update_data: Словарь с полями для обновления
        """
        logger.info("Запрос обновления профиля")
        self._make_request(
            method="PATCH",
            endpoint="/me",
            data=update_data,
            success_callback=self.update_finished_signal.emit,
            error_callback=self.error_occurred_signal.emit,
        )

    def get_all_users(self) -> None:
        """
        Загружает список всех пользователей (требует прав администратора).

        Отправляет GET запрос на /users.
        """
        logger.info("Запрос списка всех пользователей")
        self._make_request(
            method="GET",
            endpoint="/users",
            success_callback=self.users_loaded_signal.emit,
            error_callback=self.error_occurred_signal.emit,
        )

    def toggle_user_status(self, user_id: int) -> None:
        """
        Переключает статус активности пользователя.

        Отправляет PATCH запрос на /users/{user_id}/status.

        Аргументы:
            user_id: ID пользователя
        """
        logger.info(f"Запрос изменения статуса пользователя {user_id}")
        self._make_request(
            method="PATCH",
            endpoint=f"/users/{user_id}/status",
            success_callback=self.user_status_updated_signal.emit,
            error_callback=self.error_occurred_signal.emit,
        )

    def edit_user(self, user_id: int, update_data: dict) -> None:
        """
        Редактирует данные пользователя (требует прав администратора).

        Отправляет PATCH запрос на /users/{user_id}.

        Аргументы:
            user_id: ID пользователя для редактирования
            update_data: Словарь с полями для обновления
        """
        logger.info(f"Запрос редактирования пользователя {user_id}")
        self._make_request(
            method="PATCH",
            endpoint=f"/users/{user_id}",
            data=update_data,
            success_callback=self.user_edited_signal.emit,
            error_callback=self.error_occurred_signal.emit,
        )
