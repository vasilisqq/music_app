from PyQt6.QtWidgets import (
    QMessageBox, QTableWidgetItem, QAbstractItemView, 
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QTextEdit, QPushButton, QMenu
)
from PyQt6.QtCore import Qt
from workers.topic_worker import TopicWorker
from schemas.topic import TopicCreate, TopicResponse


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


class AdminController:
    def __init__(self, ui):
        self.ui = ui
        self.worker = TopicWorker()
        
        # Сигналы
        self.ui.btn_add_topic.clicked.connect(self.show_add_topic_dialog)
        self.worker.topics_loaded_signal.connect(self.on_topics_loaded)
        self.worker.topic_added_signal.connect(self.on_topic_added)
        self.worker.topic_updated_signal.connect(self.on_topic_updated)
        self.worker.topic_deleted_signal.connect(self.on_topic_deleted)
        self.worker.error_signal.connect(self.show_error)

        self.setup_admin_panel()

    def setup_admin_panel(self):
        header = self.ui.table_topics.horizontalHeader()
        header.setSectionResizeMode(0, header.ResizeMode.ResizeToContents) 
        header.setSectionResizeMode(1, header.ResizeMode.Stretch)          
        header.setSectionResizeMode(2, header.ResizeMode.ResizeToContents) 
        
        self.ui.table_topics.verticalHeader().setVisible(False)
        self.ui.table_topics.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ui.table_topics.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        # ВКЛЮЧАЕМ контекстное меню
        self.ui.table_topics.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ui.table_topics.customContextMenuRequested.connect(self.show_context_menu)
        
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
        
        button_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3f8bde, stop:1 #2968c0);
                border-radius: 15px; color: white; font-size: 16px; font-weight: bold;
                padding: 10px 20px; border: none;
            }
            QPushButton:hover { background: #2968c0; }
            QPushButton:pressed { background: #1f4a8a; }
        """
        self.ui.btn_add_topic.setStyleSheet(button_style)
        
        self.fetch_topics()

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