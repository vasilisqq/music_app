from PyQt6.QtWidgets import QMainWindow, QMessageBox, QWidget, QGridLayout, QHBoxLayout
from PyQt6.QtCore import Qt
from loader import settings
from GUI.main_window import Ui_MainWindow
from GUI.LessonCard import LessonCard
from GUI.helpful import FlowLayout

from PyQt6.QtWidgets import QMainWindow, QMessageBox, QWidget, QHBoxLayout, QScrollArea
from GUI.main_window import Ui_MainWindow
from GUI.LessonCard import LessonCard
from GUI.helpful import FlowLayout

class Main(QMainWindow):
    def __init__(self, user_data: dict):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.adminPanelBtn.setVisible(False) 
        self.user_data = user_data
        # Проверяем роль из полученных от сервера данных
        user_role = self.user_data.get("role", "пользователь") 
        if user_role in ["администратор", "учитель"]: 
            self.ui.adminPanelBtn.setVisible(True)
        self.ui.topicsListWidget.hide()
        
        # 1. Создаем Scroll Area, чтобы можно было крутить список вниз
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True) # Это критично для адаптивности
        self.scroll_area.setStyleSheet("background: transparent; border: none;")
        
        # 2. Создаем внутренний виджет и назначаем ему FlowLayout
        self.ui.topicsListWidget.hide()
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")
        
        self.topics_container = QWidget()
        # Важно: убираем лишние QHBoxLayout с addStretch вокруг контейнера, 
        # так как теперь FlowLayout сам центрирует содержимое внутри себя.
        self.flow_layout = FlowLayout(self.topics_container, spacing=25)
        
        self.scroll_area.setWidget(self.topics_container)
        self.ui.topicsPageLayout.addWidget(self.scroll_area)

        self.setup_profile()
        self._setup_signals()
        self._load_topics()

    def _load_topics(self):
        # ... (данные те же самые)
        topics_data = [
            {"title": "🎹 Основы пианино", "progress": 0.45},
            {"title": "🎸 Гитара для новичков", "progress": 0.10},
            {"title": "🥁 Ритм и барабаны", "progress": 0.80},
            {"title": "🎤 Вокал и дыхание", "progress": 0.0},
            {"title": "🎼 Теория музыки", "progress": 0.25},
            {"title": "🎵 Импровизация", "progress": 0.05},
        ]

        while self.flow_layout.count():
            item = self.flow_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for data in topics_data:
            card = LessonCard(title=data["title"], progress=data["progress"])
            
            # Подключаем клик по ВСЕЙ карточке
            card.clicked.connect(self.on_topic_selected_by_name)
            
            self.flow_layout.addWidget(card)

    def on_topic_selected_by_name(self, topic_name):
        print(f"Выбрана тема: {topic_name}")

    def _setup_signals(self):
        self.ui.cardPlayBtn.clicked.connect(self.show_topics)
        self.ui.backBtn.clicked.connect(self.show_home)
        self.ui.logoutBtn.clicked.connect(self.logout)

    def show_topics(self):
        self.ui.stackedWidget.setCurrentWidget(self.ui.topicsPageWidget)

    def show_home(self):
        self.ui.stackedWidget.setCurrentWidget(self.ui.homePageWidget)

    def logout(self):
        reply = QMessageBox.question(self, "Выход", "Вы уверены?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.close()

    def setup_profile(self):
        if self.ui.userNameLabel: # Например, лейбл для имени пользователя
            self.ui.userNameLabel.setText(self.user_data.get("username", "Гость"))
            
        if self.ui.emailLabel: # Например, лейбл для почты
            self.ui.emailLabel.setText(self.user_data.get("email", "Не привязана"))

    def logout(self):
        """Обработчик нажатия на кнопку 'Выйти'"""
        
        # 1. Удаляем токен из QSettings
        settings.remove("token")
        
        # 2. Локальный импорт, чтобы избежать циклической зависимости
        from controllers.auth import Auth
        
        # 3. Создаем и показываем окно авторизации
        self.auth_window = Auth()
        self.close()
        self.auth_window.show()