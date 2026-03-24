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
    def __init__(self, x, y, name, scene, duration, has_shtil=False, reversing=False, bit=None):
        super().__init__(parent=bit)
        self.note_lenght = duration
        self.note_name = name
        self.x = x
        self.y = y
        self.width = 12
        self.height = 10
        self.shtil = has_shtil
        self.reversing = reversing
        self.scene = scene
        self.bit = bit
        self.flag_path = None
        self.tilt_angle = -15   # угол наклона в градусах

        # Устанавливаем прямоугольник для коллизий и bounding rect (не используется для рисования)
        self.setRect(QRectF(x - self.width/2, y - self.height/2, self.width, self.height))
        
        if duration < 0.5:
            self.setBrush(QBrush(Qt.GlobalColor.black))
        self.setPen(NORMAL_PEN)
        self.prev_note = None
        self.next_note = None
        self.stem_x = int(self.x + self.width/2) if not self.reversing else int(self.x - self.width/2)

    def paint(self, painter: QPainter, option, widget):
        # Рисуем головку ноты с наклоном
        painter.save()
        painter.translate(self.x, self.y)
        painter.rotate(self.tilt_angle)
        painter.setBrush(self.brush())
        painter.setPen(self.pen())
        painter.drawEllipse(QRectF(-self.width/2, -self.height/2, self.width, self.height))
        painter.restore()

        if self.note_lenght != 1:
            # Рисуем штиль и бим (без наклона)
            stem_y_top = self.y - 32
            painter.drawLine(self.stem_x, self.y, self.stem_x, stem_y_top)
            match self.note_lenght:
                case 0.125:
                    if self.shtil:
                        self.flag_path = self.computeFlagPath()
                        painter.drawPath(self.flag_path)
                    elif self.next_note:
                        beam_pen = QPen(Qt.GlobalColor.black, 3.2)
                        beam_pen.setCapStyle(Qt.PenCapStyle.FlatCap)
                        painter.setPen(beam_pen)
                        painter.drawLine(self.stem_x, self.y-32, self.next_note.stem_x, self.next_note.y-32)

    # Остальные методы (boundingRect, computeFlagPath, mousePressEvent и т.д.) без изменений

    def computeFlagPath(self):
        """Строит QPainterPath для флажка (восьмая нота)."""
        ax = self.stem_x
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
        self.bit.remove_note(self)
        self.scene.removeItem(self)
        self.scene.update()
        del self


    def reverse(self, reverse):
        if self.reversing == reverse:
            return
        self.reversing = reverse
        if self.reversing:
            self.x += self.width
        else:
            self.x -= self.width
        self.setRect(QRectF(self.x - self.width/2, self.y - self.height/2, 
                           self.width, self.height))
        self.update()


    def remove_shtil(self):
        self.shtil = False
        self.update()

    def create_shtil(self):
        self.shtil = True
        self.update()

    # def delete_prev(self):
    #     self.prev_note = None
    #     self.



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
    
    
    def has_near_note(self, note_):
        for note in self.notes:
            if abs(note.y - note_.y) <= 6 and note != note_:
                return True
            elif abs(note.y - note_.y) <= 12 and note != note_:
                return False
        return False


    def update_notes(self):
        pred_note = None
        linked_note_next = None
        linked_note_prev = None
        for note in self.notes:
            if pred_note:
                pred_note.remove_shtil()
                if abs(note.y - pred_note.y) <= 6:
                    note.reverse(not pred_note.reversing)
                elif note.reversing:
                    note.reverse(False)
            elif note.reversing:
                note.reverse(False)
            pred_note = note
            if n:=note.prev_note:
               linked_note_prev,n = n,linked_note_prev
            if n:=note.next_note: 
                print("эта нота левая в соединении")
                linked_note_next,note.next_note = note.next_note,linked_note_next
        if self.notes:
            last_note = self.notes[-1]
            last_note.create_shtil()
            last_note.next_note = linked_note_next
            last_note.prev_note = linked_note_prev
        else:
            self.tact.change_bits(self)
        self.tact.update_beams()
        

            
    def remove_note(self, note):
        self.notes.remove(note)
        if note.note_lenght == 0.125:
            if next:= note.next_note:
                next.prev_note = None
                next.shtil= True
                next.update()
            elif prev:=note.prev_note:
                prev.shtil= True
                prev.next_note = None
                prev.update()
        self.update_notes()


    def add_note(self, duration, line, scene):
        print(duration, self.weigth)
        if duration != self.weigth:
            return False
        if self.isExist_note(line):
            return False
        note_item = NoteItem(
            self.x0+15, 
            line.y, 
            line.note_name,
            scene, 
            duration, 
            bit=self)
        self.notes.append(note_item)
        self.notes.sort(key=lambda note:note.y, reverse=True)
        self.update_notes()
        return note_item



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
                x1 = (self.width - 100)/count_bits*i+self.x0+100
            else:
                x1 = self.width/count_bits*i+self.x0
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
        if not self.x0 <= click_x <= self.x0 + self.width:
            return
        for bit in self.bits:
            if bit.x0 <= click_x <= bit.x1:
                item = bit
                break
        else:
            return
        if len(item.notes) == 5:
            return
        if note := item.add_note(self.duration, line, self.scene):
            self.scene.addItem(note)


    def update_beams(self):
        pred_bit = None
        for bit in self.bits:
            print(bit.x0, bit.x1)
            if bit.notes:
                if pred_bit:
                    if bit.weigth == pred_bit.weigth == 0.125:
                        pred_note = pred_bit.notes[-1]
                        current_note = bit.notes[-1]
                        if pred_note.prev_note:
                            pred_bit = bit
                            continue
                        pred_note.remove_shtil()
                        pred_note.next_note = current_note
                        current_note.prev_note = pred_note
                        if current_note.next_note:
                            current_note.next_note.create_shtil()
                            current_note.next_note.prev_note = None
                            current_note.next_note = None
                        current_note.remove_shtil()
                        pred_note.update()
                        pred_bit = bit
                    else:
                        pred_bit = bit
                else:
                    pred_bit = bit
            else:
                pred_bit = None
        self.scene.update()


    def increase_duration(self, duration):
        self.duration *= 2
        available_bit = None
        new_bits = []
        for bit in self.bits:
            if available_bit:
                print("есть пустой бит")
                if bit.notes:
                    print("в этом бите есть ноты, оставляем не тронутым, пустой бит сбрасывается")
                    new_bits.append(available_bit)
                    new_bits.append(bit)
                    available_bit = None
                    continue
                if bit.weigth == available_bit.weigth:
                    print("биты одинаковой длительности, их можно сложить")
                    width = (bit.x1-available_bit.x0)
                    new_bits.append(Bits(QRectF(available_bit.x0, 
                                                Y0, 
                                                width, 
                                                self.y_bottom-Y0), 
                                            available_bit.x0, 
                                            available_bit.x0+width,
                                            weigth=self.duration, 
                                            tact=self))
                    self.scene.addItem(new_bits[-1])
                    self.scene.removeItem(bit)
                    self.scene.removeItem(available_bit)
                    available_bit = None
            elif not bit.notes:
                print("пустого бита нет, добавляем существующий если нет нот в нем")
                available_bit = bit
            else:
                new_bits.append(bit)
        if available_bit:
            new_bits.append(available_bit)
        self.bits = new_bits
        if self.duration != duration:
            self.increase_duration(duration)
                    

    def change_bits(self, empty_bit):
        """Обрабатывает изменения битов: объединяет пустые биты одинаковой длительности или разбивает слишком большие пустые биты."""
        # Если бит пуст и его длительность больше текущей (требуется разбиение)
        if not empty_bit.notes and empty_bit.weigth > self.duration:
            # Разбиваем на несколько битов текущей длительности
            ratio = int(empty_bit.weigth / self.duration)
            if ratio > 1:
                new_width = (empty_bit.x1 - empty_bit.x0) / ratio
                new_bits = []
                x = empty_bit.x0
                for i in range(ratio):
                    new_bit = Bits(
                        QRectF(x, Y0, new_width, self.y_bottom - Y0),
                        x, x + new_width,
                        weigth=self.duration,
                        tact=self
                    )
                    self.scene.addItem(new_bit)
                    new_bits.append(new_bit)
                    x += new_width
                # Удаляем старый бит
                self.scene.removeItem(empty_bit)
                # Заменяем старый бит в списке на новые
                idx = self.bits.index(empty_bit)
                self.bits.pop(idx)
                for new_bit in reversed(new_bits):
                    self.bits.insert(idx, new_bit)
                # После разбиения возможны дальнейшие объединения с соседями, но это уже будет обработано при последующих вызовах
                # (например, если соседние биты тоже пусты и той же длительности)
                return

        # Старая логика объединения соседей (как ранее)
        # Находим индекс пустого бита в списке битов такта
        try:
            idx = self.bits.index(empty_bit)
        except ValueError:
            return

        # Проверяем левого соседа
        left_idx = idx - 1
        if left_idx >= 0 and self.bits[left_idx].weigth == empty_bit.weigth and not self.bits[left_idx].notes:
            left_bit = self.bits[left_idx]
            new_x0 = left_bit.x0
            new_x1 = empty_bit.x1
            new_weigth = left_bit.weigth * 2
            new_bit = Bits(
                QRectF(new_x0, Y0, new_x1 - new_x0, self.y_bottom - Y0),
                new_x0, new_x1, weigth=new_weigth, tact=self
            )
            self.scene.addItem(new_bit)
            self.scene.removeItem(left_bit)
            self.scene.removeItem(empty_bit)
            self.bits.pop(left_idx)
            self.bits.pop(left_idx)
            self.bits.insert(left_idx, new_bit)
            self.change_bits(new_bit)  # рекурсивно
            return

        # Проверяем правого соседа
        right_idx = idx + 1
        if right_idx < len(self.bits) and self.bits[right_idx].weigth == empty_bit.weigth and not self.bits[right_idx].notes:
            right_bit = self.bits[right_idx]
            new_x0 = empty_bit.x0
            new_x1 = right_bit.x1
            new_weigth = empty_bit.weigth * 2
            new_bit = Bits(
                QRectF(new_x0, Y0, new_x1 - new_x0, self.y_bottom - Y0),
                new_x0, new_x1, weigth=new_weigth, tact=self
            )
            self.scene.addItem(new_bit)
            self.scene.removeItem(empty_bit)
            self.scene.removeItem(right_bit)
            # Индексы: сначала удаляем правый, потом пустой (индекс пустого смещается после удаления правого?)
            # Удаляем правый, индекс idx остаётся действительным, пока мы не удалили empty_bit
            self.bits.pop(right_idx)
            self.bits.pop(idx)
            self.bits.insert(idx, new_bit)
            self.change_bits(new_bit)
            return

        # Если соседей для объединения нет, ничего не делаем



    def decrease_duration(self, duration):
        if self.duration != duration: self.duration /= 2
        new_bits = []
        for bit in self.bits:
            if not bit.notes and not bit.weigth <= duration:
                width = (bit.x1-bit.x0)/2
                new_bits.extend([
                    Bits(QRectF(bit.x0, Y0, width, self.y_bottom-Y0), bit.x0, bit.x0+width,weigth=bit.weigth/2, tact=self),
                    Bits(QRectF(bit.x0+width, Y0, width, self.y_bottom-Y0), bit.x0+width+1, bit.x1,weigth=bit.weigth/2, tact=self)]
                    )
                self.scene.addItem(new_bits[-2])
                self.scene.addItem(new_bits[-1])
                self.scene.removeItem(bit)
            else:
                new_bits.append(bit)
        self.bits = new_bits
        if self.duration != duration:
            self.decrease_duration(duration) 


        


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
        if duration > self.current_duration:
            print("объединяем ячейки")
            self.current_duration = duration
            for tact in self.tacts:
                tact.increase_duration(duration)
        else:
            print("разделяем ячейки")
            self.current_duration = duration
            for tact in self.tacts:
                tact.decrease_duration(duration)
        self.scene.update()
                        



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
