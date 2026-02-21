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
from config import *
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from schemas.lesson import LessonCreate

class NoteItem(QGraphicsEllipseItem):
    def __init__(self, x, y, name, has_shtil=True, reversing=False):
        super().__init__()
        self.note_lenght = 1/4
        self.note_name = name
        self.x = x
        self.y = y
        self.width = 12
        self.height = 10
        self.shtil = has_shtil
        self.reversing = reversing
        
        # Устанавливаем rect овала
        self.setRect(QRectF(x - self.width/2, y - self.height/2, 
                           self.width, self.height))
        self.setBrush(QBrush(Qt.GlobalColor.black))
        self.setPen(QPen(Qt.GlobalColor.black))

    def boundingRect(self):
        # Учитываем штиль (выше овала на 32px) и крест (по ширине овала)
        rect = super().boundingRect()
        return rect.adjusted(-self.width/2, -32, self.width/2, self.height/2)

    def paint(self, painter: QPainter, option, widget):
        # Рисуем овал (автоматически от super())
        super().paint(painter, option, widget)
        if self.shtil:
            # Штиль
            painter.setPen(QPen(Qt.GlobalColor.black, LINE_WIDTH, Qt.PenStyle.SolidLine))
            stem_x = int(self.x + self.width/2 - 1)
            stem_y_top = self.y - 32
            painter.drawLine(stem_x, self.y, stem_x, stem_y_top)
        
        # Крест (для C4)
        if self.note_name in ["C4"]:
            cross_y = self.y
            painter.drawLine(self.x - self.width, cross_y, self.x + self.width, cross_y)





class HighlightableLineItem(QGraphicsLineItem):
    """Класс линии, которая подсвечивается при наведении"""
    
    def __init__(self, line:QLineF, tact, y, note_name, transparent=False, parent=None):
        super().__init__(line, parent)
        self.line_obj = line   
        self.tact = tact
        self.y = y
        # Стандартные параметры линии
        self.normal_pen = QPen(Qt.GlobalColor.transparent) if transparent else  QPen(Qt.GlobalColor.black)
        self.normal_pen.setWidthF(LINE_WIDTH)
        
        # Параметры при наведении
        self.hover_pen = QPen(QColor(255, 0, 0))  # Красный цвет
        self.hover_pen.setWidthF(LINE_WIDTH*1.5)  # Толще обычной линии
        
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
        # line = self.line_obj
        # self.setLine(line.x1(), line.y1(), line.x2()+200, line.y2())
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update()  # Принудительное обновление
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        """Событие при уходе курсора"""
        self.is_hovered = False
        self.setPen(self.normal_pen)
        # self.setLine(self.line_obj)
        self.unsetCursor()
        self.update()  # Принудительное обновление
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        """Обработка клика на линии"""
        if event.button() == Qt.MouseButton.LeftButton and self.is_hovered:
            # Получаем позицию клика
            pos = event.pos()
            scene_pos = self.mapToScene(pos)
            # Сообщаем такту, что нужно добавить ноту на этой линии
            self.tact.add_note_at_position(scene_pos.x(), self)
        
        super().mousePressEvent(event)


class StaffSpaceItem(QGraphicsRectItem):
    """Класс для пространства между линиями нотного стана"""
    
    def __init__(self, rect, space_number, tact, note_name, y, parent=None):
        super().__init__(rect, parent)
        self.tact = tact
        self.note_name = note_name
        self.y = y
        # Сохраняем номер пространства 
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

    def mousePressEvent(self, event):
        """Обработка клика на линии"""
        if event.button() == Qt.MouseButton.LeftButton and self.is_hovered:
            # Получаем позицию клика
            pos = event.pos()
            scene_pos = self.mapToScene(pos)
            # Сообщаем такту, что нужно добавить ноту на этой линии
            self.tact.add_note_at_position(scene_pos.x(), self)
        
        super().mousePressEvent(event)


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
        font = QFont("Arial", 26)
        font.setBold(True)
        numerator_text.setFont(font)
        
        # Позиционируем числитель
        numerator_text.setPos(self.x, self.y-12)
        self.scene.addItem(numerator_text)
        
        # Создаем элемент текста для знаменателя
        denominator_text = QGraphicsTextItem(str(self.denominator))
        denominator_text.setFont(font)
        
        # Позиционируем знаменатель под числителем
        denominator_text.setPos(self.x, self.y+12)
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
        line = QGraphicsLineItem(self.x, self.y_top+0.6, self.x, self.y_bottom-0.6)
        
        # Настраиваем перо для линии такта (толще обычных линий)
        pen = QPen(Qt.GlobalColor.black)
        pen.setWidthF(2.0)
        line.setPen(pen)
        
        self.scene.addItem(line)


