import sys
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QShortcut, QKeySequence
from PyQt6.QtWidgets import (
    QGraphicsScene,
    QWidget,
    QMessageBox
)
from PyQt6.QtGui import QPen, QColor, QBrush
from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsLineItem
from staff import StaffLayout
from test import player
from config import BACKGROUND_SCENE_COLOR
from workers.lesson_worker import LessonWorker
from scipy.io import wavfile
import time
from GUI.creator import Ui_MainWindow
import threading
from config import X0

# SAMPLE_RATE, PIANO_C4 = wavfile.read('C4.wav')



class CreatorController(QWidget):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.api = LessonWorker()
        self.load_scene()
        self.init_playhead()

        self.api.lesson_created_sygnal.connect(self.on_lesson_created)
        self.api.lesson_error_sygnal.connect(self.on_lesson_error)
        self.api.lesson_get_signal.connect(self.on_lesson_get)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.connect_buttons()

        self.current_note = None
        self.score = 0
        self.misses = 0
        player.note_correct.connect(self.on_note_correct_graphic)
        player.note_wrong.connect(self.on_note_wrong_graphic)
        self.player_thread = None
        self.current_feedback_bit = None  # какая нота сейчас оцениваем
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_playhead)

    def on_note_correct_graphic(self, note_item, note_name):
        """Зелёный кружок под сыгранной нотой"""
        if note_item is None:
            return
        # Координаты центра ноты
        x = note_item.x
        y = note_item.y + 20   # немного ниже ноты
        self.create_feedback_circle(x, y, is_correct=True)


    def on_note_wrong_graphic(self, note_item, note_name):
        """Красный кружок на текущей позиции playhead, на высоте ожидаемой ноты"""
        if note_item is None:
            return
        # Получаем текущую X-координату playhead (если линия видна)
        if self.playhead.isVisible():
            x = self.playhead.line().x1()   # вертикальная линия – x1 и x2 равны
        else:
            x = note_item.x                 # запасной вариант
        y = note_item.y                      # прямо на линии ноты
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
        self.playhead = QGraphicsLineItem(0, 0, 0, 500)  # x1,y1,x2,y2
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


    def on_space_pressed(self):
        player.check_space_press()
    

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
            if not event.isAutoRepeat():     # только первое нажатие
                player.check_space_press()
            event.accept()                   # не передаём событие дальше
        else:
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
        self.lay.start_lesson()
        self.start_playhead_animation()

    def start_playhead_animation(self):
        """Запускает движение красной линии"""
        # Рассчитываем общую длительность урока
        total_duration = 0
        for tact in self.lay.tacts:
            for bit in tact.bits:
                total_duration += 60 / self.lay.bpm   # все биты одинаковой длины

        # Начальная и конечная позиции playhead
        start_x = X0 + 100                     # как в первом такте
        # Конец последнего такта
        last_tact = self.lay.tacts[-1]
        end_x = last_tact.x0 + last_tact.width

        # Настраиваем playhead
        self.playhead.setLine(start_x, 0, start_x, 500)
        self.playhead.show()

        # Сохраняем параметры анимации
        self.anim_start_x = start_x
        self.anim_end_x = end_x
        self.anim_total_duration = total_duration
        self.anim_start_time = time.time()

        # Запускаем таймер (обновление каждые 50 мс)
        self.animation_timer.start(50)

    def update_playhead(self):
        """Сдвигает playhead пропорционально прошедшему времени"""
        elapsed = time.time() - self.anim_start_time
        if elapsed >= self.anim_total_duration:
            self.animation_timer.stop()
            self.playhead.hide()
            return
        progress = elapsed / self.anim_total_duration
        current_x = self.anim_start_x + progress * (self.anim_end_x - self.anim_start_x)
        self.playhead.setLine(current_x, 0, current_x, 500)




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

