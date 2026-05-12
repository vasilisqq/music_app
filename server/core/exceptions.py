"""
Custom Exception Classes

Определяет кастомные исключения для единообразной обработки ошибок
во всём приложении.
"""


class APIException(Exception):
    """Базовое исключение для API ошибок"""

    def __init__(self, message: str, status_code: int = 400) -> None:
        """
        Аргументы:
            message: Сообщение об ошибке
            status_code: HTTP статус код
        """
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class AuthenticationError(APIException):
    """Ошибка аутентификации (неверные учётные данные)"""

    def __init__(self, message: str = "Invalid credentials") -> None:
        super().__init__(message, status_code=401)


class AuthorizationError(APIException):
    """Ошибка авторизации (недостаточно прав)"""

    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(message, status_code=403)


class NotFoundError(APIException):
    """Ошибка: ресурс не найден"""

    def __init__(self, resource_type: str, resource_id: str | int) -> None:
        message = f"{resource_type} with ID {resource_id} not found"
        super().__init__(message, status_code=404)


class DuplicateError(APIException):
    """Ошибка: попытка создать дубликат"""

    def __init__(self, field: str, value: str) -> None:
        message = f"{field} '{value}' already exists"
        super().__init__(message, status_code=409)


class ValidationError(APIException):
    """Ошибка валидации данных"""

    def __init__(self, message: str = "Validation error") -> None:
        super().__init__(message, status_code=422)


class InternalServerError(APIException):
    """Внутренняя ошибка сервера"""

    def __init__(self, message: str = "Internal server error") -> None:
        super().__init__(message, status_code=500)
