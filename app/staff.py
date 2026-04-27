from PyQt6.QtCore import Qt, QRectF, QLineF, QPointF
from PyQt6.QtGui import QPen, QBrush, QFont, QPixmap, QColor, QPainter, QPainterPath
from PyQt6.QtWidgets import (
    QGraphicsItem,
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


DURATION_EPSILON = 1e-6
NATURAL_NOTE_ORDER = ["C", "D", "E", "F", "G", "A", "B"]
BASE_STAFF_TOP_INDEX = 16
BASE_STAFF_BOTTOM_INDEX = 24
LEDGER_LINE_NOTE_INDICES = {14, 12, 10, 8, 6, 4, 2, 0, 26, 28, 30, 32, 34, 36, 38, 40, 42}


def build_natural_note_range(highest_note: str = "C8", lowest_note: str = "F3") -> list[str]:
    note_name = highest_note[0]
    octave = int(highest_note[1:])
    notes: list[str] = []

    while True:
        current_note = f"{note_name}{octave}"
        notes.append(current_note)
        if current_note == lowest_note:
            return notes
        note_position = NATURAL_NOTE_ORDER.index(note_name)
        if note_position == 0:
            note_name = NATURAL_NOTE_ORDER[-1]
            octave -= 1
        else:
            note_name = NATURAL_NOTE_ORDER[note_position - 1]


def build_staff_note_positions() -> list[tuple[str, str, int, bool, bool]]:
    positions: list[tuple[str, str, int, bool, bool]] = []
    note_range = build_natural_note_range()
    base_line_offset = note_range.index("F5")

    for note_index, full_name in enumerate(note_range):
        relative_index = note_index - base_line_offset
        kind = "line" if relative_index % 2 == 0 else "space"
        is_base_staff_line = kind == "line" and BASE_STAFF_TOP_INDEX <= note_index <= BASE_STAFF_BOTTOM_INDEX
        is_ledger_line = note_index in LEDGER_LINE_NOTE_INDICES
        positions.append((kind, full_name, relative_index, not is_base_staff_line, is_ledger_line))
    return positions


STAFF_NOTE_POSITIONS = build_staff_note_positions()
TOP_NOTE_OFFSET = STAFF_NOTE_POSITIONS[0][2]
BOTTOM_NOTE_OFFSET = STAFF_NOTE_POSITIONS[-1][2]


def durations_equal(left: float, right: float, epsilon: float = DURATION_EPSILON) -> bool:
    return abs(left - right) <= epsilon


def get_base_duration(duration: float) -> float:
    dotted_bases = {
        0.75: 0.5,
        0.375: 0.25,
        0.1875: 0.125,
    }
    for dotted_duration, base_duration in dotted_bases.items():
        if durations_equal(duration, dotted_duration):
            return base_duration
    return duration


def is_dotted_duration(duration: float) -> bool:
    return not durations_equal(get_base_duration(duration), duration)


class LaySettings:
    def __init__(self):
        self.accidental = "natural"
        self.input_mode = "note"
        self.scene = None

settings = LaySettings()


class RestItem(QGraphicsItem):
    SVG_PATHS = {
        0.25: "app/photos/quarter_pause.svg",
        0.125: "app/photos/eight_pause.svg",
    }

    def __init__(self, x: float, y: float, duration: float, scene, bit=None):
        super().__init__(parent=bit)
        self.x = x
        self.y = y
        self.duration = duration
        self.base_duration = get_base_duration(duration)
        self.is_dotted = is_dotted_duration(duration)
        self.scene = scene
        self.bit = bit
        self.svg_item = None
        self.rect = QRectF()
        self.dot_rect = QRectF()
        self.setZValue(10)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton)
        self._update_geometry()

    def _update_geometry(self):
        whole_or_half_width = 18
        whole_or_half_height = 6
        line_y = self.y

        if durations_equal(self.base_duration, 1):
            self.rect = QRectF(self.x - whole_or_half_width / 2, line_y, whole_or_half_width, whole_or_half_height)
            self._clear_svg_item()
        elif durations_equal(self.base_duration, 0.5):
            self.rect = QRectF(self.x - whole_or_half_width / 2, line_y - whole_or_half_height, whole_or_half_width, whole_or_half_height)
            self._clear_svg_item()
        else:
            self.rect = QRectF(self.x - 10, line_y - 20, 20, 40)
            self._ensure_svg_item()
            self._position_svg_item()

        if self.is_dotted:
            self.dot_rect = QRectF(self.rect.right() + 4, self.rect.center().y() - 2, 4, 4)
        else:
            self.dot_rect = QRectF()

    def _ensure_svg_item(self):
        if self.svg_item is not None:
            return
        svg_path = self.SVG_PATHS.get(self.base_duration)
        if not svg_path:
            return
        self.svg_item = QGraphicsSvgItem(svg_path, self)
        self.svg_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

    def _clear_svg_item(self):
        if self.svg_item is None:
            return
        self.scene.removeItem(self.svg_item)
        self.svg_item = None

    def _position_svg_item(self):
        if self.svg_item is None:
            return
        original_rect = self.svg_item.boundingRect()
        if original_rect.isEmpty():
            return

        if durations_equal(self.base_duration, 0.25):
            target_height = 32.0
        else:
            target_height = 26.0

        y_offset = -18.0

        scale_factor = target_height / original_rect.height()
        self.svg_item.setScale(scale_factor)
        scaled_width = original_rect.width() * scale_factor
        self.svg_item.setPos(self.x - scaled_width / 2, self.y + y_offset)
        self.rect = self.svg_item.mapRectToParent(self.svg_item.boundingRect())

    @classmethod
    def create_for_bit(cls, bit, duration, scene):
        center_x = (bit.x0 + bit.x1) / 2
        base_duration = get_base_duration(duration)
        if durations_equal(base_duration, 1):
            line_y = bit.tact.lines[1].y
        elif durations_equal(base_duration, 0.5):
            line_y = bit.tact.lines[2].y
        else:
            line_y = bit.tact.lines[2].y
        return cls(center_x, line_y, duration, scene, bit=bit)

    def sync_to_bit(self):
        self.prepareGeometryChange()
        self.x = (self.bit.x0 + self.bit.x1) / 2
        self._update_geometry()
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton and self.bit is not None:
            self.bit.remove_rest()
            return
        super().mousePressEvent(event)

    def boundingRect(self):
        if self.dot_rect.isNull():
            return self.rect.adjusted(-2, -2, 2, 2)
        return self.rect.united(self.dot_rect).adjusted(-2, -2, 2, 2)

    def paint(self, painter: QPainter, option, widget):
        if durations_equal(self.base_duration, 1) or durations_equal(self.base_duration, 0.5):
            painter.setPen(QPen(Qt.GlobalColor.black, 1.4))
            painter.setBrush(QBrush(Qt.GlobalColor.black))
            painter.drawRect(self.rect)
        if self.is_dotted:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(Qt.GlobalColor.black))
            painter.drawEllipse(self.dot_rect)


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
        self.base_duration = get_base_duration(duration)
        self.is_dotted = is_dotted_duration(duration)
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
        if self.base_duration < 0.5:
            self.setBrush(QBrush(Qt.GlobalColor.black))
        self.setPen(NORMAL_PEN)
        self.prev_note = None
        self.next_note = None
        self.stem_x = int(self.x + self.width/2) if not self.reversing else int(self.x - self.width/2)

    def get_stem_group_notes(self):
        if self.bit is None:
            return [self]
        return [note for note in self.bit.notes if note.reversing == self.reversing] or [self]

    def has_split_upward_chord(self) -> bool:
        if self.bit is None or self.reversing or len(self.bit.notes) < 2:
            return False
        upward_notes = [note for note in self.bit.notes if not note.reversing]
        if len(upward_notes) < 2:
            return False
        ordered_notes = sorted(upward_notes, key=lambda note: note.y, reverse=True)
        return any(abs(current.y - following.y) > 12 for current, following in zip(ordered_notes, ordered_notes[1:]))

    def get_stem_start_y(self) -> float:
        group_notes = self.get_stem_group_notes()
        if self.reversing:
            return min(note.y for note in group_notes)
        return max(note.y for note in group_notes)

    def get_stem_top_y(self) -> float:
        stem_top_y = self.get_stem_start_y() - 32
        if self.has_split_upward_chord():
            upward_notes = sorted(
                [note for note in self.bit.notes if not note.reversing],
                key=lambda note: note.y,
                reverse=True,
            )
            lowest_note = upward_notes[0]
            highest_note = upward_notes[-1]
            if self is lowest_note:
                return min(stem_top_y, highest_note.y - 32)
        return stem_top_y

    def is_stem_leader(self) -> bool:
        group_notes = self.get_stem_group_notes()
        if self.reversing:
            return self.y == min(note.y for note in group_notes)
        return self.y == max(note.y for note in group_notes)

    def get_dot_bounds(self) -> QRectF:
        return QRectF(self.x + self.width / 2 + 4, self.y - 1.5, 4, 4)

    def has_ledger_line(self) -> bool:
        if self.bit is None or self.note_name is None:
            return False
        target = self.bit.tact.find_note_target(self.get_base_note_name())
        return bool(target and getattr(target, "ledger_line", False))

    def get_ledger_line_rect(self) -> QRectF:
        padding = 7
        return QRectF(
            self.x - self.width / 2 - padding,
            self.y - LINE_WIDTH / 2,
            self.width + padding * 2,
            LINE_WIDTH,
        )

    def update_stem_x(self):
        self.stem_x = int(self.x + self.width / 2) if not self.reversing else int(self.x - self.width / 2)

    def sync_geometry(self):
        self.update_stem_x()
        self.update()

    def refresh_group_geometry(self):
        if self.bit is None:
            self.sync_geometry()
            return
        for note in self.bit.notes:
            note.sync_geometry()

    def delete_accidental(self):
        if self.accidental_item:
            self.scene.removeItem(self.accidental_item)
            self.accidental_item = None

    def draw_stem(self, painter: QPainter):
        stem_top_y = self.get_stem_top_y()
        painter.drawLine(QLineF(float(self.stem_x), float(self.y), float(self.stem_x), float(stem_top_y)))

    def draw_beam(self, painter: QPainter):
        if self.next_note is None:
            return
        beam_pen = QPen(Qt.GlobalColor.black, 3.2)
        beam_pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(beam_pen)
        painter.drawLine(
            QLineF(
                float(self.stem_x),
                float(self.get_stem_top_y()),
                float(self.next_note.stem_x),
                float(self.next_note.get_stem_top_y()),
            )
        )

    def draw_dot(self, painter: QPainter):
        painter.drawEllipse(self.get_dot_bounds())

    def get_visual_bounds(self) -> QRectF:
        rect = QRectF(self.x - self.width, self.y - self.height, self.width * 2, self.height * 2)
        if self.has_ledger_line():
            rect = rect.united(self.get_ledger_line_rect())
        if not durations_equal(self.base_duration, 1):
            stem_top_y = self.get_stem_top_y()
            rect = rect.united(QRectF(self.stem_x - 2, min(self.y, stem_top_y), 4, abs(self.y - stem_top_y)))
        if durations_equal(self.base_duration, 0.125) and self.shtil:
            rect = rect.united(QRectF(self.stem_x, self.get_stem_top_y(), 12, 22))
        if self.next_note is not None:
            min_x = min(self.stem_x, self.next_note.stem_x)
            max_x = max(self.stem_x, self.next_note.stem_x)
            min_y = min(self.get_stem_top_y(), self.next_note.get_stem_top_y())
            max_y = max(self.get_stem_top_y(), self.next_note.get_stem_top_y())
            rect = rect.united(QRectF(min_x, min_y - 2, max_x - min_x, (max_y - min_y) + 4))
        if self.is_dotted:
            rect = rect.united(self.get_dot_bounds())
        return rect.adjusted(-5, -5, 5, 5)

    def reverse(self, reverse):
        if self.reversing == reverse:
            return
        self.reversing = reverse
        self.x += self.width if self.reversing else -self.width
        self.update_stem_x()
        self.update()

    def remove_shtil(self):
        self.shtil = False
        self.update()

    def create_shtil(self):
        self.shtil = True
        self.update()

    def boundingRect(self):
        return self.get_visual_bounds()

    def shape(self):
        path = QPainterPath()
        path.addEllipse(QRectF(self.x - self.width/2, self.y - self.height/2, self.width, self.height))
        return path

    def get_base_note_name(self):
        if self.accidental:
            symbol = self._accidental_to_symbol(self.accidental)
            if self.note_name.endswith(symbol):
                return self.note_name[:-len(symbol)]
        return self.note_name

    def paint(self, painter: QPainter, option, widget):
        painter.save()
        painter.translate(self.x, self.y)
        painter.rotate(self.tilt_angle)
        painter.setBrush(self.brush())
        painter.setPen(self.pen())
        painter.drawEllipse(QRectF(-self.width/2, -self.height/2, self.width, self.height))
        painter.restore()

        if self.has_ledger_line():
            painter.setPen(QPen(Qt.GlobalColor.black, LINE_WIDTH))
            painter.drawLine(QLineF(self.get_ledger_line_rect().left(), self.y, self.get_ledger_line_rect().right(), self.y))

        if not durations_equal(self.base_duration, 1):
            painter.setPen(self.pen())
            self.draw_stem(painter)
            if durations_equal(self.base_duration, 0.125):
                if self.shtil:
                    self.flag_path = self.computeFlagPath()
                    painter.drawPath(self.flag_path)
                elif self.next_note:
                    self.draw_beam(painter)

        if self.is_dotted:
            self.draw_dot(painter)

    def computeFlagPath(self):
        ax = self.stem_x
        ay = self.get_stem_top_y()
        sign_x = 1
        sign_y = 1
        bx = ax + sign_x * 10
        by = ay + sign_y * 20
        up_c1 = (ax + sign_x * 0, ay + sign_y * 20)
        up_c2 = (ax + sign_x * 10, ay + sign_y * 10)
        low_c1 = (ax + sign_x * 8, ay + sign_y * 10)
        low_c2 = (ax + sign_x * 0, ay + sign_y * 23)
        path = QPainterPath()
        path.moveTo(ax, ay)
        path.cubicTo(up_c1[0], up_c1[1], up_c2[0], up_c2[1], bx, by)
        path.cubicTo(low_c1[0], low_c1[1], low_c2[0], low_c2[1], ax, ay)
        path.closeSubpath()
        return path

    def _add_accidental(self, acc_type, display=True):
        if self.accidental_item is not None:
            self.scene.removeItem(self.accidental_item)
            self.accidental_item = None

        if acc_type == "natural":
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
            self.update()
            return

        symbol = self._accidental_to_symbol(acc_type)
        if not self.note_name.endswith(symbol):
            self.note_name += symbol
        self.accidental = acc_type

        if display:
            svg_path = f"app/photos/{acc_type}.svg"
            acc_item = QGraphicsSvgItem(svg_path)
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
        self._add_accidental(acc_type, display=False)

    def _remove_accidental(self):
        if self.accidental_item is not None:
            self.scene.removeItem(self.accidental_item)
            self.accidental_item = None
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

    def delete(self):
        self.bit.remove_note(self)
        self.scene.removeItem(self)
        if self.accidental_item is not None:
            self.scene.removeItem(self.accidental_item)
        self.scene.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.delete()
            return
        self.accidental = settings.accidental
        self.bit.recalculate_accidental(self)

    def draw_accidental(self, index):
        if self.accidental_item is not None:
            self.scene.removeItem(self.accidental_item)
            self.accidental_item = None
        if self.accidental == "natural" and index == 0:
            return
        symbol = self._accidental_to_symbol(self.accidental)
        if not self.note_name.endswith(symbol):
            self.note_name += symbol
        svg_path = f"app/photos/{self.accidental}.svg"
        acc_item = QGraphicsSvgItem(svg_path)
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

