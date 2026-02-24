import sys
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QShortcut, QKeySequence
from PyQt6.QtWidgets import (
    QGraphicsScene,
    QWidget,
    QMessageBox
)
from staff import StaffLayout
from test import player
from config import BACKGROUND_SCENE_COLOR
from workers.lesson_worker import LessonWorker
from scipy.io import wavfile
import time
from GUI.creator import Ui_MainWindow
import threading

SAMPLE_RATE, PIANO_C4 = wavfile.read('C4.wav')



class CreatorController(QWidget):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.api = LessonWorker()
        self.load_scene()

        self.api.lesson_created_sygnal.connect(self.on_lesson_created)
        self.api.lesson_error_sygnal.connect(self.on_lesson_error)
        self.api.lesson_get_signal.connect(self.on_lesson_get)

        self.connect_buttons()


        self.score = 0
        self.misses = 0
        player.set_note_handlers(
            on_correct=self.on_note_correct,
            on_wrong=self.on_note_wrong
        )
        
        # 🔥 Создаём шорткат для пробела
        self.space_shortcut = QShortcut(QKeySequence("Space"), self)
        self.space_shortcut.activated.connect(self.on_space_pressed)
    
    def on_space_pressed(self):
        """Обработчик нажатия пробела"""
        if player.check_space_press():
            print("✅ ПРАВИЛЬНО! Пробел совпал с нотой")
        else:
            print("❌ ПРОМАХ! Нет активной ноты")
            if player.on_note_wrong:
                player.on_note_wrong()
    
    def on_note_correct(self, note_name):
        """Правильное нажатие"""
        print(f"🎯 Идеально! Нота {note_name}")
        self.score += 1
        # self.update_score_display()
    
    def on_note_wrong(self):
        """Неправильное нажатие"""
        print("💥 Рано/поздно!")
        self.misses += 1

    def keyPressEvent(self, event):
        """🔥 ТОЧНАЯ обработка клавиш без спама"""
        if event.key() == Qt.Key.Key_Space:
            event.accept()  # Блокируем системный пробел
            self.player.check_space_press()
        super().keyPressEvent(event)

    def connect_buttons(self):
        self.ui.start_button.clicked.connect(self.on_start_clicked)
        self.ui.save_button.clicked.connect(self.on_save_clicked)
        self.ui.reset_button.clicked.connect(self.on_listen_clicked)

    
    def load_scene(self):
        self.scene = QGraphicsScene(0,0,1000,500)
        self.lay = StaffLayout(self.scene)
        self.scene.setBackgroundBrush(BACKGROUND_SCENE_COLOR)
        self.ui.graphicsView.setScene(self.scene)
        self.ui.graphicsView.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        # Устанавливаем для view политику размеров, чтобы он растягивался
        # self.view.setSizePolicy(
        #     QSizePolicy.Policy.Expanding,  # По горизонтали - расширяющийся
        #     QSizePolicy.Policy.Expanding   # По вертикали - расширяющийся
        # )
        # Настраиваем view - ВАЖНО: убираем fitInView и центрирование!
        # self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # self.view.fitInView(self.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        # Выравниваем содержимое в левом верхнем углу
        self.ui.graphicsView.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        # Устанавливаем область сцены (важно для корректного отображения)
        # self.view.setSceneRect(self.scene.sceneRect())
        # Чтобы изображение не было пиксельным, устанавливаем режим сглаживания для изображений
        self.ui.graphicsView.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)


    def on_start_clicked(self):
        def play_sequence():
            for tact in self.lay.tacts:
                for bit in tact.bits:
                    for note in bit.notes:
                        duration = 60/self.lay.bpm * note.note_lenght * 4
                        player.play_note(note.note_name, duration, 0.7)
                    time.sleep(duration)  # Даём время нажать
    
        # Запуск в отдельном потоке
        threading.Thread(target=play_sequence, daemon=True).start()


    def on_save_clicked(self):
        QMessageBox.warning(self, "Ошибка", "Не все такты заполнены")
        # lesson = self.lay.save_lesson()
        # print(lesson)
        # self.api.create_lesson(lesson)


    def on_listen_clicked(self):
        self.api.get_lesson()


    def on_lesson_created(self):
        QMessageBox.information(self, "Успех", "Упражнение создано")

    def on_lesson_error(self,error):
        QMessageBox.warning(self, "Ошибка", error)

    def on_lesson_get(self, lesson):
        self.lay.display_lesson(lesson)

