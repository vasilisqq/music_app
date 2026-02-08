from PyQt6.QtCore import Qt, QRectF, QLineF
from PyQt6.QtGui import QPen, QBrush, QFont, QPixmap,QColor
from PyQt6.QtWidgets import (
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsEllipseItem
)
from musicpy import note, play, C


class NoteItem(QGraphicsEllipseItem):
    """Класс для отображения ноты"""
    
    def __init__(self, x, y, name):
        super().__init__()
        self.note_lenght = 1/4
        self.note_name = name
        self.x = x
        # Размеры ноты
        self.width = 12
        self.height = 9
        
        # Устанавливаем позицию и размер
        self.setRect(QRectF(x - self.width/2, y - self.height/2, 
                           self.width, self.height))
        
        # Настройка внешнего вида
        self.setBrush(QBrush(Qt.GlobalColor.black))
        self.setPen(QPen(Qt.GlobalColor.black))
        
        # Добавляем штиль
        self.add_stem(x, y)
    
    def add_stem(self, x, y):
        """Добавляет штиль к ноте"""
        # Для четвертных нот штиль вверх длиной 32px
        stem_length = 32
        
        # Координаты штиля
        if self.note_lenght == 1/4:
            stem_x = x + self.width/2 - 1
            stem_y_top = y - stem_length
            stem_y_bottom = y
        else:
            # Для других типов нот можно настроить по-другому
            ...
        
        # Создаем линию штиля
        self.stem = QGraphicsLineItem(stem_x, stem_y_bottom, stem_x, stem_y_top)
        pen = QPen(Qt.GlobalColor.black)
        pen.setWidthF(1.2)
        self.stem.setPen(pen)
        
        # Сохраняем родительскую сцену для добавления штиля
        self._stem_item = self.stem


