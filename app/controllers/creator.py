import time

from config import BACKGROUND_SCENE_COLOR, X0, Y0
from GUI.creator import Ui_MainWindow
from PyQt6.QtCore import QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QIcon, QPainter, QPen
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsScene,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from staff import StaffLayout, settings
from test import player
from workers.lesson_worker import LessonWorker

from schemas.lesson import LessonResponse, LessonUpdate


class StarRatingWidget(QWidget):
    def __init__(self, parent=None, max_rating: int = 5):
        super().__init__(parent)
        self.max_rating = max_rating
        self.rating = 0
        self.buttons = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        for index in range(1, max_rating + 1):
            button = QPushButton("☆")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFlat(True)
            button.clicked.connect(lambda _, value=index: self.set_rating(value))
            layout.addWidget(button)
            self.buttons.append(button)

        layout.addStretch()
        self._refresh()

    def set_rating(self, rating: int):
        self.rating = rating
        self._refresh()

    def _refresh(self):
        for index, button in enumerate(self.buttons, start=1):
            is_active = index <= self.rating
            button.setText("★" if is_active else "☆")
            color = "#f4b400" if is_active else "#c8c8c8"
            button.setStyleSheet(
                "QPushButton { border: none; background: transparent; font-size: 28px; padding: 0; color: %s; }"
                "QPushButton:hover { color: #f4b400; }" % color
            )


class SaveLessonDialog(QDialog):
    DEFAULT_STYLE = "padding: 8px; font-size: 14px; border: 1px solid #ccc; border-radius: 5px; background-color: white;"
    ERROR_STYLE = "padding: 8px; font-size: 14px; border: 2px solid #ff4444; border-radius: 5px; background-color: #fff0f0;"
    ERROR_LABEL_STYLE = "color: #ff4444; font-size: 13px; margin-left: 5px;"

    def __init__(
        self, topic_id: int, parent=None, lesson: LessonResponse | None = None
    ):
        super().__init__(parent)
        self.topic_id = int(topic_id)
        self.lesson = lesson
        self.setWindowTitle("Редактирование урока" if lesson else "Сохранение урока")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Название урока:"))
        self.name_edit = QLineEdit(lesson.name if lesson else "")
        self.name_edit.setPlaceholderText("Введите название урока...")
        self.name_edit.setStyleSheet(self.DEFAULT_STYLE)
        layout.addWidget(self.name_edit)

        self.name_error_label = QLabel("")
        self.name_error_label.setStyleSheet(self.ERROR_LABEL_STYLE)
        self.name_error_label.hide()
        layout.addWidget(self.name_error_label)

        layout.addWidget(QLabel("Тема:"))
        self.topic_value = QLineEdit(f"Тема ID: {self.topic_id}")
        self.topic_value.setReadOnly(True)
        self.topic_value.setStyleSheet(self.DEFAULT_STYLE)
        layout.addWidget(self.topic_value)

        layout.addWidget(QLabel("Описание урока:"))
        self.description_edit = QTextEdit()
        self.description_edit.setPlainText(lesson.description if lesson else "")
        self.description_edit.setPlaceholderText("Введите описание урока...")
        self.description_edit.setStyleSheet(self.DEFAULT_STYLE)
        self.description_edit.setMinimumHeight(110)
        layout.addWidget(self.description_edit)

        layout.addWidget(QLabel("Сложность:"))
        self.rating_widget = StarRatingWidget(self)
        self.rating_widget.set_rating(lesson.difficult if lesson else 0)
        layout.addWidget(self.rating_widget)

        self.rating_error_label = QLabel("Выбери сложность урока")
        self.rating_error_label.setStyleSheet(self.ERROR_LABEL_STYLE)
        self.rating_error_label.hide()
        layout.addWidget(self.rating_error_label)

        layout.addWidget(QLabel("Рука:"))
        self.hand_combo = QComboBox()
        self.hand_combo.addItem("Правая рука", "right")
        self.hand_combo.addItem("Левая рука", "left")
        if lesson and hasattr(lesson, "hand") and lesson.hand == "left":
            self.hand_combo.setCurrentIndex(1)
        else:
            self.hand_combo.setCurrentIndex(0)
        self.hand_combo.setStyleSheet(self.DEFAULT_STYLE)
        layout.addWidget(self.hand_combo)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self.btn_cancel = QPushButton("Отмена")
        self.btn_save = QPushButton("Сохранить")
        self.btn_save.setEnabled(False)

        self.btn_save.setStyleSheet(
            "QPushButton { background: #3f8bde; color: white; border-radius: 8px; padding: 8px 15px; font-weight: bold; }"
            "QPushButton:hover { background: #2968c0; }"
            "QPushButton:disabled { background: #a0c4eb; color: #f0f0f0; }"
        )
        self.btn_cancel.setStyleSheet(
            "QPushButton { background: #f0f0f0; color: #333; border-radius: 8px; padding: 8px 15px; font-weight: bold; border: 1px solid #ccc; }"
            "QPushButton:hover { background: #e0e0e0; }"
        )

        buttons_layout.addWidget(self.btn_cancel)
        buttons_layout.addWidget(self.btn_save)
        layout.addLayout(buttons_layout)

        self.name_edit.textChanged.connect(self.validate_form)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self.accept)

        for button in self.rating_widget.buttons:
            button.clicked.connect(self.validate_form)

        self.validate_form()

    def validate_form(self):
        has_name = bool(self.name_edit.text().strip())
        has_rating = self.rating_widget.rating > 0

        self.name_edit.setStyleSheet(
            self.DEFAULT_STYLE if has_name else self.ERROR_STYLE
        )
        self.name_error_label.setVisible(not has_name)
        if not has_name:
            self.name_error_label.setText("Название урока не может быть пустым")

        self.rating_error_label.setVisible(not has_rating)
        self.btn_save.setEnabled(has_name and has_rating)

    def get_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "description": self.description_edit.toPlainText().strip(),
            "difficult": self.rating_widget.rating,
            "hand": self.hand_combo.currentData(),
            "topic_id": self.topic_id,
        }


