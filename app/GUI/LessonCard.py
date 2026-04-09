from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QRect, QRectF, pyqtSignal, QSize, QPoint
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QLinearGradient, QPainterPath

class LessonCard(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, title="", progress=0.0, parent=None):
        super().__init__(parent)
        self._progress = progress
        self.title = title
        
        # Строго фиксированный размер, который не меняется
        self.setFixedSize(320, 200)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Настройка тени
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(15)
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(4)
        self.shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(self.shadow)

        self._set_style(hover=False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        
        top_layout = QHBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-size: 19px; font-weight: 800; color: #1a1a1a; background: transparent;")
        self.title_label.setWordWrap(True)
        
        self.percent_label = QLabel(f"{int(self._progress * 100)}%")
        self.percent_label.setStyleSheet("font-size: 17px; font-weight: bold; color: #3f8bde; background: transparent;")
        
        top_layout.addWidget(self.title_label)
        top_layout.addStretch()
        top_layout.addWidget(self.percent_label)
        layout.addLayout(top_layout)
        layout.addStretch()

    def _set_style(self, hover):
        if hover:
            # Делаем рамку толще внутрь и ярче фон
            self.setStyleSheet("""
                LessonCard {
                    background-color: #ffffff;
                    border-radius: 20px;
                    border: 4px solid #3f8bde;
                }
            """)
        else:
            self.setStyleSheet("""
                LessonCard {
                    background-color: #fcfcfc;
                    border-radius: 20px;
                    border: 1px solid rgba(63, 139, 222, 0.3);
                }
            """)

    def enterEvent(self, event):
        self._set_style(hover=True)
        # Вместо размера меняем только глубину тени (это не ломает сетку)
        self.shadow.setBlurRadius(30)
        self.shadow.setYOffset(8)
        self.shadow.setColor(QColor(63, 139, 222, 70))

    def leaveEvent(self, event):
        self._set_style(hover=False)
        self.shadow.setBlurRadius(15)
        self.shadow.setYOffset(4)
        self.shadow.setColor(QColor(0, 0, 0, 40))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.shadow.setYOffset(2)
            self.clicked.emit(self.title)
            
    def mouseReleaseEvent(self, event):
        if self.underMouse():
            self.shadow.setYOffset(8)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), 20, 20)
        
        painter.setClipPath(path)
        # Цвет фона зависит от наведения
        bg_color = QColor(255, 255, 255) if self.underMouse() else QColor(252, 252, 252)
        painter.fillPath(path, QBrush(bg_color))

        if self._progress > 0:
            h = int(rect.height() * self._progress)
            prog_rect = QRect(0, rect.height() - h, rect.width(), h)
            grad = QLinearGradient(0, rect.height(), 0, rect.height() - h)
            
            # Сделаем заливку чуть более насыщенной при наведении
            alpha = 90 if self.underMouse() else 50
            grad.setColorAt(0, QColor(63, 139, 222, alpha)) 
            grad.setColorAt(1, QColor(41, 104, 192, alpha // 2))
            painter.fillRect(prog_rect, QBrush(grad))
            
        painter.setClipping(False)