class HighlightableLineItem(QGraphicsLineItem):
    """Класс линии, которая подсвечивается при наведении"""

    def __init__(self, line:QLineF, tact, y, note_name, transparent=False, ledger_line=False, parent=None):
        super().__init__(line, parent)
        self.line_obj = line
        self.tact = tact
        self.read_only = False
        self.y = y
        self.transparent = transparent
        self.ledger_line = ledger_line
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
            self.tact.add_item_at_position(scene_pos.x(), self)

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
        self.ledger_line = False
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
            self.tact.add_item_at_position(scene_pos.x(), self)

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
        self.rest_item = None
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

    @property
    def is_filled(self) -> bool:
        return bool(self.notes) or self.rest_item is not None

    def sync_rest(self):
        if self.rest_item is not None:
            self.rest_item.sync_to_bit()

    def add_rest(self, duration, scene):
        if not durations_equal(duration, self.weigth):
            return False
        if self.notes or self.rest_item is not None:
            return False
        self.rest_item = RestItem.create_for_bit(self, duration, scene)
        scene.addItem(self.rest_item)
        self.update()
        return self.rest_item

    def remove_rest(self):
        if self.rest_item is None:
            return
        self.scene().removeItem(self.rest_item)
        self.rest_item = None
        self.tact.change_bits(self)
        self.tact.update_beams()
        self.update()

    def clear_contents(self):
        for note in self.notes[:]:
            self.scene().removeItem(note)
        self.notes.clear()
        if self.rest_item is not None:
            self.scene().removeItem(self.rest_item)
            self.rest_item = None
        self.update()

    def setRect(self, rect):
        super().setRect(rect)
        self.sync_rest()
        self.update()

    def itemChange(self, change, value):
        result = super().itemChange(change, value)
        self.sync_rest()
        return result

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
        elif self.rest_item is None:
            self.tact.change_bits(self)
        self.tact.update_beams()
        


    def add_note(self, duration, line, scene):
        if not durations_equal(duration, self.weigth):
            return False
        if self.rest_item is not None:
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
        if durations_equal(note.base_duration, 0.125):
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


