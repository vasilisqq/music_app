from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QAbstractItemView, QApplication, QMessageBox
from PyQt6.QtCore import Qt, QMimeData, QPoint
from PyQt6.QtGui import QCursor

class DraggableTableWidget(QTableWidget):
    """Кастомная таблица с поддержкой Drag-and-Drop для перемещения строк"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        
        # Отключаем редактирование ячеек при перетаскивании
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        self._dragged_row = -1

    def startDrag(self, supportedActions):
        """Начинает перетаскивание строки"""
        selected_items = self.selectedItems()
        if not selected_items:
            return
        
        # Запоминаем индекс перетаскиваемой строки
        self._dragged_row = selected_items[0].row()
        
        # Создаем MIME-данные для перетаскивания
        mime_data = QMimeData()
        mime_data.setData("application/x-row-index", str(self._dragged_row).encode())
        
        drag = self.createDrag(mime_data)
        drag.exec(supportedActions)
        
        self._dragged_row = -1

    def dragEnterEvent(self, event):
        """Разрешаем вход только если перетаскиваем из этой же таблицы"""
        if event.source() == self:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """Показываем индикатор перемещения"""
        if event.source() == self:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Обрабатывает событие сброса строки"""
        if event.source() != self:
            event.ignore()
            return

        event.accept()
        
        # Определяем позицию сброса
        pos = event.position().toPoint()
        item = self.itemAt(pos)
        
        if self._dragged_row < 0:
            return
            
        # Определяем новую позицию
        if item:
            new_row = item.row()
        else:
            new_row = self.rowCount() - 1
        
        if new_row == self._dragged_row or new_row < 0:
            return
        
        # Визуально перемещаем строку
        self._move_row_visual(self._dragged_row, new_row)
        
        # Отправляем новый порядок на сервер
        self._send_reorder_to_server()

    def _move_row_visual(self, from_row: int, to_row: int):
        """Визуально перемещает строку в таблице без отправки на сервер"""
        if from_row == to_row:
            return
        
        # Сохраняем данные всех ячеек перемещаемой строки
        row_data = []
        for column in range(self.columnCount()):
            item = self.item(from_row, column)
            if item:
                row_data.append({
                    'text': item.text(),
                    'data_roles': {
                        role: item.data(role) 
                        for role in range(Qt.ItemDataRole.UserRole, Qt.ItemDataRole.UserRole + 10)
                        if item.data(role) is not None
                    }
                })
            else:
                row_data.append(None)
        
        # Удаляем строку
        self.removeRow(from_row)
        
        # Корректируем позицию вставки, если удалили строку выше целевой
        insert_row = to_row if to_row < from_row else to_row
        
        # Вставляем новую строку
        self.insertRow(insert_row)
        
        # Восстанавливаем данные
        for column, data in enumerate(row_data):
            if data:
                new_item = QTableWidgetItem(data['text'])
                for role, value in data['data_roles'].items():
                    new_item.setData(role, value)
                self.setItem(insert_row, column, new_item)
        
        # Выделяем перемещенную строку
        self.selectRow(insert_row)

    def _send_reorder_to_server(self):
        """Собирает ID уроков в новом порядке и отправляет на сервер"""
        lesson_ids = []
        
        for row in range(self.rowCount()):
            # Предполагаем, что ID урока хранится в первом столбце
            id_item = self.item(row, 0)
            if id_item and id_item.text().isdigit():
                lesson_ids.append(int(id_item.text()))
        
        if not lesson_ids:
            return
        
        # Вызываем метод родителя (AdminController)
        parent = self.parent()
        if hasattr(parent, 'handle_lesson_reorder'):
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                parent.handle_lesson_reorder(lesson_ids)
            finally:
                QApplication.restoreOverrideCursor()
        else:
            print("Ошибка: Родительский виджет не имеет метода handle_lesson_reorder")