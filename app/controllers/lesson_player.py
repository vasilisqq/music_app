from __future__ import annotations

import time

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QMessageBox

from GUI.creator import Ui_MainWindow
from schemas.lesson import LessonResponse
from staff import StaffLayout
from test import player
from workers.progress_worker import ProgressWorker


class LessonPlayerController(QWidget):
    closed = pyqtSignal(bool)  # was_completed

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

        self._setup_readonly_ui()
        self._setup_scene()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _setup_readonly_ui(self):
        for w in [
            self.ui.add_tact_button,
            self.ui.delete_tact_button,
            self.ui.save_button,
            self.ui.reset_button,
            self.ui.duration_combo,
            self.ui.accidental_combo,
        ]:
            w.hide()

        self.ui.start_button.setText("Слушать")
        self.ui.exit_button.setText("Назад")

        header = QWidget(self)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(2)

        title_label = QLabel(self.lesson.name)
        title_label.setStyleSheet("font-size: 18px; font-weight: 800; color: #1a1a1a;")
        desc_label = QLabel((self.lesson.description or "").strip())
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("font-size: 12px; color: rgba(26, 26, 26, 0.7);")

        header_layout.addWidget(title_label)
        header_layout.addWidget(desc_label)

        self.ui.verticalLayout.insertWidget(0, header)

        self.repeat_button = QPushButton("Повторить")
        self.repeat_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.repeat_button.setStyleSheet(
            "QPushButton { background: #3f8bde; color: white; border-radius: 10px; padding: 10px 18px; font-weight: 800; }"
            "QPushButton:hover { background: #2968c0; }"
        )

        self.ui.buttonsRow.insertWidget(1, self.repeat_button)

        self.ui.exit_button.clicked.connect(self._close)
        self.ui.start_button.clicked.connect(self._listen)
        self.repeat_button.clicked.connect(self._repeat)

    def _setup_scene(self):
        self.scene = self.ui.graphicsView.scene()
        if self.scene is None:
            from PyQt6.QtWidgets import QGraphicsScene
            self.scene = QGraphicsScene(0, 0, 1000, 1000)
            self.scene = self.scene
            # self.lay = StaffLayout(self.scene, self.time_signature)
            # self.scene.setBackgroundBrush(BACKGROUND_SCENE_COLOR)
            self.ui.graphicsView.setScene(self.scene)
            # self.ui.graphicsView.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            self.ui.graphicsView.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
            self.ui.graphicsView.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            # self.ui.graphicsView.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        time_signature = "4/4"
        try:
            beats = int(float(self.lesson.rhythm) * 4)
            time_signature = f"{beats}/4"
        except Exception:
            pass

        self.layout = StaffLayout(self.scene, time_signature, read_only=True)
        self.layout.display_lesson(self.lesson)

    def _estimate_duration_ms(self) -> int:
        bpm = float(getattr(self.layout, "bpm", 60))
        beats_per_measure = int(getattr(self.layout, "beats_per_measure", 4))
        total_duration_sec = (60.0 / bpm) * beats_per_measure * len(getattr(self.layout, "tacts", []))
        return max(1000, int(total_duration_sec * 1000))

    def _listen(self):
        self._stop_practice_listeners()
        self._practice_mode = False
        self.layout.start_lesson(wait_for_input=False, play_sound=True)

    def _repeat(self):
        self._stop_practice_listeners()
        self._practice_mode = True
        self._correct = 0
        self._wrong = 0

        player.note_correct.connect(self._on_note_correct)
        player.note_wrong.connect(self._on_note_wrong)

        self._start_metronome()
        self.layout.start_lesson(wait_for_input=True, play_sound=False)

        self._repeat_timer.stop()
        self._repeat_timer.start(self._estimate_duration_ms())

    def _start_metronome(self):
        self._playback_token += 1
        token = self._playback_token
        self._metronome_active = True
        self._play_metronome_beat(token)

    def _play_metronome_beat(self, token: int):
        if token != self._playback_token or not self._metronome_active:
            return

        interval_ms = int(60 / float(getattr(self.layout, "bpm", 60)) * 1000)
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

        total = self._correct + self._wrong
        accuracy = 0.0 if total == 0 else (self._correct / total) * 100.0
        QMessageBox.information(self, "Результат", f"Точность: {accuracy:.0f}% (correct: {self._correct}, wrong: {self._wrong})")

        if accuracy >= 80.0:
            self.progress_worker.complete_lesson(int(self.lesson.id))
        else:
            self._close()

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
        self._metronome_active = False
        self._stop_practice_listeners()
        self.closed.emit(self._was_completed)

    def closeEvent(self, event):
        self._metronome_active = False
        self._stop_practice_listeners()
        super().closeEvent(event)

    def _show_error(self, msg: str):
        QMessageBox.warning(self, "Ошибка", msg)
