from PyQt6.QtWidgets import QMainWindow, QMessageBox, QWidget, QGridLayout, QHBoxLayout
from PyQt6.QtCore import Qt
from loader import settings
from GUI.main_window import Ui_MainWindow
from GUI.LessonCard import LessonCard
from GUI.helpful import FlowLayout
import re
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QWidget, QHBoxLayout, QScrollArea
from GUI.main_window import Ui_MainWindow
from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator
from workers.auth_worker import AuthWorker

# Импортируем стили для единообразия (можно вынести в отдельный файл constants.py)
NORMAL_STYLE = """
QLineEdit { 
    padding: 15px 20px; border: 2px solid #eee; border-radius: 15px; font-size: 16px; 
    background: rgba(255,255,255,0.95); color: #333; 
}
QLineEdit:focus { 
    background: rgba(255,255,255,1); border: 3px solid #3f8bde; 
    padding: 14px 19px; 
}
"""

ERROR_STYLE = """
QLineEdit { 
    padding: 15px 20px; border: 3px solid #ff4444; border-radius: 15px; 
    font-size: 16px; background: rgba(255,220,220,0.95); color: #333; 
}
"""


class Main(QMainWindow):
    def __init__(self, user_data: dict):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.adminPanelBtn.setVisible(False) 
        self.user_data = user_data
        self.auth_worker = AuthWorker()
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
        self.errors = {}
        self.setup_profile()
        self._setup_signals()
        self._load_topics()
        self.show_home()
        self.setup_profile_validation()
        self.fill_profile_data()

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
        # Кнопки бокового меню
        self.ui.homeBtn.clicked.connect(self.show_home)
        self.ui.profileBtn.clicked.connect(self.show_profile)
        self.ui.logoutBtn.clicked.connect(self.logout)
        self.ui.saveProfileBtn.clicked.connect(self.on_save_profile)
        # Кнопки навигации внутри страниц
        self.ui.cardPlayBtn.clicked.connect(self.show_topics)
        self.ui.backBtn.clicked.connect(self.show_home)

        self.auth_worker.update_finished_signal.connect(self.on_update_success)
        self.auth_worker.error_occurred_signal.connect(self.on_update_error)

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

    def _set_active_tab(self, button, widget):
        """Переключает страницу и визуально выделяет активную кнопку"""
        # 1. Меняем страницу в StackedWidget
        self.ui.stackedWidget.setCurrentWidget(widget)
        
        # 2. Список всех кнопок навигации, которые могут быть активными
        nav_buttons = [self.ui.homeBtn, self.ui.profileBtn, self.ui.settingsBtn, self.ui.adminPanelBtn]
        
        for btn in nav_buttons:
            # Устанавливаем свойство active (True для нажатой, False для остальных)
            is_active = (btn == button)
            btn.setProperty("active", is_active)
            
            # Принудительно обновляем стиль (нужно для корректной работы динамических свойств)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def show_home(self):
        self._set_active_tab(self.ui.homeBtn, self.ui.homePageWidget)

    def show_profile(self):
        # Метод для отображения новой вкладки профиля
        self._set_active_tab(self.ui.profileBtn, self.ui.profilePageWidget)

    def show_topics(self):
        # При просмотре тем оставляем активной кнопку 'Главная'
        self.ui.stackedWidget.setCurrentWidget(self.ui.topicsPageWidget)

    def setup_profile_validation(self):
        """Настройка валидаторов как в Auth контроллере"""
        # Валидатор Email
        email_re = QRegularExpression(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        self.ui.emailEdit.setValidator(QRegularExpressionValidator(email_re, self))
        
        # Валидатор Логина
        username_re = QRegularExpression(r'^[a-zA-Z0-9_]{3,20}$')
        self.ui.usernameEdit.setValidator(QRegularExpressionValidator(username_re, self))

        # Подключаем проверку "на лету"
        self.ui.usernameEdit.textChanged.connect(self.validate_username)
        self.ui.emailEdit.textChanged.connect(self.validate_email)
        self.ui.passwordEdit.textChanged.connect(self.validate_password)
        self.ui.confirmPasswordEdit.textChanged.connect(self.validate_confirm)

    def fill_profile_data(self):
        self.ui.usernameEdit.setText(self.user_data.get("username", ""))
        self.ui.emailEdit.setText(self.user_data.get("email", ""))
        # Очищаем стили при загрузке
        for edit in [self.ui.usernameEdit, self.ui.emailEdit, self.ui.passwordEdit, self.ui.confirmPasswordEdit]:
            edit.setStyleSheet(NORMAL_STYLE)

    def show_error(self, field, message, edit_widget, label_widget):
        self.errors[field] = message
        edit_widget.setStyleSheet(ERROR_STYLE)
        label_widget.setText(message)

    def clear_error(self, field, edit_widget, label_widget):
        self.errors.pop(field, None)
        edit_widget.setStyleSheet(NORMAL_STYLE)
        label_widget.setText("")

    # --- Методы валидации (адаптировано из auth.py) ---

    def validate_username(self):
        val = self.ui.usernameEdit.text().strip()
        self.clear_error('username', self.ui.usernameEdit, self.ui.usernameErrors)
        if not val:
            self.show_error('username', 'Логин обязателен', self.ui.usernameEdit, self.ui.usernameErrors)
            return False
        if len(val) < 3:
            self.show_error('username', 'Минимум 3 символа', self.ui.usernameEdit, self.ui.usernameErrors)
            return False
        return True

    def validate_email(self):
        val = self.ui.emailEdit.text().strip()
        self.clear_error('email', self.ui.emailEdit, self.ui.emailErrors)
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', val):
            self.show_error('email', 'Неверный формат email', self.ui.emailEdit, self.ui.emailErrors)
            return False
        return True

    def validate_password(self):
        val = self.ui.passwordEdit.text()
        self.clear_error('password', self.ui.passwordEdit, self.ui.passwordErrors)
        if not val: return True # Пароль не обязателен при редактировании
        
        if len(val) < 6:
            self.show_error('password', 'Минимум 6 символов', self.ui.passwordEdit, self.ui.passwordErrors)
            return False
        if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)', val):
            self.show_error('password', 'Нужна 1 заглавная, 1 строчная и цифра', self.ui.passwordEdit, self.ui.passwordErrors)
            return False
        return True

    def validate_confirm(self):
        p = self.ui.passwordEdit.text()
        c = self.ui.confirmPasswordEdit.text()
        self.clear_error('confirm', self.ui.confirmPasswordEdit, self.ui.confirmErrors)
        if p != c:
            self.show_error('confirm', 'Пароли не совпадают', self.ui.confirmPasswordEdit, self.ui.confirmErrors)
            return False
        return True

    def on_save_profile(self):
        """Сбор данных и отправка запроса к API"""
        if self.validate_username() and self.validate_email() and \
           self.validate_password() and self.validate_confirm():
            
            token = settings.value("token")
            update_payload = {
                "username": self.ui.usernameEdit.text().strip(),
                "email": self.ui.emailEdit.text().strip()
            }
            
            new_pwd = self.ui.passwordEdit.text()
            if new_pwd:
                update_payload["password"] = new_pwd
                
            self.auth_worker.update_profile(token, update_payload)

    def on_update_success(self, new_user_data):
        """Действия при успешном ответе от сервера"""
        QMessageBox.information(self, "Профиль", "Данные успешно обновлены!")
        
        # 1. Обновляем локальный словарь данными, которые прислал сервер
        self.user_data.update(new_user_data) 
        
        # 2. Синхронизируем боковую панель (имя и почту под иконкой)
        self.setup_profile() 
        
        # 3. Синхронизируем поля ввода на странице профиля
        self.fill_profile_data() 
        
        # 4. Очищаем поля паролей для безопасности
        self.ui.passwordEdit.clear()
        self.ui.confirmPasswordEdit.clear()

    def on_update_error(self, message):
        QMessageBox.warning(self, "Ошибка", f"Не удалось обновить профиль: {message}")