"""
Authentication Controller Module

Управляет окном аутентификации и взаимодействием с пользователем
при входе и регистрации.
"""

import logging
import re
from typing import Dict

from config import AUTH_ERROR_STYLE, AUTH_NORMAL_STYLE
from controllers.main_window import Main
from GUI.auth import Ui_AuthWindow
from loader import settings
from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtWidgets import QMainWindow, QMessageBox
from workers.auth_worker import AuthWorker

from schemas.auth import UserCreate, UserLogin

logger = logging.getLogger(__name__)


# Валидационные паттерны
EMAIL_PATTERN: str = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
"""Регулярное выражение для проверки email"""

USERNAME_PATTERN: str = r"^[a-zA-Z0-9_]{3,20}$"
"""Регулярное выражение для проверки username (3-20 символов)"""

PASSWORD_PATTERN: str = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)"
"""Регулярное выражение для проверки пароля (минимум 1 заглавная, 1 строчная, 1 цифра)"""

# Константы для валидации
MIN_PASSWORD_LENGTH: int = 6
MIN_USERNAME_LENGTH: int = 3
MAX_USERNAME_LENGTH: int = 20


class Auth(QMainWindow):
    """
    Окно аутентификации и регистрации.

    Обеспечивает:
    - Регистрацию новых пользователей
    - Вход в аккаунт
    - Валидацию введённых данных
    - Обработку ошибок
    """

    def __init__(self) -> None:
        """Инициализация окна аутентификации"""
        super().__init__()
        self.ui = Ui_AuthWindow()
        self.ui.setupUi(self)

        # Подключаем кнопки
        self.ui.switch.clicked.connect(lambda: self.switch(1))
        self.ui.switch_2.clicked.connect(lambda: self.switch(0))
        self.ui.regBtn.clicked.connect(self.register)
        self.ui.authBtn.clicked.connect(self.auth)

        # Инициализируем API worker
        self.api = AuthWorker()
        self.api.user_received_signal.connect(self.on_user_received)
        self.api.error_occurred_signal.connect(self.on_error)

        # Хранилище ошибок валидации
        self.errors: Dict[str, str] = {}

        # Кэш использованных email и username для предотвращения дублирования
        self.cached_emails: set = set()
        self.cached_usernames: set = set()

        self.setup_validation()
        logger.debug("Auth controller initialized")

    def switch(self, index: int) -> None:
        """
        Переключает между вкладками регистрации и входа.

        Аргументы:
            index: 0 для регистрации, 1 для входа
        """
        self.ui.stackedWidget.setCurrentIndex(index)
        self.clear_all_errors()
        logger.debug(f"Switched to tab {index}")

    def setup_validation(self) -> None:
        """Настраивает валидаторы и обработчики событий для полей ввода"""
        # Email валидаторы
        email_regex = QRegularExpression(EMAIL_PATTERN)
        email_validator = QRegularExpressionValidator(email_regex, self)
        self.ui.emailInput.setValidator(email_validator)
        self.ui.emailInput1.setValidator(email_validator)

        # Username валидатор
        username_regex = QRegularExpression(USERNAME_PATTERN)
        username_validator = QRegularExpressionValidator(username_regex, self)
        self.ui.usernameInput.setValidator(username_validator)

        # Подключаем обработчики событий
        self.ui.emailInput.textChanged.connect(self.validate_email)
        self.ui.emailInput1.textChanged.connect(self.validate_email_auth)
        self.ui.usernameInput.textChanged.connect(self.validate_username)
        self.ui.passwordInput.textChanged.connect(self.validate_password)
        self.ui.passwordInput1.textChanged.connect(self.validate_password_auth)
        self.ui.passwordConfirmInput.textChanged.connect(self.validate_password_confirm)

    def clear_all_errors(self) -> None:
        """Очищает все ошибки валидации"""
        self.clear_error("email")
        self.clear_error("email_auth")
        self.clear_error("username")
        self.clear_error("password")
        self.clear_error("password_auth")
        self.clear_error("confirm")

    def clear_error(self, field: str) -> None:
        """
        Очищает ошибку для конкретного поля.

        Аргументы:
            field: Название поля (email, username, password и т.д.)
        """
        field_mapping = {
            "email": (self.ui.emailInput, self.ui.emailErrors),
            "email_auth": (self.ui.emailInput1, self.ui.emailErrors1),
            "username": (self.ui.usernameInput, self.ui.LoginErrors),
            "password": (self.ui.passwordInput, self.ui.passwordErrors),
            "password_auth": (self.ui.passwordInput1, self.ui.passwordErrors1),
            "confirm": (self.ui.passwordConfirmInput, self.ui.passwordConfirmErrors),
        }

        if field in field_mapping:
            input_widget, error_label = field_mapping[field]
            input_widget.setStyleSheet(AUTH_NORMAL_STYLE)
            error_label.setText("")
            self.errors.pop(field, None)

    def show_error(self, field: str, message: str) -> None:
        """
        Показывает ошибку для конкретного поля.

        Аргументы:
            field: Название поля
            message: Сообщение об ошибке
        """
        self.errors[field] = message

        field_mapping = {
            "email": (self.ui.emailInput, self.ui.emailErrors),
            "email_auth": (self.ui.emailInput1, self.ui.emailErrors1),
            "username": (self.ui.usernameInput, self.ui.LoginErrors),
            "password": (self.ui.passwordInput, self.ui.passwordErrors),
            "password_auth": (self.ui.passwordInput1, self.ui.passwordErrors1),
            "confirm": (self.ui.passwordConfirmInput, self.ui.passwordConfirmErrors),
        }

        if field in field_mapping:
            input_widget, error_label = field_mapping[field]
            input_widget.setStyleSheet(AUTH_ERROR_STYLE)
            error_label.setText(message)

    def validate_email(self) -> bool:
        """
        Валидирует email при регистрации.

        Возвращает:
            True если email валиден, False иначе
        """
        email = self.ui.emailInput.text().strip()
        self.clear_error("email")

        if not email:
            self.show_error("email", "Email обязателен")
            return False

        if not re.match(EMAIL_PATTERN, email):
            self.show_error("email", "Неверный формат email")
            return False

        if email in self.cached_emails:
            self.show_error("email", "Пользователь с такой почтой уже существует")
            return False

        return True

    def validate_email_auth(self) -> bool:
        """
        Валидирует email при входе.

        Возвращает:
            True если email валиден, False иначе
        """
        email = self.ui.emailInput1.text().strip()
        self.clear_error("email_auth")

        if not email:
            self.show_error("email_auth", "Email обязателен")
            return False

        if not re.match(EMAIL_PATTERN, email):
            self.show_error("email_auth", "Неверный формат email")
            return False

        return True

    def validate_username(self) -> bool:
        """
        Валидирует имя пользователя.

        Возвращает:
            True если username валиден, False иначе
        """
        username = self.ui.usernameInput.text().strip()
        self.clear_error("username")

        if not username:
            self.show_error("username", "Логин обязателен")
            return False

        if len(username) < MIN_USERNAME_LENGTH:
            self.show_error("username", f"Логин минимум {MIN_USERNAME_LENGTH} символа")
            return False

        if not re.match(USERNAME_PATTERN, username):
            self.show_error("username", "Только буквы, цифры, подчёркивание")
            return False

        if username in self.cached_usernames:
            self.show_error("username", "Такой логин уже занят")
            return False

        return True

    def validate_password(self) -> bool:
        """
        Валидирует пароль при регистрации.

        Возвращает:
            True если пароль валиден, False иначе
        """
        password = self.ui.passwordInput.text()
        self.clear_error("password")

        if not password:
            self.show_error("password", "Пароль обязателен")
            return False

        if len(password) < MIN_PASSWORD_LENGTH:
            self.show_error(
                "password", f"Пароль минимум {MIN_PASSWORD_LENGTH} символов"
            )
            return False

        if not re.match(PASSWORD_PATTERN, password):
            self.show_error("password", "1 заглавная буква, 1 строчная, 1 цифра")
            return False

        return True

    def validate_password_auth(self) -> bool:
        """
        Валидирует пароль при входе.

        Возвращает:
            True если пароль валиден, False иначе
        """
        password = self.ui.passwordInput1.text()
        self.clear_error("password_auth")

        if not password:
            self.show_error("password_auth", "Пароль обязателен")
            return False

        if len(password) < MIN_PASSWORD_LENGTH:
            self.show_error(
                "password_auth", f"Пароль минимум {MIN_PASSWORD_LENGTH} символов"
            )
            return False

        if not re.match(PASSWORD_PATTERN, password):
            self.show_error("password_auth", "1 заглавная буква, 1 строчная, 1 цифра")
            return False

        return True

    def validate_password_confirm(self) -> bool:
        """
        Валидирует совпадение пароля и подтверждения.

        Возвращает:
            True если пароли совпадают, False иначе
        """
        password = self.ui.passwordInput.text()
        confirm = self.ui.passwordConfirmInput.text()
        self.clear_error("confirm")

        if confirm and password != confirm:
            self.show_error("confirm", "Пароли не совпадают")
            return False

        return True

    def is_registration_valid(self) -> bool:
        """
        Проверяет валидность всех полей регистрации.

        Возвращает:
            True если все поля валидны, False иначе
        """
        return (
            self.validate_email()
            and self.validate_username()
            and self.validate_password()
            and self.validate_password_confirm()
            and len(self.errors) == 0
        )

    def is_login_valid(self) -> bool:
        """
        Проверяет валидность всех полей входа.

        Возвращает:
            True если все поля валидны, False иначе
        """
        return (
            self.validate_email_auth()
            and self.validate_password_auth()
            and len(self.errors) == 0
        )

    def register(self) -> None:
        """Обработчик кнопки регистрации"""
        if self.ui.stackedWidget.currentIndex() != 0:
            return

        if not self.is_registration_valid():
            logger.warning("Registration validation failed")
            return

        user_data = UserCreate(
            email=self.ui.emailInput.text().strip(),
            username=self.ui.usernameInput.text().strip(),
            password=self.ui.passwordConfirmInput.text().strip(),
        )

        logger.info(f"Registering user: {user_data.email}")
        self.api.create_user(user_data)

    def auth(self) -> None:
        """Обработчик кнопки входа"""
        if self.ui.stackedWidget.currentIndex() != 1:
            return

        if not self.is_login_valid():
            logger.warning("Login validation failed")
            return

        user_data = UserLogin(
            email=self.ui.emailInput1.text().strip(),
            password=self.ui.passwordInput1.text().strip(),
        )

        logger.info(f"Logging in user: {user_data.email}")
        self.api.login_user(user_data)

    def on_user_received(self, data: Dict[str, any]) -> None:
        """
        Обработчик успешной регистрации/входа.

        Аргументы:
            data: Ответ от сервера с токеном и данными пользователя
        """
        try:
            token = data.get("access_token")
            user_info = data.get("user", {})

            if not token:
                logger.error("No access token in response")
                QMessageBox.warning(self, "Ошибка", "Ошибка сервера: нет токена")
                return

            # Сохраняем токен для будущих сессий
            settings.setValue("token", token)

            logger.info(f"User authenticated successfully: {user_info.get('email')}")
            QMessageBox.information(self, "Успех", "Добро пожаловать!")

            # Открываем главное окно
            self.main_window = Main(user_info)
            self.main_window.show()
            self.close()

        except Exception as e:
            logger.error(f"Error processing user data: {str(e)}")
            QMessageBox.warning(self, "Ошибка", f"Ошибка обработки данных: {str(e)}")

    def on_error(self, error: str) -> None:
        """
        Обработчик ошибок от сервера.

        Аргументы:
            error: Сообщение об ошибке от сервера
        """
        logger.warning(f"Authentication error: {error}")

        # Обработка ошибок по типам
        if "username" in error.lower():
            self.show_error("username", "Такой логин уже занят")
            self.cached_usernames.add(self.ui.usernameInput.text().strip())
        elif "email" in error.lower():
            email = (
                self.ui.emailInput1.text().strip() or self.ui.emailInput.text().strip()
            )
            self.show_error(
                "email" if self.ui.stackedWidget.currentIndex() == 0 else "email_auth",
                "Пользователь с такой почтой уже существует",
            )
            self.cached_emails.add(email)

        QMessageBox.warning(self, "Ошибка аутентификации", error)
