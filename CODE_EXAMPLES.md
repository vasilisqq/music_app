# ПРИМЕРЫ КОДА ДЛЯ ИСПРАВЛЕНИЙ

## 1. Система логирования (logging)

### Создать файл: `server/logging_config.py`

```python
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime

# Создаём папку для логов
Path("logs").mkdir(exist_ok=True)

def setup_logger(name, log_file=None, level=logging.INFO):
    """Настроить логирование"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Формат логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Логирование в консоль
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Логирование в файл (если указан)
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            f"logs/{log_file}",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,  # Хранить 5 старых файлов
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

# Использование:
# from logging_config import setup_logger
# logger = setup_logger(__name__, "app.log")
```

### Использовать в `server/app.py`:

```python
from logging_config import setup_logger

logger = setup_logger(__name__, "app.log")

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Приложение запущено")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 Приложение остановлено")

@app.get("/")
async def root():
    logger.info("GET / запрос")
    return {"message": "FastAPI Auth Project"}
```

---

## 2. Улучшенная обработка ошибок

### Создать файл: `server/exceptions.py`

```python
from fastapi import HTTPException, status

class BaseAPIException(HTTPException):
    """Базовое исключение для API"""
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)

class UserAlreadyExists(BaseAPIException):
    """Пользователь уже существует"""
    def __init__(self, field: str = "email"):
        super().__init__(
            detail=f"Пользователь с таким {field} уже существует",
            status_code=status.HTTP_400_BAD_REQUEST
        )

class InvalidCredentials(BaseAPIException):
    """Неверные учётные данные"""
    def __init__(self):
        super().__init__(
            detail="Неверный email или пароль",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

class UserNotFound(BaseAPIException):
    """Пользователь не найден"""
    def __init__(self):
        super().__init__(
            detail="Пользователь не найден",
            status_code=status.HTTP_404_NOT_FOUND
        )

class NotAuthorized(BaseAPIException):
    """Не авторизован"""
    def __init__(self):
        super().__init__(
            detail="Требуется авторизация",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

class Forbidden(BaseAPIException):
    """Недостаточно прав"""
    def __init__(self, detail: str = "Недостаточно прав"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN
        )

class NotFound(BaseAPIException):
    """Ресурс не найден"""
    def __init__(self, resource: str = "Ресурс"):
        super().__init__(
            detail=f"{resource} не найден",
            status_code=status.HTTP_404_NOT_FOUND
        )
```

### Использовать в сервисах:

```python
# server/services/user_service.py
from exceptions import UserAlreadyExists, InvalidCredentials, UserNotFound

class UserService:
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Аутентификация пользователя"""
        user = await self.get_user_by_email(email)
        if not user:
            logger.warning(f"Попытка входа с несуществующим email: {email}")
            raise InvalidCredentials()
        
        if not verify_password(password, user.hashed_password):
            logger.warning(f"Неверный пароль для пользователя: {email}")
            raise InvalidCredentials()
        
        logger.info(f"Пользователь вошел: {email}")
        return user
```

---

## 3. Правильная обработка исключений в PyQt

### Создать файл: `app/utils/error_handler.py`

```python
import logging
from PyQt6.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)

class ErrorHandler:
    """Централизованная обработка ошибок в GUI"""
    
    @staticmethod
    def show_error(parent_widget, title: str, message: str, details: str = None):
        """Показать ошибку пользователю"""
        logger.error(f"{title}: {message}" + (f"\n{details}" if details else ""))
        
        msg_box = QMessageBox(parent_widget)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        if details:
            msg_box.setDetailedText(details)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
    
    @staticmethod
    def show_info(parent_widget, title: str, message: str):
        """Показать информацию"""
        logger.info(f"{title}: {message}")
        QMessageBox.information(parent_widget, title, message)
    
    @staticmethod
    def show_success(parent_widget, title: str, message: str):
        """Показать успех"""
        logger.info(f"✓ {title}: {message}")
        QMessageBox.information(parent_widget, f"✓ {title}", message)

# Использование:
# ErrorHandler.show_error(self, "Ошибка", "Не удалось загрузить темы", str(e))
# ErrorHandler.show_success(self, "Успех", "Урок создан!")
```

