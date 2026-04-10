from PyQt6.QtWidgets import QMainWindow, QMessageBox, QWidget, QScrollArea
from loader import settings
from GUI.main_window import Ui_MainWindow
from GUI.LessonCard import LessonCard
from GUI.helpful import FlowLayout
from workers.auth_worker import AuthWorker

# Импорт наших новых контроллеров!
from controllers.admin import AdminController
from controllers.profile import ProfileController

class Main(QMainWindow):
    def __init__(self, user_data: dict):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.user_data = user_data
        self.auth_worker = AuthWorker()
        
        # Настройка доступа к админке
        self.ui.adminPanelBtn.setVisible(False) 
        user_role = self.user_data.get("role", "пользователь") 
        if user_role == "администратор": 
            self.ui.adminPanelBtn.setVisible(True)

        # Настройка страницы с темами (FlowLayout и ScrollArea)
        self.ui.topicsListWidget.hide()
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")
        self.topics_container = QWidget()
        self.flow_layout = FlowLayout(self.topics_container, spacing=25)
        self.scroll_area.setWidget(self.topics_container)
        self.ui.topicsPageLayout.addWidget(self.scroll_area)
        
        # --- ИНИЦИАЛИЗАЦИЯ КОНТРОЛЛЕРОВ ---
        self.admin_controller = AdminController(self.ui)
        self.profile_controller = ProfileController(self.ui, self.user_data, self.auth_worker)
        
        self._setup_signals()
        self._load_topics()
        self.show_home()

    def _load_topics(self):
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
            card.clicked.connect(self.on_topic_selected_by_name)
            self.flow_layout.addWidget(card)

    def on_topic_selected_by_name(self, topic_name):
        print(f"Выбрана тема: {topic_name}")

    def _setup_signals(self):
        # Только навигация и выход (остальные кнопки забрали контроллеры)
        self.ui.homeBtn.clicked.connect(self.show_home)
        self.ui.profileBtn.clicked.connect(self.show_profile)
        self.ui.adminPanelBtn.clicked.connect(self.show_admin_panel)
        self.ui.logoutBtn.clicked.connect(self.logout)
        
        self.ui.cardPlayBtn.clicked.connect(self.show_topics)
        self.ui.backBtn.clicked.connect(self.show_home)

    def _set_active_tab(self, button, widget):
        self.ui.stackedWidget.setCurrentWidget(widget)
        nav_buttons = [self.ui.homeBtn, self.ui.profileBtn, self.ui.settingsBtn, self.ui.adminPanelBtn]
        for btn in nav_buttons:
            is_active = (btn == button)
            btn.setProperty("active", is_active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def show_home(self):
        self._set_active_tab(self.ui.homeBtn, self.ui.homePageWidget)

    def show_profile(self):
        self._set_active_tab(self.ui.profileBtn, self.ui.profilePageWidget)

    def show_admin_panel(self):
        self._set_active_tab(self.ui.adminPanelBtn, self.ui.adminPageWidget)

    def show_topics(self):
        self.ui.stackedWidget.setCurrentWidget(self.ui.topicsPageWidget)

    def logout(self):
        reply = QMessageBox.question(self, "Выход", "Вы уверены?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            settings.remove("token")
            from controllers.auth import Auth
            self.auth_window = Auth()
            self.close()
            self.auth_window.show()