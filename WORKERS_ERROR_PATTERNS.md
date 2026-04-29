ШПАРГАЛКА: ОСНОВНЫЕ ПАТТЕРНЫ ОБРАБОТКИ ОШИБОК
==============================================

1. ЗАГОЛОВКИ ФАЙЛА
─────────────────
from PyQt6.QtCore import QTimer  # ← ВАЖНО!
REQUEST_TIMEOUT_MS = 10000      # 10 сек

def __init__(self):
    self.timeout_timers = {}    # ← Словарь для таймаутов


2. МЕТОДЫ ОТПРАВКИ ЗАПРОСА
──────────────────────────
def some_request(self, data):
    try:
        request = QNetworkRequest(url)
        request.setTransferTimeoutAttribute(REQUEST_TIMEOUT_MS)  # ← Таймаут!
        reply = self.manager.post(request, json_bytes)
        self._setup_timeout(reply, "Ошибка: превышено время")
        reply.finished.connect(lambda: self._on_reply(reply))
    except Exception as e:
        self.error_signal.emit(f"Ошибка подготовки: {str(e)}")


3. ОБРАБОТЧИКИ ОТВЕТОВ
─────────────────────
def _on_reply(self, reply: QNetworkReply) -> None:
    try:
        if reply.error() == QNetworkReply.NetworkError.NoError:
            try:
                data = json.loads(reply.readAll().data().decode("utf-8"))
                self.success_signal.emit(data)
            except json.JSONDecodeError as e:
                self.error_signal.emit(f"Ошибка парсинга: {str(e)}")
        else:
            self._handle_error(reply, "Ошибка запроса")
    except Exception as e:
        self.error_signal.emit(f"Критическая ошибка: {str(e)}")
    finally:
        reply.deleteLater()
        self._cleanup_timeout(reply)


4. ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
────────────────────────
def _handle_error(self, reply: QNetworkReply, default_msg: str):
    try:
        data = json.loads(reply.readAll().data().decode("utf-8"))
        self.error_signal.emit(data.get("detail", default_msg))
    except json.JSONDecodeError:
        error_str = reply.readAll().data().decode("utf-8", errors="ignore")
        self.error_signal.emit(error_str or "Ошибка связи с сервером")
    except Exception as e:
        self.error_signal.emit(f"Ошибка обработки: {str(e)}")

def _setup_timeout(self, reply: QNetworkReply, timeout_msg: str) -> None:
    try:
        timer = QTimer()
        timer.setSingleShot(True)
        self.timeout_timers[id(reply)] = (timer, timeout_msg)
        
        def on_timeout():
            if not reply.isFinished():
                reply.abort()
                self.error_signal.emit(timeout_msg)
        
        timer.timeout.connect(on_timeout)
        timer.start(REQUEST_TIMEOUT_MS)
    except Exception as e:
        print(f"Ошибка при установке таймаута: {str(e)}")

def _cleanup_timeout(self, reply: QNetworkReply) -> None:
    try:
        reply_id = id(reply)
        if reply_id in self.timeout_timers:
            timer, _ = self.timeout_timers[reply_id]
            timer.stop()
            del self.timeout_timers[reply_id]
    except Exception as e:
        print(f"Ошибка при очистке таймаута: {str(e)}")


КЛЮЧЕВЫЕ МОМЕНТЫ
================

✓ Всегда используйте try-except-finally в обработчиках
✓ request.setTransferTimeoutAttribute(REQUEST_TIMEOUT_MS) ОБЯЗАТЕЛЕН
✓ reply.deleteLater() ВСЕГДА в finally блоке
✓ _cleanup_timeout(reply) ВСЕГДА в finally блоке
✓ json.JSONDecodeError специфичнее, чем bare except
✓ reply.readAll().data().decode("utf-8", errors="ignore") для надежности
✓ print() для критических ошибок в консоль
✓ error_signal.emit() для уведомления UI


ТЕСТИРОВАНИЕ ТАЙМАУТОВ
======================

Чтобы проверить таймауты:

1. Остановить сервер: Ctrl+C на сервере
2. Попробовать выполнить действие в приложении
3. Должна появиться ошибка через 10 секунд: "превышено время ожидания сервера"

Чтобы проверить обработку ошибок:

1. Отправить неверные данные (напр., пустую тему)
2. Проверить, что ошибка вернулась от сервера
3. Должно отобразиться сообщение от сервера (detail)
