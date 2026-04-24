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
from PyQt6.QtSvgWidgets import QGraphicsSvgItem
from config import *
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from schemas.lesson import LessonCreate, LessonResponse
import time
from test import player
import threading


class LaySettings:
    def __init__(self):
        self.accidental = "natural"
        self.scene = None

settings = LaySettings()


class NoteItem(QGraphicsEllipseItem):
    def __init__(self, 
                 x, 
                 y, 
                 name, 
                 scene, 
                 duration, 
                 has_shtil=False, 
                 reversing=False, 
                 bit=None):
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
        self.accidental = settings.accidental
        self.accidental_item = None
        self.setZValue(10)
        if duration < 0.5:
            self.setBrush(QBrush(Qt.GlobalColor.black))
        self.setPen(NORMAL_PEN)
        self.prev_note = None
        self.next_note = None
        self.stem_x = int(self.x + self.width/2) if not self.reversing else int(self.x - self.width/2)


    def delete_accidental(self):
        if self.accidental_item:
            self.scene.removeItem(self.accidental_item)
            self.accidental_item = None

    def draw_accidental(self, index):
        # Удаляем старый знак, если был
        if self.accidental_item is not None:
            self.scene.removeItem(self.accidental_item)
            self.accidental_item = None
        if self.accidental == "natural" and index == 0:
            return
        # Обычные знаки (sharp, flat)
        symbol = self._accidental_to_symbol(self.accidental)
        if not self.note_name.endswith(symbol):
            self.note_name += symbol
        svg_path = f"app/photos/{self.accidental}.svg"
        acc_item = QGraphicsSvgItem(svg_path)
        # Масштабирование и позиционирование (твой существующий код)
        original_rect = acc_item.boundingRect()
        if self.accidental == "sharp":
            target_height = 15.0
            x_pos = self.x - 20
            y_pos = self.y - 8
        else:
            target_height = 25.0
            x_pos = self.x - 18
            y_pos = self.y - 17

        scale_factor = target_height / original_rect.height()
        acc_item.setScale(scale_factor)
        acc_item.setPos(x_pos, y_pos)
        acc_item.setAcceptHoverEvents(False)
        self.scene.addItem(acc_item)
        self.accidental_item = acc_item
        self.update()


    def delete(self):
        self.bit.remove_note(self)   # внутри remove_note вызовется пересчёт
        self.scene.removeItem(self)
        self.scene.removeItem(self.accidental_item)
        self.scene.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.delete()
            return
        self.accidental = settings.accidental
        self.bit.recalculate_accidental(self)


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



    def _add_accidental(self, acc_type, display=True):
        # Удаляем старый знак, если был
        if self.accidental_item is not None:
            self.scene.removeItem(self.accidental_item)
            self.accidental_item = None

        if acc_type == "natural":
            # Бекар – только если display=True (пользователь явно поставил)
            if display:
                svg_path = "app/photos/natural.svg"
                acc_item = QGraphicsSvgItem(svg_path)
                target_height = 15.0
                x_pos = self.x - 20
                y_pos = self.y - 10
                original_rect = acc_item.boundingRect()
                scale_factor = target_height / original_rect.height()
                acc_item.setScale(scale_factor)
                acc_item.setPos(x_pos, y_pos)
                self.scene.addItem(acc_item)
                self.accidental_item = acc_item
            self.accidental = "natural"
            # Убираем символ из имени ноты (natural не добавляет символ)
            # ... (код удаления символа, если был)
            self.update()
            return

        # Обычные знаки (sharp, flat)
        symbol = self._accidental_to_symbol(acc_type)
        if not self.note_name.endswith(symbol):
            self.note_name += symbol
        self.accidental = acc_type

        if display:
            svg_path = f"app/photos/{acc_type}.svg"
            acc_item = QGraphicsSvgItem(svg_path)

            # Масштабирование и позиционирование (твой существующий код)
            original_rect = acc_item.boundingRect()
            if acc_type == "sharp":
                target_height = 15.0
                x_pos = self.x - 20
                y_pos = self.y - 8
            else:
                target_height = 25.0
                x_pos = self.x - 18
                y_pos = self.y - 17

            scale_factor = target_height / original_rect.height()
            acc_item.setScale(scale_factor)
            acc_item.setPos(x_pos, y_pos)
            acc_item.setAcceptHoverEvents(False)
            self.scene.addItem(acc_item)
            self.accidental_item = acc_item
        self.update()



    def _set_accidental_without_display(self, acc_type):
        """Устанавливает знак на ноту без отображения."""
        self._add_accidental(acc_type, display=False)

    def _remove_accidental(self):
        if self.accidental_item is not None:
            self.scene.removeItem(self.accidental_item)
            self.accidental_item = None
        # Убираем символ из имени ноты
        if self.accidental and self.accidental != "natural":
            symbol = self._accidental_to_symbol(self.accidental)
            if self.note_name.endswith(symbol):
                self.note_name = self.note_name[:-len(symbol)]
        self.accidental = None
        self.update()


    def _accidental_to_symbol(self, acc_type):
        mapping = {
            "sharp": "#",
            "flat": "b",
            "natural": "",
        }
        return mapping.get(acc_type, "")

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

    def boundingRect(self):
        """Сообщает Qt реальные границы отрисовки элемента (включая штили и флаги)"""
        min_x = self.x - self.width
        max_x = self.x + self.width
        min_y = self.y - self.height
        max_y = self.y + self.height
        
        # Учитываем высоту штиля
        if self.note_lenght != 1:
            min_y = min(min_y, self.y - 35)
            
        # Учитываем ширину флага и длину ребра (beam)
        if self.note_lenght == 0.125:
            if self.shtil:
                max_x = max(max_x, self.stem_x + 55) # Запас для флага
            if self.next_note:
                max_x = max(max_x, self.next_note.stem_x + 55)
                min_y = min(min_y, self.next_note.y - 35)
                
        # Возвращаем прямоугольник с небольшим запасом (padding = 5px)
        return QRectF(min_x - 5, min_y - 5, (max_x - min_x) + 10, (max_y - min_y) + 10)

    def shape(self):
        """Определяет область для коллизий и кликов мыши (только головка ноты)"""
        path = QPainterPath()
        # Кликабельной остается только область самой головки ноты
        path.addEllipse(QRectF(self.x - self.width/2, self.y - self.height/2, self.width, self.height))
        return path


    def get_base_note_name(self):
        """Возвращает имя ноты без знака альтерации."""
        if self.accidental:
            symbol = self._accidental_to_symbol(self.accidental)
            if self.note_name.endswith(symbol):
                return self.note_name[:-len(symbol)]
        return self.note_name



