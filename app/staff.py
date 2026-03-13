from PyQt6.QtCore import Qt, QRectF, QLineF, QPointF
from PyQt6.QtGui import QPen, QBrush, QFont, QPixmap,QColor, QPainterPath
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
from schemas.lesson import LessonCreate, LessonResponse
import time
from test import player
import threading


class NoteItem(QGraphicsEllipseItem):
    def __init__(self, x, y, name, scene, duration, has_shtil=True, reversing=False, bit=None):
        super().__init__()
        self.note_lenght = duration
        self.note_name = name
        self.x = x
        self.y = y
        self.width = 12
        self.height = 10
        self.reversing = reversing
        self.scene = scene
        self.bit = bit
        self.flag_path = None
        self.setRect(QRectF(x - self.width/2, y - self.height/2, 
                           self.width, self.height))
        self.setBrush(QBrush(Qt.GlobalColor.black))
        self.setPen(QPen(Qt.GlobalColor.black))
        self.prev_note = None   # первая нота в группе (для себя)
        self.next_note = None    # последняя нота в группе

    # def stem_x(self):
    #     return int(self.x + self.width/2 - 1) if not self.reversing else int(self.x - self.width/2 - 1)

    # def stem_y_top(self):
    #     return self.y - 32 if not self.reversing else self.y + 32



    def boundingRect(self):
        rect = super().boundingRect()
        return rect.adjusted(-self.width, -32, self.width, self.height/2)


    def paint(self, painter: QPainter, option, widget):
        super().paint(painter, option, widget)
        painter.setPen(QPen(Qt.GlobalColor.black, LINE_WIDTH, Qt.PenStyle.SolidLine))
        stem_x = int(self.x + self.width/2 - 1) if not self.reversing else int(self.x - self.width/2 - 1)
        stem_y_top = self.y - 32
        painter.drawLine(stem_x, self.y, stem_x, stem_y_top)
        match self.note_lenght:
            case 0.125:
                if not self.reversing:
                    self.flag_path = self.computeFlagPath()
                    painter.drawPath(self.flag_path)
                


    def computeFlagPath(self):
        """Строит QPainterPath для флажка (восьмая нота)."""
        ax = int(self.x + self.width/2 - 1) if not self.reversing else int(self.x - self.width/2 - 1)
        ay = self.y - 32
        sign_x = 1
        sign_y = 1 
        # ---- Верхняя кривая (A -> B) ----
        # Координаты B
        bx = ax + sign_x * 10
        by = ay + sign_y * 20
        # Контрольные точки верхней
        up_c1 = (ax + sign_x * 0, ay + sign_y * 20)
        up_c2 = (ax + sign_x * 10, ay + sign_y * 10)
        # ---- Нижняя кривая (B -> A) ----
        # Контрольные точки (абсолютные координаты от A)
        low_c1 = (ax + sign_x * 8, ay + sign_y * 10)   # первая контрольная (от B)
        low_c2 = (ax + sign_x * 0, ay + sign_y * 23)   # вторая контрольная (от A)
        # Конечная точка - A (ax, ay)
        # ---- Замкнутый путь ----
        path = QPainterPath()
        path.moveTo(ax, ay)
        # Верхняя сторона
        path.cubicTo(up_c1[0], up_c1[1], up_c2[0], up_c2[1], bx, by)
        # Нижняя сторона (обратно к A)
        path.cubicTo(low_c1[0], low_c1[1], low_c2[0], low_c2[1], ax, ay)
        path.closeSubpath()
        return path


    def mousePressEvent(self, event) -> None:
        event.accept()
        self.bit.update_notes(self)
        self.scene.removeItem(self)
        if self.bit.tact:
            self.bit.tact.update_beams()
        self.scene.update()
        del self


    def reverse(self):
        self.x -= self.width
        self.setRect(QRectF(self.x - self.width/2, self.y-self.height/2, self.width,
                        self.height))
        self.reversing = False
        self.scene.update()




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

    def __init__(self, rect, x0, x1, tact=None, weigth=0.25, parent=None):
        super().__init__(rect, parent)
        self.notes = []
        self.x0 = x0
        self.x1 = x1
        self.weigth = weigth
        self.full = False
        self.tact = tact
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
        if self.weigth == 0.25:
            for note in self.notes:
                if abs(note.y - line.y) <= 6 and note != line:
                    print(note.y, "note", line.y, "line")
                    return 0 if note.reversing else 12
                elif abs(note.y - line.y) <= 12 and note != line:
                    return 12 if note.reversing else 0
            return None
        elif self.weigth == 0.125:
            for note in self.notes:
                if abs(note.y - line.y) <= 6:
                    if line.y > note.y:
                        return 0 if note.reversing else 12
                    

    def update_notes(self, note:NoteItem):
        if note.note_lenght == 0.25:
            self.notes.remove(note)
            for active_note in self.notes:
                if self.has_upper_or_lower(active_note) is None and abs(active_note.y - note.y) <= 6 and active_note.reversing:
                    active_note.reverse()

            




    def add_note(self, note):
        if note.note_lenght != self.weigth:
            return False
        note.bit = self
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
        self.duration = 0.25
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
            bit = Bits(QRectF(x_left, Y0, x1-x_left, self.y_bottom-Y0), x_left, x1,tact=self)
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
                break
        if len(item.notes) == 5:
            return
        if not item.isExist_note(line):
            if (rev:=item.has_upper_or_lower(line)) is None:
                note_item = NoteItem(item.x0+15, line.y, line.note_name, self.scene, self.duration) 
            else:
                note_item = NoteItem(item.x0+15+rev, line.y, line.note_name,self.scene, self.duration, False, True if rev>0 else False)
            if item.add_note(note_item):
                self.scene.addItem(note_item)
                self.update_beams()


    def update_beams(self):
        # Сброс групповых атрибутов у всех нот
        for bit in self.bits:
            for note in bit.notes:
                note.group_first = None
                note.group_last = None

        # Словарь активных групп: имя ноты -> список нот
        active_groups = {}
        groups = []

        for bit in self.bits:
            # Все восьмые ноты в текущем бите
            current_notes = [n for n in bit.notes if n.note_lenght == 0.125]

            # Закрываем группы, которые не получили продолжения
            for name in list(active_groups.keys()):
                if not any(n.note_name == name for n in current_notes):
                    groups.append(active_groups.pop(name))

            # Обрабатываем текущие ноты
            for note in current_notes:
                name = note.note_name
                if name in active_groups:
                    active_groups[name].append(note)
                else:
                    active_groups[name] = [note]

        # Закрываем оставшиеся группы
        for group in active_groups.values():
            groups.append(group)

        # Для каждой группы длиной >1 устанавливаем связи
        for group in groups:
            if len(group) > 1:
                first = group[0]
                last = group[-1]
                first.group_first = first
                first.group_last = last
                for note in group[1:]:
                    note.group_first = first
                    note.group_last = last
        