class Bits(QGraphicsRectItem):

    def __init__(self, rect, x0, x1,parent=None):
        super().__init__(rect, parent)
        self.notes = []
        self.x0 = x0
        self.x1 = x1
        self.weigth = 0
        self.max_weigth = 1/4
        self.full = False
        # self.y0 = Y0
        # self.y1 = y1

        self.normal_brush = QBrush(Qt.GlobalColor.transparent)
        self.normal_pen = QPen(QColor(100, 100, 100, 50),1.5, Qt.PenStyle.SolidLine)
        # self.normal_pen.width()

        self.setBrush(self.normal_brush)
        self.setPen(self.normal_pen)

    def isExist_note(self, line: StaffSpaceItem | HighlightableLineItem):
        for note in self.notes:
            if note.note_name == line.note_name:
                return True
        return False


    def has_upper_or_lower(self, line):
        for note in self.notes:
            if abs(note.y - line.y) <= 6:
                print(note.y, "note", line.y, "line")
                return 0 if note.reversing else 8
        return None

    def add_note(self, note):
        if note.note_lenght > self.max_weigth:
            return False
        self.notes.append(note)
        return True





class Tact:
    def __init__(self,y_bottom,scene,number):
        self.tact_number = number
        self.bits_count = 4
        self.x0 = X0*(number+1)
        self.spaces = []
        self.width = WIDTH if number > 0 else WIDTH + 100
        self.y_bottom = y_bottom
        self.note_x = X0 if number > 0 else X0 + 100
        self.lines = []
        self.bar_lines = []  # Храним вертикальные линии тактов
        self.notes = []  # Список нот в такте
        self.scene = scene
        self.bits = []
        self.current_bit = 0
        self.init_bits()
        self.init_tact()
    

    def init_tact(self):
    # Сначала создаем пространства между линиями (4 пространства между 5 линиями)
        for i in range(5):
            y_top = Y0 + i * LINE_SPACING
            space_rect = QRectF(X0, y_top, self.width, LINE_SPACING)
            match i:
                case 0:
                    note_name = "E5"
                case 1:
                    note_name = "C5"
                case 2:
                    note_name = "A4"
                case 3:
                    note_name = "F4"
                case 4:
                    note_name = "D4"
            space_item = StaffSpaceItem(space_rect, i, self, note_name, int(y_top+LINE_SPACING/2))
            self.scene.addItem(space_item)
            self.spaces.append(space_item)
        # Затем создаем 5 линий стана
        for i in range(6):
            y = Y0 + i * LINE_SPACING
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
                    QLineF(X0, y, X0 + self.width, y),
                    self,y, note_name, transparent=True
                )
            if i != 5:
                line_item = HighlightableLineItem(
                    QLineF(X0, y, X0 + self.width, y),
                    self,y, note_name
                )
            line_item.line_number = i
            self.scene.addItem(line_item)
            self.lines.append(line_item)
            self.add_bar_lines()


    def init_bits(self):
        count_bits = self.bits_count
        if self.tact_number == 0:
            x_left = self.x0+100
        else:
            x_left = self.x0
        for i in range(1, count_bits+1):
            if self.tact_number == 0:
                x1 = int((self.width - 100)/count_bits*i+self.x0+100)
            else:
                x1 = int(self.width/count_bits*i+self.x0)
            bit = Bits(QRectF(x_left, Y0, x1-x_left, self.y_bottom-Y0), x_left, x1)
            x_left = x1
            self.bits.append(bit)
            self.scene.addItem(bit)


    def add_bar_lines(self):
        """Добавляет вертикальные линии тактов"""
        # Добавляем левую тактовую черту (сразу после размерности такта)
        scene = self.scene
        left_bar = BarLine(scene, X0 , Y0, self.y_bottom)
        self.bar_lines.append(left_bar)
        # Добавляем правую тактовую черту (конечную)
        right_bar_x = X0 + self.width
        right_bar = BarLine(scene, right_bar_x, Y0, self.y_bottom)
        self.bar_lines.append(right_bar)



    def add_note_at_position(self, click_x, line):
        """Добавляет ноту на ближайшую доступную позицию"""
        if not int(click_x) in range(self.note_x, self.note_x+self.width):
            return
        for bit in self.bits:
            if int(click_x) in range(bit.x0, bit.x1):
                item = bit
        if not item.isExist_note(line):
            if (rev:=item.has_upper_or_lower(line)) is None:
                note_item = NoteItem(item.x0+15, line.y, line.note_name) 
            else:
                note_item = NoteItem(item.x0+15+rev, line.y, line.note_name, False, True if rev>0 else False)
            if item.add_note(note_item):
                self.scene.addItem(note_item)
        


