"""
Main Application Entry Point

Инициализирует Qt приложение и управляет навигацией между окнами
аутентификации и основного приложения.
"""

import logging
import sys
from typing import Optional

from controllers.auth import Auth
from controllers.main_window import Main
from loader import settings
from PyQt6.QtCore import QEventLoop
from PyQt6.QtWidgets import QApplication
from workers.auth_worker import AuthWorker

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> None:
    """
    Главная функция приложения.

    Логика:
    1. Проверяет наличие сохранённого токена
    2. Если токен есть, проверяет его валидность
    3. Загружает главное окно если токен валиден
    4. Показывает окно аутентификации если токена нет или он невалиден
    """
    app = QApplication(sys.argv)

    token = settings.value("token")
    window: Optional[Auth | Main] = None

    if token:
        logger.info("Найден сохранённый токен, проверяем его...")
        window = _verify_existing_token(token)
    else:
        logger.info("Токен не найден, показываем окно аутентификации")
        window = Auth()

    if window:
        window.show()

    sys.exit(app.exec())


def _verify_existing_token(token: str) -> Optional[Auth | Main]:
    """
    Проверяет валидность сохранённого токена.

    Аргументы:
        token: Сохранённый JWT токен

    Возвращает:
        Main окно если токен валиден, иначе Auth окно
    """
    worker = AuthWorker()
    loop = QEventLoop()

    # Переменные для хранения результата проверки
    is_token_valid = False
    window_data = {}

    def on_token_valid(user_data: dict) -> None:
        """Обработчик валидного токена"""
        nonlocal is_token_valid, window_data
        is_token_valid = True
        window_data = user_data
        logger.info("Токен валиден")
        loop.quit()

    def on_token_invalid() -> None:
        """Обработчик невалидного токена"""
        nonlocal is_token_valid
        is_token_valid = False
        logger.warning("Токен невалиден, требуется переавторизация")
        loop.quit()

    def on_error(error_message: str) -> None:
        """Обработчик ошибки при проверке токена"""
        logger.error(f"Ошибка при проверке токена: {error_message}")
        on_token_invalid()

    # Подключаем сигналы
    worker.token_valid_signal.connect(on_token_valid)
    worker.token_invalid_signal.connect(on_token_invalid)
    worker.error_occurred_signal.connect(on_error)

    # Запускаем проверку токена
    worker.verify_token(token)
    loop.exec()

    # Возвращаем соответствующее окно
    if is_token_valid:
        logger.info("Загружаем главное окно приложения")
        return Main(window_data)
    else:
        logger.info("Загружаем окно аутентификации")
        settings.remove("token")
        return Auth()


if __name__ == "__main__":
    main()