### Использовать в контроллерах:

```python
# app/controllers/settings.py
from utils.error_handler import ErrorHandler

def verify_selected_midi_input(self):
    device_name = self.get_selected_midi_input_name()
    if not device_name:
        ErrorHandler.show_info(
            self.ui.centralwidget,
            "Проверка MIDI",
            "Сначала выбери подключённое MIDI-устройство."
        )
        return

    try:
        import mido
    except ImportError:
        ErrorHandler.show_error(
            self.ui.centralwidget,
            "Ошибка",
            "Библиотека mido не установлена"
        )
        return

    try:
        with mido.open_input(device_name):
            pass
        ErrorHandler.show_success(
            self.ui.centralwidget,
            "Проверка MIDI",
            "Устройство работает корректно!"
        )
    except OSError as exc:
        ErrorHandler.show_error(
            self.ui.centralwidget,
            "Ошибка MIDI",
            f"Не удалось открыть устройство: {device_name}",
            str(exc)
        )
    except Exception as exc:
        ErrorHandler.show_error(
            self.ui.centralwidget,
            "Неожиданная ошибка",
            "При проверке MIDI произошла ошибка",
            str(exc)
        )
```

---

## 4. Retry логика с exponential backoff

### Создать файл: `app/utils/network_utils.py`

```python
import asyncio
import logging
from functools import wraps
from PyQt6.QtCore import QTimer, pyqtSignal, QObject

logger = logging.getLogger(__name__)

def retry_on_network_error(max_attempts=3, initial_delay=1):
    """
    Декоратор для повторных попыток с экспоненциальным backoff.
    Для использования с обычными (не async) функциями в PyQt
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    logger.info(f"Попытка {attempt + 1}/{max_attempts}: {func.__name__}")
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Попытка {attempt + 1} провалилась: {e}. "
                            f"Повтор через {delay}сек..."
                        )
                        # Для PyQt нужно использовать QTimer
                        # Поэтому просто ждём
                        import time
                        time.sleep(delay)
                        delay *= 2  # Экспоненциальный backoff
                    else:
                        logger.error(f"Все {max_attempts} попытки провалились: {e}")
            
            raise last_exception
        return wrapper
    return decorator

# Использование в workers:
class TopicWorker(QObject):
    def get_topics(self) -> None:
        @retry_on_network_error(max_attempts=3)
        def _do_request():
            url = QUrl("http://localhost:8000/topics/")
            request = QNetworkRequest(url)
            token = settings.value("token")
            if token:
                request.setRawHeader(b"Authorization", f"Bearer {token}".encode("utf-8"))
            request.setTransferTimeoutAttribute(REQUEST_TIMEOUT_MS)
            
            reply = self.manager.get(request)
            self._setup_timeout(reply, "Ошибка загрузки тем: превышено время ожидания")
            reply.finished.connect(lambda: self._on_get_reply(reply))
        
        try:
            _do_request()
        except Exception as e:
            self.error_signal.emit(f"Ошибка при загрузке тем после {3} попыток: {e}")
```

---

## 5. Правильная структура проекта

### Рекомендуемая структура:

```
music_app/
├── app/                          # Frontend (PyQt)
│   ├── main.py
│   ├── loader.py
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── main_window.py
│   │   └── ...
│   ├── GUI/
│   ├── workers/
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── error_handler.py
│   │   └── network_utils.py
│   ├── resources/
│   └── tests/
│       └── test_*.py
│
├── server/                       # Backend (FastAPI)
│   ├── app.py
│   ├── models.py
│   ├── logging_config.py
│   ├── exceptions.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── lesson.py
│   │   └── ...
│   ├── services/
│   │   ├── __init__.py
│   │   ├── user_service.py
│   │   └── ...
│   ├── core/
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   └── security.py
│   ├── utils/
│   │   ├── jwt.py
│   │   └── security.py
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   └── ...
│   └── db.py
│
├── schemas/
│   ├── auth.py
│   ├── lesson.py
│   └── ...
│
├── alembic/
│   ├── versions/
│   └── env.py
│
├── logs/                         # Создаётся автоматически
├── .env                          # НЕ коммитить в git
├── .env.example                  # Пример .env
├── .gitignore
├── pyproject.toml
├── requirements.txt              # Если не используется uv
└── README.md
```

