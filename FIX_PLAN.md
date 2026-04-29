# ПЛАН ИСПРАВЛЕНИЯ ПРОБЛЕМ

## 🔴 КРИТИЧЕСКИЕ (СРОЧНО)

### 2️⃣ Добавить логирование

**Файл:** `server/app.py` (добавить в начало)
```python
import logging

# Настроить логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

**Создать папку:** `mkdir -p logs/`


### 4️⃣ Заменить bare except в lesson_player.py

Там 8 мест. Общий шаблон:

```diff
- try:
-     # код
- except Exception:
-     pass
+ try:
+     # код
+ except SpecificError:
+     handle_specific_error()
+ except Exception as e:
+     logger.error(f"Неожиданная ошибка: {e}")
+     pass  # или показать пользователю
```

---

## 🟠 СЕРЬЁЗНЫЕ (В ПЕРВЫЙ ДЕНЬ)

### 5️⃣ Добавить глобальную обработку ошибок в FastAPI

**Файл:** `server/app.py`

```python
from fastapi import FastAPI
from fastapi.exception_handlers import http_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

app = FastAPI(
    title="music_app",
    version="1.0.0",
    description="FastAPI приложение с полной системой аутентификации",
    openapi_url="/api/v1/openapi.json"
)

# ✅ Обработчик HTTP исключений
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request, exc):
    logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
    return await http_exception_handler(request, exc)

# ✅ Обработчик всех остальных исключений
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal Server Error",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# ✅ Healthcheck
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat()
    }
```

### 6️⃣ Улучшить обработку ошибок БД в services

**Файл:** `server/services/user_service.py`

```python
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)

class UserService:
    async def create_user(self, user_data: UserCreate) -> Optional[User]:
        """Создание нового пользователя"""
        try:
            hashed_password = get_password_hash(user_data.password)
            result = await self.db.execute(
                select(Role.id).where(Role.name == "пользователь")
            )
            role_id = result.scalar_one_or_none()
            if not role_id:
                logger.error("Роль 'пользователь' не найдена в БД")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Ошибка конфигурации сервера"
                )
            
            db_user = User(
                email=user_data.email,
                username=user_data.username,
                hashed_password=hashed_password,
                role=role_id
            )
            self.db.add(db_user)
            await self.db.commit()
            await self.db.refresh(db_user)
            logger.info(f"Создан новый пользователь: {user_data.email}")
            return db_user
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Нарушение уникальности при создании пользователя: {e}")
            # Пробуем определить какое именно поле нарушило constraint
            if "user_email_key" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Пользователь с таким email уже существует"
                )
            elif "user_username_key" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Пользователь с таким username уже существует"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ошибка при создании пользователя"
                )
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Неожиданная ошибка при создании пользователя: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при создании пользователя"
            )
```

### 7️⃣ Закрыть CORS

**Файл:** `server/app.py`

```python
import os
from dotenv import load_dotenv

load_dotenv()

# Получить разрешённые домены из переменной окружения
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # ✅ Только разрешённые
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],  # ✅ Конкретные методы
    allow_headers=["Content-Type", "Authorization"],  # ✅ Конкретные заголовки
)
```

**Файл:** `.env`
```
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### 8️⃣ Добавить валидацию паролей

**Файл:** `schemas/auth.py`

```python
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional

class UserCreate(BaseModel):
    """Схема для создания пользователя"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Минимум 8 символов, должна быть буква и цифра"
    )

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if not v.isalnum() and "_" not in v:
            raise ValueError('Имя пользователя может содержать только буквы, цифры и подчёркивание')
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну заглавную букву')
        if not any(c.isdigit() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        return v
```

---

## 🟡 ВАЖНЫЕ (В ПЕРВУЮ НЕДЕЛЮ)

### 9️⃣ Добавить unit тесты

**Создать файл:** `tests/test_auth.py`

