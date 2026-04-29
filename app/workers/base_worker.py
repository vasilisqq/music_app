import json
from PyQt6.QtCore import QUrl, QObject
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

# Импортируем settings для получения токена
from loader import settings 

class BaseAPIWorker(QObject):
    def __init__(self, base_url: str = "http://localhost:8000"):
        super().__init__()
        self.manager = QNetworkAccessManager()
        self.base_url = base_url
        self.timeout_ms = 10000  # 10 секунд (встроенный таймаут)

    def _make_request(self, method: str, endpoint: str, data=None, success_callback=None, error_callback=None):
        """
        Универсальный метод для отправки HTTP запросов.
        """
        url = QUrl(f"{self.base_url}{endpoint}")
        request = QNetworkRequest(url)
        
        # Подставляем токен, если он есть
        token = settings.value("token")
        if token:
            request.setRawHeader(b"Authorization", f"Bearer {token}".encode("utf-8"))
            
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        
        # ✅ Встроенный таймаут PyQt6. QTimer больше не нужен!
        request.setTransferTimeout(self.timeout_ms)

        # Подготовка тела запроса, если оно есть
        import json
        
        # Подготовка тела запроса
        if data:
            if isinstance(data, dict):
                json_bytes = json.dumps(data).encode("utf-8")
            else:
                json_bytes = data.model_dump_json().encode("utf-8")
        else:
            json_bytes = b""

        # Выполнение запроса
        if method == "GET":
            reply = self.manager.get(request)
        elif method == "POST":
            reply = self.manager.post(request, json_bytes)
        elif method == "PUT":
            reply = self.manager.put(request, json_bytes)
        elif method == "DELETE":
            reply = self.manager.deleteResource(request)
        else:
            if error_callback:
                error_callback(f"Неподдерживаемый метод: {method}")
            return

        # Привязываем лямбду к сигналу finished
        reply.finished.connect(lambda: self._handle_reply(reply, success_callback, error_callback))

    def _handle_reply(self, reply: QNetworkReply, success_callback, error_callback):
        """
        Единый обработчик ответов от сервера.
        """
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
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
                except json.JSONDecodeError as e:
                    if error_callback:
                        error_callback(f"Ошибка парсинга ответа: {str(e)}")
            else:
                self._handle_error(reply, error_callback)
        except Exception as e:
            if error_callback:
                error_callback(f"Критическая ошибка обработки запроса: {str(e)}")
        finally:
            # Обязательно освобождаем память
            reply.deleteLater()

    def _handle_error(self, reply: QNetworkReply, error_callback):
        """
        Единый обработчик ошибок (сетевых и серверных).
        """
        if not error_callback:
            return
            
        # Обработка таймаута
        if reply.error() == QNetworkReply.NetworkError.TimeoutError:
            error_callback("Превышено время ожидания ответа от сервера (таймаут).")
            return

        # Обработка ошибок FastAPI (400, 404, 500 и т.д.)
        try:
            raw_data = reply.readAll().data()
            if raw_data:
                data = json.loads(raw_data.decode("utf-8"))
                error_callback(data.get("detail", "Неизвестная ошибка сервера"))
            else:
                error_callback(f"Сетевая ошибка: {reply.errorString()}")
        except json.JSONDecodeError:
            error_callback(f"Сетевая ошибка: {reply.errorString()}")