class HighlightableLineItem(QGraphicsLineItem):
    """Класс линии, которая подсвечивается при наведении"""

    def __init__(self, line:QLineF, tact, y, note_name, transparent=False, parent=None):
        super().__init__(line, parent)
        self.line_obj = line
        self.tact = tact
        self.read_only = False
        self.y = y
        self.transparent = transparent
        self.normal_pen = QPen(Qt.GlobalColor.transparent) if transparent else QPen(Qt.GlobalColor.black)
        self.normal_pen.setWidthF(LINE_WIDTH)
        self.hover_pen = QPen(QColor(255, 0, 0))
        self.hover_pen.setWidthF(LINE_WIDTH * 1.5)
        self.setPen(self.normal_pen)
        self.setAcceptHoverEvents(True)
        self.setAcceptTouchEvents(True)
        self.is_hovered = False
        self.line_number = -1
        self.note_name = note_name

    def hoverEnterEvent(self, event):
        """Событие при наведении курсора"""
        if self.read_only:
            self.is_hovered = False
            self.unsetCursor()
            self.setPen(self.normal_pen)
            return super().hoverEnterEvent(event)
        self.is_hovered = True
        self.setPen(self.hover_pen)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """Событие при уходе курсора"""
        self.is_hovered = False
        self.setPen(self.normal_pen)
        self.unsetCursor()
        self.update()
        super().hoverLeaveEvent(event)

    def set_read_only(self, value: bool):
        self.read_only = value
        self.is_hovered = False
        self.setPen(self.normal_pen)
        self.unsetCursor()
        self.update()

    def set_highlight_enabled(self, enabled: bool):
        self.set_read_only(not enabled)

    def mousePressEvent(self, event):
        """Обработка клика на линии"""
        if self.read_only:
            super().mousePressEvent(event)
            return

        if event.button() == Qt.MouseButton.LeftButton and self.is_hovered:
            pos = event.pos()
            scene_pos = self.mapToScene(pos)
            self.tact.add_note_at_position(scene_pos.x(), self)

        super().mousePressEvent(event)


