"""
Base API Worker Module

Обеспечивает базовую функциональность для взаимодействия с FastAPI сервером
через PyQt6 асинхронные сетевые запросы.
"""

import json
import logging
from typing import Any, Callable, Optional, Union

from loader import settings
from pydantic import BaseModel
from PyQt6.QtCore import QObject, QUrl
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

# Настройка логирования
logger = logging.getLogger(__name__)


class BaseAPIWorker(QObject):
    """
    Базовый класс для работы с REST API через PyQt6.

    Предоставляет методы для отправки HTTP запросов (GET, POST, PUT, DELETE)
    с обработкой ошибок и таймаутов.

    Атрибуты:
        manager (QNetworkAccessManager): Менеджер сетевых запросов
        base_url (str): Базовый URL сервера API
        timeout_ms (int): Таймаут запроса в миллисекундах
    """

    DEFAULT_TIMEOUT_MS: int = 10000
    """Стандартный таймаут для запросов (10 секунд)"""

    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        """
        Инициализация базового API воркера.

        Аргументы:
            base_url: Базовый URL API сервера (по умолчанию localhost:8000)
        """
        super().__init__()
        self.manager: QNetworkAccessManager = QNetworkAccessManager()
        self.base_url: str = base_url
        self.timeout_ms: int = self.DEFAULT_TIMEOUT_MS

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Union[dict, BaseModel]] = None,
        success_callback: Optional[Callable[[Any], None]] = None,
        error_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        """
        Универсальный метод для отправки HTTP запросов.

        Аргументы:
            method: HTTP метод (GET, POST, PUT, DELETE)
            endpoint: Endpoint API (например, "/users")
            data: Данные для отправки (dict или Pydantic модель)
            success_callback: Функция обратного вызова при успехе
            error_callback: Функция обратного вызова при ошибке
        """
        url = QUrl(f"{self.base_url}{endpoint}")
        request = QNetworkRequest(url)

        # Добавление токена авторизации если он есть
        token = settings.value("token")
        if token:
            request.setRawHeader(b"Authorization", f"Bearer {token}".encode("utf-8"))

        request.setHeader(
            QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json"
        )

        # Установка таймаута
        request.setTransferTimeout(self.timeout_ms)

        # Подготовка тела запроса
        json_bytes = self._prepare_request_body(data)

        # Выполнение запроса в зависимости от метода
        reply = self._execute_http_method(method, request, json_bytes)

        if reply is None:
            if error_callback:
                error_callback(f"Неподдерживаемый HTTP метод: {method}")
            return

        # Привязываем обработчик к сигналу завершения
        reply.finished.connect(
            lambda: self._handle_reply(reply, success_callback, error_callback)
        )

    def _prepare_request_body(self, data: Optional[Union[dict, BaseModel]]) -> bytes:
        """
        Подготавливает тело запроса.

        Аргументы:
            data: Данные в виде dict или Pydantic модели

        Возвращает:
            Закодированное в UTF-8 JSON тело запроса (пусто если data=None)
        """
        if not data:
            return b""

        if isinstance(data, dict):
            json_bytes = json.dumps(data).encode("utf-8")
        elif isinstance(data, BaseModel):
            json_bytes = data.model_dump_json().encode("utf-8")
        else:
            json_bytes = b""

        return json_bytes

    def _execute_http_method(
        self, method: str, request: QNetworkRequest, data: bytes
    ) -> Optional[QNetworkReply]:
        """
        Выполняет HTTP запрос нужного метода.

        Аргументы:
            method: HTTP метод (GET, POST, PUT, DELETE)
            request: Объект QNetworkRequest
            data: Тело запроса в байтах

        Возвращает:
            QNetworkReply объект или None при ошибке метода
        """
        try:
            if method == "GET":
                return self.manager.get(request)
            elif method == "POST":
                return self.manager.post(request, data)
            elif method == "PUT":
                return self.manager.put(request, data)
            elif method == "DELETE":
                return self.manager.deleteResource(request)
            else:
                logger.warning(f"Неподдерживаемый HTTP метод: {method}")
                return None
        except Exception as e:
            logger.error(f"Ошибка при выполнении {method} запроса: {str(e)}")
            return None

    def _handle_reply(
        self,
        reply: QNetworkReply,
        success_callback: Optional[Callable[[Any], None]],
        error_callback: Optional[Callable[[str], None]],
    ) -> None:
        """
        Обрабатывает ответ от сервера.

        Аргументы:
            reply: Ответ от сервера
            success_callback: Функция обратного вызова при успехе
            error_callback: Функция обратного вызова при ошибке
        """
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                self._handle_success_response(reply, success_callback)
            else:
                self._handle_error_response(reply, error_callback)
        except Exception as e:
            logger.error(f"Критическая ошибка обработки ответа: {str(e)}")
            if error_callback:
                error_callback(f"Критическая ошибка: {str(e)}")
        finally:
            # Освобождение ресурсов
            reply.deleteLater()

    def _handle_success_response(
        self,
        reply: QNetworkReply,
        success_callback: Optional[Callable[[Any], None]],
    ) -> None:
        """
        Обрабатывает успешный ответ от сервера.

        Аргументы:
            reply: Ответ от сервера
            success_callback: Функция обратного вызова
        """
        raw_data = reply.readAll().data()

        # Для DELETE запросов тело ответа может быть пустым
        if not raw_data:
            if success_callback:
                success_callback(None)
            return

        try:
            parsed_data = json.loads(raw_data.decode("utf-8"))
            if success_callback:
                success_callback(parsed_data)
            logger.debug(f"Успешный ответ получен: {type(parsed_data)}")
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON: {str(e)}")
            logger.error(f"Raw data: {raw_data}")

    def _handle_error_response(
        self,
        reply: QNetworkReply,
        error_callback: Optional[Callable[[str], None]],
    ) -> None:
        """
        Обрабатывает ошибки при получении ответа.

        Аргументы:
            reply: Ответ от сервера с ошибкой
            error_callback: Функция обратного вызова для обработки ошибки
        """
        if not error_callback:
            return

        # Проверка таймаута
        if reply.error() == QNetworkReply.NetworkError.TimeoutError:
            logger.warning("Таймаут при ожидании ответа сервера")
            error_callback("Превышено время ожидания ответа (таймаут)")
            return

        # Попытка получить детали ошибки от сервера
        try:
            raw_data = reply.readAll().data()
            if raw_data:
                data = json.loads(raw_data.decode("utf-8"))
                error_message = data.get("detail", "Неизвестная ошибка сервера")
            else:
                error_message = f"Сетевая ошибка: {reply.errorString()}"
        except json.JSONDecodeError:
            error_message = f"Сетевая ошибка: {reply.errorString()}"

        logger.error(f"Ошибка API: {error_message}")
        error_callback(error_message)
