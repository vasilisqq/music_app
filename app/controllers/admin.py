from PyQt6.QtWidgets import (
    QMessageBox, QTableWidgetItem, QAbstractItemView,
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTextEdit, QPushButton, QMenu, QComboBox,
    QFrame, QWidget, QDialogButtonBox
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtCore import Qt, QRectF
from workers.topic_worker import TopicWorker
from workers.auth_worker import AuthWorker
from workers.lesson_worker import LessonWorker
from workers.admin_stats_worker import AdminStatsWorker
from schemas.topic import TopicCreate, TopicResponse
from schemas.lesson import LessonResponse, LessonUpdate
from PyQt6.QtWidgets import QHeaderView
from PyQt6.QtGui import QColor, QBrush, QPainter, QPen, QPainterPath
from controllers.creator import CreatorController


class StatsLineChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._points = []
        self.setMinimumHeight(220)

    def set_points(self, points):
        self._points = points
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(16, 16, -16, -28)
        painter.fillRect(self.rect(), QColor("#ffffff"))

        if not self._points:
            painter.setPen(QColor("#667085"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Нет данных")
            return

        max_value = max((point.completions_count for point in self._points), default=0)
        max_value = max(max_value, 1)

        painter.setPen(QPen(QColor("#dfe7f3"), 1))
        painter.drawRoundedRect(QRectF(rect), 12, 12)

        count = len(self._points)
        step_x = rect.width() / max(count - 1, 1)
        path = QPainterPath()
        label_y = rect.bottom() + 18

        coords = []
        for idx, point in enumerate(self._points):
            x = rect.left() + idx * step_x
            y = rect.bottom() - ((point.completions_count / max_value) * rect.height())
            coords.append((x, y, point))
            if idx == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)

        painter.setPen(QPen(QColor("#3f8bde"), 3))
        painter.drawPath(path)

        painter.setPen(QPen(QColor("#3f8bde"), 1))
        painter.setBrush(QColor("#3f8bde"))
        for x, y, point in coords:
            painter.drawEllipse(QRectF(x - 3, y - 3, 6, 6))

        painter.setPen(QColor("#667085"))
        tick_step = max(1, count // 6)
        for idx, (x, _y, point) in enumerate(coords):
            if idx % tick_step == 0 or idx == count - 1:
                painter.drawText(QRectF(x - 20, label_y, 40, 16), Qt.AlignmentFlag.AlignCenter, point.label)

        painter.setPen(QColor("#98a2b3"))
        painter.drawText(QRectF(rect.left(), 0, 80, 14), Qt.AlignmentFlag.AlignLeft, str(max_value))
        painter.drawText(QRectF(rect.left(), rect.bottom() - 8, 80, 14), Qt.AlignmentFlag.AlignLeft, "0")


class AddTopicDialog(QDialog):
    # Стили для обычного состояния и состояния ошибки
    DEFAULT_STYLE = "padding: 8px; font-size: 14px; border: 1px solid #ccc; border-radius: 5px; background-color: white;"
    ERROR_STYLE = "padding: 8px; font-size: 14px; border: 2px solid #ff4444; border-radius: 5px; background-color: #fff0f0;"
    ERROR_LABEL_STYLE = "color: #ff4444; font-size: 13px; margin-left: 5px;"

    def __init__(self, parent=None, topic_name="", topic_desc=""):
        super().__init__(parent)
        self.setWindowTitle("Создание новой темы" if not topic_name else "Редактирование темы")
        self.setMinimumSize(400, 330)
        
        layout = QVBoxLayout(self)
        
        # --- ПОЛЕ: Название темы ---
        layout.addWidget(QLabel("Название темы:"))
        self.name_edit = QLineEdit(topic_name)
        self.name_edit.setPlaceholderText("Введите название темы...")
        self.name_edit.setStyleSheet(self.DEFAULT_STYLE)
        layout.addWidget(self.name_edit)
        
        self.name_error_label = QLabel("")
        self.name_error_label.setStyleSheet(self.ERROR_LABEL_STYLE)
        self.name_error_label.hide()
        layout.addWidget(self.name_error_label)
        
        # --- ПОЛЕ: Описание темы ---
        layout.addWidget(QLabel("Описание темы:"))
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlainText(topic_desc)
        self.desc_edit.setPlaceholderText("Введите подробное описание темы...")
        self.desc_edit.setStyleSheet(self.DEFAULT_STYLE)
        layout.addWidget(self.desc_edit)
        
        self.desc_error_label = QLabel("")
        self.desc_error_label.setStyleSheet(self.ERROR_LABEL_STYLE)
        self.desc_error_label.hide()
        layout.addWidget(self.desc_error_label)
        
        # --- КНОПКИ ---
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Сохранить")
        self.btn_cancel = QPushButton("Отмена")
        
        self.btn_save.setStyleSheet("""
            QPushButton { background: #3f8bde; color: white; border-radius: 8px; padding: 8px 15px; font-weight: bold; }
            QPushButton:hover { background: #2968c0; }
            QPushButton:disabled { background: #a0c4eb; color: #f0f0f0; }
        """)
        self.btn_cancel.setStyleSheet("""
            QPushButton { background: #f0f0f0; color: #333; border-radius: 8px; padding: 8px 15px; font-weight: bold; border: 1px solid #ccc; }
            QPushButton:hover { background: #e0e0e0; }
        """)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)
        
        # --- СИГНАЛЫ ---
        self.btn_save.clicked.connect(self.accept) 
        self.btn_cancel.clicked.connect(self.reject)
        
        # ПОДКЛЮЧАЕМ ДИНАМИЧЕСКУЮ ВАЛИДАЦИЮ
        self.name_edit.textChanged.connect(self.validate_name_realtime)
        self.desc_edit.textChanged.connect(self.validate_desc_realtime)
        
        # Флаги, чтобы не ругаться на пустые поля сразу при открытии окна создания
        self.is_name_touched = bool(topic_name)
        self.is_desc_touched = bool(topic_desc)
        
        # Если это режим редактирования, проверим состояние кнопки
        self.update_save_button_state()

    def validate_name_realtime(self):
        """Динамическая проверка названия при вводе"""
        self.is_name_touched = True
        name_text = self.name_edit.text().strip()
        
        if not name_text:
            self.name_edit.setStyleSheet(self.ERROR_STYLE)
            self.name_error_label.setText("Название темы не может быть пустым!")
            self.name_error_label.show()
        else:
            self.name_edit.setStyleSheet(self.DEFAULT_STYLE)
            self.name_error_label.hide()
            
        self.update_save_button_state()

    def validate_desc_realtime(self):
        """Динамическая проверка описания при вводе"""
        self.is_desc_touched = True
        desc_text = self.desc_edit.toPlainText().strip()
        
        if not desc_text:
            self.desc_edit.setStyleSheet(self.ERROR_STYLE)
            self.desc_error_label.setText("Описание темы не может быть пустым!")
            self.desc_error_label.show()
        else:
            self.desc_edit.setStyleSheet(self.DEFAULT_STYLE)
            self.desc_error_label.hide()
            
        self.update_save_button_state()

    def update_save_button_state(self):
        """Блокирует кнопку Сохранить, если есть ошибки"""
        name_valid = bool(self.name_edit.text().strip())
        desc_valid = bool(self.desc_edit.toPlainText().strip())
        
        # Кнопка активна только если оба поля заполнены
        self.btn_save.setEnabled(name_valid and desc_valid)

    def get_data(self):
        return self.name_edit.text().strip(), self.desc_edit.toPlainText().strip()

class ChangeLessonTopicDialog(QDialog):
    def __init__(self, parent, topics: list[tuple[int, str]], current_topic_id: int | None = None):
        super().__init__(parent)
        self.setWindowTitle("Сменить тему урока")
        self.setMinimumSize(420, 160)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Выберите новую тему:"))

        self.topic_combo = QComboBox()
        for topic_id, topic_name in topics:
            self.topic_combo.addItem(topic_name, topic_id)

        if current_topic_id is not None:
            idx = self.topic_combo.findData(current_topic_id)
            if idx != -1:
                self.topic_combo.setCurrentIndex(idx)

        layout.addWidget(self.topic_combo)

        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Отмена")
        self.btn_apply = QPushButton("Сменить")

        self.btn_apply.setStyleSheet(
            "QPushButton { background: #3f8bde; color: white; border-radius: 8px; padding: 8px 15px; font-weight: bold; }"
            "QPushButton:hover { background: #2968c0; }"
        )
        self.btn_cancel.setStyleSheet(
            "QPushButton { background: #f0f0f0; color: #333; border-radius: 8px; padding: 8px 15px; font-weight: bold; border: 1px solid #ccc; }"
            "QPushButton:hover { background: #e0e0e0; }"
        )

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_apply)
        layout.addLayout(btn_layout)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_apply.clicked.connect(self.accept)

    def get_selected_topic_id(self) -> int:
        return int(self.topic_combo.currentData())


class EditUserDialog(QDialog):
    save_requested = pyqtSignal(str, str)
    # Стили для обычного состояния и состояния ошибки
    DEFAULT_STYLE = "padding: 8px; font-size: 14px; border: 1px solid #ccc; border-radius: 5px; background-color: white;"
    ERROR_STYLE = "padding: 8px; font-size: 14px; border: 2px solid #ff4444; border-radius: 5px; background-color: #fff0f0;"
    ERROR_LABEL_STYLE = "color: #ff4444; font-size: 13px; margin-left: 5px;"

    def __init__(self, parent=None, username="", email=""):
        super().__init__(parent)
        self.setWindowTitle("Редактирование пользователя")
        self.setMinimumSize(350, 250)
        layout = QVBoxLayout(self)

        # --- ПОЛЕ: Логин ---
        layout.addWidget(QLabel("Логин:"))
        self.username_edit = QLineEdit(username)
        self.username_edit.setStyleSheet(self.DEFAULT_STYLE)
        layout.addWidget(self.username_edit)
        
        self.username_error = QLabel("")
        self.username_error.setStyleSheet(self.ERROR_LABEL_STYLE)
        self.username_error.hide()
        layout.addWidget(self.username_error)

        # --- ПОЛЕ: Email ---
        layout.addWidget(QLabel("Email:"))
        self.email_edit = QLineEdit(email)
        self.email_edit.setStyleSheet(self.DEFAULT_STYLE)
        layout.addWidget(self.email_edit)
        
        self.email_error = QLabel("")
        self.email_error.setStyleSheet(self.ERROR_LABEL_STYLE)
        self.email_error.hide()
        layout.addWidget(self.email_error)

        # --- КНОПКИ ---
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Сохранить")
        self.btn_cancel = QPushButton("Отмена")
        
        self.btn_save.setStyleSheet("""
            QPushButton { background: #3f8bde; color: white; border-radius: 8px; padding: 8px 15px; font-weight: bold; }
            QPushButton:hover { background: #2968c0; }
            QPushButton:disabled { background: #a0c4eb; color: #f0f0f0; }
        """)
        self.btn_cancel.setStyleSheet("""
            QPushButton { background: #f0f0f0; color: #333; border-radius: 8px; padding: 8px 15px; font-weight: bold; border: 1px solid #ccc; }
            QPushButton:hover { background: #e0e0e0; }
        """)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

        # Сигналы
        self.btn_save.clicked.connect(self.handle_save_click)
        self.btn_cancel.clicked.connect(self.reject)
        
        self.username_edit.textChanged.connect(self.validate_fields)
        self.email_edit.textChanged.connect(self.validate_fields)

    def validate_fields(self):
        """Динамическая проверка полей на пустоту"""
        is_valid = True
        
        # Проверка логина
        if not self.username_edit.text().strip():
            self.username_edit.setStyleSheet(self.ERROR_STYLE)
            self.username_error.setText("Логин не может быть пустым!")
            self.username_error.show()
            is_valid = False
        else:
            self.username_edit.setStyleSheet(self.DEFAULT_STYLE)
            self.username_error.hide()

        # Проверка email
        if not self.email_edit.text().strip():
            self.email_edit.setStyleSheet(self.ERROR_STYLE)
            self.email_error.setText("Email не может быть пустым!")
            self.email_error.show()
            is_valid = False
        else:
            self.email_edit.setStyleSheet(self.DEFAULT_STYLE)
            self.email_error.hide()
            
        self.btn_save.setEnabled(is_valid)

    def get_data(self):
        return self.username_edit.text().strip(), self.email_edit.text().strip()
    
    def handle_save_click(self):
        """Метод вызывается при нажатии Сохранить, но НЕ закрывает окно"""
        username, email = self.get_data()
        self.btn_save.setEnabled(False) # Блокируем кнопку на время запроса
        self.btn_save.setText("Сохранение...")
        self.save_requested.emit(username, email)

    # Метод для ручного закрытия окна из контроллера
    def close_success(self):
        self.accept()



class AdminController:
    def __init__(self, ui):
        self.ui = ui
        self.creator_window = None
        self.selected_topic_id = None
        self.ui.table_topics.itemSelectionChanged.connect(self._toggle_lesson_btn)
        self.ui.btn_add_lesson.clicked.connect(self.on_add_lesson_clicked)
        table_style = """
            QTableWidget {
                background-color: white; border: 1px solid #e0e0e0; border-radius: 10px;
                gridline-color: #f5f5f5; selection-background-color: rgba(63, 139, 222, 0.2);
                selection-color: #1a1a1a; font-size: 15px;
            }
            QHeaderView::section {
                background-color: #f8f9fa; color: #333333; font-weight: bold;
                padding: 12px; border: none; border-bottom: 2px solid #dcdcdc;
            }
            QTableWidget::item { padding: 8px; border-bottom: 1px solid #f5f5f5; }
        """
        self.ui.table_topics.setStyleSheet(table_style)
        self.ui.table_lessons.setStyleSheet(table_style)
        self.ui.table_topics.verticalHeader().setVisible(False) # Убираем номера строк слева
        
        # --- СТИЛИ ДЛЯ КНОПОК ---
        button_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3f8bde, stop:1 #2968c0);
                border-radius: 15px; color: white; font-size: 16px; font-weight: bold;
                padding: 10px 20px; border: none;
            }
            QPushButton:hover { background: #2968c0; }
            QPushButton:pressed { background: #1f4a8a; }
            QPushButton:disabled { background: #a0c4eb; color: #f0f0f0; }
        """
        self.ui.btn_add_topic.setStyleSheet(button_style)
        self.ui.btn_add_lesson.setStyleSheet(button_style)


        self.worker = TopicWorker()
        self.auth_worker = AuthWorker()
        self.lesson_worker = LessonWorker()
        self.stats_worker = AdminStatsWorker()
        self.stats_chart = StatsLineChart(self.ui.statsChartPlaceholder)
        self._current_stats_period = 30
        # Сигналы
        self.ui.btn_add_topic.clicked.connect(self.show_add_topic_dialog)
        self.worker.topics_loaded_signal.connect(self.on_topics_loaded)
        self.worker.topic_added_signal.connect(self.on_topic_added)
        self.worker.topic_updated_signal.connect(self.on_topic_updated)
        self.worker.topic_deleted_signal.connect(self.on_topic_deleted)
        self.worker.error_signal.connect(self.show_error)
        self.auth_worker.users_loaded_signal.connect(self.on_users_loaded)
        self.auth_worker.user_status_updated_signal.connect(self.on_user_status_updated)
        self.auth_worker.user_edited_signal.connect(self.on_user_edited) # НОВЫЙ СИГНАЛ
        self.auth_worker.error_occurred_signal.connect(self.show_error)
        self.ui.table_topics.cellClicked.connect(self.on_topic_selected)
        self.lesson_worker.lessons_by_topic_loaded_signal.connect(self.on_lessons_loaded)
        self.lesson_worker.lesson_deleted_signal.connect(self.on_lesson_deleted)
        self.lesson_worker.lesson_updated_signal.connect(self.on_lesson_topic_changed)
        self.lesson_worker.lesson_error_sygnal.connect(self.show_error)
        self.stats_worker.stats_loaded_signal.connect(self.on_stats_loaded)
        self.stats_worker.error_signal.connect(self.show_error)
        self.ui.statsRefreshBtn.clicked.connect(self.refresh_stats)
        self.ui.statsPeriodCombo.currentIndexChanged.connect(self._on_stats_period_changed)

        self._pending_lesson_topic_change_to: int | None = None
        self.setup_admin_panel()
        self.setup_users_table()
        self.setup_stats_tab()

        # Загружаем пользователей
        self.auth_worker.get_all_users()
        self.refresh_stats()
        
    def _toggle_lesson_btn(self):
        # Активируем кнопку "Добавить урок", если в таблице тем что-то выбрано
        has_selection = len(self.ui.table_topics.selectedItems()) > 0
        self.ui.btn_add_lesson.setEnabled(has_selection)

    def on_add_lesson_clicked(self):
        # 1. Получаем ID выбранной темы из таблицы
        selected_row = self.ui.table_topics.currentRow()
        if selected_row == -1:
            return

        # Берем текст из 0-й колонки (ID)
        topic_id = self.ui.table_topics.item(selected_row, 0).text()

        # 2. Показываем диалог выбора ритма и руки
        dialog = TimeSignatureDialog()
        if dialog.exec():
            selected_signature = dialog.get_signature()
            selected_hand = dialog.get_hand()
            # 3. Передаем ритм, ID темы и руку
            self.open_creator(selected_signature, topic_id, hand=selected_hand)

    def open_creator(self, time_signature: str, topic_id: str, lesson: LessonResponse | None = None, hand: str = "right"):
        self.ui.drawerWidget.hide()

        self.creator_page = CreatorController(time_signature, topic_id, lesson, hand=hand)
        self.creator_page.lesson_created.connect(self.on_lesson_created)
        self.creator_page.lesson_updated.connect(self.on_lesson_updated)

        self.ui.stackedWidget.addWidget(self.creator_page)
        self.ui.stackedWidget.setCurrentWidget(self.creator_page)
        self.creator_page.ui.exit_button.clicked.connect(self.close_creator)

    def refresh_lessons(self, topic_id: int):
        self.ui.table_lessons.setRowCount(0)
        self.lesson_worker.get_lessons_by_topic(topic_id)

    def get_selected_lesson(self, row: int) -> LessonResponse:
        lesson_id = int(self.ui.table_lessons.item(row, 0).text())
        lesson_name = self.ui.table_lessons.item(row, 1).text()
        lesson_item = self.ui.table_lessons.item(row, 1)
        lesson_description = lesson_item.data(Qt.ItemDataRole.UserRole) or ""
        lesson_difficult = lesson_item.data(Qt.ItemDataRole.UserRole + 1)
        lesson_rhythm = lesson_item.data(Qt.ItemDataRole.UserRole + 2)
        lesson_notes = lesson_item.data(Qt.ItemDataRole.UserRole + 3)
        lesson_topic = lesson_item.data(Qt.ItemDataRole.UserRole + 4)
        return LessonResponse(
            id=lesson_id,
            name=lesson_name,
            description=lesson_description,
            difficult=lesson_difficult,
            rhythm=lesson_rhythm,
            notes=lesson_notes,
            topic=lesson_topic,
        )

    def show_lesson_context_menu(self, pos):
        item = self.ui.table_lessons.itemAt(pos)
        if item is None:
            return

        row = item.row()
        menu = QMenu(self.ui.centralwidget)
        edit_action = menu.addAction("✏️ Изменить")
        change_topic_action = menu.addAction("📚 Сменить тему…")
        delete_action = menu.addAction("🗑️ Удалить")
        action = menu.exec(self.ui.table_lessons.viewport().mapToGlobal(pos))

        if action == edit_action:
            self.edit_lesson(row)
        elif action == change_topic_action:
            self.change_lesson_topic(row)
        elif action == delete_action:
            self.confirm_and_delete_lesson(row)

    def edit_lesson(self, row: int):
        lesson = self.get_selected_lesson(row)
        time_signature = f"{int(float(lesson.rhythm) * 4)}/4"
        hand = getattr(lesson, 'hand', 'right')
        self.open_creator(time_signature, str(lesson.topic), lesson, hand=hand)

    def _get_topics_from_table(self) -> list[tuple[int, str]]:
        topics: list[tuple[int, str]] = []
        for row in range(self.ui.table_topics.rowCount()):
            id_item = self.ui.table_topics.item(row, 0)
            name_item = self.ui.table_topics.item(row, 1)
            if id_item is None or name_item is None:
                continue
            try:
                topic_id = int(id_item.text())
            except ValueError:
                continue
            topic_name = name_item.text()
            topics.append((topic_id, topic_name))
        return topics

    def change_lesson_topic(self, row: int):
        lesson = self.get_selected_lesson(row)
        topics = self._get_topics_from_table()
        if not topics:
            QMessageBox.warning(self.ui.centralwidget, "Ошибка", "Список тем пуст.")
            return

        dialog = ChangeLessonTopicDialog(self.ui.centralwidget, topics, current_topic_id=lesson.topic)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        new_topic_id = dialog.get_selected_topic_id()
        if new_topic_id == lesson.topic:
            return

        self._pending_lesson_topic_change_to = new_topic_id
        lesson_update = LessonUpdate(
            name=lesson.name,
            description=lesson.description,
            difficult=lesson.difficult,
            rhythm=float(lesson.rhythm),
            notes=lesson.notes,
            topic=new_topic_id,
        )
        self.lesson_worker.update_lesson(lesson.id, lesson_update)

    def on_lesson_topic_changed(self, lesson: LessonResponse):
        if self._pending_lesson_topic_change_to is None:
            return

        new_topic_id = self._pending_lesson_topic_change_to
        self._pending_lesson_topic_change_to = None

        self.selected_topic_id = new_topic_id
        self.refresh_lessons(new_topic_id)
        self.fetch_topics()

        QMessageBox.information(self.ui.centralwidget, "Успех", "Тема урока изменена.")

    def confirm_and_delete_lesson(self, row: int):
        lesson = self.get_selected_lesson(row)
        reply = QMessageBox.question(
            self.ui.centralwidget,
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить урок <b>«{lesson.name}»</b>?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.lesson_worker.delete_lesson(lesson.id)

    def on_lesson_deleted(self, lesson_id: int):
        if self.selected_topic_id is not None:
            self.refresh_lessons(self.selected_topic_id)
        self.fetch_topics()
        QMessageBox.information(self.ui.centralwidget, "Успех", "Урок успешно удален.")

    def close_creator(self):
        self.ui.drawerWidget.show()
        self.ui.stackedWidget.setCurrentWidget(self.ui.adminPageWidget)
        self.ui.stackedWidget.removeWidget(self.creator_page)
        self.creator_page.deleteLater()
        self.creator_page = None

    def setup_admin_panel(self):
        table_style = self.ui.table_topics.styleSheet()
        self.ui.table_lessons.setStyleSheet(table_style)

        l_header = self.ui.table_lessons.horizontalHeader()
        l_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        l_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.ui.table_lessons.verticalHeader().setVisible(False)
        self.ui.table_lessons.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.ui.table_lessons.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ui.table_lessons.customContextMenuRequested.connect(self.show_lesson_context_menu)
        self.ui.table_lessons.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        header = self.ui.table_topics.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table = self.ui.table_topics
        self.ui.table_topics.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(self.show_context_menu)
        table.setSelectionBehavior(table.SelectionBehavior.SelectRows)
        table.setEditTriggers(table.EditTrigger.NoEditTriggers)
        self.fetch_topics()

    def setup_stats_tab(self):
        self.ui.statsPeriodCombo.clear()
        self.ui.statsPeriodCombo.addItem("7 дней", 7)
        self.ui.statsPeriodCombo.addItem("30 дней", 30)
        self.ui.statsPeriodCombo.addItem("90 дней", 90)
        idx = self.ui.statsPeriodCombo.findData(30)
        if idx != -1:
            self.ui.statsPeriodCombo.setCurrentIndex(idx)

        button_style = self.ui.btn_add_topic.styleSheet()
        self.ui.statsRefreshBtn.setStyleSheet(button_style)

        card_frames = [
            self.ui.statsCardCourses,
            self.ui.statsCardLessons,
            self.ui.statsCardUsers,
            self.ui.statsCardActiveUsers,
            self.ui.statsCardCompletions,
            self.ui.statsCardAvgProgress,
            self.ui.statsCardCompletedCourses,
        ]
        for frame in card_frames:
            frame.setStyleSheet(
                "QFrame { background: #f8fbff; border: 1px solid rgba(63, 139, 222, 0.18); border-radius: 16px; }"
                "QLabel { background: transparent; }"
            )

        value_labels = [
            self.ui.statsCoursesValue,
            self.ui.statsLessonsValue,
            self.ui.statsUsersValue,
            self.ui.statsActiveUsersValue,
            self.ui.statsCompletionsValue,
            self.ui.statsAvgProgressValue,
            self.ui.statsCompletedCoursesValue,
        ]
        title_labels = [
            self.ui.statsCoursesTitle,
            self.ui.statsLessonsTitle,
            self.ui.statsUsersTitle,
            self.ui.statsActiveUsersTitle,
            self.ui.statsCompletionsTitle,
            self.ui.statsAvgProgressTitle,
            self.ui.statsCompletedCoursesTitle,
            self.ui.statsPopularityTitle,
            self.ui.statsProgressTitle,
            self.ui.statsChartTitle,
        ]
        for label in title_labels:
            label.setStyleSheet("color: #667085; font-size: 13px; font-weight: 600;")
        for label in value_labels:
            label.setStyleSheet("color: #1d2939; font-size: 28px; font-weight: 800;")

        chart_layout = QVBoxLayout(self.ui.statsChartPlaceholder)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        chart_layout.addWidget(self.stats_chart)
        self.ui.statsChartFrame.setStyleSheet(
            "QFrame { background: #ffffff; border: 1px solid #e4e7ec; border-radius: 16px; }"
        )

        self.ui.table_stats_popularity.setStyleSheet(self.ui.table_topics.styleSheet())
        self.ui.table_stats_progress.setStyleSheet(self.ui.table_topics.styleSheet())
        self.ui.table_stats_popularity.verticalHeader().setVisible(False)
        self.ui.table_stats_progress.verticalHeader().setVisible(False)
        self.ui.table_stats_popularity.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.ui.table_stats_progress.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.ui.table_stats_popularity.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ui.table_stats_progress.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        popularity_header = self.ui.table_stats_popularity.horizontalHeader()
        popularity_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        popularity_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

        progress_header = self.ui.table_stats_progress.horizontalHeader()
        progress_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, 8):
            progress_header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

    def _on_stats_period_changed(self):
        current_data = self.ui.statsPeriodCombo.currentData()
        if current_data:
            self._current_stats_period = int(current_data)
            self.refresh_stats()

    def refresh_stats(self):
        self.ui.statsRefreshBtn.setEnabled(False)
        self.stats_worker.get_dashboard_stats(self._current_stats_period)

    def on_stats_loaded(self, stats):
        self.ui.statsRefreshBtn.setEnabled(True)
        summary = stats.summary
        self.ui.statsCoursesValue.setText(str(summary.total_courses))
        self.ui.statsLessonsValue.setText(str(summary.total_lessons))
        self.ui.statsUsersValue.setText(str(summary.total_users))
        self.ui.statsActiveUsersValue.setText(str(summary.active_users))
        self.ui.statsCompletionsValue.setText(str(summary.completions_in_period))
        self.ui.statsAvgProgressValue.setText(f"{summary.avg_course_progress * 100:.0f}%")
        self.ui.statsCompletedCoursesValue.setText(str(summary.completed_courses))

        self.stats_chart.set_points(stats.timeline)

        self.ui.table_stats_popularity.setRowCount(len(stats.popularity))
        for row, item in enumerate(stats.popularity):
            self.ui.table_stats_popularity.setItem(row, 0, QTableWidgetItem(item.topic_name))
            self.ui.table_stats_popularity.setItem(row, 1, QTableWidgetItem(str(item.completions_count)))

        self.ui.table_stats_progress.setRowCount(len(stats.course_progress))
        for row, item in enumerate(stats.course_progress):
            self.ui.table_stats_progress.setItem(row, 0, QTableWidgetItem(item.topic_name))
            self.ui.table_stats_progress.setItem(row, 1, QTableWidgetItem(str(item.lessons_count)))
            self.ui.table_stats_progress.setItem(row, 2, QTableWidgetItem(f"{item.average_progress * 100:.0f}%"))
            self.ui.table_stats_progress.setItem(row, 3, QTableWidgetItem(str(item.learners_started)))
            self.ui.table_stats_progress.setItem(row, 4, QTableWidgetItem(str(item.reached_25)))
            self.ui.table_stats_progress.setItem(row, 5, QTableWidgetItem(str(item.reached_50)))
            self.ui.table_stats_progress.setItem(row, 6, QTableWidgetItem(str(item.reached_75)))
            self.ui.table_stats_progress.setItem(row, 7, QTableWidgetItem(str(item.reached_100)))

        self.ui.statsChartTitle.setText(f"Динамика завершений за {stats.period_days} дней")
        self.ui.statsPopularityTitle.setText(f"Популярность курсов за {stats.period_days} дней")
        self.ui.statsProgressTitle.setText("Эффективность курсов")

    def _show_error(self, message: str):
        self.ui.statsRefreshBtn.setEnabled(True)
        self.show_error(message)

    def on_topic_selected(self, row, column):
        """Обработка клика по теме: загрузка уроков"""
        topic_id = int(self.ui.table_topics.item(row, 0).text())
        self.selected_topic_id = topic_id
        self.ui.btn_add_lesson.setEnabled(True)
        self.refresh_lessons(topic_id)

    def on_lesson_created(self, topic_id: int):
        self.selected_topic_id = topic_id
        self.close_creator()
        self.refresh_lessons(topic_id)
        self.fetch_topics()

    def on_lesson_updated(self, topic_id: int):
        self.selected_topic_id = topic_id
        self.close_creator()
        self.refresh_lessons(topic_id)
        self.fetch_topics()

    def on_lessons_loaded(self, lessons):
        """Отображение полученных уроков в таблице"""
        self.ui.table_lessons.setRowCount(len(lessons))
        for row, lesson in enumerate(lessons):
            self.ui.table_lessons.setItem(row, 0, QTableWidgetItem(str(lesson.id)))
            name_item = QTableWidgetItem(lesson.name)
            name_item.setData(Qt.ItemDataRole.UserRole, lesson.description)
            name_item.setData(Qt.ItemDataRole.UserRole + 1, lesson.difficult)
            name_item.setData(Qt.ItemDataRole.UserRole + 2, float(lesson.rhythm))
            name_item.setData(Qt.ItemDataRole.UserRole + 3, lesson.notes)
            name_item.setData(Qt.ItemDataRole.UserRole + 4, lesson.topic)
            self.ui.table_lessons.setItem(row, 1, name_item)

    def fetch_topics(self):
        self.ui.table_topics.setRowCount(0)
        self.worker.get_topics()

    def on_topics_loaded(self, topics: list[TopicResponse]): # Type hinting!
        self.ui.table_topics.setRowCount(len(topics))
        for row_index, topic in enumerate(topics):
            desc = topic.description if topic.description else ""
            self._insert_topic_row(row_index, topic.id, topic.name, desc, topic.lessons_count)

        if self.selected_topic_id is None:
            return

        for row in range(self.ui.table_topics.rowCount()):
            id_item = self.ui.table_topics.item(row, 0)
            if id_item and id_item.text().isdigit() and int(id_item.text()) == self.selected_topic_id:
                self.ui.table_topics.setCurrentCell(row, 1)
                return

    def show_add_topic_dialog(self):
        dialog = AddTopicDialog(self.ui.centralwidget)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            topic_name, topic_desc = dialog.get_data()
            topic_data = TopicCreate(name=topic_name, description=topic_desc)
            self.ui.btn_add_topic.setEnabled(False)
            self.worker.create_topic(topic_data)

    def show_edit_topic_dialog(self, row):
        topic_id = int(self.ui.table_topics.item(row, 0).text())
        topic_name = self.ui.table_topics.item(row, 1).text()
        topic_desc = self.ui.table_topics.item(row, 1).data(Qt.ItemDataRole.UserRole)

        dialog = AddTopicDialog(self.ui.centralwidget, topic_name=topic_name, topic_desc=topic_desc)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_name, new_desc = dialog.get_data()

            if new_name == topic_name and new_desc == topic_desc:
                return

            topic_data = TopicCreate(name=new_name, description=new_desc)
            self.worker.edit_topic(topic_id, topic_data)
            self.editing_row = row

    def on_topic_added(self, new_topic: TopicResponse):
        self.ui.btn_add_topic.setEnabled(True)
        current_rows = self.ui.table_topics.rowCount()
        self.ui.table_topics.insertRow(current_rows)

        desc = new_topic.description if new_topic.description else ""
        self._insert_topic_row(current_rows, new_topic.id, new_topic.name, desc, new_topic.lessons_count)

    def on_topic_updated(self, updated_topic: TopicResponse):
        if hasattr(self, "editing_row"):
            name_item = self.ui.table_topics.item(self.editing_row, 1)
            name_item.setText(updated_topic.name)

            desc = updated_topic.description if updated_topic.description else ""
            name_item.setData(Qt.ItemDataRole.UserRole, desc)

            QMessageBox.information(self.ui.centralwidget, "Успех", f"Тема '{updated_topic.name}' успешно обновлена!")

    def show_context_menu(self, pos):
        """Отображает меню при клике ПКМ по таблице"""
        item = self.ui.table_topics.itemAt(pos)
        if item is None:
            return

        row = item.row()
        menu = QMenu(self.ui.centralwidget)
        edit_action = menu.addAction("✏️ Изменить")
        delete_action = menu.addAction("🗑️ Удалить")

        action = menu.exec(self.ui.table_topics.viewport().mapToGlobal(pos))

        if action == edit_action:
            self.show_edit_topic_dialog(row)
        elif action == delete_action:
            self.confirm_and_delete_topic(row)

    def confirm_and_delete_topic(self, row):
        """Проверяет уроки и запрашивает подтверждение на удаление"""
        topic_id = int(self.ui.table_topics.item(row, 0).text())
        topic_name = self.ui.table_topics.item(row, 1).text()
        lessons_count = int(self.ui.table_topics.item(row, 2).text())

        if lessons_count > 0:
            msg = (f"Вы уверены, что хотите удалить тему <b>«{topic_name}»</b>?<br><br>"
                   f"⚠️ В этой теме содержится <b>{lessons_count} уроков</b>. "
                   f"Они будут удалены безвозвратно вместе с темой!")
        else:
            msg = f"Вы уверены, что хотите удалить пустую тему <b>«{topic_name}»</b>?"

        reply = QMessageBox.question(
            self.ui.centralwidget,
            "Подтверждение удаления",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.worker.delete_topic(topic_id)

    def on_topic_deleted(self, deleted_topic_id: int):
        """Находит строку с удаленной темой и стирает её из таблицы"""
        for row in range(self.ui.table_topics.rowCount()):
            item = self.ui.table_topics.item(row, 0)
            if item and int(item.text()) == deleted_topic_id:
                self.ui.table_topics.removeRow(row)
                QMessageBox.information(self.ui.centralwidget, "Успех", "Тема успешно удалена.")
                break

    def show_error(self, message: str):
        self.ui.btn_add_topic.setEnabled(True)
        if hasattr(self.ui, "statsRefreshBtn"):
            self.ui.statsRefreshBtn.setEnabled(True)
        QMessageBox.warning(self.ui.centralwidget, "Ошибка", message)

    def _insert_topic_row(self, row_index, topic_id, name, description, lessons_count):
        self.ui.table_topics.setItem(row_index, 0, QTableWidgetItem(str(topic_id)))
        name_item = QTableWidgetItem(name)
        name_item.setData(Qt.ItemDataRole.UserRole, description)
        self.ui.table_topics.setItem(row_index, 1, name_item)
        self.ui.table_topics.setItem(row_index, 2, QTableWidgetItem(str(lessons_count)))

    def setup_users_table(self):
        """Настройка внешнего вида таблицы пользователей"""
        table = self.ui.table_users
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["ID", "Логин", "Email", "Роль", "Статус"])

        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        table.verticalHeader().setVisible(False)
        table.setColumnHidden(0, True)

        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(self.show_user_context_menu)
        table.setSelectionBehavior(table.SelectionBehavior.SelectRows)
        table.setEditTriggers(table.EditTrigger.NoEditTriggers)

        table.setStyleSheet(self.ui.table_topics.styleSheet())

    def on_users_loaded(self, users):
        table = self.ui.table_users
        table.setRowCount(0)

        sorted_users = sorted(users, key=lambda x: x['is_active'], reverse=True)

        for user in sorted_users:
            self._add_or_update_user_row(user)

    def _add_or_update_user_row(self, user, update_row=None):
        """Универсальный метод добавления или обновления строки"""
        table = self.ui.table_users
        row = table.rowCount() if update_row is None else update_row

        if update_row is None:
            table.insertRow(row)

        id_item = QTableWidgetItem(str(user['id']))
        name_item = QTableWidgetItem(user['username'])
        email_item = QTableWidgetItem(user['email'])
        role_item = QTableWidgetItem(user['role'])
        status_text = "🟢 Активен" if user['is_active'] else "🔴 Заблокирован"
        status_item = QTableWidgetItem(status_text)

        table.setItem(row, 0, id_item)
        table.setItem(row, 1, name_item)
        table.setItem(row, 2, email_item)
        table.setItem(row, 3, role_item)
        table.setItem(row, 4, status_item)

        self._paint_row(row, inactive=not user['is_active'])

    def _paint_row(self, row, inactive=False):
        color = QColor("#a0a0a0") if inactive else QColor("#000000")
        brush = QBrush(color)
        for col in range(self.ui.table_users.columnCount()):
            item = self.ui.table_users.item(row, col)
            if item:
                item.setForeground(brush)

    def show_user_context_menu(self, pos):
        item = self.ui.table_users.itemAt(pos)
        if not item:
            return

        row = item.row()
        user_id = int(self.ui.table_users.item(row, 0).text())
        is_active = "Активен" in self.ui.table_users.item(row, 4).text()

        menu = QMenu()
        edit_action = menu.addAction("✏️ Изменить")
        toggle_action = menu.addAction("🚫 Заблокировать" if is_active else "✅ Разблокировать")

        action = menu.exec(self.ui.table_users.viewport().mapToGlobal(pos))

        if action == toggle_action:
            self.auth_worker.toggle_user_status(user_id)
        elif action == edit_action:
            username = self.ui.table_users.item(row, 1).text()
            email = self.ui.table_users.item(row, 2).text()

            self.editing_user_row = row
            self.current_edit_dialog = EditUserDialog(self.ui.centralwidget, username=username, email=email)
            self.current_edit_dialog.save_requested.connect(
                lambda u, e: self.process_user_edit(user_id, username, email, u, e)
            )
            self.current_edit_dialog.exec()

    def process_user_edit(self, user_id, old_username, old_email, new_username, new_email):
        if new_username == old_username and new_email == old_email:
            self.current_edit_dialog.close()
            return

        update_data = {}
        if new_username != old_username:
            update_data["username"] = new_username
        if new_email != old_email:
            update_data["email"] = new_email

        self.editing_user_row = self.ui.table_users.currentRow()
        self.auth_worker.edit_user(user_id, update_data)

    def on_user_edited(self, updated_user):
        if hasattr(self, "current_edit_dialog") and self.current_edit_dialog:
            self.current_edit_dialog.close_success()

        if hasattr(self, "editing_user_row"):
            self._add_or_update_user_row(updated_user, update_row=self.editing_user_row)
            QMessageBox.information(self.ui.centralwidget, "Успех", "Данные пользователя обновлены!")

    def on_user_status_updated(self, updated_user):
        self.auth_worker.get_all_users()


from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QDialogButtonBox

class TimeSignatureDialog(QDialog):
    """Диалоговое окно для выбора музыкального размера перед созданием урока."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройка нового урока")
        self.setFixedSize(300, 150)

        layout = QVBoxLayout(self)
        label = QLabel("Выберите размер такта (ритм) для нового урока:", self)
        layout.addWidget(label)

        self.combo = QComboBox(self)
        self.combo.addItems(["4/4", "3/4", "2/4", "6/8"])
        self.combo.setCurrentText("4/4")
        layout.addWidget(self.combo)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def get_signature(self) -> str:
        return self.combo.currentText()

    def on_lesson_created(self, topic_id: int):
        self.selected_topic_id = topic_id
        self.close_creator()
        self.refresh_lessons(topic_id)
        self.fetch_topics()

    def on_lesson_updated(self, topic_id: int):
        self.selected_topic_id = topic_id
        self.close_creator()
        self.refresh_lessons(topic_id)
        self.fetch_topics()

    def on_lessons_loaded(self, lessons):
        """Отображение полученных уроков в таблице"""
        self.ui.table_lessons.setRowCount(len(lessons))
        for row, lesson in enumerate(lessons):
            self.ui.table_lessons.setItem(row, 0, QTableWidgetItem(str(lesson.id)))
            name_item = QTableWidgetItem(lesson.name)
            name_item.setData(Qt.ItemDataRole.UserRole, lesson.description)
            name_item.setData(Qt.ItemDataRole.UserRole + 1, lesson.difficult)
            name_item.setData(Qt.ItemDataRole.UserRole + 2, float(lesson.rhythm))
            name_item.setData(Qt.ItemDataRole.UserRole + 3, lesson.notes)
            name_item.setData(Qt.ItemDataRole.UserRole + 4, lesson.topic)
            self.ui.table_lessons.setItem(row, 1, name_item)

    def fetch_topics(self):
        self.ui.table_topics.setRowCount(0)
        self.worker.get_topics()

    def on_topics_loaded(self, topics: list[TopicResponse]): # Type hinting!
        self.ui.table_topics.setRowCount(len(topics))
        for row_index, topic in enumerate(topics):
            # Обращаемся к атрибутам через точку: topic.name, topic.id
            desc = topic.description if topic.description else ""
            self._insert_topic_row(row_index, topic.id, topic.name, desc, topic.lessons_count)

        if self.selected_topic_id is None:
            return

        for row in range(self.ui.table_topics.rowCount()):
            id_item = self.ui.table_topics.item(row, 0)
            if id_item and id_item.text().isdigit() and int(id_item.text()) == self.selected_topic_id:
                self.ui.table_topics.setCurrentCell(row, 1)
                return

    def show_add_topic_dialog(self):
        dialog = AddTopicDialog(self.ui.centralwidget)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            topic_name, topic_desc = dialog.get_data()

            # Упаковываем данные в схему Pydantic перед отправкой!
            topic_data = TopicCreate(name=topic_name, description=topic_desc)

            self.ui.btn_add_topic.setEnabled(False)
            self.worker.create_topic(topic_data)

    def show_edit_topic_dialog(self, row):
        topic_id = int(self.ui.table_topics.item(row, 0).text())
        topic_name = self.ui.table_topics.item(row, 1).text()
        topic_desc = self.ui.table_topics.item(row, 1).data(Qt.ItemDataRole.UserRole)

        dialog = AddTopicDialog(self.ui.centralwidget, topic_name=topic_name, topic_desc=topic_desc)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_name, new_desc = dialog.get_data()

            if new_name == topic_name and new_desc == topic_desc:
                return

            # Формируем объект Pydantic
            topic_data = TopicCreate(name=new_name, description=new_desc)
            self.worker.edit_topic(topic_id, topic_data)
            self.editing_row = row

    def on_topic_added(self, new_topic: TopicResponse):
        self.ui.btn_add_topic.setEnabled(True)
        current_rows = self.ui.table_topics.rowCount()
        self.ui.table_topics.insertRow(current_rows)

        desc = new_topic.description if new_topic.description else ""
        self._insert_topic_row(current_rows, new_topic.id, new_topic.name, desc, new_topic.lessons_count)

    def on_topic_updated(self, updated_topic: TopicResponse):
        if hasattr(self, "editing_row"):
            name_item = self.ui.table_topics.item(self.editing_row, 1)
            name_item.setText(updated_topic.name)

            desc = updated_topic.description if updated_topic.description else ""
            name_item.setData(Qt.ItemDataRole.UserRole, desc)

            QMessageBox.information(self.ui.centralwidget, "Успех", f"Тема '{updated_topic.name}' успешно обновлена!")

    def show_context_menu(self, pos):
        """Отображает меню при клике ПКМ по таблице"""
        item = self.ui.table_topics.itemAt(pos)
        if item is None:
            return

        row = item.row()
        menu = QMenu(self.ui.centralwidget)

        # Добавляем действия в меню
        edit_action = menu.addAction("✏️ Изменить")
        delete_action = menu.addAction("🗑️ Удалить") # Новая кнопка

        action = menu.exec(self.ui.table_topics.viewport().mapToGlobal(pos))

        if action == edit_action:
            self.show_edit_topic_dialog(row)
        elif action == delete_action:
            self.confirm_and_delete_topic(row) # Вызываем новый метод

    def confirm_and_delete_topic(self, row):
        """Проверяет уроки и запрашивает подтверждение на удаление"""
        # Считываем данные из таблицы
        topic_id = int(self.ui.table_topics.item(row, 0).text())
        topic_name = self.ui.table_topics.item(row, 1).text()
        lessons_count = int(self.ui.table_topics.item(row, 2).text())

        # Формируем текст предупреждения в зависимости от наличия уроков
        if lessons_count > 0:
            msg = (f"Вы уверены, что хотите удалить тему <b>«{topic_name}»</b>?<br><br>"
                   f"⚠️ В этой теме содержится <b>{lessons_count} уроков</b>. "
                   f"Они будут удалены безвозвратно вместе с темой!")
        else:
            msg = f"Вы уверены, что хотите удалить пустую тему <b>«{topic_name}»</b>?"

        # Показываем диалог
        reply = QMessageBox.question(
            self.ui.centralwidget,
            "Подтверждение удаления",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No # По умолчанию "Нет", чтобы избежать случайных удалений
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.worker.delete_topic(topic_id)

    def on_topic_deleted(self, deleted_topic_id: int):
        """Находит строку с удаленной темой и стирает её из таблицы"""
        # Проходимся по всем строкам и ищем нужный ID
        for row in range(self.ui.table_topics.rowCount()):
            item = self.ui.table_topics.item(row, 0)
            if item and int(item.text()) == deleted_topic_id:
                self.ui.table_topics.removeRow(row)
                QMessageBox.information(self.ui.centralwidget, "Успех", "Тема успешно удалена.")
                break


    def show_error(self, message: str):
        self.ui.btn_add_topic.setEnabled(True)
        QMessageBox.warning(self.ui.centralwidget, "Ошибка", message)

    def _insert_topic_row(self, row_index, topic_id, name, description, lessons_count):
        # ID
        self.ui.table_topics.setItem(row_index, 0, QTableWidgetItem(str(topic_id)))

        # Имя (И здесь же прячем описание в UserRole!)
        name_item = QTableWidgetItem(name)
        name_item.setData(Qt.ItemDataRole.UserRole, description)
        self.ui.table_topics.setItem(row_index, 1, name_item)

        # Количество уроков
        self.ui.table_topics.setItem(row_index, 2, QTableWidgetItem(str(lessons_count)))


    def setup_users_table(self):
        """Настройка внешнего вида таблицы пользователей"""
        table = self.ui.table_users

        # Добавляем 5-ю колонку 'Статус'
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["ID", "Логин", "Email", "Роль", "Статус"])

        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents) # Статус

        # 1. Убираем "номер строки" (вертикальный хедер)
        table.verticalHeader().setVisible(False)
        # 2. Прячем колонку ID, так как она админу не нужна визуально, но нужна нам для логики
        table.setColumnHidden(0, True)

        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(self.show_user_context_menu)
        table.setSelectionBehavior(table.SelectionBehavior.SelectRows)
        table.setEditTriggers(table.EditTrigger.NoEditTriggers)

        table.setStyleSheet(self.ui.table_topics.styleSheet())

    def on_users_loaded(self, users):
        table = self.ui.table_users
        table.setRowCount(0)

        # МАГИЯ СОРТИРОВКИ: True (активные) идут первыми, False (заблокированные) улетают в самый низ!
        sorted_users = sorted(users, key=lambda x: x['is_active'], reverse=True)

        for user in sorted_users:
            self._add_or_update_user_row(user)


    def _add_or_update_user_row(self, user, update_row=None):
        """Универсальный метод добавления или обновления строки"""
        table = self.ui.table_users
        row = table.rowCount() if update_row is None else update_row

        if update_row is None:
            table.insertRow(row)

        id_item = QTableWidgetItem(str(user['id']))
        name_item = QTableWidgetItem(user['username'])
        email_item = QTableWidgetItem(user['email'])
        role_item = QTableWidgetItem(user['role'])

        # Текстовое отображение статуса
        status_text = "🟢 Активен" if user['is_active'] else "🔴 Заблокирован"
        status_item = QTableWidgetItem(status_text)

        table.setItem(row, 0, id_item)
        table.setItem(row, 1, name_item)
        table.setItem(row, 2, email_item)
        table.setItem(row, 3, role_item)
        table.setItem(row, 4, status_item) # Новая колонка

        # Применяем бледный цвет к неактивным
        self._paint_row(row, inactive=not user['is_active'])

    def _paint_row(self, row, inactive=False):
        # Если неактивен - делаем светло-серым
        color = QColor("#a0a0a0") if inactive else QColor("#000000")
        brush = QBrush(color)
        for col in range(self.ui.table_users.columnCount()):
            item = self.ui.table_users.item(row, col)
            if item:
                item.setForeground(brush)

    def show_user_context_menu(self, pos):
        item = self.ui.table_users.itemAt(pos)
        if not item: return

        row = item.row()
        user_id = int(self.ui.table_users.item(row, 0).text())

        # Определяем статус по 5-й колонке
        is_active = "Активен" in self.ui.table_users.item(row, 4).text()

        menu = QMenu()
        edit_action = menu.addAction("✏️ Изменить")
        toggle_action = menu.addAction("🚫 Заблокировать" if is_active else "✅ Разблокировать")

        action = menu.exec(self.ui.table_users.viewport().mapToGlobal(pos))

        if action == toggle_action:
            self.auth_worker.toggle_user_status(user_id)
        elif action == edit_action:
            # Получаем текущие данные из таблицы
            username = self.ui.table_users.item(row, 1).text()
            email = self.ui.table_users.item(row, 2).text()

            # Сохраняем строку, которую редактируем
            self.editing_user_row = row

            # Создаем диалог и подключаем сигнал
            self.current_edit_dialog = EditUserDialog(self.ui.centralwidget, username=username, email=email)
            self.current_edit_dialog.save_requested.connect(
                lambda u, e: self.process_user_edit(user_id, username, email, u, e)
            )

            # Открываем диалог. Теперь он не закроется, пока мы не вызовем close_success()
            self.current_edit_dialog.exec()

    def process_user_edit(self, user_id, old_username, old_email, new_username, new_email):
        """Метод для формирования и отправки запроса"""
        if new_username == old_username and new_email == old_email:
            self.current_edit_dialog.close()
            return

        update_data = {}
        if new_username != old_username: update_data["username"] = new_username
        if new_email != old_email: update_data["email"] = new_email

        self.editing_user_row = self.ui.table_users.currentRow()
        self.auth_worker.edit_user(user_id, update_data)

    def on_user_edited(self, updated_user):
        """Вызывается только при УДАЧНОМ ответе сервера"""
        if hasattr(self, "current_edit_dialog") and self.current_edit_dialog:
            self.current_edit_dialog.close_success() # Закрываем окно

        if hasattr(self, "editing_user_row"):
            self._add_or_update_user_row(updated_user, update_row=self.editing_user_row)
            QMessageBox.information(self.ui.centralwidget, "Успех", "Данные пользователя обновлены!")

    def show_error(self, message: str):
        """Обновленный метод показа ошибок"""
        # Если окно редактирования открыто, разблокируем в нем кнопку обратно
        if hasattr(self, "current_edit_dialog") and self.current_edit_dialog.isVisible():
            self.current_edit_dialog.btn_save.setEnabled(True)
            self.current_edit_dialog.btn_save.setText("Сохранить")

        QMessageBox.warning(self.ui.centralwidget, "Ошибка", message)

    def on_user_status_updated(self, updated_user):
        """Когда статус меняется, проще всего перезапросить список, чтобы таблица отсортировалась сама!"""
        self.auth_worker.get_all_users()



# app/GUI/dialogs.py (или внутри admin.py)
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QDialogButtonBox

class TimeSignatureDialog(QDialog):
    """Диалоговое окно для выбора музыкального размера перед созданием урока."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройка нового урока")
        self.setFixedSize(300, 150)

        # Основной слой
        layout = QVBoxLayout(self)

        # Текст
        label = QLabel("Выберите размер такта (ритм) для нового урока:", self)
        layout.addWidget(label)

        # Выпадающий список с размерами
        self.combo = QComboBox(self)
        self.combo.addItems(["4/4", "3/4", "2/4", "6/8"])
        # Можно сделать 4/4 по умолчанию
        self.combo.setCurrentText("4/4")
        layout.addWidget(self.combo)

        # Кнопки Ок/Отмена
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def get_signature(self) -> str:
        """Возвращает выбранный размер такта."""
        return self.combo.currentText()

    def on_lesson_created(self, topic_id: int):
        self.selected_topic_id = topic_id
        self.close_creator()
        self.refresh_lessons(topic_id)
        self.fetch_topics()

    def on_lesson_updated(self, topic_id: int):
        self.selected_topic_id = topic_id
        self.close_creator()
        self.refresh_lessons(topic_id)
        self.fetch_topics()

    def on_lessons_loaded(self, lessons):
        """Отображение полученных уроков в таблице"""
        self.ui.table_lessons.setRowCount(len(lessons))
        for row, lesson in enumerate(lessons):
            self.ui.table_lessons.setItem(row, 0, QTableWidgetItem(str(lesson.id)))
            name_item = QTableWidgetItem(lesson.name)
            name_item.setData(Qt.ItemDataRole.UserRole, lesson.description)
            name_item.setData(Qt.ItemDataRole.UserRole + 1, lesson.difficult)
            name_item.setData(Qt.ItemDataRole.UserRole + 2, float(lesson.rhythm))
            name_item.setData(Qt.ItemDataRole.UserRole + 3, lesson.notes)
            name_item.setData(Qt.ItemDataRole.UserRole + 4, lesson.topic)
            self.ui.table_lessons.setItem(row, 1, name_item)

    def fetch_topics(self):
        self.ui.table_topics.setRowCount(0)
        self.worker.get_topics()

    def on_topics_loaded(self, topics: list[TopicResponse]): # Type hinting!
        self.ui.table_topics.setRowCount(len(topics))
        for row_index, topic in enumerate(topics):
            # Обращаемся к атрибутам через точку: topic.name, topic.id
            desc = topic.description if topic.description else ""
            self._insert_topic_row(row_index, topic.id, topic.name, desc, topic.lessons_count)

        if self.selected_topic_id is None:
            return

        for row in range(self.ui.table_topics.rowCount()):
            id_item = self.ui.table_topics.item(row, 0)
            if id_item and id_item.text().isdigit() and int(id_item.text()) == self.selected_topic_id:
                self.ui.table_topics.setCurrentCell(row, 1)
                return

    def show_add_topic_dialog(self):
        dialog = AddTopicDialog(self.ui.centralwidget)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            topic_name, topic_desc = dialog.get_data()
            
            # Упаковываем данные в схему Pydantic перед отправкой!
            topic_data = TopicCreate(name=topic_name, description=topic_desc)
            
            self.ui.btn_add_topic.setEnabled(False)
            self.worker.create_topic(topic_data)

    def show_edit_topic_dialog(self, row):
        topic_id = int(self.ui.table_topics.item(row, 0).text())
        topic_name = self.ui.table_topics.item(row, 1).text()
        topic_desc = self.ui.table_topics.item(row, 1).data(Qt.ItemDataRole.UserRole)
        
        dialog = AddTopicDialog(self.ui.centralwidget, topic_name=topic_name, topic_desc=topic_desc)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_name, new_desc = dialog.get_data()
            
            if new_name == topic_name and new_desc == topic_desc:
                return

            # Формируем объект Pydantic
            topic_data = TopicCreate(name=new_name, description=new_desc)
            self.worker.edit_topic(topic_id, topic_data)
            self.editing_row = row 

    def on_topic_added(self, new_topic: TopicResponse):
        self.ui.btn_add_topic.setEnabled(True)
        current_rows = self.ui.table_topics.rowCount()
        self.ui.table_topics.insertRow(current_rows)
        
        desc = new_topic.description if new_topic.description else ""
        self._insert_topic_row(current_rows, new_topic.id, new_topic.name, desc, new_topic.lessons_count)

    def on_topic_updated(self, updated_topic: TopicResponse):
        if hasattr(self, "editing_row"):
            name_item = self.ui.table_topics.item(self.editing_row, 1)
            name_item.setText(updated_topic.name)
            
            desc = updated_topic.description if updated_topic.description else ""
            name_item.setData(Qt.ItemDataRole.UserRole, desc)
            
            QMessageBox.information(self.ui.centralwidget, "Успех", f"Тема '{updated_topic.name}' успешно обновлена!")

    def show_context_menu(self, pos):
        """Отображает меню при клике ПКМ по таблице"""
        item = self.ui.table_topics.itemAt(pos)
        if item is None:
            return

        row = item.row()
        menu = QMenu(self.ui.centralwidget)
        
        # Добавляем действия в меню
        edit_action = menu.addAction("✏️ Изменить")
        delete_action = menu.addAction("🗑️ Удалить") # Новая кнопка
        
        action = menu.exec(self.ui.table_topics.viewport().mapToGlobal(pos))
        
        if action == edit_action:
            self.show_edit_topic_dialog(row)
        elif action == delete_action:
            self.confirm_and_delete_topic(row) # Вызываем новый метод

    def confirm_and_delete_topic(self, row):
        """Проверяет уроки и запрашивает подтверждение на удаление"""
        # Считываем данные из таблицы
        topic_id = int(self.ui.table_topics.item(row, 0).text())
        topic_name = self.ui.table_topics.item(row, 1).text()
        lessons_count = int(self.ui.table_topics.item(row, 2).text())

        # Формируем текст предупреждения в зависимости от наличия уроков
        if lessons_count > 0:
            msg = (f"Вы уверены, что хотите удалить тему <b>«{topic_name}»</b>?<br><br>"
                   f"⚠️ В этой теме содержится <b>{lessons_count} уроков</b>. "
                   f"Они будут удалены безвозвратно вместе с темой!")
        else:
            msg = f"Вы уверены, что хотите удалить пустую тему <b>«{topic_name}»</b>?"

        # Показываем диалог
        reply = QMessageBox.question(
            self.ui.centralwidget, 
            "Подтверждение удаления", 
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No # По умолчанию "Нет", чтобы избежать случайных удалений
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.worker.delete_topic(topic_id)

    def on_topic_deleted(self, deleted_topic_id: int):
        """Находит строку с удаленной темой и стирает её из таблицы"""
        # Проходимся по всем строкам и ищем нужный ID
        for row in range(self.ui.table_topics.rowCount()):
            item = self.ui.table_topics.item(row, 0)
            if item and int(item.text()) == deleted_topic_id:
                self.ui.table_topics.removeRow(row)
                QMessageBox.information(self.ui.centralwidget, "Успех", "Тема успешно удалена.")
                break


    def show_error(self, message: str):
        self.ui.btn_add_topic.setEnabled(True)
        QMessageBox.warning(self.ui.centralwidget, "Ошибка", message)
        
    def _insert_topic_row(self, row_index, topic_id, name, description, lessons_count):
        # ID
        self.ui.table_topics.setItem(row_index, 0, QTableWidgetItem(str(topic_id)))
        
        # Имя (И здесь же прячем описание в UserRole!)
        name_item = QTableWidgetItem(name)
        name_item.setData(Qt.ItemDataRole.UserRole, description)
        self.ui.table_topics.setItem(row_index, 1, name_item)
        
        # Количество уроков
        self.ui.table_topics.setItem(row_index, 2, QTableWidgetItem(str(lessons_count)))


    def setup_users_table(self):
        """Настройка внешнего вида таблицы пользователей"""
        table = self.ui.table_users
        
        # Добавляем 5-ю колонку 'Статус'
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["ID", "Логин", "Email", "Роль", "Статус"])
        
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) 
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)          
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)          
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents) # Статус
        
        # 1. Убираем "номер строки" (вертикальный хедер)
        table.verticalHeader().setVisible(False)
        # 2. Прячем колонку ID, так как она админу не нужна визуально, но нужна нам для логики
        table.setColumnHidden(0, True)
        
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(self.show_user_context_menu)
        table.setSelectionBehavior(table.SelectionBehavior.SelectRows)
        table.setEditTriggers(table.EditTrigger.NoEditTriggers)
        
        table.setStyleSheet(self.ui.table_topics.styleSheet())

    def on_users_loaded(self, users):
        table = self.ui.table_users
        table.setRowCount(0)
        
        # МАГИЯ СОРТИРОВКИ: True (активные) идут первыми, False (заблокированные) улетают в самый низ!
        sorted_users = sorted(users, key=lambda x: x['is_active'], reverse=True)
        
        for user in sorted_users:
            self._add_or_update_user_row(user)


    def _add_or_update_user_row(self, user, update_row=None):
        """Универсальный метод добавления или обновления строки"""
        table = self.ui.table_users
        row = table.rowCount() if update_row is None else update_row
        
        if update_row is None:
            table.insertRow(row)
            
        id_item = QTableWidgetItem(str(user['id']))
        name_item = QTableWidgetItem(user['username'])
        email_item = QTableWidgetItem(user['email'])
        role_item = QTableWidgetItem(user['role'])
        
        # Текстовое отображение статуса
        status_text = "🟢 Активен" if user['is_active'] else "🔴 Заблокирован"
        status_item = QTableWidgetItem(status_text)
            
        table.setItem(row, 0, id_item)
        table.setItem(row, 1, name_item)
        table.setItem(row, 2, email_item)
        table.setItem(row, 3, role_item)
        table.setItem(row, 4, status_item) # Новая колонка
        
        # Применяем бледный цвет к неактивным
        self._paint_row(row, inactive=not user['is_active'])

    def _paint_row(self, row, inactive=False):
        # Если неактивен - делаем светло-серым
        color = QColor("#a0a0a0") if inactive else QColor("#000000")
        brush = QBrush(color)
        for col in range(self.ui.table_users.columnCount()):
            item = self.ui.table_users.item(row, col)
            if item:
                item.setForeground(brush)

    def show_user_context_menu(self, pos):
        item = self.ui.table_users.itemAt(pos)
        if not item: return
        
        row = item.row()
        user_id = int(self.ui.table_users.item(row, 0).text())
        
        # Определяем статус по 5-й колонке
        is_active = "Активен" in self.ui.table_users.item(row, 4).text()

        menu = QMenu()
        edit_action = menu.addAction("✏️ Изменить")
        toggle_action = menu.addAction("🚫 Заблокировать" if is_active else "✅ Разблокировать")
        
        action = menu.exec(self.ui.table_users.viewport().mapToGlobal(pos))
        
        if action == toggle_action:
            self.auth_worker.toggle_user_status(user_id)
        elif action == edit_action:
            # Получаем текущие данные из таблицы
            username = self.ui.table_users.item(row, 1).text()
            email = self.ui.table_users.item(row, 2).text()
            
            # Сохраняем строку, которую редактируем
            self.editing_user_row = row 

            # Создаем диалог и подключаем сигнал
            self.current_edit_dialog = EditUserDialog(self.ui.centralwidget, username=username, email=email)
            self.current_edit_dialog.save_requested.connect(
                lambda u, e: self.process_user_edit(user_id, username, email, u, e)
            )
            
            # Открываем диалог. Теперь он не закроется, пока мы не вызовем close_success()
            self.current_edit_dialog.exec()

    def process_user_edit(self, user_id, old_username, old_email, new_username, new_email):
        """Метод для формирования и отправки запроса"""
        if new_username == old_username and new_email == old_email:
            self.current_edit_dialog.close()
            return

        update_data = {}
        if new_username != old_username: update_data["username"] = new_username
        if new_email != old_email: update_data["email"] = new_email
        
        self.editing_user_row = self.ui.table_users.currentRow()
        self.auth_worker.edit_user(user_id, update_data)

    def on_user_edited(self, updated_user):
        """Вызывается только при УДАЧНОМ ответе сервера"""
        if hasattr(self, "current_edit_dialog") and self.current_edit_dialog:
            self.current_edit_dialog.close_success() # Закрываем окно
            
        if hasattr(self, "editing_user_row"):
            self._add_or_update_user_row(updated_user, update_row=self.editing_user_row)
            QMessageBox.information(self.ui.centralwidget, "Успех", "Данные пользователя обновлены!")

    def show_error(self, message: str):
        """Обновленный метод показа ошибок"""
        # Если окно редактирования открыто, разблокируем в нем кнопку обратно
        if hasattr(self, "current_edit_dialog") and self.current_edit_dialog.isVisible():
            self.current_edit_dialog.btn_save.setEnabled(True)
            self.current_edit_dialog.btn_save.setText("Сохранить")
            
        QMessageBox.warning(self.ui.centralwidget, "Ошибка", message)

    def on_user_status_updated(self, updated_user):
        """Когда статус меняется, проще всего перезапросить список, чтобы таблица отсортировалась сама!"""
        self.auth_worker.get_all_users()



# app/GUI/dialogs.py (или внутри admin.py)
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QDialogButtonBox

class TimeSignatureDialog(QDialog):
    """Диалоговое окно для выбора музыкального размера и руки перед созданием урока."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройка нового урока")
        self.setFixedSize(300, 220)

        # Основной слой
        layout = QVBoxLayout(self)

        # Текст для ритма
        label = QLabel("Выберите размер такта (ритм) для нового урока:", self)
        layout.addWidget(label)

        # Выпадающий список с размерами
        self.combo = QComboBox(self)
        self.combo.addItems(["4/4", "3/4", "2/4", "6/8"])
        # Можно сделать 4/4 по умолчанию
        self.combo.setCurrentText("4/4") 
        layout.addWidget(self.combo)

        # Текст для руки
        hand_label = QLabel("Выберите руку:", self)
        layout.addWidget(hand_label)

        # Выпадающий список для выбора руки
        self.hand_combo = QComboBox(self)
        self.hand_combo.addItem("Правая рука", "right")
        self.hand_combo.addItem("Левая рука", "left")
        self.hand_combo.setCurrentIndex(0)
        layout.addWidget(self.hand_combo)

        # Кнопки Ок/Отмена
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def get_signature(self) -> str:
        """Возвращает выбранный размер такта."""
        return self.combo.currentText()

    def get_hand(self) -> str:
        """Возвращает выбранную руку."""
        return self.hand_combo.currentData()