import sys
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPen, QBrush, QPainter, QColor
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsView,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QSizePolicy
)
from staff import HighlightableLineItem, StaffLayout
from musicpy import note, play, C, chord, concat, N, write
from test import play_piano_note
import sounddevice as sd
import numpy as np

class MainWindow(QWidget):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        # Настройка главного окна
        self.setWindowTitle("Rhythm Trainer")
        
        # Создаем главный вертикальный layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)  # Добавляем отступы
        
        # Создаем панель с кнопками
        button_panel = QWidget()
        
        # Устанавливаем для панели политику размеров, чтобы она не растягивалась
        button_panel.setSizePolicy(
            QSizePolicy.Policy.Preferred,  # По горизонтали - предпочтительный
            QSizePolicy.Policy.Fixed       # По вертикали - фиксированный
        )
        
        button_layout = QHBoxLayout(button_panel)
        button_layout.setContentsMargins(0, 0, 0, 0)  # Убираем отступы у панели кнопок
        
        # Создаем кнопки
        self.start_button = QPushButton("Старт")
        self.pause_button = QPushButton("Пауза")
        self.reset_button = QPushButton("Сброс")
        self.settings_button = QPushButton("Настройки")
        
        # Кнопки для изменения размерности такта
        self.time_44_button = QPushButton("4/4")
        self.time_34_button = QPushButton("3/4")
        
        # Добавляем кнопки на панель
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(QLabel("Размерность:"))  # Метка для кнопок размерности
        button_layout.addWidget(self.time_44_button)
        button_layout.addWidget(self.time_34_button)
        button_layout.addStretch()  # Растягивающее пространство
        button_layout.addWidget(self.settings_button)
        
        # Добавляем метку с названием
        title_label = QLabel("Rhythm Trainer - Отработка ритма")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 5px;")
        button_layout.insertWidget(0, title_label)
        
        # Создаем графическую сцену и представление
        self.lay = StaffLayout()
        self.scene = self.lay.init_staff()
        
        # Устанавливаем фон сцены
        self.scene.setBackgroundBrush(QColor(255, 255, 240))  # Светло-кремовый фон
        
        # Простой QGraphicsView без масштабирования
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        # Устанавливаем для view политику размеров, чтобы он растягивался
        self.view.setSizePolicy(
            QSizePolicy.Policy.Expanding,  # По горизонтали - расширяющийся
            QSizePolicy.Policy.Expanding   # По вертикали - расширяющийся
        )
        
        # Настраиваем view - ВАЖНО: убираем fitInView и центрирование!
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Выравниваем содержимое в левом верхнем углу
        self.view.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        # Устанавливаем область сцены (важно для корректного отображения)
        self.view.setSceneRect(self.scene.sceneRect())
        
        # Чтобы изображение не было пиксельным, устанавливаем режим сглаживания для изображений
        self.view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        
        # Добавляем виджеты в главный layout
        main_layout.addWidget(button_panel)  # Панель с кнопками (фиксированная высота)
        main_layout.addWidget(self.view, 1)  # Графическая сцена (растягивается)
        
        # Подключаем кнопки к функциям
        self.start_button.clicked.connect(self.on_start_clicked)
        self.pause_button.clicked.connect(self.on_pause_clicked)
        self.reset_button.clicked.connect(self.on_reset_clicked)
        self.settings_button.clicked.connect(self.on_settings_clicked)
        self.time_44_button.clicked.connect(lambda: self.on_time_signature_changed(4, 4))
        self.time_34_button.clicked.connect(lambda: self.on_time_signature_changed(3, 4))
        
        # Устанавливаем стили для кнопок
        self.setup_button_styles()
        
        # Устанавливаем минимальную высоту для панели кнопок
        button_panel.setMinimumHeight(60)
        
        # Добавляем информационную метку
        info_label = QLabel("Подсказка: Наведите курсор на линии и пространства между ними")
        info_label.setStyleSheet("color: #666; font-style: italic; padding: 5px;")
        main_layout.insertWidget(1, info_label)
    
    def setup_button_styles(self):
        """Настраивает стили кнопок"""
        button_style = """
        QPushButton {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 10px 20px;
            text-align: center;
            text-decoration: none;
            font-size: 16px;
            margin: 4px 2px;
            border-radius: 8px;
            min-width: 80px;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QPushButton:pressed {
            background-color: #3e8e41;
        }
        QPushButton:focus {
            outline: none;
        }
        """
        
        self.start_button.setStyleSheet(button_style)
        self.settings_button.setStyleSheet(button_style)
        
        # Изменяем цвет кнопки паузы для разнообразия
        self.pause_button.setStyleSheet("""
            QPushButton {
                background-color: #f0ad4e;
                color: white;
                border: none;
                padding: 10px 20px;
                text-align: center;
                text-decoration: none;
                font-size: 16px;
                margin: 4px 2px;
                border-radius: 8px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #ec971f;
            }
            QPushButton:pressed {
                background-color: #d58512;
            }
        """)
        
        # Изменяем цвет кнопки сброса
        self.reset_button.setStyleSheet("""
            QPushButton {
                background-color: #d9534f;
                color: white;
                border: none;
                padding: 10px 20px;
                text-align: center;
                text-decoration: none;
                font-size: 16px;
                margin: 4px 2px;
                border-radius: 8px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #c9302c;
            }
            QPushButton:pressed {
                background-color: #ac2925;
            }
        """)
        
        # Стиль для кнопок размерности такта
        time_button_style = """
        QPushButton {
            background-color: #5bc0de;
            color: white;
            border: none;
            padding: 10px 20px;
            text-align: center;
            text-decoration: none;
            font-size: 16px;
            margin: 4px 2px;
            border-radius: 8px;
            min-width: 60px;
        }
        QPushButton:hover {
            background-color: #31b0d5;
        }
        QPushButton:pressed {
            background-color: #269abc;
        }
        """
        
        self.time_44_button.setStyleSheet(time_button_style)
        self.time_34_button.setStyleSheet(time_button_style)
    


    def on_start_clicked(self):
        for tact in self.lay.tacts:
            for notes in tact.notes:
                duration = 60/self.lay.bpm * notes.note_lenght
                play_piano_note(notes.note_name, duration)




        


    def on_pause_clicked(self):
        """Обработчик кнопки Пауза"""
        print("Пауза")
    
    def on_reset_clicked(self):
        """Обработчик кнопки Сброс"""
        print("Сброс")
        # Очистка сцены от нот
        # Удаляем только элементы нот (QGraphicsEllipseItem и QGraphicsLineItem для штилей)
        for item in self.scene.items():
            if isinstance(item, QGraphicsEllipseItem) or isinstance(item, QGraphicsLineItem):
                # Проверяем, что это не линии нотного стана
                if not isinstance(item, HighlightableLineItem):
                    self.scene.removeItem(item)
    
    def on_settings_clicked(self):
        """Обработчик кнопки Настройки"""
        print("Открытие настроек")
    
    def on_time_signature_changed(self, numerator, denominator):
        """Обработчик изменения размерности такта"""
        print(f"Изменена размерность такта на {numerator}/{denominator}")
        
        # В реальном приложении здесь нужно обновить отображение размерности такта
        # и пересчитать расположение нот в соответствии с новой размерностью
        
        # Просто выводим сообщение для демонстрации
        info_label = QLabel(f"Размерность такта изменена на {numerator}/{denominator}")
        info_label.setStyleSheet("color: green; font-weight: bold; padding: 5px;")
        
        # Можно добавить временное сообщение в интерфейс
        # В данном примере просто выводим в консоль


    def add_quarter_note(self, scene: QGraphicsScene, x: float, y: float) -> None:
        w, h = 12, 9
        head = QGraphicsEllipseItem(QRectF(x - w / 2, y - h / 2, w, h))
        head.setBrush(QBrush(Qt.GlobalColor.black))
        head.setPen(QPen(Qt.GlobalColor.black))
        scene.addItem(head)
        
        stem = QGraphicsLineItem(x + w / 2 - 1, y, x + w / 2 - 1, y - 32)
        pen = QPen(Qt.GlobalColor.black)
        pen.setWidthF(1.2)
        stem.setPen(pen)
        scene.addItem(stem)
