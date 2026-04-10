from PyQt6.QtWidgets import QMessageBox, QTableWidgetItem, QAbstractItemView
from config import NORMAL_STYLE
from workers.topic_worker import TopicWorker

class AdminController:
    def __init__(self, ui):
        self.ui = ui
        self.worker = TopicWorker()
        
        # 1. СНАЧАЛА подключаем ВСЕ сигналы ("развешиваем уши")
        self.ui.btn_add_topic.clicked.connect(self.add_new_topic)
        self.worker.topics_loaded_signal.connect(self.on_topics_loaded) # ВАЖНО: Этого не хватало!
        self.worker.topic_added_signal.connect(self.on_topic_added)
        self.worker.error_signal.connect(self.show_error)

        # 2. ПОТОМ настраиваем интерфейс и делаем запросы
        self.setup_admin_panel()

    def setup_admin_panel(self):
        # 1. Настройка растягивания колонок
        header = self.ui.table_topics.horizontalHeader()
        header.setSectionResizeMode(0, header.ResizeMode.ResizeToContents) 
        header.setSectionResizeMode(1, header.ResizeMode.Stretch)          
        header.setSectionResizeMode(2, header.ResizeMode.ResizeToContents) 
        
        # 2. Убираем стандартную колонку с номерами строк
        self.ui.table_topics.verticalHeader().setVisible(False)
        
        # 3. Полностью блокируем возможность изменять текст
        self.ui.table_topics.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        # 4. Выделение всей строки
        self.ui.table_topics.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        # 5. Добавляем современную стилизацию
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
        self.ui.line_new_topic.setStyleSheet(NORMAL_STYLE)
        
        # 7. Стилизация кнопки
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
        
        # Загрузка реальных данных с сервера
        self.fetch_topics()

    def fetch_topics(self):
        """Запускает запрос для получения тем с сервера"""
        self.ui.table_topics.setRowCount(0) # Очищаем таблицу перед загрузкой
        self.worker.get_topics()

    def on_topics_loaded(self, topics: list):
        """Заполняет таблицу данными от сервера при запуске"""
        self.ui.table_topics.setRowCount(len(topics))
        for row_index, topic in enumerate(topics):
            self._insert_topic_row(row_index, topic["id"], topic["name"], topic.get("lessons_count", 0))

    def add_new_topic(self):
        """Отправляет запрос на создание новой темы"""
        topic_name = self.ui.line_new_topic.text().strip()
        
        if not topic_name:
            QMessageBox.warning(self.ui.centralwidget, "Ошибка", "Название темы не может быть пустым!")
            return
            
        topic_data = {"name": topic_name, "description": "Описание появится позже"}
        
        # Блокируем кнопку, чтобы не нажали дважды
        self.ui.btn_add_topic.setEnabled(False)
        self.ui.btn_add_topic.setText("Загрузка...")
        
        self.worker.create_topic(topic_data)

    def on_topic_added(self, new_topic: dict):
        """Добавляет созданную тему в конец таблицы без перезагрузки всего списка"""
        self.ui.line_new_topic.clear()
        self.ui.btn_add_topic.setEnabled(True)
        self.ui.btn_add_topic.setText("Добавить тему")
        
        current_rows = self.ui.table_topics.rowCount()
        self.ui.table_topics.insertRow(current_rows)
        self._insert_topic_row(current_rows, new_topic["id"], new_topic["name"], new_topic.get("lessons_count", 0))
        
        QMessageBox.information(self.ui.centralwidget, "Успех", f"Тема '{new_topic['name']}' создана!")

    def show_error(self, message: str):
        """Показывает ошибки от сервера"""
        self.ui.btn_add_topic.setEnabled(True)
        self.ui.btn_add_topic.setText("Добавить тему")
        QMessageBox.warning(self.ui.centralwidget, "Ошибка", message)
        
    def _insert_topic_row(self, row_index, topic_id, name, lessons_count):
        self.ui.table_topics.setItem(row_index, 0, QTableWidgetItem(str(topic_id)))
        self.ui.table_topics.setItem(row_index, 1, QTableWidgetItem(name))
        self.ui.table_topics.setItem(row_index, 2, QTableWidgetItem(str(lessons_count)))