class CreatorController(QWidget):
    lesson_created = pyqtSignal(int)
    lesson_updated = pyqtSignal(int)

    def __init__(
        self,
        time_signature,
        topic_id,
        lesson: LessonResponse | None = None,
        hand: str = "right",
    ):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.api = LessonWorker()
        self.time_signature = time_signature
        self.topic_id = int(topic_id)
        self.lesson = lesson
        self.lesson_id = lesson.id if lesson else None
        self.hand = (
            hand if lesson is None else (getattr(lesson, "hand", "right") or "right")
        )
        self.metronome_beats = int(self.time_signature.split("/")[0])
        self.metronome_count = 0
        self._playback_token = 0
        self._metronome_active = False
        self.practice_mode = False
        self.play_started = False
        self.current_note = None
        self.score = 0
        self.misses = 0
        self.current_playhead_x = 0
        self.current_playhead_y = Y0
        player.note_correct.connect(self.on_note_correct_graphic)
        player.note_wrong.connect(self.on_note_wrong_graphic)
        self.player_thread = None
        self.current_feedback_bit = None
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_playhead)

        combo = self.ui.duration_combo
        combo.setIconSize(QSize(28, 28))
        combo.addItem(QIcon("app/photos/whole.png"), "Целая", 1.0)
        combo.addItem(QIcon("app/photos/half.png"), "Половинная", 0.5)
        combo.addItem(QIcon("app/photos/half_dot.png"), "Половинная с точкой", 0.75)
        combo.addItem(QIcon("app/photos/quarter.png"), "Четверть", 0.25)
        combo.addItem(QIcon("app/photos/quarter_dot.png"), "Четверть с точкой", 0.375)
        combo.addItem(QIcon("app/photos/eight.png"), "Восьмая", 0.125)
        # combo.addItem(QIcon("app/photos/eight_dot.png"), "Восьмая с точкой", 0.1875)
        combo.setCurrentIndex(3)
        combo.currentIndexChanged.connect(self.on_duration_changed)

        accidental_combo = self.ui.accidental_combo
        accidental_combo.addItem("Нет (♮)", "natural")
        accidental_combo.addItem("Диез (♯)", "sharp")
        accidental_combo.addItem("Бемоль (♭)", "flat")
        accidental_combo.setCurrentIndex(0)
        accidental_combo.currentIndexChanged.connect(self.on_accidental_changed)

        input_mode_combo = self.ui.input_mode_combo
        input_mode_combo.addItem("Нота", "note")
        input_mode_combo.addItem("Пауза", "rest")
        input_mode_combo.setCurrentIndex(0)
        input_mode_combo.currentIndexChanged.connect(self.on_input_mode_changed)

        hand_combo = self.ui.hand_combo
        hand_combo.addItem("Правая", "right")
        hand_combo.addItem("Левая", "left")
        # Устанавливаем выбранную руку (либо переданную, либо из существующего урока)
        if self.hand == "left":
            hand_combo.setCurrentIndex(1)
        else:
            hand_combo.setCurrentIndex(0)
        hand_combo.currentIndexChanged.connect(self.on_hand_changed)

        self.load_scene(self.hand)
        self.init_playhead()
        self.on_input_mode_changed(self.ui.input_mode_combo.currentIndex())

        self.api.lesson_created_sygnal.connect(self.on_lesson_created)
        self.api.lesson_updated_signal.connect(self.on_lesson_updated)
        self.api.lesson_error_sygnal.connect(self.on_lesson_error)
        self.api.lesson_get_signal.connect(self.on_lesson_get)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.connect_buttons()

        if self.lesson:
            self.on_lesson_get(self.lesson)

    def on_accidental_changed(self, _index):
        settings.accidental = self.ui.accidental_combo.currentData()

    def on_input_mode_changed(self, _index):
        settings.input_mode = self.ui.input_mode_combo.currentData()
        is_note_mode = settings.input_mode == "note"
        self.ui.accidental_combo.setEnabled(is_note_mode)

    def on_hand_changed(self, _index):
        hand = self.ui.hand_combo.currentData()
        self.load_scene(hand)

    def on_note_correct_graphic(self, note_item, _note_name):
        if not self.practice_mode:
            return
        if note_item is None:
            return
        x = self.playhead.line().x1()
        y = Y0 + 200
        self.create_feedback_circle(x, y, is_correct=True)

    def on_note_wrong_graphic(
        self, note_item, _expected_note_name, _played_note_name, is_timeout
    ):
        if not self.practice_mode:
            return

        if is_timeout:
            x = note_item.x
            y = Y0 + 200
        else:
            if self.playhead.isVisible():
                x = self.playhead.line().x1()
            else:
                x = note_item.x
            y = Y0 + 200

        self.create_feedback_circle(x, y, is_correct=False)

    def create_feedback_circle(self, x, y, is_correct):
        circle = QGraphicsEllipseItem(x - 5, y - 5, 10, 10)
        color = QColor("green") if is_correct else QColor("red")
        circle.setBrush(QBrush(color))
        circle.setPen(QPen(Qt.GlobalColor.transparent))
        self.scene.addItem(circle)

    def init_playhead(self):
        self.playhead = QGraphicsLineItem(X0, Y0, X0, Y0 + 200)
        self.playhead.setPen(QPen(QColor("#ff4444"), 3))
        self.playhead.setZValue(100)
        self.scene.addItem(self.playhead)
        self.playhead.hide()

    def on_note_feedback(self, note_name, dt):
        print("on_note_feedback")
        circle = QGraphicsEllipseItem(20, 20, 40, 40)
        circle.setBrush(QColor("green"))
        circle.setPos(100, 100)
        self.scene.addItem(circle)
        print(f"🎯 Идеально! {note_name} dt={dt:.3f}")

    def on_note_miss(self, note_name, dt):
        print(f"💥 Промах! {note_name} dt={dt:.3f}")

    def on_duration_changed(self, _index):
        self.current_duration = self.ui.duration_combo.currentData()
        self.lay.set_duration(self.current_duration)
        print(f"Выбрана длительность: {self.current_duration}")

    def on_note_correct(self, note_name):
        print(f"🎯 Идеально! Нота {note_name}")
        self.score += 1

    def on_note_wrong(self, note_name):
        print(f"💥 Рано/поздно! {note_name or 'неизвестная нота'}")
        self.misses += 1

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            if not event.isAutoRepeat() and self.play_started:
                player.check_space_press()
            event.accept()
        else:
            super().keyPressEvent(event)

    def connect_buttons(self):
        self.ui.start_button.clicked.connect(self.on_start_clicked)
        self.ui.save_button.clicked.connect(self.on_save_clicked)
        self.ui.add_tact_button.clicked.connect(self.on_add_tact_clicked)
        self.ui.reset_button.clicked.connect(self.on_reset_clicked)
        self.ui.exit_button.clicked.connect(self.on_exit_clicked)
        self.ui.delete_tact_button.clicked.connect(self.on_delete_tact)

    def on_add_tact_clicked(self):
        self.lay.add_tact()
        print("Такт добавлен")

    def load_scene(self, hand="right"):
        self.scene = QGraphicsScene(0, 0, 1000, 1000)
        settings.scene = self.scene
        self.lay = StaffLayout(self.scene, self.time_signature, hand=hand)
        self.scene.setBackgroundBrush(BACKGROUND_SCENE_COLOR)
        self.ui.graphicsView.setScene(self.scene)
        self.ui.graphicsView.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.ui.graphicsView.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self.ui.graphicsView.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self.ui.graphicsView.setRenderHint(
            QPainter.RenderHint.SmoothPixmapTransform, True
        )

    def _find_first_unfilled_bit(self) -> tuple[int, int] | None:
        for tact_index, tact in enumerate(self.lay.tacts, start=1):
            for bit_index, bit in enumerate(tact.bits, start=1):
                if not getattr(bit, "is_filled", False):
                    return tact_index, bit_index
        return None

    def on_start_clicked(self):
        if self.animation_timer.isActive():
            self.animation_timer.stop()

        self._metronome_active = False
        if self.playhead.isVisible():
            self.playhead.hide()

        unfilled = self._find_first_unfilled_bit()
        if unfilled is not None:
            tact_index, bit_index = unfilled
            QMessageBox.warning(
                self,
                "Нельзя воспроизвести",
                f"Не все биты заполнены нотами.\nПусто: такт {tact_index}, бит {bit_index}.",
            )
            return

        self._playback_token += 1
        self._metronome_active = True
        self.play_started = False
        self.metronome_count = 0
        self.start_playhead_animation()
        self.play_metronome_beat(self._playback_token)

    def play_metronome_beat(self, token: int):
        if token != self._playback_token or not self._metronome_active:
            return

        interval_ms = int(60 / self.lay.bpm * 1000)
        player.play_click()
        self.metronome_count += 1

        if self.metronome_count < self.metronome_beats:
            QTimer.singleShot(interval_ms, lambda: self.play_metronome_beat(token))
            return

        if not self.playhead.isVisible():
            self._metronome_active = False
            return

        if not self.play_started:
            QTimer.singleShot(
                interval_ms - 50,
                lambda: self.lay.start_lesson(wait_for_input=self.practice_mode),
            )
            QTimer.singleShot(interval_ms, self.start_playhead_animation)
            QTimer.singleShot(interval_ms, lambda: self.animation_timer.start(50))

        QTimer.singleShot(interval_ms, lambda: self.play_metronome_beat(token))
        QTimer.singleShot(interval_ms - 50, lambda: setattr(self, "play_started", True))

    def start_playhead_animation(self):
        total_duration = 60 / self.lay.bpm * self.metronome_beats * len(self.lay.tacts)
        self.anim_total_duration = total_duration
        self.anim_start_time = time.time()

        self.playhead_segments, self.total_path_length = self.lay.get_playhead_path()
        if not self.playhead_segments:
            return

        first_seg = self.playhead_segments[0]
        start_x, start_y = first_seg[0], first_seg[1]
        self.playhead.setLine(start_x, start_y, start_x, start_y + 200)
        self.playhead.show()

    def update_playhead(self):
        elapsed = time.time() - self.anim_start_time
        if elapsed >= self.anim_total_duration:
            self.animation_timer.stop()
            self.playhead.hide()
            self._metronome_active = False
            return

        progress = elapsed / self.anim_total_duration
        target_dist = progress * self.total_path_length

        for x_start, y, x_end, _y_end, length, cum_start in self.playhead_segments:
            cum_end = cum_start + length
            if cum_start <= target_dist <= cum_end:
                local_dist = target_dist - cum_start
                t = local_dist / length
                current_x = x_start + t * (x_end - x_start)
                current_y = y
                self.playhead.setLine(current_x, current_y, current_x, current_y + 200)
                break

    def on_save_clicked(self):
        dialog = SaveLessonDialog(self.topic_id, self, self.lesson)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            form_data = dialog.get_data()
            lesson_data = self.lay.save_lesson(
                name=form_data["name"],
                description=form_data["description"],
                difficult=form_data["difficult"],
                topic_id=form_data["topic_id"],
                hand=form_data["hand"],
            )
            if self.lesson_id is None:
                self.api.create_lesson(lesson_data)
            else:
                self.api.update_lesson(
                    self.lesson_id, LessonUpdate(**lesson_data.model_dump())
                )
        except AttributeError:
            QMessageBox.warning(
                self, "Ошибка", "Метод save_lesson не реализован в StaffLayout"
            )

    def on_reset_clicked(self):
        self.score = 0
        self.misses = 0
        self.metronome_count = 0
        self.play_started = False
        self._metronome_active = False
        self.animation_timer.stop()
        self.playhead.hide()
        self.load_scene()
        self.init_playhead()
        print("Состояние сброшено")

    def on_listen_clicked(self):
        if self.lesson is not None:
            self.on_lesson_get(self.lesson)

    def on_delete_tact(self):
        self.lay.delete_tact()

    def on_lesson_created(self, lesson: LessonResponse):
        self.lesson = lesson
        self.lesson_id = lesson.id
        QMessageBox.information(self, "Успех", "Упражнение создано")
        self.lesson_created.emit(self.topic_id)

    def on_lesson_updated(self, lesson: LessonResponse):
        self.lesson = lesson
        self.lesson_id = lesson.id
        QMessageBox.information(self, "Успех", "Упражнение обновлено")
        self.lesson_updated.emit(self.topic_id)

    def on_lesson_error(self, error):
        QMessageBox.warning(self, "Ошибка", error)

    def on_lesson_get(self, lesson: LessonResponse):
        self.lesson = lesson
        self.lesson_id = lesson.id
        self.topic_id = lesson.topic
        self.lay.display_lesson(lesson)

    def on_exit_clicked(self):
        self.close()
