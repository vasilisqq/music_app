from PyQt6.QtWidgets import QMainWindow,QMessageBox
from GUI.auth import Ui_AuthWindow
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtCore import QRegularExpression
import re


class Auth(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_AuthWindow()
        self.ui.setupUi(self)
        self.ui.switch.clicked.connect(lambda: self.ui.stackedWidget.setCurrentIndex(1))
        self.ui.switch_2.clicked.connect(lambda: self.ui.stackedWidget.setCurrentIndex(0))

        self.setup_validation()
        
        # Состояние ошибок
        self.errors = {}
        
    def setup_validation(self):
        """Настройка валидаторов и стилей для полей регистрации"""
        # Валидаторы
        email_re = QRegularExpression(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        email_validator = QRegularExpressionValidator(email_re, self)
        self.ui.emailInput.setValidator(email_validator)

        username_re = QRegularExpression(r'^[a-zA-Z0-9_]{3,20}$')
        username_validator = QRegularExpressionValidator(username_re, self)
        self.ui.usernameInput.setValidator(username_validator)
        
        # Подключаем обработчики изменений
        self.ui.emailInput.textChanged.connect(self.validate_email)
        self.ui.usernameInput.textChanged.connect(self.validate_username)
        self.ui.passwordInput.textChanged.connect(self.validate_password)
        self.ui.passwordConfirmInput.textChanged.connect(self.validate_password_confirm)
        
        # Кнопка регистрации
        self.ui.regBtn.clicked.connect(self.register)

    def clear_errors(self, field=None):
        """Очистка ошибок для поля или всех"""
        
        if field == 'email':
            self.ui.emailInput.setStyleSheet("QLineEdit { padding: 15px 20px; border: none; border-radius: 15px; font-size: 18px; background: rgba(255,255,255,0.95); color: #333; } QLineEdit:focus { background: rgba(255,255,255,1); border: 3px solid #4facfe; padding: 12px 17px; }")
            if 'email' in self.errors: del self.errors['email']
        elif field == 'username':
            self.ui.usernameInput.setStyleSheet("QLineEdit { padding: 15px 20px; border: none; border-radius: 15px; font-size: 18px; background: rgba(255,255,255,0.95); color: #333; } QLineEdit:focus { background: rgba(255,255,255,1); border: 3px solid #4facfe; padding: 12px 17px; }")
            if 'username' in self.errors: del self.errors['username']
        elif field == 'password':
            self.ui.passwordInput.setStyleSheet("QLineEdit { padding: 15px 20px; border: none; border-radius: 15px; font-size: 18px; background: rgba(255,255,255,0.95); color: #333; } QLineEdit:focus { background: rgba(255,255,255,1); border: 3px solid #4facfe; padding: 12px 17px; }")
            if 'password' in self.errors: del self.errors['password']
        elif field == 'confirm':
            self.ui.passwordConfirmInput.setStyleSheet("QLineEdit { padding: 15px 20px; border: none; border-radius: 15px; font-size: 18px; background: rgba(255,255,255,0.95); color: #333; } QLineEdit:focus { background: rgba(255,255,255,1); border: 3px solid #4facfe; padding: 12px 17px; }")
            if 'confirm' in self.errors: del self.errors['confirm']
        else:
            # Очистить все
            self.clear_errors('email')
            self.clear_errors('username')
            self.clear_errors('password')
            self.clear_errors('confirm')
    
    def show_error(self, field, message):
        """Показать ошибку и подсветить поле красным"""
        self.errors[field] = message
        
        if field == 'email':
            self.ui.emailInput.setStyleSheet("""
                QLineEdit { 
                    padding: 15px 20px; border: 3px solid #ff4444; border-radius: 15px; 
                    font-size: 18px; background: rgba(255,220,220,0.95); color: #333; 
                }
            """)
        elif field == 'username':
            self.ui.usernameInput.setStyleSheet("""
                QLineEdit { 
                    padding: 15px 20px; border: 3px solid #ff4444; border-radius: 15px; 
                    font-size: 18px; background: rgba(255,220,220,0.95); color: #333; 
                }
            """)
        elif field == 'password':
            self.ui.passwordInput.setStyleSheet("""
                QLineEdit { 
                    padding: 15px 20px; border: 3px solid #ff4444; border-radius: 15px; 
                    font-size: 18px; background: rgba(255,220,220,0.95); color: #333; 
                }
            """)
        elif field == 'confirm':
            self.ui.passwordConfirmInput.setStyleSheet("""
                QLineEdit { 
                    padding: 15px 20px; border: 3px solid #ff4444; border-radius: 15px; 
                    font-size: 18px; background: rgba(255,220,220,0.95); color: #333; 
                }
            """)
    
    def validate_email(self):
        email = self.ui.emailInput.text().strip()
        
        self.clear_errors('email')
        
        if not email:
            self.show_error('email', 'Email обязателен')
            return False
        
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            self.show_error('email', 'Неверный формат email')
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
    
    def validate_password_confirm(self):
        password = self.ui.passwordInput.text()
        confirm = self.ui.passwordConfirmInput.text()
        
        self.clear_errors('confirm')
        
        if confirm and password != confirm:
            self.show_error('confirm', 'Пароли не совпадают')
            return False
        return True
    
    def is_valid(self):
        """Полная проверка всех полей"""
        valid = (self.validate_email() and 
                self.validate_username() and 
                self.validate_password() and 
                self.validate_password_confirm())
        return len(self.errors) == 0 and valid
    
    def register(self):
        """Обработка регистрации"""
        if self.ui.stackedWidget.currentIndex() != 0:
            return
            
        
        # Полная валидация
        if not self.is_valid():
            QMessageBox.warning(self, "Ошибка", "Исправьте ошибки!")
            return
        email = self.ui.emailInput_2.text().strip()
        username = self.ui.usernameInput_2.text().strip()
        
        QMessageBox.information(self, "Успех", 
            f"Пользователь {username} зарегистрирован!\nEmail: {email}")
        
        # Переход на логин
        self.ui.stackedWidget.setCurrentIndex(1)
