"""
Logging Configuration Module

Централизованная настройка логирования для всего приложения.
"""

import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging(
    app_name: str = "music_app",
    log_dir: str = "logs",
    log_level: int = logging.INFO,
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5,
) -> logging.Logger:
    """
    Настраивает логирование для приложения.

    Создаёт как файловое логирование (с ротацией), так и вывод в консоль.

    Аргументы:
        app_name: Имя приложения для логов
        log_dir: Директория для логов
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        max_bytes: Максимальный размер файла до ротации (байты)
        backup_count: Количество резервных копий логов

    Возвращает:
        Logger объект для приложения
    """
    # Создаём директорию если её нет
    os.makedirs(log_dir, exist_ok=True)

    # Создаём логгер
    logger = logging.getLogger(app_name)
    logger.setLevel(log_level)

    # Удаляем существующие обработчики чтобы избежать дублирования
    logger.handlers.clear()

    # Форматер логов
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Обработчик для файла с ротацией
    file_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, f"{app_name}.log"),
        maxBytes=max_bytes,
        backupCount=backup_count,
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Обработчик для консоли
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.info(f"Logging configured for {app_name}")
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Получает логгер для модуля.

    Аргументы:
        name: Имя модуля (__name__)

    Возвращает:
        Logger объект
    """
    return logging.getLogger(name)