class HighlightableLineItem(QGraphicsLineItem):
    """Класс линии, которая подсвечивается при наведении"""
    
    def __init__(self, line, tact, y, note_name, transparent=False, parent=None):
        super().__init__(line, parent)
        self.tact = tact
        self.y = y
        # Стандартные параметры линии
        self.normal_pen = QPen(Qt.GlobalColor.black)
        self.normal_pen.setWidthF(1.2)
        
        # Параметры при наведении
        self.hover_pen = QPen(QColor(255, 0, 0))  # Красный цвет
        self.hover_pen.setWidthF(2.0)  # Толще обычной линии
        
        # Устанавливаем стандартное перо
        self.setPen(self.normal_pen)
        
        # Включаем обработку событий наведения
        self.setAcceptHoverEvents(True)
        self.setAcceptTouchEvents(True)
        # Флаг наведения
        self.is_hovered = False
        
        # Для отладки можно сохранить номер линии
        self.line_number = -1
        self.note_name = note_name

    def hoverEnterEvent(self, event):
        """Событие при наведении курсора"""
        self.is_hovered = True
        self.setPen(self.hover_pen)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update()  # Принудительное обновление
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        """Событие при уходе курсора"""
        self.is_hovered = False
        self.setPen(self.normal_pen)
        self.unsetCursor()
        self.update()  # Принудительное обновление
        super().hoverLeaveEvent(event)
    
    def paint(self, painter, option, widget=None):
        """Переопределяем отрисовку для лучшего визуального эффекта"""
        # Если линия подсвечена, можно добавить дополнительный эффект
        if self.is_hovered:
            # Рисуем немного более толстую линию на заднем плане для эффекта свечения
            glow_pen = QPen(QColor(255, 100, 100, 50))  # Полупрозрачный красный
            glow_pen.setWidthF(5.0)
            painter.setPen(glow_pen)
            painter.drawLine(self.line())
        
        # Рисуем основную линию
        super().paint(painter, option, widget)


    def mousePressEvent(self, event):
        """Обработка клика на линии"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Получаем позицию клика
            pos = event.pos()
            scene_pos = self.mapToScene(pos)
            
            # Определяем y-координату линии
            y = self.tact.y0 + self.line_number * 12
            
            # Сообщаем такту, что нужно добавить ноту на этой линии
            self.tact.add_note_at_position(scene_pos.x(), self)
        
        super().mousePressEvent(event)


class StaffSpaceItem(QGraphicsRectItem):
    """Класс для пространства между линиями нотного стана"""
    
    def __init__(self, rect, space_number, parent=None):
        super().__init__(rect, parent)
        
        # Сохраняем номер пространства (0-3 для 4 промежутков между 5 линиями)
        self.space_number = space_number
        
        # Прозрачная заливка по умолчанию
        self.normal_brush = QBrush(Qt.GlobalColor.transparent)
        self.normal_pen = QPen(Qt.GlobalColor.transparent)
        
        # Заливка при наведении
        self.hover_brush = QBrush(QColor(173, 216, 230, 80))  # Светло-голубой с прозрачностью
        self.hover_pen = QPen(Qt.GlobalColor.transparent)
        
        # Устанавливаем стандартные параметры
        self.setBrush(self.normal_brush)
        self.setPen(self.normal_pen)
        
        # Включаем обработку событий наведения
        self.setAcceptHoverEvents(True)
        
        # Флаг наведения
        self.is_hovered = False
    
    def hoverEnterEvent(self, event):
        """Событие при наведении курсора"""
        self.is_hovered = True
        self.setBrush(self.hover_brush)
        self.setPen(self.hover_pen)
        
        # Меняем курсор на указатель
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.update()
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        """Событие при уходе курсора"""
        self.is_hovered = False
        self.setBrush(self.normal_brush)
        self.setPen(self.normal_pen)
        
        # Возвращаем стандартный курсор
        self.unsetCursor()
        
        self.update()
        super().hoverLeaveEvent(event)


class TimeSignature:
    """Класс для отображения размерности такта"""
    
    def __init__(self, scene, x, y, numerator=4, denominator=4):
        self.scene = scene
        self.x = x
        self.y = y
        self.numerator = numerator
        self.denominator = denominator
        
        self.render()
    
    def render(self):
        """Отображает размерность такта на сцене"""
        # Создаем элемент текста для числителя
        numerator_text = QGraphicsTextItem(str(self.numerator))
        font = QFont("Arial", 24)
        font.setBold(True)
        numerator_text.setFont(font)
        
        # Позиционируем числитель
        numerator_text.setPos(self.x, self.y-10)
        self.scene.addItem(numerator_text)
        
        # Создаем элемент текста для знаменателя
        denominator_text = QGraphicsTextItem(str(self.denominator))
        denominator_text.setFont(font)
        
        # Позиционируем знаменатель под числителем
        denominator_text.setPos(self.x, self.y+14)
        self.scene.addItem(denominator_text)
    
    def update_signature(self, numerator, denominator):
        """Обновляет размерность такта"""
        self.numerator = numerator
        self.denominator = denominator
        # В реальном приложении нужно было бы обновить существующие элементы,
        # но для простоты мы просто перерисуем всю сцену


class BarLine:
    """Класс для вертикальных линий такта"""
    
    def __init__(self, scene, x, y_top, y_bottom):
        self.scene = scene
        self.x = x
        self.y_top = y_top
        self.y_bottom = y_bottom
        
        self.render()
    
    def render(self):
        """Отображает вертикальную линию такта на сцене"""
        # Создаем вертикальную линию
        line = QGraphicsLineItem(self.x, self.y_top, self.x, self.y_bottom)
        
        # Настраиваем перо для линии такта (толще обычных линий)
        pen = QPen(Qt.GlobalColor.black)
        pen.setWidthF(2.0)
        line.setPen(pen)
        
        self.scene.addItem(line)

class Tact:
    def __init__(self, x0, y0, y_bottom, width=None):
        self.tact_number = 1
        self.spaces = []
        self.x0 = x0
        self.y0 = y0
        self.y_bottom = y_bottom
        self.lines = []
        self.bar_lines = []  # Храним вертикальные линии тактов
        self.width: float = width if width else 400
        self.note_x = x0 + 40 if width else x0
        self.notes = []  # Список нот в такте
        self.scene = None
    
    def add_bar_lines(self, scene):
        """Добавляет вертикальные линии тактов"""
        # Добавляем левую тактовую черту (сразу после размерности такта)
        left_bar = BarLine(scene, self.x0 , self.y0, self.y_bottom)
        self.bar_lines.append(left_bar)
        
        # Добавляем правую тактовую черту (конечную)
        right_bar_x = self.x0 + self.width
        right_bar = BarLine(scene, right_bar_x, self.y0, self.y_bottom)
        self.bar_lines.append(right_bar)

    def get_note_positions(self):
        """Возвращает 4 равноудаленные позиции для нот в такте"""
        # Вычисляем расстояния между нотами и от краев
        # Для 4 нот в такте: 5 промежутков (2 от краев + 3 между нотами)
        if self.tact_number == 1:
            interval = (self.width - 40) / 5
        else:
            interval = self.width / 5
        # Позиции для 4 нот
        positions = []
        for i in range(4):
            # Первая нота на расстоянии interval от левого края,
            # каждая следующая еще +interval
            x = self.note_x + interval * (i + 1)
            positions.append(x)
        
        return positions
    
    def find_closest_note_position(self, click_x):
        """Находит ближайшую позицию для ноты из возможных 4"""
        note_positions = self.get_note_positions()
        
        # Находим ближайшую позицию
        closest_pos = min(note_positions, key=lambda x: abs(x - click_x))
        
        return closest_pos


    def add_note_at_position(self, click_x, line):
        """Добавляет ноту на ближайшую доступную позицию"""
        # Находим ближайшую позицию по X
        note_x = self.find_closest_note_position(click_x)
        
        # Проверяем, есть ли уже нота на этой позиции
        for note in self.notes:
            if abs(note.x - note_x) < 5:  # Если позиция уже занята (с небольшой погрешностью)
                # Удаляем существующую ноту
                self.scene.removeItem(note)
                self.scene.removeItem(note._stem_item)
                # Удаляем из списка
                self.notes.remove(note)
                return
        
        # Проверяем, не превышено ли максимальное количество нот
        note_sum = 0
        for note in self.notes:
            note_sum += note.note_lenght
        if note_sum == 1:
            return
        
        # Создаем ноту
        note_item = NoteItem(note_x, line.y, line.note_name)
        self.scene.addItem(note_item)
        
        # Добавляем штиль отдельно (NoteItem создает его, но не добавляет на сцену)
        self.scene.addItem(note_item._stem_item)
        
        # Сохраняем информацию о ноте
        self.notes.append(note_item)
    


class StaffLayout:
    def __init__(self):
        self.left_hand = False
        self.tacts = [] 
        self.x0: float = 60  # Отступ слева
        self.y0: float = 118  # Отступ сверху
        self.line_spacing: float = 12
        self.time_signature = None  # Будет хранить объект размерности такта
        self.current_tact = None
        self.bpm = 120
    
    @property
    def y_bottom(self) -> float:
        return self.y0 + 4 * self.line_spacing
    
    @property
    def staff_height(self) -> float:
        return 4 * self.line_spacing
    
    def init_staff(self):
        self.current_tact = Tact(self.x0, self.y0, self.y_bottom, 500)
        self.tacts.append(self.current_tact)
        # Создаем сцену с нужными размерами
        scene = QGraphicsScene(0, 0, 1, 1)
        
        self.current_tact.scene = scene
        # Сначала создаем пространства между линиями (4 пространства между 5 линиями)
        for i in range(4):
            # Рассчитываем координаты для пространства между линиями i и i+1
            y_top = self.y0 + i * self.line_spacing
            # Создаем прямоугольник для пространства
            space_rect = QRectF(self.x0, y_top, 500, self.line_spacing)
            space_item = StaffSpaceItem(space_rect, i)
            scene.addItem(space_item)
            self.current_tact.spaces.append(space_item)


        # Затем создаем 5 линий стана
        for i in range(6):
            y = self.y0 + i * self.line_spacing
            match i:
                case 0:
                    note_name = "F5"
                case 1: 
                    note_name = "D5"
                case 2: 
                    note_name = "B4"
                case 3: 
                    note_name = "G4"
                case 4: 
                    note_name = "E4"
                case 5: 
                    note_name = "C4"
            line_item = HighlightableLineItem(
                QLineF(self.x0, y, self.x0 + 500, y),
                self.current_tact,y, note_name
            )
            line_item.line_number = i  # Сохраняем номер для отладки
            scene.addItem(line_item)
            self.current_tact.lines.append(line_item)
        
        # Добавляем скрипичный ключ
        self.add_treble_clef(scene)
        
        # Добавляем размерность такта (4/4) после скрипичного ключа
        self.time_signature = TimeSignature(
            scene, 
            self.x0 + 50,  # Отступ от левого края после скрипичного ключа
            self.y0,   # Немного выше первой линии
            4, 4           # Размерность 4/4
        )
        
        # Добавляем вертикальные линии тактов
        self.current_tact.add_bar_lines(scene)
        return scene

    def add_treble_clef(self, scene):
        """Добавляет изображение скрипичного ключа на нотный стан"""
        try:
            # Загружаем изображение скрипичного ключа
            pixmap = QPixmap("photos/scrip.png")
            # Уменьшаем масштаб изображения, чтобы оно не было слишком большим
            target_height = self.line_spacing * 7  # Высота в 4.5 интервала (меньше чем было)
            
            # Масштабируем изображение
            scaled_pixmap = pixmap.scaledToHeight(
                int(target_height), 
                Qt.TransformationMode.SmoothTransformation
            )
            
            # Создаем элемент изображения
            clef_item = QGraphicsPixmapItem(scaled_pixmap)
            
            # Корректируем позицию для лучшего размещения
            x_pos = self.x0 + 5  # Сдвигаем чуть левее начала линий
            y_pos = self.y0 + 1.5 * self.line_spacing - target_height / 2.5
            
            clef_item.setPos(x_pos, y_pos)
            
            # Делаем скрипичный ключ неинтерактивным, чтобы не мешал наведению
            clef_item.setAcceptHoverEvents(False)
            
            # Добавляем на сцену
            scene.addItem(clef_item)
            
        except Exception as e:
            print(f"Ошибка при загрузке изображения скрипичного ключа: {e}")
