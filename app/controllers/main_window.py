from PyQt6.QtWidgets import QMainWindow, QMessageBox
from loader import settings
from GUI.main_window import Ui_MainWindow

class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        # Вызываем метод заполнения профиля
        self.setup_profile()
        # ... (тут остается твой код для анимации выезжающего меню, если ты его добавил) ...

    def setup_profile(self):
        """Читаем данные из кэша и обновляем интерфейс"""
        # Достаем сохраненные значения (второй аргумент - заглушка на случай, если данных нет)
        username = settings.value("username", "👤 Гость")
        email = settings.value("email", "no-reply@example.com")
        
        # Устанавливаем текст в твои лейблы
        self.ui.userNameLabel.setText(f"👤 {username}")
        self.ui.emailLabel.setText(email)