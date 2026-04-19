import sys
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QShortcut, QKeySequence, QIcon
from PyQt6.QtWidgets import (
    QGraphicsScene,
    QWidget,
    QMessageBox
)
from PyQt6.QtGui import QPen, QColor, QBrush
from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsLineItem
from staff import StaffLayout, settings
from test import player
from config import BACKGROUND_SCENE_COLOR
from workers.lesson_worker import LessonWorker
from scipy.io import wavfile
import time
from GUI.creator import Ui_MainWindow
import threading
from config import X0, Y0

# SAMPLE_RATE, PIANO_C4 = wavfile.read('C4.wav')



class CreatorController(QWidget):
    def __init__(self, time_signature, topic_id):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.api = LessonWorker()
        self.time_signature = time_signature
        self.topic_id = topic_id
        self.metronome_beats = int(self.time_signature.split('/')[0])
        combo = self.ui.duration_combo
        combo.addItem("Целая", 1.0)
        combo.addItem("Половинная", 0.5)
        combo.addItem("Четверть", 0.25)
        combo.addItem("Восьмая", 0.125)
        combo.setCurrentIndex(2)  # четверть по умолчанию
        combo.currentIndexChanged.connect(self.on_duration_changed)
        accidental_combo = self.ui.accidental_combo
        accidental_combo.addItem("Нет (♮)", "natural")
        accidental_combo.addItem("Диез (♯)", "sharp")
        accidental_combo.addItem("Бемоль (♭)", "flat")
        accidental_combo.setCurrentIndex(0) # По умолчанию знака нет
        accidental_combo.currentIndexChanged.connect(self.on_accidental_changed)
        self.load_scene()
        self.init_playhead()



        self.api.lesson_created_sygnal.connect(self.on_lesson_created)
        self.api.lesson_error_sygnal.connect(self.on_lesson_error)
        self.api.lesson_get_signal.connect(self.on_lesson_get)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.connect_buttons()
        self.play_started = False
        self.current_note = None
        self.score = 0
        self.misses = 0
        self.metronome_beats = 4          # количество ударов метронома перед стартом
        self.metronome_count = 0
        self.current_playhead_x = 0
        self.current_playhead_y = Y0
        player.note_correct.connect(self.on_note_correct_graphic)
        player.note_wrong.connect(self.on_note_wrong_graphic)
        self.player_thread = None
        self.current_feedback_bit = None  # какая нота сейчас оцениваем
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_playhead)

    # И новый метод для обработки изменения:
    def on_accidental_changed(self, index):
        settings.accidental = self.ui.accidental_combo.currentData()


    def on_note_correct_graphic(self, note_item, note_name):
        """Зелёный кружок под сыгранной нотой"""
        if note_item is None:
            return
        # Координаты центра ноты
        x = self.playhead.line().x1()
        y = Y0 + 200   # немного ниже ноты
        self.create_feedback_circle(x, y, is_correct=True)


    def on_note_wrong_graphic(self, note_item, note_name, is_timeout):
        """Красный кружок: при таймауте — под нотой, при неправильном нажатии — на playhead"""
        # if note_item is None:
        #     return

        if is_timeout:
            # Не нажали ничего — рисуем под нотой (или вообще ничего не рисуем)
            x = note_item.x
            y = Y0 + 200   # под нотой, как зелёный
            # Если хотите вообще не рисовать, просто return
        else:
            # Неправильное нажатие — на текущей позиции playhead
            if self.playhead.isVisible():
                x = self.playhead.line().x1()
            else:
                x = note_item.x
            y = Y0 + 200   # прямо на линии ноты

        self.create_feedback_circle(x, y, is_correct=False)

    def create_feedback_circle(self, x, y, is_correct):
        """Создаёт кружок и автоматически удаляет его через 1 сек"""
        circle = QGraphicsEllipseItem(x-5, y-5, 10, 10)
        color = QColor("green") if is_correct else QColor("red")
        circle.setBrush(QBrush(color))
        circle.setPen(QPen(Qt.GlobalColor.transparent))
        self.scene.addItem(circle)
        # QTimer.singleShot(1000, lambda: self.scene.removeItem(circle))



    def init_playhead(self):
        """🔥 Создаём красную вертикальную линию для анимации"""
        self.playhead = QGraphicsLineItem(X0, Y0, X0, Y0+200)  # x1,y1,x2,y2
        self.playhead.setPen(QPen(QColor("#ff4444"), 3))
        self.playhead.setZValue(100)  # поверх всех нот
        self.scene.addItem(self.playhead)
        self.playhead.hide()  # скрыта до старта


    def on_note_feedback(self, note_name, dt):
        print("on_note_feedback")
        """✅ ЗЕЛЁНЫЙ круг!"""
        circle = QGraphicsEllipseItem(20, 20, 40, 40)
        circle.setBrush(QColor("green"))
        circle.setPos(100, 100)
        self.scene.addItem(circle)
        print(f"🎯 Идеально! {note_name} dt={dt:.3f}")
        # self.show_feedback(True, dt)  # зелёный + точность
        

    def on_note_miss(self, note_name, dt):
        print(f"💥 Промах! {note_name} dt={dt:.3f}")
        # self.show_feedback(False, dt)

    def on_duration_changed(self, index):
        self.current_duration = self.ui.duration_combo.currentData()
        self.lay.set_duration(self.current_duration)
        print(f"Выбрана длительность: {self.current_duration}")

    def on_note_correct(self, note_name):
        """Правильное нажатие"""
        print(f"🎯 Идеально! Нота {note_name}")
        self.score += 1
    

    def on_note_wrong(self, note_name):
        """Неправильное нажатие"""
        print(f"💥 Рано/поздно! {note_name or 'неизвестная нота'}")
        self.misses += 1


    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            if not event.isAutoRepeat() and self.play_started:     # только первое нажатие
                player.check_space_press()
            event.accept()                   # не передаём событие дальше
        else:
            super().keyPressEvent(event)


    def connect_buttons(self):
        # Правильная привязка всех кнопок из UI
        self.ui.start_button.clicked.connect(self.on_start_clicked)
        self.ui.save_button.clicked.connect(self.on_save_clicked)
        self.ui.add_tact_button.clicked.connect(self.on_add_tact_clicked)
        self.ui.reset_button.clicked.connect(self.on_reset_clicked)
        self.ui.exit_button.clicked.connect(self.on_exit_clicked)
        self.ui.delete_tact_button.clicked.connect(self.on_delete_tact)


    def on_add_tact_clicked(self):
        """Добавляет новый такт на нотный стан"""
        self.lay.add_tact()
        print("Такт добавлен")


    

    def load_scene(self):
        self.scene = QGraphicsScene(0,0,1000,1000)
        settings.scene = self.scene
        self.lay = StaffLayout(self.scene, self.time_signature)
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
        self.ui.graphicsView.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        # self.view.fitInView(self.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        # Выравниваем содержимое в левом верхнем углу
        self.ui.graphicsView.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        # Устанавливаем область сцены (важно для корректного отображения)
        # self.ui.graphicsView.setSceneRect(self.scene.sceneRect())
        # Чтобы изображение не было пиксельным, устанавливаем режим сглаживания для изображений
        self.ui.graphicsView.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        # self.scene.setSceneRect(self.scene.itemsBoundingRect())
        


    def on_start_clicked(self):
        # self.lay.start_lesson()
        # QTimer.singleShot(int(0.4 * 1000), self.start_playhead_animation)
        self.metronome_count = 0
        self.start_playhead_animation()
        self.play_metronome_beat()


    def play_metronome_beat(self):
        interval_ms = int(60 / self.lay.bpm * 1000)
        player.play_click()
        self.metronome_count += 1
        """Воспроизводит один удар метронома и планирует следующий или запускает упражнение"""
        if self.metronome_count < self.metronome_beats:
            # Планируем следующий удар через интервал, соответствующий BPM
            QTimer.singleShot(interval_ms, self.play_metronome_beat)
        elif self.playhead.isVisible():
            if not self.play_started:
                QTimer.singleShot(interval_ms - 50, self.lay.start_lesson)
                QTimer.singleShot(interval_ms, self.start_playhead_animation)
                QTimer.singleShot(interval_ms, lambda: self.animation_timer.start(50))
            QTimer.singleShot(interval_ms, self.play_metronome_beat)
            QTimer.singleShot(interval_ms - 50, lambda: setattr(self, 'play_started', True))
            # Последний удар был – запускаем упражнение
                

    def start_playhead_animation(self):
        total_duration = 60 / self.lay.bpm * 4 * len(self.lay.tacts)  # или точнее через сумму длительностей
        self.anim_total_duration = total_duration
        self.anim_start_time = time.time()

        # Получаем путь от StaffLayout
        self.playhead_segments, self.total_path_length = self.lay.get_playhead_path()
        if not self.playhead_segments:
            return

        # Начальная точка первого сегмента
        first_seg = self.playhead_segments[0]
        start_x, start_y = first_seg[0], first_seg[1]
        self.playhead.setLine(start_x, start_y, start_x, start_y + 200)
        self.playhead.show()

        

    def update_playhead(self):
        elapsed = time.time() - self.anim_start_time
        if elapsed >= self.anim_total_duration:
            self.animation_timer.stop()
            self.playhead.hide()
            return

        progress = elapsed / self.anim_total_duration
        target_dist = progress * self.total_path_length

        # Находим сегмент, содержащий target_dist
        for (x_start, y, x_end, y_end, length, cum_start) in self.playhead_segments:
            cum_end = cum_start + length
            if cum_start <= target_dist <= cum_end:
                local_dist = target_dist - cum_start
                t = local_dist / length
                current_x = x_start + t * (x_end - x_start)
                current_y = y  # если y не меняется внутри строки
                # Если в будущем понадобятся строки с наклоном, можно интерполировать y
                self.playhead.setLine(current_x, current_y, current_x, current_y + 200)
                break




    def on_save_clicked(self):
        """Собирает данные урока и отправляет на сервер"""
        # Раскомментируем и доводим до ума логику сохранения
        try:
            lesson_data = self.lay.save_lesson()
            if lesson_data:
                print("Сохранение урока:", lesson_data)
                self.api.create_lesson(lesson_data)
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось сохранить урок. Возможно, не все такты заполнены.")
        except AttributeError:
             QMessageBox.warning(self, "Ошибка", "Метод save_lesson не реализован в StaffLayout")


    def on_reset_clicked(self):
        """Сброс состояния окна/урока"""
        # Сбрасываем счетчики и останавливаем воспроизведение
        self.score = 0
        self.misses = 0
        self.metronome_count = 0
        self.play_started = False
        self.animation_timer.stop()
        self.playhead.hide()
        
        # Полностью перерисовываем сцену для сброса (или можно добавить метод clear() в StaffLayout)
        self.load_scene()
        self.init_playhead()
        print("Состояние сброшено")



    def on_listen_clicked(self):
        self.api.get_lesson()

    def on_delete_tact(self):
        """Метод для удаления последнего такта"""
        self.lay.delete_tact()

    def on_lesson_created(self):
        QMessageBox.information(self, "Успех", "Упражнение создано")

    def on_lesson_error(self,error):
        QMessageBox.warning(self, "Ошибка", error)

    def on_lesson_get(self, lesson):
        self.lay.display_lesson(lesson)

    def on_exit_clicked(self):
        """Закрывает текущее окно"""
        self.close()

    