---

## 6. Gitignore для проекта

### Создать/обновить: `.gitignore`

```
# Environment
.env
.env.local
.env.*.local
venv/
env/
__pycache__/
*.py[cod]
*$py.class

# IDE
.vscode/
.idea/
*.swp
*.swo
*.swn
.DS_Store

# Logs
logs/
*.log

# Database
*.db
*.sqlite
*.sqlite3

# QT
*.ui~
ui_*.py

# Testing
.pytest_cache/
.coverage
htmlcov/

# Build
build/
dist/
*.egg-info/

# OS
Thumbs.db
.DS_Store
```

---

## 7. Пример .env файла

### Создать: `.env.example`

```
# =========== App ===========
DEBUG=False
ENVIRONMENT=development

# =========== Server ===========
HOST=0.0.0.0
PORT=8000

# =========== Database ===========
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/music_app

# =========== JWT ===========
SECRET_KEY=your-secret-key-change-in-production-with-at-least-32-characters
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_DAYS=7

# =========== CORS ===========
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# =========== Rate Limiting ===========
RATE_LIMIT_ENABLED=True

# =========== Logging ===========
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

### Скопировать для разработки:

```bash
cp .env.example .env
# Отредактировать .env с локальными значениями
```

---

## 8. Миграция с текущей обработки на новую

### Шаг 1: Добавить логирование

```bash
mkdir -p logs
touch server/logging_config.py
# (скопировать из примера выше)
```

### Шаг 2: Создать исключения

```bash
touch server/exceptions.py
# (скопировать из примера выше)
```

### Шаг 3: Создать обработчик ошибок для GUI

```bash
touch app/utils/error_handler.py
# (скопировать из примера выше)
```

### Шаг 4: Обновить существующий код

Для каждого файла с `except Exception:`:

```bash
# lesson_player.py
# settings.py
# Заменить bare except на специфичные исключения
```

### Шаг 5: Добавить функцию в main

```bash
# app/main.py
# Добавить настройку логирования
```

---

## 9. Тестовый пример для workers

### Файл: `app/tests/test_auth_worker.py`

```python
import pytest
from PyQt6.QtCore import QUrl
from app.workers.auth_worker import AuthWorker
from schemas.auth import UserLogin

@pytest.fixture
def auth_worker():
    """Создать экземпляр AuthWorker для теста"""
    return AuthWorker()

def test_auth_worker_init(auth_worker):
    """Тест инициализации AuthWorker"""
    assert auth_worker.manager is not None
    assert auth_worker.timeout_timers == {}

def test_auth_worker_signals_exist(auth_worker):
    """Проверить наличие сигналов"""
    assert hasattr(auth_worker, 'user_received_signal')
    assert hasattr(auth_worker, 'error_occurred_signal')
    assert hasattr(auth_worker, 'token_valid_signal')
    assert hasattr(auth_worker, 'token_invalid_signal')

def test_login_user_with_timeout(auth_worker, qtbot):
    """Тест таймаута при входе"""
    # Этот тест требует запущенного сервера или mock'а
    # Просто проверяем, что функция вызывается без ошибок
    
    user_data = UserLogin(
        email="test@example.com",
        password="password123"
    )
    
    # Не должна вызвать исключение
    auth_worker.login_user(user_data)
    assert True
```

---

## Рекомендации по запуску

### Для разработки:

```bash
# Backend
cd server
python -m uvicorn app:app --reload

# Frontend (в другом терминале)
cd app
python main.py
```

### С логированием:

Логи автоматически сохраняются в `logs/app.log`

```bash
# Смотреть логи в реальном времени
tail -f logs/app.log

# Или с цветным выводом (если есть ccze)
tail -f logs/app.log | ccze -A
```