class StaffLayout:
    def __init__(self, scene):
        self.left_hand = False
        self.tacts = []
        self.time_signature = None  # Будет хранить объект размерности такта
        self.current_tact = None
        self.bpm = 120
        self.scene = scene
        self.init_staff(scene)
    
    @property
    def y_bottom(self) -> float:
        return Y0 + 4 * LINE_SPACING
    
    @property
    def staff_height(self) -> float:
        return 4 * LINE_SPACING
    
    def init_staff(self, scene):
        self.current_tact = Tact(self.y_bottom, scene, len(self.tacts))
        self.tacts.append(self.current_tact)
        # Добавляем скрипичный ключ
        self.add_treble_clef(scene)
        # Добавляем размерность такта (4/4) после скрипичного ключа
        self.time_signature = TimeSignature(
            scene, 
            X0 + 50,  # Отступ от левого края после скрипичного ключа
            Y0,   # Немного выше первой линии
            4, 4           # Размерность 4/4
        )

    def add_treble_clef(self, scene):
        """Добавляет изображение скрипичного ключа на нотный стан"""
        pixmap = QPixmap("app/photos/output.png")
        target_height = LINE_SPACING * 7  # Высота в 4.5 интервала (меньше чем было)
        scaled_pixmap = pixmap.scaledToHeight(
            int(target_height), 
            Qt.TransformationMode.SmoothTransformation
        )

        clef_item = QGraphicsPixmapItem(scaled_pixmap)
        # Корректируем позицию для лучшего размещения
        x_pos = X0 + 5  # Сдвигаем чуть левее начала линий
        y_pos = Y0 + 1.5 * LINE_SPACING - target_height / 2.5
        clef_item.setPos(x_pos, y_pos)
        # Делаем скрипичный ключ неинтерактивным, чтобы не мешал наведению
        clef_item.setAcceptHoverEvents(False)
        # Добавляем на сцену
        scene.addItem(clef_item)

    def save_lesson(self):
        lesson = LessonCreate(
            name="Первый тестовый урок111111111",
            difficult="легко",
            rhythm=4/4,
            notes = {"right_hand": []},
            topic=1
        )
        for tact in self.tacts:
            notes = []
            for note in tact.notes:
                notes.append({"name":note.note_name, "duration":note.note_lenght})
            lesson.notes["right_hand"].append(notes)
        return lesson
    

    def check_full(self):
        ...

