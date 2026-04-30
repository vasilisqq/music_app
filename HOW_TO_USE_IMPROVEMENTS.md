"""
ИНСТРУКЦИЯ: КАК ИСПОЛЬЗОВАТЬ УЛУЧШЕННЫЙ КОД
=============================================

Этот документ содержит пошаговые инструкции по использованию
улучшенного кода в вашем проекте.
"""

# ============================================================================
# 1️⃣ ИМПОРТИРОВАНИЕ СТИЛЕЙ
# ============================================================================

## Было:
```python
NORMAL_STYLE = """QLineEdit { ... }"""
ERROR_STYLE = """QLineEdit { ... }"""
```

## Стало:
```python
from config import AUTH_NORMAL_STYLE, AUTH_ERROR_STYLE

# Используем:
self.ui.emailInput.setStyleSheet(AUTH_NORMAL_STYLE)
```

---

# ============================================================================
# 2️⃣ ЛОГИРОВАНИЕ
# ============================================================================

## Было:
```python
print(user)
```

## Стало:
```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"User authenticated: {user.email}")
logger.error(f"Authentication failed: {error}")
logger.debug(f"User data: {user}")
```

## Где использовать:
- ✅ Начало каждого файла: `import logging` + `logger = logging.getLogger(__name__)`
- ✅ В методах: логируйте важные события
- ✅ На ошибки: `logger.error(...)`
- ✅ На успехи: `logger.info(...)`

---

# ============================================================================
# 3️⃣ TYPE HINTS
# ============================================================================

## Было:
```python
def validate_email(self):
    return False
```

## Стало:
```python
def validate_email(self) -> bool:
    """Валидирует email адрес"""
    return False
```

## Примеры:
```python
# Для параметров
def create_user(self, email: str, age: int) -> User:
    pass

# Для опциональных
def find_user(self, user_id: int) -> Optional[User]:
    pass

# Для коллекций
def get_users(self) -> List[User]:
    pass

def get_user_data(self) -> Dict[str, any]:
    pass

# Для функций что ничего не возвращают
def log_error(self, error: str) -> None:
    pass
```

---

# ============================================================================
# 4️⃣ DOCSTRINGS
# ============================================================================

## Было:
```python
def my_method(self):
    pass
```

## Стало:
```python
def my_method(self, param1: str, param2: int = 5) -> bool:
    """
    Одна строка что делает метод.
    
    Подробное описание если нужно. Может быть на нескольких строках.
    Объясняет как именно работает метод.
    
    Аргументы:
        param1: Описание первого параметра
        param2: Описание второго параметра (по умолчанию 5)
        
    Возвращает:
        True если успешно, False если неудача
        
    Исключения:
        ValueError: Если param1 пустой
        TypeError: Если param2 не число
        
    Примеры:
        >>> result = my_method("hello", 10)
        >>> result
        True
    """
    return True
```

## Для классов:
```python
class MyWorker(BaseAPIWorker):
    """
    Одна строка описания класса.
    
    Подробное описание:
    - Что делает класс
    - Как его использовать
    - Какие методы важные
    
    Атрибуты:
        my_signal: PyQt сигнал при успехе
        error_signal: PyQt сигнал при ошибке
        
    Примеры:
        >>> worker = MyWorker()
        >>> worker.do_something()
    """
```

---

# ============================================================================
# 5️⃣ CUSTOM EXCEPTIONS
# ============================================================================

## Было:
```python
if not user:
    raise Exception("User not found")
```

## Стало:
```python
from server.core.exceptions import NotFoundError, DuplicateError

if not user:
    raise NotFoundError("User", user_id)

if user_exists:
    raise DuplicateError("email", user_email)
```

## Доступные исключения:
- `AuthenticationError` - неверные учётные данные
- `AuthorizationError` - недостаточно прав
- `NotFoundError` - ресурс не найден
- `DuplicateError` - дублирование данных
- `ValidationError` - ошибка валидации
- `InternalServerError` - внутренняя ошибка

---

# ============================================================================
# 6️⃣ КОНСТАНТЫ
# ============================================================================

## Было:
```python
if len(password) < 6:
    pass

EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
```

## Стало:
```python
MIN_PASSWORD_LENGTH: int = 6
EMAIL_PATTERN: str = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

if len(password) < MIN_PASSWORD_LENGTH:
    pass
```

## Правило:
- ✅ Все "магические числа" → в константы
- ✅ Все регулярные выражения → в константы
- ✅ Все таймауты → в константы
- ✅ Все URL/endpoints → в константы

---

# ============================================================================
# 7️⃣ СТРУКТУРА ФАЙЛА
# ============================================================================