class StaffSpaceItem(QGraphicsRectItem):
    """Класс для пространства между линиями нотного стана"""

    def __init__(self, rect, space_number, tact, note_name, y, parent=None):
        super().__init__(rect, parent)
        self.tact = tact
        self.read_only = False
        self.note_name = note_name
        self.y = y
        self.space_number = space_number
        self.normal_brush = QBrush(Qt.GlobalColor.transparent)
        self.normal_pen = QPen(Qt.GlobalColor.transparent)
        self.hover_brush = QBrush(QColor(173, 216, 230, 80))
        self.hover_pen = QPen(Qt.GlobalColor.transparent)
        self.setBrush(self.normal_brush)
        self.setPen(self.normal_pen)
        self.setAcceptHoverEvents(True)
        self.is_hovered = False

    def hoverEnterEvent(self, event):
        """Событие при наведении курсора"""
        if self.read_only:
            self.is_hovered = False
            self.setBrush(self.normal_brush)
            self.setPen(self.normal_pen)
            self.unsetCursor()
            return super().hoverEnterEvent(event)
        self.is_hovered = True
        self.setBrush(self.hover_brush)
        self.setPen(self.hover_pen)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """Событие при уходе курсора"""
        self.is_hovered = False
        self.setBrush(self.normal_brush)
        self.setPen(self.normal_pen)
        self.unsetCursor()
        self.update()
        super().hoverLeaveEvent(event)

    def set_read_only(self, value: bool):
        self.read_only = value
        self.is_hovered = False
        self.setBrush(self.normal_brush)
        self.setPen(self.normal_pen)
        self.unsetCursor()
        self.update()

    def mousePressEvent(self, event):
        """Обработка клика на линии"""
        if self.read_only:
            super().mousePressEvent(event)
            return

        if event.button() == Qt.MouseButton.LeftButton and self.is_hovered:
            pos = event.pos()
            scene_pos = self.mapToScene(pos)
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
        self.line_item = None
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
        self.line_item = line


class Bits(QGraphicsRectItem):

    def __init__(self, rect, x0, x1, tact=None, weigth=0.25, parent=None):
        super().__init__(rect, parent)
        self.notes = []
        self.x0 = x0
        self.x1 = x1
        self.weigth = weigth
        self.full = False
        self.tact = tact
        self.normal_brush = QBrush(Qt.GlobalColor.transparent)
        self.normal_pen = QPen(QColor(100, 100, 100, 50), 1.5, Qt.PenStyle.SolidLine)
        self.hidden_pen = QPen(Qt.GlobalColor.transparent)
        self.read_only = False
        self.setBrush(self.normal_brush)
        self.setPen(self.normal_pen)

    def set_read_only(self, value: bool):
        self.read_only = value
        self.setBrush(self.normal_brush)
        self.setPen(self.hidden_pen if value else self.normal_pen)
        self.update()

    def setVisible(self, visible):
        super().setVisible(visible)
        self.update()


    def isExist_note(self, line: StaffSpaceItem | HighlightableLineItem):
        for note in self.notes:
            if note.note_name[:2] == line.note_name:
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
                linked_note_next,note.next_note = note.next_note,linked_note_next
        if self.notes:
            last_note = self.notes[-1]
            last_note.create_shtil()
            last_note.next_note = linked_note_next
            last_note.prev_note = linked_note_prev
        else:
            self.tact.change_bits(self)
        self.tact.update_beams()
        


    def add_note(self, duration, line, scene):
        if duration != self.weigth:
            return False
        if self.isExist_note(line):
            return False
        note_item = NoteItem(self.x0+15, line.y, line.note_name, scene, duration, bit=self)
        self.notes.append(note_item)
        self.notes.sort(key=lambda note: note.y, reverse=True)
        self.update_notes()
        self.tact.recalculate_all_accidentals(note_item)
        print(note_item.note_name)
        return note_item

    def remove_note(self, note):
        self.notes.remove(note)
        if note.note_lenght == 0.125:
            if next_note := note.next_note:
                next_note.prev_note = None
                next_note.shtil = True
                next_note.update()
            elif prev_note := note.prev_note:
                prev_note.shtil = True
                prev_note.next_note = None
                prev_note.update()
        self.update_notes()

        # Пересчитываем знаки для всего такта (после удаления)
        self.tact.recalculate_all_accidentals(note)

    def recalculate_accidental(self, note):
        self.tact.recalculate_all_accidentals(note)


