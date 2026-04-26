import re

from PyQt6.QtCore import QRegularExpression, QObject
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtWidgets import QMessageBox

from config import NORMAL_STYLE, ERROR_STYLE
from loader import settings


class ProfileController(QObject):
    def __init__(self, ui, user_data, auth_worker, progress_worker):
        super().__init__()
        self.ui = ui
        self.user_data = user_data
        self.auth_worker = auth_worker
        self.progress_worker = progress_worker
        self.errors = {}

        self.setup_profile()
        self.setup_profile_validation()
        self.fill_profile_data()
        self._set_profile_stats_defaults()

        self.ui.saveProfileBtn.clicked.connect(self.on_save_profile)
        self.auth_worker.update_finished_signal.connect(self.on_update_success)
        self.auth_worker.error_occurred_signal.connect(self.on_update_error)
        self.progress_worker.profile_stats_loaded_signal.connect(self.on_profile_stats_loaded)

        self.load_profile_stats()

    def setup_profile(self):
        if self.ui.userNameLabel:
            self.ui.userNameLabel.setText(self.user_data.get("username", "Гость"))
        if self.ui.emailLabel:
            self.ui.emailLabel.setText(self.user_data.get("email", "Не привязана"))

    def setup_profile_validation(self):
        email_re = QRegularExpression(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        self.ui.emailEdit.setValidator(QRegularExpressionValidator(email_re, self.ui.centralwidget))

        username_re = QRegularExpression(r'^[a-zA-Z0-9_]{3,20}$')
        self.ui.usernameEdit.setValidator(QRegularExpressionValidator(username_re, self.ui.centralwidget))

        self.ui.usernameEdit.textChanged.connect(self.validate_username)
        self.ui.emailEdit.textChanged.connect(self.validate_email)
        self.ui.passwordEdit.textChanged.connect(self.validate_password)
        self.ui.confirmPasswordEdit.textChanged.connect(self.validate_confirm)

    def fill_profile_data(self):
        self.ui.usernameEdit.setText(self.user_data.get("username", ""))
        self.ui.emailEdit.setText(self.user_data.get("email", ""))
        for edit in [self.ui.usernameEdit, self.ui.emailEdit, self.ui.passwordEdit, self.ui.confirmPasswordEdit]:
            edit.setStyleSheet(NORMAL_STYLE)

    def load_profile_stats(self):
        self.progress_worker.get_profile_stats()

    def _set_profile_stats_defaults(self):
        self.ui.profileLessonsValue.setText("0")
        self.ui.profileStartedTopicsValue.setText("0")
        self.ui.profileCompletedTopicsValue.setText("0")
        self.ui.profileAverageValue.setText("0%")
        self.ui.profileRatingValue.setText("—")

    def on_profile_stats_loaded(self, stats):
        self.ui.profileLessonsValue.setText(str(stats.completed_lessons_count))
        self.ui.profileStartedTopicsValue.setText(str(stats.started_topics_count))
        self.ui.profileCompletedTopicsValue.setText(str(stats.completed_topics_count))
        self.ui.profileAverageValue.setText(f"{stats.average_progress_percent:.1f}%")
        self.ui.profileRatingValue.setText(f"{stats.rating_place} из {stats.total_users}")

    def show_error(self, field, message, edit_widget, label_widget):
        self.errors[field] = message
        edit_widget.setStyleSheet(ERROR_STYLE)
        label_widget.setText(message)

    def clear_error(self, field, edit_widget, label_widget):
        self.errors.pop(field, None)
        edit_widget.setStyleSheet(NORMAL_STYLE)
        label_widget.setText("")

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
        if not val:
            return True

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
        if self.validate_username() and self.validate_email() and self.validate_password() and self.validate_confirm():
            token = settings.value("token")
            update_payload = {
                "username": self.ui.usernameEdit.text().strip(),
                "email": self.ui.emailEdit.text().strip(),
            }

            new_pwd = self.ui.passwordEdit.text()
            if new_pwd:
                update_payload["password"] = new_pwd

            self.auth_worker.update_profile(token, update_payload)

    def on_update_success(self, new_user_data):
        QMessageBox.information(self.ui.centralwidget, "Профиль", "Данные успешно обновлены!")
        self.user_data.update(new_user_data)
        self.setup_profile()
        self.fill_profile_data()
        self.ui.passwordEdit.clear()
        self.ui.confirmPasswordEdit.clear()

    def on_update_error(self, message):
        QMessageBox.warning(self.ui.centralwidget, "Ошибка", f"Не удалось обновить профиль: {message}")
