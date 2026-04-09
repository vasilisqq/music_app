from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QRect, QRectF, QPropertyAnimation, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QLinearGradient, QPainterPath

class LessonCard(QFrame):
    def __init__(self, title="", progress=0.0, parent=None):
        super().__init__(parent)
        self._progress = progress  # от 0.0 до 1.0
        self.title = title
        self.setMinimumSize(300, 180)
        self.setMaximumSize(400, 220)
        self.setStyleSheet("""
            LessonCard {
                background-color: white;
                border-radius: 20px;
                border: 2px solid rgba(63, 139, 222, 0.2);
            }
        """)

        # Основной layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # Верхняя строка: название + процент
        top_layout = QHBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #1e8b1f; background: transparent;")
        self.percent_label = QLabel(self._get_percent_text())
        self.percent_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #3f8bde; background: transparent;")
        self.percent_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top_layout.addWidget(self.title_label)
        top_layout.addStretch()
        top_layout.addWidget(self.percent_label)
        layout.addLayout(top_layout)

        # Кнопка "Начать урок"
        self.play_btn = QPushButton("▶ Начать урок")
        self.play_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #26af27, stop:1 #1a9f26);
                border-radius: 12px;
                padding: 8px;
                font-size: 14px;
                font-weight: bold;
                color: white;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #1e8b1f, stop:1 #158015);
            }
        """)
        layout.addWidget(self.play_btn)
        layout.addStretch()

        # Анимация для плавного изменения прогресса
        self.animation = QPropertyAnimation(self, b"progress")
        self.animation.setDuration(500)

    def _get_percent_text(self):
        return f"{int(self._progress * 100)}%"

    def setProgress(self, value):
        """value от 0.0 до 1.0"""
        self._progress = max(0.0, min(1.0, value))
        self.percent_label.setText(self._get_percent_text())
        self.update()  # перерисовать фон

    def progress(self):
        return self._progress

    # Для PyQt6 используем pyqtProperty (не Property из QtCore)
    progress = pyqtProperty(float, fget=progress, fset=setProgress)

    def paintEvent(self, event):
        """Рисуем фон с цветной заливкой в зависимости от прогресса"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        # Рисуем белый фон с закруглениями
        path = self._rounded_rect_path(rect, 20)
        painter.fillPath(path, QBrush(QColor(255, 255, 255)))

        # Рисуем цветную полосу прогресса (снизу вверх)
        if self._progress > 0:
            progress_height = int(rect.height() * self._progress)
            progress_rect = QRect(rect.x(), rect.height() - progress_height,
                                  rect.width(), progress_height)
            # Градиент для красоты
            gradient = QLinearGradient(0, rect.height(), 0, rect.height() - progress_height)
            gradient.setColorAt(0, QColor(63, 139, 222, 180))   # #3f8bde с прозрачностью
            gradient.setColorAt(1, QColor(41, 104, 192, 180))   # #2968c0
            painter.fillRect(progress_rect, QBrush(gradient))

        # Обводим рамку
        painter.setPen(QPen(QColor(63, 139, 222, 50), 2))
        painter.drawPath(path)

    def _rounded_rect_path(self, rect, radius):
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), radius, radius)
        return path