class Tact:
    def __init__(self,y_bottom,scene,number,x0=X0, y=Y0, duration=0.25, numerator=4):
        self.tact_number = number
        self.numerator = numerator
        self.x0 = x0
        self.spaces = []
        self.width = WIDTH if number > 0 else WIDTH + 100
        self.y_bottom = y_bottom
        self.y0 = y
        self.note_x = X0 if number > 0 else X0 + 100
        self.lines = []
        self.bar_lines = []  # Храним вертикальные линии тактов
        self.notes = []  # Список нот в такте
        self.scene = scene
        self.bits = []
        self.active_accidentals = {}
        self.displayed_accidentals = set()
        self.current_bit = 0
        self.duration = duration
        self.init_bits()
        self.init_tact()
    

    def init_tact(self):
    # Сначала создаем пространства между линиями (4 пространства между 5 линиями)
        for i in range(5):
            y_top = self.y0 + i * LINE_SPACING
            space_rect = QRectF(self.x0, y_top, self.width, LINE_SPACING)
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
            y = self.y0 + i * LINE_SPACING
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
                    QLineF(self.x0, y, self.x0 + self.width, y),
                    self,y, note_name, transparent=True
                )
            if i != 5:
                line_item = HighlightableLineItem(
                    QLineF(self.x0, y, self.x0 + self.width, y),
                    self,y, note_name
                )
            line_item.line_number = i
            self.scene.addItem(line_item)
            self.lines.append(line_item)
            self.add_bar_lines()


    def init_bits(self):
        tact_total_duration = self.numerator / 4
        remaining = round(tact_total_duration, 4)
        grid_duration = round(self.duration, 4)

        bit_weights = []
        while remaining > 0:
            if remaining >= grid_duration:
                bit_weights.append(grid_duration)
                remaining = round(remaining - grid_duration, 4)
            else:
                bit_weights.append(remaining)
                remaining = 0

        self.set_bit_weights(bit_weights)

    def set_bit_weights(self, bit_weights):
        for bit in self.bits:
            for note in bit.notes[:]:
                self.scene.removeItem(note)
            self.scene.removeItem(bit)
        self.bits.clear()

        tact_total_duration = self.numerator / 4
        print(f"Tact {self.tact_number} | Rhythm: {self.numerator/4} | Weights: {bit_weights}")

        x_start_offset = 100 if self.tact_number == 0 else 0
        usable_width = self.width - x_start_offset
        x_left = self.x0 + x_start_offset

        for weight in bit_weights:
            bit_width = usable_width * (weight / tact_total_duration)
            x1 = x_left + bit_width

            bit = Bits(
                QRectF(x_left, self.y0, bit_width, self.y_bottom - self.y0),
                x_left,
                x1,
                tact=self,
                weigth=weight,
            )
            x_left = x1
            self.bits.append(bit)
            self.scene.addItem(bit)

        self.duration = min(bit_weights) if bit_weights else self.duration

        self.update_beams()
        self.scene.update()


    def add_bar_lines(self):
        """Добавляет вертикальные линии тактов"""
        # Добавляем левую тактовую черту (сразу после размерности такта)
        scene = self.scene
        left_bar = BarLine(scene, self.x0 , self.y0, self.y_bottom)
        self.bar_lines.append(left_bar)
        # Добавляем правую тактовую черту (конечную)
        right_bar_x = self.x0 + self.width
        right_bar = BarLine(scene, right_bar_x, self.y0, self.y_bottom)
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
                if bit.notes:
                    new_bits.append(available_bit)
                    new_bits.append(bit)
                    available_bit = None
                    continue
                if bit.weigth == available_bit.weigth:
                    width = (bit.x1-available_bit.x0)
                    new_bits.append(Bits(QRectF(available_bit.x0, 
                                                self.y0, 
                                                width, 
                                                self.y_bottom-self.y0), 
                                            available_bit.x0, 
                                            available_bit.x0+width,
                                            weigth=self.duration, 
                                            tact=self))
                    self.scene.addItem(new_bits[-1])
                    self.scene.removeItem(bit)
                    self.scene.removeItem(available_bit)
                    available_bit = None
            elif not bit.notes:
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
                QRectF(new_x0, self.y0, new_x1 - new_x0, self.y_bottom - self.y0),
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
                QRectF(new_x0, self.y0, new_x1 - new_x0, self.y_bottom - self.y0),
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
                    Bits(QRectF(bit.x0, self.y0, width, self.y_bottom-self.y0), bit.x0, bit.x0+width,weigth=bit.weigth/2, tact=self),
                    Bits(QRectF(bit.x0+width, self.y0, width, self.y_bottom-self.y0), bit.x0+width+1, bit.x1,weigth=bit.weigth/2, tact=self)]
                    )
                self.scene.addItem(new_bits[-2])
                self.scene.addItem(new_bits[-1])
                self.scene.removeItem(bit)
            else:
                new_bits.append(bit)
        self.bits = new_bits
        if self.duration != duration:
            self.decrease_duration(duration) 



    def remove_from_scene(self):
        # Удаляем линии
        for line in self.lines[:]:          # копия списка для безопасной итерации
            self.scene.removeItem(line)
            # При необходимости: del line
        self.lines.clear()
        # Удаляем пробелы
        for space in self.spaces[:]:
            self.scene.removeItem(space)
        self.spaces.clear()
        # Удаляем тактовые черты
        for bar in self.bar_lines[:]:
            self.scene.removeItem(bar.line_item)
        self.bar_lines.clear()

        # Удаляем биты (и их ноты)
        for bit in self.bits:
            for note in bit.notes[:]:
                self.scene.removeItem(note)
            self.scene.removeItem(bit)
        self.bits.clear()

        # Дополнительно: удаляем ноты, если они хранятся отдельно
        for note in self.notes[:]:
            self.scene.removeItem(note)
        del self


    def recalculate_all_accidentals(self, note_item):
        """Убирает все знаки и заново рисует только те, что явно поставил пользователь."""
        alteration = None
        drawed = False

        for i, bit in enumerate(self.bits):
            for note in bit.notes:
                if note == note_item and note.accidental == "natural" and alteration is None:
                    note.draw_accidental(0)
                    alteration = note.accidental
                    drawed = True
                    continue
                if note.note_name[:2] == note_item.note_name[:2]:
                    if alteration is None and note.accidental == "natural":
                        alteration = note.accidental
                        note.draw_accidental(0)
                        drawed = True
                        continue 
                    if alteration == note.accidental:
                        symbol = note._accidental_to_symbol(alteration)
                        if not note.note_name.endswith(symbol):
                            note.note_name += symbol
                        if drawed:
                            note.delete_accidental()
                        else:
                            note.draw_accidental(i)
                            drawed = True
                    else:

                        alteration = note.accidental
                        note.draw_accidental(i)
                        drawed = True
        # if note_item.accidental != "natural":
        #     note_item.draw_accidental()

                    