def build_bit_weights(total_duration: float, step_duration: float) -> list[float]:
    remaining = round(total_duration, 6)
    step = round(step_duration, 6)
    bit_weights: list[float] = []

    while remaining > DURATION_EPSILON:
        if remaining + DURATION_EPSILON >= step:
            bit_weights.append(step)
            remaining = round(remaining - step, 6)
        else:
            bit_weights.append(round(remaining, 6))
            remaining = 0.0

    return bit_weights


class Tact:
    def __init__(self,y_bottom,scene,number,x0=X0, y=Y0, duration=0.25, numerator=4):
        self.tact_number = number
        self.numerator = numerator
        self.x0 = x0
        self.spaces = []
        self.width = WIDTH if number > 0 else WIDTH + 100
        self.y_bottom = y_bottom
        self.y0 = y
        self.note_area_top = self.y0 + (TOP_NOTE_OFFSET * LINE_SPACING / 2) - LINE_SPACING / 2
        self.note_area_bottom = self.y0 + (BOTTOM_NOTE_OFFSET * LINE_SPACING / 2) + LINE_SPACING / 2
        self.note_area_height = self.note_area_bottom - self.note_area_top
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
        line_index = 0
        space_index = 0

        for kind, note_name, step_index, transparent, ledger_line in STAFF_NOTE_POSITIONS:
            y = self.y0 + (step_index * LINE_SPACING / 2)
            if kind == "line":
                line_item = HighlightableLineItem(
                    QLineF(self.x0, y, self.x0 + self.width, y),
                    self,
                    y,
                    note_name,
                    transparent=transparent,
                    ledger_line=ledger_line,
                )
                line_item.line_number = line_index
                self.scene.addItem(line_item)
                self.lines.append(line_item)
                line_index += 1
                continue

            space_rect = QRectF(self.x0, y - LINE_SPACING / 2, self.width, LINE_SPACING)
            space_item = StaffSpaceItem(space_rect, space_index, self, note_name, int(y))
            self.scene.addItem(space_item)
            self.spaces.append(space_item)
            space_index += 1

        self.add_bar_lines()

    def get_note_targets(self):
        return self.lines + self.spaces

    def find_note_target(self, note_name: str):
        for item in self.get_note_targets():
            if item.note_name == note_name:
                return item
        return None

    def init_bits(self):
        tact_total_duration = self.numerator / 4
        self.set_bit_weights(build_bit_weights(tact_total_duration, self.duration))

    def set_bit_weights(self, bit_weights):
        for bit in self.bits:
            for note in bit.notes[:]:
                self.scene.removeItem(note)
            if bit.rest_item is not None:
                self.scene.removeItem(bit.rest_item)
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
                QRectF(x_left, self.note_area_top, bit_width, self.note_area_height),
                x_left,
                x1,
                tact=self,
                weigth=weight,
            )
            x_left = x1
            self.bits.append(bit)
            self.scene.addItem(bit)

        self.duration = min(bit_weights) if bit_weights else self.duration
        self.current_bit = 0

        self.update_beams()
        self.scene.update()


    def add_bar_lines(self):
        """Добавляет вертикальные линии тактов"""
        # Добавляем левую тактовую черту (сразу после размерности такта)
        scene = self.scene
        left_bar = BarLine(scene, self.x0 , self.note_area_top, self.note_area_bottom)
        self.bar_lines.append(left_bar)
        # Добавляем правую тактовую черту (конечную)
        right_bar_x = self.x0 + self.width
        right_bar = BarLine(scene, right_bar_x, self.note_area_top, self.note_area_bottom)
        self.bar_lines.append(right_bar)



    def add_item_at_position(self, click_x, line):
        if not self.x0 <= click_x <= self.x0 + self.width:
            return
        for bit in self.bits:
            if bit.x0 <= click_x <= bit.x1:
                item = bit
                break
        else:
            return

        if settings.input_mode == "rest":
            item.add_rest(self.duration, self.scene)
            return

        if len(item.notes) == 5:
            return
        item.add_note(self.duration, line, self.scene)

    def add_note_at_position(self, click_x, line):
        self.add_item_at_position(click_x, line)


    def update_beams(self):
        pred_bit = None
        for bit in self.bits:
            if bit.notes:
                if pred_bit:
                    if durations_equal(bit.weigth, 0.125) and durations_equal(pred_bit.weigth, 0.125):
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
                        QRectF(x, self.note_area_top, new_width, self.note_area_height),
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
                QRectF(new_x0, self.note_area_top, new_x1 - new_x0, self.note_area_height),
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
                QRectF(new_x0, self.note_area_top, new_x1 - new_x0, self.note_area_height),
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
                    Bits(QRectF(bit.x0, self.note_area_top, width, self.note_area_height), bit.x0, bit.x0+width,weigth=bit.weigth/2, tact=self),
                    Bits(QRectF(bit.x0+width, self.note_area_top, width, self.note_area_height), bit.x0+width+1, bit.x1,weigth=bit.weigth/2, tact=self)]
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
            if bit.rest_item is not None:
                self.scene.removeItem(bit.rest_item)
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

    def update_scene_bounds(self):
        current_rect = self.scene.sceneRect()
        bounding = self.scene.itemsBoundingRect()
        top_y = min(bounding.top() - 40, current_rect.top(), (min((tact.y0 for tact in self.tacts), default=Y0) - 80))
        bottom_y = max(bounding.bottom() + 100, current_rect.bottom())
        self.scene.setSceneRect(0, top_y, max(current_rect.width(), SCENE_WIDTH), bottom_y - top_y)

    def set_duration(self, duration):
        self.current_duration = duration
        for tact in self.tacts:
            self._rebuild_empty_bits_for_duration(tact, duration)
        self.scene.update()

    def _rebuild_empty_bits_for_duration(self, tact: Tact, duration: float):
        rebuilt_entries: list[Bits | dict[str, float]] = []
        empty_group_duration = 0.0

        for bit in tact.bits:
            if bit.is_filled:
                if empty_group_duration > DURATION_EPSILON:
                    for weight in build_bit_weights(empty_group_duration, duration):
                        rebuilt_entries.append({"weight": weight})
                    empty_group_duration = 0.0
                rebuilt_entries.append(bit)
            else:
                empty_group_duration = round(empty_group_duration + bit.weigth, 6)

        if empty_group_duration > DURATION_EPSILON:
            for weight in build_bit_weights(empty_group_duration, duration):
                rebuilt_entries.append({"weight": weight})

        for bit in tact.bits:
            if not bit.is_filled:
                self.scene.removeItem(bit)

        tact_total_duration = tact.numerator / 4
        x_start_offset = 100 if tact.tact_number == 0 else 0
        usable_width = tact.width - x_start_offset
        current_x = tact.x0 + x_start_offset
        tact.bits = []

        for entry in rebuilt_entries:
            if isinstance(entry, Bits):
                bit = entry
                bit_width = usable_width * (bit.weigth / tact_total_duration)
                bit.x0 = current_x
                bit.x1 = current_x + bit_width
                bit.setRect(QRectF(current_x, tact.note_area_top, bit_width, tact.note_area_height))
                for note in bit.notes:
                    note.x = current_x + 15
                    note.stem_x = int(note.x + note.width / 2) if not note.reversing else int(note.x - note.width / 2)
                    note.update()
                bit.sync_rest()
                tact.bits.append(bit)
                current_x += bit_width
                continue

            weight = entry["weight"]
            bit_width = usable_width * (weight / tact_total_duration)
            bit = Bits(
                QRectF(current_x, tact.note_area_top, bit_width, tact.note_area_height),
                current_x,
                current_x + bit_width,
                tact=tact,
                weigth=weight,
            )
            tact.bits.append(bit)
            self.scene.addItem(bit)
            current_x += bit_width

        tact.duration = duration
        tact.current_bit = 0
        tact.update_beams()
        self.scene.update()
                        



    def init_staff(self, scene):
        self.current_tact = Tact(self.y_bottom, scene, len(self.tacts), duration=self.current_duration, numerator=self.beats_per_measure)
        self._apply_read_only_to_tact(self.current_tact)
        self.tacts.append(self.current_tact)
        self.update_scene_bounds()
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
                if bit.rest_item is not None:
                    note_names.append("REST")
                else:
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
            for bit_idx, saved_bit in enumerate(saved_tact):
                if bit_idx >= len(tact.bits):
                    continue
                bit = tact.bits[bit_idx]

                for note_name in saved_bit["notes"]:
                    if note_name == "REST":
                        bit.add_rest(bit.weigth, self.scene)
                        continue

                    base_name = note_name[:2]
                    item = tact.find_note_target(base_name)
                    if item is None:
                        continue

                    if "#" in note_name:
                        settings.accidental = "sharp"
                    elif "b" in note_name:
                        settings.accidental = "flat"
                    else:
                        settings.accidental = "natural"

                    bit.add_note(bit.weigth, item, self.scene)


    def touch_thread(self):
        for tact in self.tacts:
            for bit in tact.bits:
                duration = 60 / self.bpm * bit.weigth * 4
                if bit.notes:
                    note_item = bit.notes[0]
                    player.start_waiting_for_note(note_item.note_name, note_item)
                time.sleep(duration)

    def sound_thread(self):
            time.sleep(0.05)
            for tact in self.tacts:
                for bit in tact.bits:
                    duration = 60 / self.bpm * bit.weigth * 4
                    if bit.notes:
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
        self.update_scene_bounds()


    def delete_tact(self):
        if len(self.tacts) == 1:
            return False
        tact = self.tacts[-1]
        tact.remove_from_scene()
        self.tacts.pop(-1)
        self.y = self.tacts[-1].y0
        self.update_scene_bounds()



    # staff.py (внутри StaffLayout)
    def get_playhead_path(self):
        """
        Возвращает список сегментов пути playhead.
        Каждый сегмент: (x_start, y_start, x_end, y_end, length, cum_length)
        """
        segments = []
        cum_length = 0.0

        for tact in self.tacts:
            y = tact.y0
            for bit in tact.bits:
                x_start = bit.x0 + 15
                x_end = bit.x1 + 15
                length = x_end - x_start
                segments.append((x_start, y, x_end, y, length, cum_length))
                cum_length += length

        return segments, cum_length