## Рекомендуемая структура:
```python
"""
Module Description

Одна строка что делает модуль.

Подробное описание если нужно.
"""

# Стандартные импорты
import logging
from typing import Optional, List

# PyQt импорты
from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtCore import pyqtSignal

# Локальные импорты
from config import NORMAL_STYLE
from workers.auth_worker import AuthWorker

# Логирование
logger = logging.getLogger(__name__)

# Константы
MIN_PASSWORD_LENGTH: int = 6
EMAIL_PATTERN: str = r'^...$'

# Классы
class MyClass:
    """Документация класса"""
    pass

# Функции
def my_function() -> None:
    """Документация функции"""
    pass
```

---

# ============================================================================
# 8️⃣ РЕФАКТОРИНГ СУЩЕСТВУЮЩЕГО КОДА
# ============================================================================

### Шаг 1: Добавить модульный docstring
```python
"""
Module Name

Description of what this module does.
"""
```

### Шаг 2: Добавить импорты и логирование
```python
import logging
logger = logging.getLogger(__name__)
```

### Шаг 3: Добавить type hints к методам
```python
# Было:
def validate(self):

# Стало:
def validate(self) -> bool:
```

### Шаг 4: Добавить docstrings к методам
```python
def validate(self) -> bool:
    """
    Валидирует данные.
    
    Возвращает:
        True если валидно, False иначе
    """
```

### Шаг 5: Добавить логирование
```python
logger.info("Validating data")
if not is_valid:
    logger.error("Validation failed")
    return False
```

### Шаг 6: Использовать custom exceptions
```python
if not data:
    raise ValidationError("Data is required")
```

---

# ============================================================================
# 9️⃣ БЫСТРЫЙ ЧЕКЛИСТ ДЛЯ КАЖДОГО ФАЙЛА
# ============================================================================

Используйте этот чеклист при рефакторинге:

- [ ] Добавлен модульный docstring в начало файла
- [ ] Все импорты отсортированы (стандартные → PyQt → локальные)
- [ ] Добавлено `import logging` и `logger = logging.getLogger(__name__)`
- [ ] Извлечены все "магические числа" в константы
- [ ] Все функции/методы имеют type hints
- [ ] Все функции/методы имеют docstrings
- [ ] Добавлено логирование в критические места
- [ ] Использованы custom exceptions вместо generic Exception
- [ ] Нет дублирования кода (использованы методы/переменные)
- [ ] Нет sys.path.append или других опасных конструкций

---

# ============================================================================
# 🔟 ПРИМЕРЫ РЕАЛЬНЫХ УЛУЧШЕНИЙ
# ============================================================================

### Пример 1: Простая функция

**Было:**
```python
def login(self, email, password):
    user = authenticate(email, password)
    if not user:
        return False
    return True
```

**Стало:**
```python
async def login(self, email: str, password: str) -> bool:
    """
    Аутентифицирует пользователя.
    
    Аргументы:
        email: Email пользователя
        password: Пароль
        
    Возвращает:
        True если успешно, False иначе
    """
    try:
        user = await self.authenticate_user(email, password)
        if not user:
            logger.warning(f"Authentication failed for {email}")
            return False
        logger.info(f"User authenticated: {email}")
        return True
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return False
```

### Пример 2: Класс с документацией

**Было:**
```python
class Worker:
    def __init__(self):
        self.api = None
    
    def make_request(self, url):
        pass
```

**Стало:**
```python
class APIWorker(QObject):
    """
    Базовый класс для работы с REST API.
    
    Обеспечивает безопасную отправку HTTP запросов
    с обработкой ошибок и таймаутов.
    
    Атрибуты:
        api: API клиент
    """
    
    DEFAULT_TIMEOUT_MS: int = 10000
    
    def __init__(self) -> None:
        """Инициализация API worker"""
        super().__init__()
        self.api = None
        logger.debug("APIWorker initialized")
    
    def make_request(self, url: str) -> Optional[dict]:
        """
        Отправляет HTTP запрос.
        
        Аргументы:
            url: URL для запроса
            
        Возвращает:
            Данные ответа или None при ошибке
        """
        try:
            logger.debug(f"Making request to {url}")
            response = self.api.get(url)
            logger.info(f"Request successful: {url}")
            return response
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            return None
```

---

# ============================================================================
# ✅ ГОТОВО К ИСПОЛЬЗОВАНИЮ
# ============================================================================

Все файлы уже обновлены и готовы к использованию как образцы!

Просто откройте и смотрите как пример:
- `server/services/user_service.py` - отличный пример документации
- `app/workers/base_worker.py` - отличный пример архитектуры
- `app/controllers/auth.py` - отличный пример рефакторинга
