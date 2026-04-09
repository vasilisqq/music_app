from PyQt6.QtWidgets import QMainWindow, QMessageBox, QListWidgetItem
from loader import settings
from GUI.main_window import Ui_MainWindow
from GUI.LessonCard import LessonCard

class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        # home_layout = self.ui.homePageLayout
        # card1 = LessonCard("Аккорды для начинающих", progress=0.45)
        # card1.play_btn.clicked.connect(lambda: self.start_lesson("chords"))

        # card2 = LessonCard("Ритм и темп", progress=0.80)
        # card2.play_btn.clicked.connect(lambda: self.start_lesson("rhythm"))

        # card3 = LessonCard("Игра по нотам", progress=0.20)
        # card3.play_btn.clicked.connect(lambda: self.start_lesson("notes"))

        # home_layout.addWidget(card1)
        # home_layout.addWidget(card2)
        # home_layout.addWidget(card3)
        # Вызываем метод заполнения профиля
        self.setup_profile()
        
        # Подключаем события
        self._setup_signals()
        
        # Загружаем доступные темы
        self._load_topics()

    def _setup_signals(self):
        """Подключаем кнопки к методам"""
        self.ui.cardPlayBtn.clicked.connect(self.show_topics)
        self.ui.backBtn.clicked.connect(self.show_home)
        self.ui.logoutBtn.clicked.connect(self.logout)

    def _load_topics(self):
        """Загружаем список доступных тем в QListWidget"""
        # Пример тем — замени на реальные данные из API или БД
        topics = [
            "🎹 Основы пианино",
            "🎸 Гитара для новичков",
            "🥁 Ритм и основы барабанов",
            "🎤 Вокал и дыхание",
            "🎼 Музыкальная теория",
            "🎵 Импровизация",
        ]
        
        self.ui.topicsListWidget.clear()
        for topic in topics:
            item = QListWidgetItem(topic)
            self.ui.topicsListWidget.addItem(item)
        
        # Подключаем выбор темы
        self.ui.topicsListWidget.itemClicked.connect(self.on_topic_selected)

    def show_topics(self):
        """Показать страницу с темами"""
        self.ui.stackedWidget.setCurrentWidget(self.ui.topicsPageWidget)

    def show_home(self):
        """Вернуться на главную страницу"""
        self.ui.stackedWidget.setCurrentWidget(self.ui.homePageWidget)
        self.ui.topicsListWidget.clearSelection()

    def on_topic_selected(self, item):
        """Обработка выбора темы"""
        topic_name = item.text()
        print(f"Выбрана тема: {topic_name}")
        # Здесь можно запустить урок по выбранной теме
        # Например: self.start_lesson(topic_name)

    def logout(self):
        """Выход из приложения"""
        reply = QMessageBox.question(
            self,
            "Выход",
            "Вы уверены, что хотите выйти?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.close()

    def setup_profile(self):
        """Читаем данные из кэша и обновляем интерфейс"""
        # Достаем сохраненные значения (второй аргумент - заглушка на случай, если данных нет)
        username = settings.value("username", "👤 Гость")
        email = settings.value("email", "no-reply@example.com")
        
        # Устанавливаем текст в твои лейблы
        self.ui.userNameLabel.setText(f"👤 {username}")
        self.ui.emailLabel.setText(email)