class StaffLayout:
    def __init__(self, scene, time_signature="4/4", read_only: bool = False):
        self.left_hand = False
        self.read_only = read_only
        self.tacts = []
        self.time_signature = time_signature
        self.tacts_per_rows = 0
        self.current_tact = None
        self.bpm = 60
        self.y = Y0
        self.x = X0
        self.scene = scene
        self.beats_per_measure = int(self.time_signature.split('/')[0])
        # self.max_tact_duration = self.beats_per_measure * 0.25
        self.current_duration = 0.25
        self.init_staff(scene)
        self.accidental = None

    @property
    def y_bottom(self) -> float:
        return self.y + (4 * LINE_SPACING) 
    
    @property
    def staff_height(self) -> float:
        return 4 * LINE_SPACING
    


    def set_duration(self, duration):
        if duration > self.current_duration:
            self.current_duration = duration
            for tact in self.tacts:
                tact.increase_duration(duration)
        else:
            self.current_duration = duration
            for tact in self.tacts:
                tact.decrease_duration(duration)
        self.scene.update()
                        



    def init_staff(self, scene):
        self.current_tact = Tact(self.y_bottom, scene, len(self.tacts), duration=self.current_duration, numerator=self.beats_per_measure)
        self._apply_read_only_to_tact(self.current_tact)
        self.tacts.append(self.current_tact)
        self.tacts_per_rows = 1
        # Добавляем скрипичный ключ
        self.add_treble_clef(scene)
        # Добавляем размерность такта (4/4) после скрипичного ключа
        self.time_signature = TimeSignature(
            scene, 
            X0 + 50,  # Отступ от левого края после скрипичного ключа
            Y0,   # Немного выше первой линии
            self.beats_per_measure, 4           # Размерность 4/4
        )
        print(self.beats_per_measure)

    def add_treble_clef(self, scene):
        """Добавляет изображение скрипичного ключа на нотный стан"""
        clef_item = QGraphicsSvgItem("app/photos/scrip.svg")
        original_rect = clef_item.boundingRect()
        original_height = original_rect.height()
        
        target_height = LINE_SPACING * 7
        
        # Вычисляем коэффициент масштабирования
        scale_factor = target_height / original_height
        
        # Применяем масштаб к элементу
        clef_item.setScale(scale_factor)

        # Корректируем позицию
        x_pos = X0 + 5
        y_pos = Y0 + 1.5 * LINE_SPACING - target_height / 2.5
        clef_item.setPos(x_pos, y_pos)
        
        # Отключаем интерактивность
        clef_item.setAcceptHoverEvents(False)
        
        # Добавляем на сцену
        scene.addItem(clef_item)

    def save_lesson(self, name: str, description: str, difficult: int, topic_id: int):
        """Собирает ноты с нотного стана и формирует lesson payload для бэкенда"""
        lesson_notes = {"right_hand": []}

        for tact in self.tacts:
            tact_data = []
            for bit in tact.bits:
                note_names = []
                for note in bit.notes:
                    note_names.append(note.note_name)

                tact_data.append({
                    "duration": bit.weigth,
                    "notes": note_names
                })

            lesson_notes["right_hand"].append(tact_data)

        rhythm_val = self.beats_per_measure / 4.0

        return LessonCreate(
            name=name,
            description=description,
            difficult=difficult,
            rhythm=rhythm_val,
            notes=lesson_notes,
            topic=topic_id
        )


    

    def display_lesson(self, lesson: LessonResponse):
        """Отрисовывает урок на нотном стане, полученный с сервера"""
        saved_tacts = lesson.notes.get("right_hand", [])

        while len(self.tacts) < len(saved_tacts):
            self.add_tact()

        for tact_idx, saved_tact in enumerate(saved_tacts):
            tact = self.tacts[tact_idx]
            bit_weights = [float(saved_bit.get("duration", tact.duration)) for saved_bit in saved_tact]
            if bit_weights:
                tact.set_bit_weights(bit_weights)
            lines_and_spaces = tact.lines + tact.spaces

            for bit_idx, saved_bit in enumerate(saved_tact):
                if bit_idx >= len(tact.bits):
                    continue
                bit = tact.bits[bit_idx]

                for note_name in saved_bit["notes"]:
                    base_name = note_name[:2]

                    for item in lines_and_spaces:
                        if item.note_name == base_name:
                            if "#" in note_name:
                                settings.accidental = "sharp"
                            elif "b" in note_name:
                                settings.accidental = "flat"
                            else:
                                settings.accidental = "natural"

                            note = bit.add_note(bit.weigth, item, self.scene)
                            if note:
                                self.scene.addItem(note)
                            break


    def touch_thread(self):
        for tact in self.tacts:
            for bit in tact.bits:
                if bit.notes:
                    # Берём первую ноту в бите (для простоты)
                    note_item = bit.notes[0]
                    player.start_waiting_for_note(note_item.note_name, note_item)
                    duration = 60/self.bpm * bit.weigth * 4
                    time.sleep(duration)

    def sound_thread(self):
            time.sleep(0.05)
            for tact in self.tacts:
                for bit in tact.bits:
                    if bit.notes:
                        duration = 60/self.bpm * bit.weigth * 4
                        chord_notes = [note.note_name for note in bit.notes]
                        player.play_chord(chord_notes, duration)
                    time.sleep(duration)

    def start_lesson(self, wait_for_input: bool = True, play_sound: bool = True):
        if wait_for_input:
            threading.Thread(target=self.touch_thread, daemon=True).start()
        if play_sound:
            threading.Thread(target=self.sound_thread, daemon=True).start()


    def change_accidental(self, data):
        self.accidental = data


    def _apply_read_only_to_tact(self, tact):
        try:
            for item in getattr(tact, "lines", []) or []:
                if hasattr(item, "set_read_only"):
                    item.set_read_only(self.read_only)
                else:
                    item.read_only = self.read_only
            for item in getattr(tact, "spaces", []) or []:
                if hasattr(item, "set_read_only"):
                    item.set_read_only(self.read_only)
                else:
                    item.read_only = self.read_only
            for item in getattr(tact, "bits", []) or []:
                if hasattr(item, "set_read_only"):
                    item.set_read_only(self.read_only)
        except Exception:
            pass

    def add_tact(self):
        pred_tact = self.tacts[-1]
        new_x0 = pred_tact.x0+pred_tact.width
        if new_x0 + WIDTH > SCENE_WIDTH:
            self.x = X0
            self.y += (self.staff_height + 100)
            self.current_tact = Tact(self.y_bottom, self.scene, len(self.tacts), X0, self.y, self.current_duration,self.beats_per_measure)
        else:
            self.x = new_x0
            self.current_tact = Tact(self.y_bottom, self.scene, len(self.tacts), new_x0, self.y, self.current_duration,self.beats_per_measure)

        self._apply_read_only_to_tact(self.current_tact)
        self.tacts.append(self.current_tact)
        current_rect = self.scene.sceneRect()
        # # Получаем реальные границы всех объектов
        bounding = self.scene.itemsBoundingRect()
        needed_height = bounding.bottom() + 100
        if needed_height > current_rect.bottom():
            self.scene.setSceneRect(0, 0, current_rect.width(), needed_height)


    def delete_tact(self):
        if len(self.tacts) == 1:
            return False
        tact = self.tacts[-1]
        tact.remove_from_scene()
        self.tacts.pop(-1)
        self.y = self.tacts[-1].y0
        current_rect = self.scene.sceneRect()
        # # Получаем реальные границы всех объектов
        bounding = self.scene.itemsBoundingRect()
        needed_height = bounding.bottom() - 100
        if needed_height < current_rect.bottom():
            self.scene.setSceneRect(0, 0, current_rect.width(), needed_height)



    # staff.py (внутри StaffLayout)
    def get_playhead_path(self):
        """
        Возвращает список сегментов пути playhead.
        Каждый сегмент: (x_start, y_start, x_end, y_end, length, cum_length)
        """
        segments = []
        cum_length = 0.0

        # Предполагаем, что такты хранятся в self.tacts в порядке добавления
        # и что они уже размещены с правильными координатами x0, y0
        # Для разбиения на строки можно сгруппировать такты по y0 (или хранить rows)
        # Упрощённо: идём по всем тактам подряд, но при изменении y добавляем разрыв
        prev_y = None
        for tact in self.tacts:
            y = tact.y0  # вертикальная координата стана
            if prev_y is not None and y != prev_y:
                # Переход на новую строку – разрыв, но мы просто продолжаем,
                # так как playhead "перепрыгнет" – координата y изменится
                pass
            # Начало такта: x0, конец такта: x0 + width
            x_start = tact.bits[0].notes[0].x
            x_end = tact.bits[-1].x1 + 15
            length = x_end - x_start
            segments.append((x_start, y, x_end, y, length, cum_length))
            cum_length += length
            prev_y = y
        return segments, cum_length