from __future__ import annotations

import time

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QPen
from PyQt6.QtWidgets import (
    QComboBox,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsScene,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from loader import settings

from GUI.creator import Ui_MainWindow
from schemas.lesson import LessonResponse
from staff import LINE_SPACING, StaffLayout
from test import normalize_note_name, player
from workers.progress_worker import ProgressWorker


class LessonPlayerController(QWidget):
    closed = pyqtSignal(bool)

    def __init__(self, lesson: LessonResponse):
        super().__init__()
        self.lesson = lesson

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.progress_worker = ProgressWorker()
        self.progress_worker.lesson_completed_signal.connect(self._on_lesson_completed)
        self.progress_worker.error_signal.connect(self._show_error)

        self._was_completed = False
        self._practice_mode = False
        self._correct = 0
        self._wrong = 0
        self._idle_presses = 0
        self._playback_token = 0
        self._metronome_active = False
        self._feedback_items = []
        self._input_active = False
        self._midi_input_port = None

        self._repeat_timer = QTimer()
        self._repeat_timer.setSingleShot(True)
        self._midi_poll_timer = QTimer()
        self._midi_poll_timer.setInterval(15)
        self._midi_poll_timer.timeout.connect(self._poll_midi_input)
        self._repeat_timer.timeout.connect(self._finish_repeat)

        self.playhead_timer = QTimer()
        self.playhead_timer.setInterval(16)
        self.playhead_timer.timeout.connect(self._update_playhead)

        self._setup_scroll_page()
        self._setup_readonly_ui()
        self._setup_scene()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()

    def _setup_scroll_page(self):
        root_layout = self.layout()
        self.page_widget = QWidget(self)
        self.page_layout = QVBoxLayout(self.page_widget)
        self.page_layout.setContentsMargins(20, 20, 20, 20)
        self.page_layout.setSpacing(15)

        items = []
        while root_layout.count():
            items.append(root_layout.takeAt(0))

        for item in items:
            if item.widget() is not None:
                self.page_layout.addWidget(item.widget())
            elif item.layout() is not None:
                self.page_layout.addLayout(item.layout())
            elif item.spacerItem() is not None:
                self.page_layout.addItem(item.spacerItem())

        self.page_widget.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred))

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.scroll_area.setWidget(self.page_widget)
        root_layout.addWidget(self.scroll_area)

        self.ui.verticalLayout = self.page_layout

    def _apply_equal_button_style(self, button: QPushButton):
        button.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed))
        button.setMinimumHeight(45)
        button.setMaximumWidth(16777215)
        button.setCursor(Qt.CursorShape.PointingHandCursor)

    def _toggle_description(self, checked: bool):
        self.description_preview_label.setVisible(not checked)
        self.description_label.setVisible(checked)
        self.description_toggle.setText("▲" if checked else "▼")
        self.page_widget.adjustSize()

    def _build_header(self) -> QWidget:
        header = QWidget(self)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        title_label = QLabel(self.lesson.name)
        title_label.setStyleSheet("font-size: 18px; font-weight: 800; color: #1a1a1a;")
        header_layout.addWidget(title_label)

        description = (self.lesson.description or "").strip()
        if description:
            preview = description if len(description) <= 80 else description[:79].rstrip() + "…"

            preview_row = QHBoxLayout()
            preview_row.setContentsMargins(0, 0, 0, 0)
            preview_row.setSpacing(4)

            self.description_preview_label = QLabel(preview)
            self.description_preview_label.setWordWrap(False)
            self.description_preview_label.setStyleSheet("font-size: 12px; color: rgba(26, 26, 26, 0.7);")
            self.description_preview_label.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred))

            self.description_toggle = QPushButton("▼")
            self.description_toggle.setCheckable(True)
            self.description_toggle.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed))
            self.description_toggle.setFixedSize(20, 20)
            self.description_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
            self.description_toggle.setStyleSheet(
                "QPushButton { background: transparent; border: none; color: rgba(26, 26, 26, 0.5); font-size: 14px; padding: 0px; }"
                "QPushButton:hover { color: rgba(26, 26, 26, 0.8); }"
                "QPushButton:checked { color: rgba(26, 26, 26, 0.8); }"
            )

            self.description_label = QLabel(description)
            self.description_label.setWordWrap(True)
            self.description_label.setVisible(False)
            self.description_label.setStyleSheet("font-size: 12px; color: rgba(26, 26, 26, 0.7); padding-left: 0px; margin-top: 2px;")

            self.description_toggle.toggled.connect(self._toggle_description)
            preview_row.addWidget(self.description_preview_label, 1)
            preview_row.addWidget(self.description_toggle, 0, Qt.AlignmentFlag.AlignTop)
            header_layout.addLayout(preview_row)
            header_layout.addWidget(self.description_label)

        return header

    def _setup_readonly_ui(self):
        for widget in [
            self.ui.add_tact_button,
            self.ui.delete_tact_button,
            self.ui.save_button,
            self.ui.reset_button,
            self.ui.duration_combo,
            self.ui.accidental_combo,
            self.ui.label_time_signature,
            self.ui.label_accidental,
        ]:
            widget.hide()

        self.bpm_label = QLabel("BPM:", self)
        self.bpm_combo = QComboBox(self)
        bpm_values = [40, 50, 60, 70, 80, 90, 100, 110, 120]
        for bpm in bpm_values:
            self.bpm_combo.addItem(str(bpm), bpm)
        selected_bpm = int(getattr(self.lesson, "bpm", 60) or 60)
        selected_index = self.bpm_combo.findData(selected_bpm)
        if selected_index < 0:
            selected_index = self.bpm_combo.findData(60)
        self.bpm_combo.setCurrentIndex(selected_index)
        self.bpm_combo.currentIndexChanged.connect(self._on_bpm_changed)
        self.ui.settingsRow.insertWidget(0, self.bpm_label)
        self.ui.settingsRow.insertWidget(1, self.bpm_combo)

        self.ui.start_button.setText("Слушать")
        self._on_bpm_changed(self.bpm_combo.currentIndex())
        self.ui.exit_button.setText("Назад")

        self.repeat_button = QPushButton("Повторить", self)
        self._apply_equal_button_style(self.ui.start_button)
        self._apply_equal_button_style(self.repeat_button)
        self._apply_equal_button_style(self.ui.exit_button)

        self.ui.exit_button.setMaximumSize(16777215, 16777215)
        self.ui.exit_button.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #ff4444, stop:1 #cc0000); border-radius: 8px; font-size: 15px; font-weight: bold; color: white; border: none; min-height: 45px; }"
            "QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #cc0000, stop:1 #990000); }"
        )

        self.ui.verticalLayout.insertWidget(0, self._build_header())
        self.ui.verticalLayout.addStretch()
        self.ui.buttonsRow.insertWidget(1, self.repeat_button)

        self.ui.exit_button.clicked.connect(self._close)
        self.ui.start_button.clicked.connect(self._listen)
        self.repeat_button.clicked.connect(self._repeat)

        self.ui.graphicsView.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred))
        self.ui.graphicsView.setMinimumHeight(400)
        self.ui.graphicsView.setMaximumHeight(560)
        self.ui.graphicsView.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.ui.graphicsView.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def _on_bpm_changed(self, _index: int):
        bpm = self.bpm_combo.currentData()
        if bpm is None:
            bpm = int(self.bpm_combo.currentText())
        if hasattr(self, "staff_layout") and self.staff_layout is not None:
            self.staff_layout.bpm = int(bpm)

    def _setup_scene(self):
        self.scene = self.ui.graphicsView.scene()
        if self.scene is None:
            self.scene = QGraphicsScene(0, 0, 1000, 1000)
            self.ui.graphicsView.setScene(self.scene)
            self.ui.graphicsView.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        time_signature = "4/4"
        try:
            beats = int(float(self.lesson.rhythm) * 4)
            time_signature = f"{beats}/4"
        except Exception:
            pass

        self.staff_layout = StaffLayout(self.scene, time_signature, read_only=True)
        self.staff_layout.display_lesson(self.lesson)
        self._on_bpm_changed(self.bpm_combo.currentIndex())

        self.playhead_line = QGraphicsLineItem()
        self.playhead_line.setPen(QPen(QColor(255, 0, 0, 180), 3))
        self.playhead_line.setZValue(100)
        self.playhead_line.hide()
        self.scene.addItem(self.playhead_line)

    def _estimate_duration_ms(self) -> int:
        bpm = float(getattr(self.staff_layout, "bpm", 60))
        beats_per_measure = int(getattr(self.staff_layout, "beats_per_measure", 4))
        total_duration_sec = (60.0 / bpm) * beats_per_measure * len(getattr(self.staff_layout, "tacts", []))
        return max(1000, int(total_duration_sec * 1000))

    def _listen(self):
        self._start_sequence(practice_mode=False)

    def _repeat(self):
        self._start_sequence(practice_mode=True)

    def _open_selected_midi_input(self) -> bool:
        device_name = settings.value("midi/input_device_name", None)
        if not device_name:
            QMessageBox.information(self, "Тренировка", "Сначала выбери MIDI-устройство в настройках.")
            return False

        try:
            import mido
        except Exception:
            QMessageBox.warning(self, "Тренировка", "Библиотека mido недоступна в текущем окружении.")
            return False

        try:
            self._midi_input_port = mido.open_input(device_name)
        except Exception as exc:
            QMessageBox.warning(self, "Тренировка", f"Не удалось открыть MIDI-устройство:\n{device_name}\n\n{exc}")
            self._midi_input_port = None
            return False

        self._midi_poll_timer.start()
        return True

    def _close_midi_input(self):
        self._midi_poll_timer.stop()
        port = self._midi_input_port
        self._midi_input_port = None
        if port is None:
            return
        try:
            port.close()
        except Exception:
            pass

    def _poll_midi_input(self):
        port = self._midi_input_port
        if port is None or not self._practice_mode or not self._input_active:
            return
        try:
            messages = list(port.iter_pending())
        except Exception:
            self._close_midi_input()
            return
        for message in messages:
            if getattr(message, "type", None) != "note_on" or getattr(message, "velocity", 0) <= 0:
                continue
            player.check_midi_note_number(int(message.note))

    def _start_sequence(self, practice_mode: bool):
        self._stop_practice_listeners()
        self._clear_feedback_markers()
        self._close_midi_input()
        self._practice_mode = practice_mode
        self._input_active = False
        self._correct = 0
        self._wrong = 0
        self._idle_presses = 0

        if practice_mode:
            if not self._open_selected_midi_input():
                self._practice_mode = False
                return
            player.note_correct.connect(self._on_note_correct)
            player.note_wrong.connect(self._on_note_wrong)
            player.note_ignored.connect(self._on_note_ignored)

        self._playback_token += 1
        token = self._playback_token

        self.playhead_timer.stop()
        self.playhead_line.hide()
        self._repeat_timer.stop()

        bpm = float(getattr(self.staff_layout, "bpm", 60))
        interval_ms = int((60.0 / bpm) * 1000)
        beats = int(getattr(self.staff_layout, "beats_per_measure", 4))
        self._count_in(beats, interval_ms, token, practice_mode)

    def _clear_feedback_markers(self):
        for item in self._feedback_items:
            try:
                self.scene.removeItem(item)
            except Exception:
                pass
        self._feedback_items.clear()

        current_note_await = getattr(player, "current_note_await", None)
        if current_note_await is not None:
            player.current_note_await = None
            player.current_note_await_time = None
            player.space_pressed_in_window = False
            player.current_note_item = None
        current_note_name = getattr(player, "current_note_name", None)
        if current_note_name is not None:
            player.current_note_name = None
            player.current_note_start_time = None
            player.pre_start_active = False

    def _update_playhead(self):
        elapsed = time.time() - self._playhead_start_time
        if elapsed >= self._playhead_total_sec:
            self.playhead_timer.stop()
            self.playhead_line.hide()
            return

        progress = elapsed / self._playhead_total_sec
        target_dist = progress * self.total_path_length

        for (x_start, y, x_end, _y_end, length, cum_start) in self.playhead_segments:
            cum_end = cum_start + length
            if cum_start <= target_dist <= cum_end:
                local_dist = target_dist - cum_start
                t = local_dist / length
                current_x = x_start + t * (x_end - x_start)
                self.playhead_line.setLine(current_x, y, current_x, y + 200)
                break

    def _count_in(self, remaining_beats: int, interval_ms: int, token: int, practice_mode: bool):
        if token != self._playback_token:
            return

        if remaining_beats > 1:
            player.play_click()
            QTimer.singleShot(interval_ms, lambda: self._count_in(remaining_beats - 1, interval_ms, token, practice_mode))
            return

        if remaining_beats == 1:
            player.play_click()
            QTimer.singleShot(interval_ms, lambda: self._start_synced_playback(token, practice_mode))

    def _start_synced_playback(self, token: int, practice_mode: bool):
        if token != self._playback_token:
            return

        self._input_active = practice_mode
        self.staff_layout.start_lesson(
            wait_for_input=practice_mode,
            play_sound=not practice_mode,
        )

        self._metronome_active = True
        self._play_metronome_beat(token)

        self.playhead_segments, self.total_path_length = self.staff_layout.get_playhead_path()
        if self.playhead_segments:
            first_seg = self.playhead_segments[0]
            start_x, start_y = first_seg[0], first_seg[1]
            self.playhead_line.setLine(start_x, start_y, start_x, start_y + 200)
            self.playhead_line.show()
            self._playhead_start_time = time.time()
            self._playhead_total_sec = self._estimate_duration_ms() / 1000.0
            self.playhead_timer.start(16)

        self._repeat_timer.start(self._estimate_duration_ms())

    def _play_metronome_beat(self, token: int):
        if token != self._playback_token or not self._metronome_active:
            return

        interval_ms = int(60 / float(getattr(self.staff_layout, "bpm", 60)) * 1000)
        player.play_click()
        QTimer.singleShot(interval_ms, lambda: self._play_metronome_beat(token))

    def keyPressEvent(self, event):
        super().keyPressEvent(event)

    def _add_feedback_circle(self, x: float, y: float, is_correct: bool):
        circle = QGraphicsEllipseItem(x - 6, y - 6, 12, 12)
        color = QColor("green") if is_correct else QColor("red")
        circle.setBrush(QBrush(color))
        circle.setPen(QPen(Qt.GlobalColor.transparent))
        circle.setZValue(150)
        self.scene.addItem(circle)
        self._feedback_items.append(circle)

    def _create_feedback_circle(self, note_item, is_correct: bool):
        if note_item is None:
            return

        x = note_item.x + 10
        y = note_item.y
        self._add_feedback_circle(x, y, is_correct=is_correct)

    def _create_playhead_feedback_circle(self, is_correct: bool):
        if not self.playhead_line.isVisible():
            return

        line = self.playhead_line.line()
        x = line.x1()
        y = line.y1() + 28
        self._add_feedback_circle(x, y, is_correct=is_correct)

    def _create_feedback_markers(self, note_item, is_correct: bool):
        if note_item is None:
            return
        notes = getattr(getattr(note_item, "bit", None), "notes", None) or [note_item]
        for bit_note in notes:
            self._create_feedback_circle(bit_note, is_correct=is_correct)

    def _get_staff_y_for_note(self, note_name: str) -> float | None:
        normalized_note = normalize_note_name(note_name)
        if not normalized_note:
            return None
        if not hasattr(self, "staff_layout") or self.staff_layout is None:
            return None
        if not getattr(self.staff_layout, "tacts", None):
            return None

        first_tact = self.staff_layout.tacts[0]
        if not getattr(first_tact, "lines", None):
            return None

        letter = normalized_note[0]
        octave_text = normalized_note[2:] if len(normalized_note) > 2 and normalized_note[1] in {"#", "b"} else normalized_note[1:]
        try:
            octave = int(octave_text)
        except ValueError:
            return None

        diatonic_steps = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}
        note_step = (octave * 7) + diatonic_steps[letter]
        top_line_step = (5 * 7) + diatonic_steps["F"]
        step_delta = top_line_step - note_step

        top_line_y = first_tact.lines[0].y
        return top_line_y + (step_delta * (LINE_SPACING / 2))

    def _create_played_note_feedback_circle(self, note_name: str, is_correct: bool):
        if not self.playhead_line.isVisible():
            return
        y = self._get_staff_y_for_note(note_name)
        if y is None:
            self._create_playhead_feedback_circle(is_correct=is_correct)
            return
        line = self.playhead_line.line()
        x = line.x1()
        self._add_feedback_circle(x, y, is_correct=is_correct)

    def _on_note_correct(self, note_item, _note_name):
        if not self._practice_mode:
            return
        self._correct += 1
        self._create_feedback_markers(note_item, is_correct=True)

    def _on_note_wrong(self, note_item, _expected_note_name, played_note_name, is_timeout):
        if not self._practice_mode:
            return
        self._wrong += 1
        if is_timeout:
            self._create_feedback_markers(note_item, is_correct=False)
        elif played_note_name:
            self._create_played_note_feedback_circle(played_note_name, is_correct=False)
        else:
            self._create_playhead_feedback_circle(is_correct=False)

    def _on_note_ignored(self):
        if not self._practice_mode:
            return
        self._idle_presses += 1
        self._create_playhead_feedback_circle(is_correct=False)

    def _finish_repeat(self):
        self._metronome_active = False
        self._input_active = False
        self._close_midi_input()
        self._stop_practice_listeners()
        self.playhead_timer.stop()
        self.playhead_line.hide()

        player.current_note_await = None
        player.current_note_await_time = None
        player.space_pressed_in_window = False
        player.current_note_item = None

        if not self._practice_mode:
            return

        total_attempts = self._correct + self._wrong + self._idle_presses
        accuracy = 0.0 if total_attempts == 0 else (self._correct / total_attempts) * 100.0
        QMessageBox.information(
            self,
            "Результат повтора",
            (
                f"Попаданий: {self._correct}\n"
                f"Промахов: {self._wrong}\n"
                f"Нажатий, когда нота не ожидалась: {self._idle_presses}\n"
                f"Общая точность: {accuracy:.0f}%"
            ),
        )
        if accuracy >= 80.0:
            self.progress_worker.complete_lesson(int(self.lesson.id))

    def _stop_practice_listeners(self):
        try:
            player.note_correct.disconnect(self._on_note_correct)
        except Exception:
            pass
        try:
            player.note_wrong.disconnect(self._on_note_wrong)
        except Exception:
            pass
        try:
            player.note_ignored.disconnect(self._on_note_ignored)
        except Exception:
            pass

    def _on_lesson_completed(self, _lesson_id: int):
        self._was_completed = True
        self._close()

    def _close(self):
        self.playhead_timer.stop()
        self.playhead_line.hide()
        self._metronome_active = False
        self._input_active = False
        self._close_midi_input()
        self._stop_practice_listeners()
        self._clear_feedback_markers()
        self.closed.emit(self._was_completed)

    def closeEvent(self, event):
        self._metronome_active = False
        self._input_active = False
        self._close_midi_input()
        self._stop_practice_listeners()
        self._clear_feedback_markers()
        super().closeEvent(event)

    def _show_error(self, msg: str):
        QMessageBox.warning(self, "Ошибка", msg)