```python
import pytest
from fastapi.testclient import TestClient
from app import app
from models import User, Role

client = TestClient(app)

@pytest.fixture
def setup_db(db_session):
    """Создать роль перед тестами"""
    role = Role(name="пользователь")
    db_session.add(role)
    db_session.commit()
    return db_session

def test_register_success(setup_db):
    """Тест успешной регистрации"""
    response = client.post("/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "SecurePass123"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["access_token"]
    assert data["user"]["email"] == "test@example.com"

def test_register_duplicate_email(setup_db):
    """Тест попытки регистрации с существующим email"""
    # Сначала создаём пользователя
    client.post("/register", json={
        "username": "user1",
        "email": "test@example.com",
        "password": "SecurePass123"
    })
    
    # Пробуем создать ещё одного с тем же email
    response = client.post("/register", json={
        "username": "user2",
        "email": "test@example.com",
        "password": "SecurePass123"
    })
    assert response.status_code == 400
    assert "email" in response.json()["detail"].lower()

def test_login_success(setup_db):
    """Тест успешного входа"""
    # Регистрируемся
    client.post("/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "SecurePass123"
    })
    
    # Входим
    response = client.post("/login", json={
        "email": "test@example.com",
        "password": "SecurePass123"
    })
    assert response.status_code == 201
    assert "access_token" in response.json()

def test_login_invalid_password(setup_db):
    """Тест входа с неверным паролем"""
    client.post("/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "SecurePass123"
    })
    
    response = client.post("/login", json={
        "email": "test@example.com",
        "password": "WrongPassword"
    })
    assert response.status_code == 401
```

### 🔟 Добавить Rate Limiting

**Файл:** `server/app.py`

```bash
pip install slowapi
```

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/login")
@limiter.limit("5/minute")  # 5 попыток в минуту
async def login(request: Request, user_data: UserLogin):
    ...

@app.post("/register")
@limiter.limit("10/hour")  # 10 регистраций в час
async def register(request: Request, user_data: UserCreate):
    ...
```

### 1️⃣1️⃣ Улучшить структуру конфигурации

**Файл:** `server/core/config.py`

```python
from pydantic_settings import BaseSettings
from typing import Optional
from enum import Enum

class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class Settings(BaseSettings):
    # App
    APP_NAME: str = "MUSIC APP"
    DEBUG: bool = False
    ENVIRONMENT: Environment = Environment.PRODUCTION
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = False
    
    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_POOL_RECYCLE: int = 3600
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        
    def is_production(self) -> bool:
        return self.ENVIRONMENT == Environment.PRODUCTION

settings = Settings()
```

**Файл:** `.env` (пример)
```
# App
DEBUG=False
ENVIRONMENT=development

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost/music_app

# JWT
SECRET_KEY=your-super-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_DAYS=7

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Logging
LOG_LEVEL=INFO
```

### 1️⃣2️⃣ Добавить Retry логику в workers

**Файл:** `app/workers/auth_worker.py` (добавить в начало класса)

```python
import asyncio
from functools import wraps

def retry_with_backoff(max_attempts=3, initial_delay=1):
    """Декоратор для повторных попыток с экспоненциальным backoff"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    print(f"Попытка {attempt + 1} провалилась, повтор через {delay}сек")
                    self = args[0]  # QObject
                    self.retry_timer = QTimer()
                    self.retry_timer.setSingleShot(True)
                    # ...запланировать повтор
        return wrapper
    return decorator
```

---

## 📊 ЧЕКЛИСТ ИСПРАВЛЕНИЙ

```
КРИТИЧЕСКИЕ (сегодня):
☐ Удалить print(password)
☐ Добавить логирование в server/app.py
☐ Заменить 8 bare except в lesson_player.py на специфичные
☐ Заменить 3 bare except в settings.py на специфичные

СЕРЬЁЗНЫЕ (завтра):
☐ Добавить exception handlers в FastAPI
☐ Улучшить обработку IntegrityError в UserService
☐ Закрыть CORS параметры
☐ Добавить валидацию паролей в Pydantic

ВАЖНЫЕ (неделя):
☐ Написать unit тесты (минимум 10)
☐ Добавить Rate Limiting
☐ Улучшить структуру конфигурации
☐ Добавить retry logic в workers
☐ Добавить healthcheck эндпоинт
☐ Добавить версионирование API (/api/v1/)
```

---

## 🔗 ДОКУМЕНТАЦИЯ

- FastAPI: https://fastapi.tiangolo.com/
- Pydantic: https://docs.pydantic.dev/latest/
- SQLAlchemy: https://docs.sqlalchemy.org/
- PyQt6: https://www.riverbankcomputing.com/static/Docs/PyQt6/
- slowapi: https://github.com/laurentS/slowapi