class StaffLayout:
    def __init__(self, scene):
        self.left_hand = False
        self.tacts = []
        self.time_signature = None  # Будет хранить объект размерности такта
        self.current_tact = None
        self.bpm = 60
        self.scene = scene
        self.current_duration = 0.25
        self.init_staff(scene)
    
    @property
    def y_bottom(self) -> float:
        return Y0 + 4 * LINE_SPACING
    
    @property
    def staff_height(self) -> float:
        return 4 * LINE_SPACING
    
    def set_duration(self, duration):
        # if duration == "0.125":
        passed = False
        for tact in self.tacts:
            tact.duration = duration
            new_bits = []
            for i, bit in enumerate(tact.bits):
                if duration < self.current_duration:
                    if not bit.notes and not bit.weigth == duration:
                        width = int((bit.x1-bit.x0)/2)
                        new_bits.extend([
                            Bits(QRectF(bit.x0, Y0, width, self.y_bottom-Y0), bit.x0, bit.x0+width,weigth=duration),
                            Bits(QRectF(bit.x0+width, Y0, width, self.y_bottom-Y0), bit.x0+width+1, bit.x1,weigth=duration)]
                            )
                        self.scene.removeItem(bit)
                    else:
                        new_bits.append(bit)
                else:
                    print(f"{i} увеличиваем размерность бита")
                    if not passed:
                        print(f"{i} этот бит не удален")
                        if not bit.notes and not bit.weigth == duration:
                            print(f"в {i} бите нет нот")
                            try:
                                next_bit = tact.bits[i+1]
                                print(f"{i} после него есть бит")
                                if not next_bit.notes:
                                    print(f"{i} в следующем бите нет нот")
                                    width = int((next_bit.x1-bit.x0))
                                    new_bits.append(Bits(QRectF(bit.x0, Y0, width, self.y_bottom-Y0), bit.x0, bit.x0+width,weigth=duration))
                                    passed = True
                                    self.scene.removeItem(bit)
                            except Exception as e:
                                print(e)
                                print(f"{i} этот последний бит")
                                new_bits.append(bit)
                                continue
                        else:
                            print(f"{i} этот бит заполнен не трогаем его")
                            new_bits.append(bit)
                    else:
                        print(f"{i} этот бит удален")
                        passed = False
                        self.scene.removeItem(bit)
                del bit
            tact.bits = new_bits
            for item in new_bits:
                self.scene.addItem(item)
        self.scene.update()
        self.current_duration = duration
                        



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
            name="ыдловрап",
            difficult="легко",
            rhythm=4/4,
            notes = {"right_hand": []},
            topic=1
        )
        for tact in self.tacts:
            all_notes = []
            for bit in tact.bits:
                validate_notes=[]
                for notes in bit.notes:
                    # for note in notes:
                        validate_notes.append({"name":notes.note_name, "duration":notes.note_lenght})
                all_notes.append(validate_notes)
            lesson.notes["right_hand"] = all_notes
        return lesson
    

    def display_lesson(self, lesson: LessonResponse):
        tacts = lesson.notes["right_hand"]
        for item in self.tacts[0].lines + self.tacts[0].spaces:
            for i, bit in enumerate(tacts):
                for note in bit:
                    if note["name"] == item.note_name:
                        self.tacts[0].add_note_at_position(self.tacts[0].bits[i].x0+10, item)


        # print(tacts)
        # for bit, bit_self in tacts, self.tacts.bits:
        #     for note in bit:
        #         self.tact.add_note_at_position(bit_self.x0+10)

    def touch_thread(self):
        for tact in self.tacts:
            for bit in tact.bits:
                if bit.notes:
                    # Берём первую ноту в бите (для простоты)
                    note_item = bit.notes[0]
                    player.start_waiting_for_note(note_item.note_name, note_item)
                    duration = 60 / self.bpm   # длительность четверти (одна бита)
                    time.sleep(duration)

    def sound_thread(self):
            time.sleep(0.4)
            for tact in self.tacts:
                for bit in tact.bits:
                    if bit.notes:
                        duration = 60/self.bpm * bit.weigth * 4
                        chord_notes = [note.note_name for note in bit.notes]
                        player.play_chord(chord_notes, duration)
                    time.sleep(duration)

    def start_lesson(self):
        threading.Thread(target=self.touch_thread, daemon=True).start()
        threading.Thread(target=self.sound_thread, daemon=True).start()
