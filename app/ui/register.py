import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QLabel, 
                             QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class AuthWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Авторизация")
        self.setFixedSize(400, 500)
        self.setStyleSheet("""
            QMainWindow { background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #667eea, stop:1 #764ba2); }
            QLabel { color: white; font-size: 14px; }
            QLineEdit { padding: 12px; border: 2px solid #ddd; 
                       border-radius: 8px; font-size: 14px; }
            QPushButton { background: #4CAF50; color: white; 
                         padding: 12px; border-radius: 8px; 
                         font-size: 16px; font-weight: bold; }
            QPushButton:hover { background: #45a049; }
            QPushButton:pressed { background: #3d8b40; }
            QPushButton#switch { background: #2196F3; }
            QPushButton#switch:hover { background: #1976D2; }
        """)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setSpacing(20)
        self.layout.setContentsMargins(40, 40, 40, 40)
        
        # Заголовок
        title = QLabel("🎵 Music App")
        title.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(title)
        
        # Поля ввода
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Логин")
        self.layout.addWidget(self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Пароль")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.layout.addWidget(self.password_input)
        
        # Email (только для регистрации)
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email")
        self.email_input.setVisible(False)
        self.layout.addWidget(self.email_input)
        
        # Основная кнопка
        self.auth_btn = QPushButton("Войти")
        self.auth_btn.clicked.connect(self.auth)
        self.layout.addWidget(self.auth_btn)
        
        # Кнопка переключения режима
        self.switch_btn = QPushButton("Нет аккаунта? Зарегистрироваться")
        self.switch_btn.setObjectName("switch")
        self.switch_btn.clicked.connect(self.toggle_mode)
        self.layout.addWidget(self.switch_btn)
        
        # Выравнивание по центру
        self.layout.addStretch()
    
    def toggle_mode(self):
        if hasattr(self, 'mode') and self.mode == "register":
            self.mode = "login"
            self.auth_btn.setText("Войти")
            self.switch_btn.setText("Нет аккаунта? Зарегистрироваться")
            self.email_input.setVisible(False)
            self.username_input.setPlaceholderText("Логин")
        else:
            self.mode = "register"
            self.auth_btn.setText("Зарегистрироваться")
            self.switch_btn.setText("Уже есть аккаунт? Войти")
            self.email_input.setVisible(True)
            self.username_input.setPlaceholderText("Логин (новый)")
    
    def auth(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        email = self.email_input.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "Ошибка", "Заполните логин и пароль!")
            return
        
        if self.mode == "register" and not email:
            QMessageBox.warning(self, "Ошибка", "Введите email для регистрации!")
            return
        
        # TODO: Подключи БД
        if self.mode == "login":
            QMessageBox.information(self, "Успех", f"Добро пожаловать, {username}!")
        else:
            QMessageBox.information(self, "Регистрация", 
                                  f"Пользователь {username} зарегистрирован!")
        
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AuthWindow()
    window.show()
    sys.exit(app.exec())
