from PyQt6.QtWidgets import (
    QMessageBox, QTableWidgetItem, QAbstractItemView, 
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QTextEdit, QPushButton, QMenu
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtCore import Qt
from workers.topic_worker import TopicWorker
from workers.auth_worker import AuthWorker
from workers.lesson_worker import LessonWorker
from schemas.topic import TopicCreate, TopicResponse
from PyQt6.QtWidgets import QMenu, QTableWidgetItem, QHeaderView
from PyQt6.QtGui import QColor, QBrush


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
        self.lesson_worker.lesson_error_sygnal.connect(self.show_error)
        self.setup_admin_panel()
        self.setup_users_table()

        # Загружаем пользователей
        self.auth_worker.get_all_users()
        

    def setup_admin_panel(self):
        # Настройка внешнего вида таблиц (используем твой стиль)
        table_style = self.ui.table_topics.styleSheet()
        self.ui.table_lessons.setStyleSheet(table_style)
        
        # Настройка колонок для таблицы уроков
        l_header = self.ui.table_lessons.horizontalHeader()
        l_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        l_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.ui.table_lessons.verticalHeader().setVisible(False)
        self.ui.table_lessons.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        # Темы (стандартная настройка)
        header = self.ui.table_topics.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.ui.table_topics.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.fetch_topics()

    def on_topic_selected(self, row, column):
        """Обработка клика по теме: загрузка уроков"""
        topic_id = int(self.ui.table_topics.item(row, 0).text())
        self.ui.btn_add_lesson.setEnabled(True)
        
        # Очистка и запуск запроса
        self.ui.table_lessons.setRowCount(0)
        self.lesson_worker.get_lessons_by_topic(topic_id)

    def on_lessons_loaded(self, lessons):
        """Отображение полученных уроков в таблице"""
        self.ui.table_lessons.setRowCount(len(lessons))
        for row, lesson in enumerate(lessons):
            # lesson - это объект LessonResponse
            self.ui.table_lessons.setItem(row, 0, QTableWidgetItem(str(lesson.id)))
            self.ui.table_lessons.setItem(row, 1, QTableWidgetItem(lesson.name))

    def fetch_topics(self):
        self.ui.table_topics.setRowCount(0)
        self.worker.get_topics()

    def on_topics_loaded(self, topics: list[TopicResponse]): # Type hinting!
        self.ui.table_topics.setRowCount(len(topics))
        for row_index, topic in enumerate(topics):
            # Обращаемся к атрибутам через точку: topic.name, topic.id
            desc = topic.description if topic.description else ""
            self._insert_topic_row(row_index, topic.id, topic.name, desc, topic.lessons_count)

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