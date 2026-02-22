from PyQt6.QtWidgets import QMainWindow,QMessageBox
from GUI.auth import Ui_AuthWindow
from controllers.main_window import Main
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtCore import QRegularExpression, QSettings
from workers.auth_worker import AuthWorker
import re
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from schemas.auth import UserCreate, UserLogin

from loader import settings


NORMAL_STYLE = """
QLineEdit { 
    padding: 15px 20px; border: none; border-radius: 15px; font-size: 18px; 
    background: rgba(255,255,255,0.95); color: #333; 
}
QLineEdit:focus { 
    background: rgba(255,255,255,1); border: 3px solid #4facfe; 
    padding: 12px 17px; 
}
"""

ERROR_STYLE = """
QLineEdit { 
    padding: 15px 20px; border: 3px solid #ff4444; border-radius: 15px; 
    font-size: 18px; background: rgba(255,220,220,0.95); color: #333; 
}
"""

class Auth(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_AuthWindow()
        self.ui.setupUi(self)

        self.ui.switch.clicked.connect(lambda: self.switch(1))
        self.ui.switch_2.clicked.connect(lambda: self.switch(0))
        self.ui.regBtn.clicked.connect(self.register)
        self.ui.authBtn.clicked.connect(self.auth)

        self.api = AuthWorker()

        self.api.user_received_signal.connect(self.on_user_recieved)
        self.api.error_occurred_signal.connect(self.on_error)
        
        self.errors = {}
        self.prev_login = []
        self.prev_email = []
        self.settings = QSettings()

        self.setup_validation()
        

    def switch(self, index):
        self.ui.stackedWidget.setCurrentIndex(index)
        self.clear_errors('email')
        self.clear_errors('email_auth')
        self.clear_errors('username')
        self.clear_errors('password')
        self.clear_errors('password_auth')
        self.clear_errors('confirm')
        

    def setup_validation(self):
        """Настройка валидаторов и стилей для полей регистрации"""
        email_re = QRegularExpression(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        email_validator = QRegularExpressionValidator(email_re, self)
        self.ui.emailInput.setValidator(email_validator)
        self.ui.emailInput1.setValidator(email_validator)
        username_re = QRegularExpression(r'^[a-zA-Z0-9_]{3,20}$')
        username_validator = QRegularExpressionValidator(username_re, self)
        self.ui.usernameInput.setValidator(username_validator)
        self.ui.emailInput.textChanged.connect(self.validate_email)
        self.ui.emailInput1.textChanged.connect(self.validate_email_auth)
        self.ui.usernameInput.textChanged.connect(self.validate_username)
        self.ui.passwordInput.textChanged.connect(self.validate_password)
        self.ui.passwordInput1.textChanged.connect(self.validate_password_auth)
        self.ui.passwordConfirmInput.textChanged.connect(self.validate_password_confirm)
        

    def clear_errors(self, field=None):
        if field == 'email':
            self.ui.emailInput.setStyleSheet(NORMAL_STYLE)
            self.ui.emailErrors.setText("")
            self.errors.pop('email', None)
        elif field == 'email_auth':
            self.ui.emailInput1.setStyleSheet(NORMAL_STYLE)
            self.ui.emailErrors1.setText("")
            self.errors.pop('email_auth', None)
        elif field == 'username':
            self.ui.usernameInput.setStyleSheet(NORMAL_STYLE)
            self.ui.LoginErrors.setText("")
            self.errors.pop('username', None)
        elif field == 'password':
            self.ui.passwordInput.setStyleSheet(NORMAL_STYLE)
            self.ui.passwordErrors.setText("")
            self.errors.pop('password', None)
        elif field == 'password_auth':
            self.ui.passwordInput1.setStyleSheet(NORMAL_STYLE)
            self.ui.passwordErrors1.setText("")
            self.errors.pop('password_auth', None)
        elif field == 'confirm':
            self.ui.passwordConfirmInput.setStyleSheet(NORMAL_STYLE)
            self.ui.passwordConfirmErrors.setText("")
            self.errors.pop('confirm', None)
        else:
            self.clear_errors('email')
            self.clear_errors('username')
            self.clear_errors('password')
            self.clear_errors('confirm')

    
    def show_error(self, field, message):
        self.errors[field] = message
        if field == 'email':
            self.ui.emailInput.setStyleSheet(ERROR_STYLE)
            self.ui.emailErrors.setText(message)
        elif field == 'email_auth':
            self.ui.emailInput1.setStyleSheet(ERROR_STYLE)
            self.ui.emailErrors1.setText(message)
        elif field == 'username':
            self.ui.usernameInput.setStyleSheet(ERROR_STYLE)
            self.ui.LoginErrors.setText(message)
        elif field == 'password':
            self.ui.passwordInput.setStyleSheet(ERROR_STYLE)
            self.ui.passwordErrors.setText(message)
        elif field == 'password_auth':
            self.ui.passwordInput1.setStyleSheet(ERROR_STYLE)
            self.ui.passwordErrors1.setText(message)
        elif field == 'confirm':
            self.ui.passwordConfirmInput.setStyleSheet(ERROR_STYLE)
            self.ui.passwordConfirmErrors.setText(message)

    
    def validate_email(self):
        email = self.ui.emailInput.text().strip()
        self.clear_errors('email')
        
        if not email:
            self.show_error('email', 'Email обязателен')
            return False
        
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            self.show_error('email', 'Неверный формат email')
            return False
        if email in self.prev_email:
            self.show_error('email', 'Пользователь с такой почтой уже существует')
            return False
        return True
    

    def validate_email_auth(self):
        email = self.ui.emailInput1.text().strip()
        self.clear_errors('email_auth')
        if not email:
            self.show_error('email_auth', 'Email обязателен')
            return False
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            self.show_error('email_auth', 'Неверный формат email')
            return False
        if email in self.prev_email:
            self.show_error('email_auth', 'Пользователь с такой почтой уже существует')
            return False
        return True
    

    def validate_username(self):
        username = self.ui.usernameInput.text().strip()
        self.clear_errors('username')
        if not username:
            self.show_error('username', 'Логин обязателен')
            return False
        if len(username) < 3:
            self.show_error('username', 'Логин минимум 3 символа')
            return False
        if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
            self.show_error('username', 'Только буквы, цифры, подчёркивание')
            return False
        if username in self.prev_login:
            self.show_error('username', 'Такой логин уже занят')
            return False
        return True
    

    def validate_password(self):
        password = self.ui.passwordInput.text()
        self.clear_errors('password')
        if not password:
            self.show_error('password', 'Пароль обязателен')
            return False
        if len(password) < 6:
            self.show_error('password', 'Пароль минимум 6 символов')
            return False
        if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)', password):
            self.show_error('password', '1 заглавная, 1 строчная, 1 цифра')
            return False
        return True
    

    def validate_password_auth(self):
        password = self.ui.passwordInput1.text()
        self.clear_errors('password_auth')
        if not password:
            self.show_error('password_auth', 'Пароль обязателен')
            return False
        if len(password) < 6:
            self.show_error('password_auth', 'Пароль минимум 6 символов')
            return False
        if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)', password):
            self.show_error('password_auth', '1 заглавная, 1 строчная, 1 цифра')
            return False
        return True
    

    def validate_password_confirm(self):
        password = self.ui.passwordInput.text()
        confirm = self.ui.passwordConfirmInput.text()
        self.clear_errors('confirm')
        if confirm and password != confirm:
            self.show_error('confirm', 'Пароли не совпадают')
            return False
        return True
    

    def is_valid(self):
        valid = (self.validate_email() and 
                self.validate_username() and 
                self.validate_password() and 
                self.validate_password_confirm())
        return len(self.errors) == 0 and valid
    

    def is_valid_auth(self):
        valid = (self.validate_email_auth() and 
                self.validate_password_auth())
        return len(self.errors) == 0 and valid
    

    def register(self):
        if self.ui.stackedWidget.currentIndex() != 0:
            return
        if self.is_valid():  
            user_reg = UserCreate(
                email=self.ui.emailInput.text().strip(),
                username = self.ui.usernameInput.text().strip(),
                password = self.ui.passwordConfirmInput.text().strip()
            )
            self.api.create_user(user_reg)


    def auth(self):
        if self.ui.stackedWidget.currentIndex() != 1:
            return
        if self.is_valid_auth():
            user = UserLogin(
                email=self.ui.emailInput1.text().strip(),
                password = self.ui.passwordInput1.text().strip()
            )
            self.api.login_user(user)

            
    def on_user_recieved(self, token):
        settings.setValue("token",token)
        print(token)
        QMessageBox.information(self, "Успех", 
                f"Добро пожаловать!")
        self.main_window = Main()
        self.main_window.show()
        self.close()
        

    def on_error(self, error:str):
        if error.find("username") != -1:
            self.show_error('username', 'Такой логин уже занят')
            self.prev_login.append(self.ui.usernameInput.text().strip())
        elif error.find("email") != -1 and self.ui.stackedWidget.currentIndex() != 1:
            self.show_error('email', 'Пользователь с такой почтой уже существует')
            self.prev_email.append(self.ui.usernameInput.text().strip())
        QMessageBox.warning(self, "Ошибка", 
                f"{error}!")
