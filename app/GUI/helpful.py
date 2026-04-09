from PyQt6.QtWidgets import QLayout, QSizePolicy, QGraphicsView
from PyQt6.QtCore import QPoint, QRect, QSize, Qt


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.itemList = []

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        margin, _, _, _ = self.getContentsMargins()
        size += QSize(2 * margin, 2 * margin)
        return size

    def _doLayout(self, rect, testOnly):
        x = rect.x()
        y = rect.y()
        lineHeight = 0
        
        # 1. Сначала рассчитываем, сколько карточек влезет в один ряд (по первой строке)
        cards_per_row = 0
        current_w = 0
        for i in range(self.count()):
            item_w = self.itemAt(i).sizeHint().width()
            if current_w + item_w > rect.width():
                break
            current_w += item_w + self.spacing()
            cards_per_row += 1
        
        cards_per_row = max(1, cards_per_row) # Минимум одна карточка

        # 2. Вычисляем ширину "контента" (целых карточек в ряду) для общего отступа
        # Берем только те карточки, которые реально помещаются
        actual_line_width = 0
        for i in range(min(cards_per_row, self.count())):
            actual_line_width += self.itemAt(i).sizeHint().width()
        actual_line_width += (min(cards_per_row, self.count()) - 1) * self.spacing()

        # 3. Общий отступ для ВСЕХ строк
        left_offset = max(0, (rect.width() - actual_line_width) // 2)

        # 4. Расставляем все карточки с этим фиксированным отступом
        current_x = rect.x() + left_offset
        for i in range(self.count()):
            item = self.itemAt(i)
            
            # Если карточка не влезает в текущую строку по ширине
            if current_x + item.sizeHint().width() > rect.x() + rect.width() - left_offset and lineHeight > 0:
                current_x = rect.x() + left_offset # Возвращаемся к началу с тем же отступом
                y = y + lineHeight + self.spacing()
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(current_x, y), item.sizeHint()))

            current_x += item.sizeHint().width() + self.spacing()
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y()

    def _center_line(self, widgets, total_width, line_height, y_offset):
        if not widgets:
            return
        
        # Считаем общую ширину всех виджетов в строке с учетом отступов
        line_width = sum(w.sizeHint().width() for w in widgets) + (len(widgets) - 1) * self.spacing()
        
        # Начальный отступ для центрирования
        start_x = (total_width - line_width) // 2
        
        current_x = start_x
        for item in widgets:
            item.setGeometry(QRect(QPoint(current_x, y_offset), item.sizeHint()))
            current_x += item.sizeHint().width() + self.spacing()



class ScalableGraphicsView(QGraphicsView):
    def __init__(self, parent=None):  # ✅ Стандартный parent!
        super().__init__(parent)  # НЕ scene!
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
    
    def resizeEvent(self, event):
        center = None
        if self.scene():
            center = self.mapToScene(self.viewport().rect().center())
            self.fitInView(self.scene().sceneRect(), 
                          Qt.AspectRatioMode.KeepAspectRatioByExpanding)
        super().resizeEvent(event)
        if center is not None:
            self.centerOn(center)