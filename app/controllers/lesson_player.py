from __future__ import annotations

import time

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPen
from PyQt6.QtWidgets import (
    QGraphicsLineItem,
    QGraphicsScene,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from GUI.creator import Ui_MainWindow
from schemas.lesson import LessonResponse
from staff import StaffLayout
from test import player
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
        self._playback_token = 0
        self._metronome_active = False

        self._repeat_timer = QTimer()
        self._repeat_timer.setSingleShot(True)
        self._repeat_timer.timeout.connect(self._finish_repeat)

        self.playhead_timer = QTimer()
        self.playhead_timer.setInterval(16)
        self.playhead_timer.timeout.connect(self._update_playhead)

        self._setup_readonly_ui()
        self._setup_scene()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()

    def _apply_equal_button_style(self, button: QPushButton):
        button.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed))
        button.setMinimumHeight(45)
        button.setMaximumWidth(16777215)
        button.setCursor(Qt.CursorShape.PointingHandCursor)

    def _toggle_description(self, checked: bool):
        self.description_label.setVisible(checked)
        self.description_toggle.setText("Скрыть описание" if checked else "Показать описание")
        self.adjustSize()

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
            self.description_toggle = QPushButton("Показать описание")
            self.description_toggle.setCheckable(True)
            self.description_toggle.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed))
            self.description_toggle.setMinimumHeight(40)
            self.description_toggle.setCursor(Qt.CursorShape.PointingHandCursor)

            self.description_label = QLabel(description)
            self.description_label.setWordWrap(True)
            self.description_label.setVisible(False)
            self.description_label.setStyleSheet("font-size: 12px; color: rgba(26, 26, 26, 0.7);")

            self.description_toggle.toggled.connect(self._toggle_description)
            header_layout.addWidget(self.description_toggle, 0, Qt.AlignmentFlag.AlignLeft)
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

        self.ui.start_button.setText("Слушать")
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
        self.ui.buttonsRow.insertWidget(1, self.repeat_button)

        self.ui.exit_button.clicked.connect(self._close)
        self.ui.start_button.clicked.connect(self._listen)
        self.repeat_button.clicked.connect(self._repeat)

        self.ui.graphicsView.setMinimumHeight(520)
        self.ui.graphicsView.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.ui.graphicsView.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

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

    def _start_sequence(self, practice_mode: bool):
        self._stop_practice_listeners()
        self._practice_mode = practice_mode
        self._correct = 0
        self._wrong = 0

        if practice_mode:
            player.note_correct.connect(self._on_note_correct)
            player.note_wrong.connect(self._on_note_wrong)

        self._playback_token += 1
        token = self._playback_token

        self.playhead_timer.stop()
        self.playhead_line.hide()
        self._repeat_timer.stop()

        bpm = float(getattr(self.staff_layout, "bpm", 60))
        interval_ms = int((60.0 / bpm) * 1000)
        beats = int(getattr(self.staff_layout, "beats_per_measure", 4))
        self._count_in(beats, interval_ms, token, practice_mode)

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
            QTimer.singleShot(interval_ms - 50, lambda: self.staff_layout.start_lesson(wait_for_input=practice_mode, play_sound=True))
            QTimer.singleShot(interval_ms, lambda: self._start_synced_playback(token))

    def _start_synced_playback(self, token: int):
        if token != self._playback_token:
            return

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
        if self._practice_mode and event.key() == Qt.Key.Key_Space:
            player.check_space_press()
            event.accept()
            return
        super().keyPressEvent(event)

    def _on_note_correct(self, *_args):
        if self._practice_mode:
            self._correct += 1

    def _on_note_wrong(self, *_args):
        if self._practice_mode:
            self._wrong += 1

    def _finish_repeat(self):
        self._metronome_active = False
        self._stop_practice_listeners()
        self.playhead_timer.stop()
        self.playhead_line.hide()

        if not self._practice_mode:
            return

        total = self._correct + self._wrong
        accuracy = 0.0 if total == 0 else (self._correct / total) * 100.0
        QMessageBox.information(
            self,
            "Результат",
            f"Точность: {accuracy:.0f}% (correct: {self._correct}, wrong: {self._wrong})",
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

    def _on_lesson_completed(self, _lesson_id: int):
        self._was_completed = True
        self._close()

    def _close(self):
        self.playhead_timer.stop()
        self.playhead_line.hide()
        self._metronome_active = False
        self._stop_practice_listeners()
        self.closed.emit(self._was_completed)

    def closeEvent(self, event):
        self._metronome_active = False
        self._stop_practice_listeners()
        super().closeEvent(event)

    def _show_error(self, msg: str):
        QMessageBox.warning(self, "Ошибка", msg)
