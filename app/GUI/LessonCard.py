from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QRect, QRectF, pyqtSignal, QSize, QPoint
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QLinearGradient, QPainterPath

class LessonCard(QFrame):
    clicked = pyqtSignal(object)

    def __init__(self, title="", progress=0.0, payload=None, status="available", parent=None):
        super().__init__(parent)
        self._progress = progress
        self.title = title
        self.payload = payload
        self.status = status # "available", "completed", "locked"
        
        self.setFixedSize(320, 200)
        
        # Меняем курсор: запрещающий для закрытых, рука для доступных
        if self.status == "locked":
            self.setCursor(Qt.CursorShape.ForbiddenCursor)
        else:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        
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
        
        # Цвет текста зависит от статуса
        text_color = "#666666" if self.status == "locked" else "#1a1a1a"
        self.title_label.setStyleSheet(f"font-size: 19px; font-weight: 800; color: {text_color}; background: transparent;")
        self.title_label.setWordWrap(True)
        
        # Индикатор в правом верхнем углу (замок, галочка или проценты)
        if self.status == "locked":
            self.percent_label = QLabel("🔒")
            self.percent_label.setStyleSheet("font-size: 17px; background: transparent;")
        elif self.status == "completed":
            self.percent_label = QLabel("✔️")
            self.percent_label.setStyleSheet("font-size: 17px; color: #28a745; background: transparent;")
        else:
            self.percent_label = QLabel(f"{int(self._progress * 100)}%")
            self.percent_label.setStyleSheet("font-size: 17px; font-weight: bold; color: #3f8bde; background: transparent;")
        
        top_layout.addWidget(self.title_label)
        top_layout.addStretch()
        top_layout.addWidget(self.percent_label)
        layout.addLayout(top_layout)
        layout.addStretch()

    def _set_style(self, hover):
        # Глухой темный стиль для заблокированных карточек
        if self.status == "locked":
            self.setStyleSheet("""
                LessonCard {
                    background-color: #2b2b2b;
                    border-radius: 20px;
                    border: 1px solid #1a1a1a;
                }
            """)
            return

        if self.status == "completed":
            border_color = "#28a745" if hover else "rgba(40, 167, 69, 0.4)"
        else:
            border_color = "#3f8bde" if hover else "rgba(63, 139, 222, 0.3)"

        border_width = "4px" if hover else "1px"
        bg_color = "#ffffff" if hover else "#fcfcfc"

        self.setStyleSheet(f"""
            LessonCard {{
                background-color: {bg_color};
                border-radius: 20px;
                border: {border_width} solid {border_color};
            }}
        """)

    def enterEvent(self, event):
        if self.status == "locked": return # Игнорируем наведение
        
        self._set_style(hover=True)
        self.shadow.setBlurRadius(30)
        self.shadow.setYOffset(8)
        
        shadow_color = QColor(40, 167, 69, 70) if self.status == "completed" else QColor(63, 139, 222, 70)
        self.shadow.setColor(shadow_color)

    def leaveEvent(self, event):
        if self.status == "locked": return # Игнорируем
        
        self._set_style(hover=False)
        self.shadow.setBlurRadius(15)
        self.shadow.setYOffset(4)
        self.shadow.setColor(QColor(0, 0, 0, 40))

    def mousePressEvent(self, event):
        # БЛОКИРУЕМ ЭМИТ СИГНАЛА КЛИКА
        if self.status == "locked": return 
        
        if event.button() == Qt.MouseButton.LeftButton:
            self.shadow.setYOffset(2)
            self.clicked.emit(self.payload if self.payload is not None else self.title)

    def mouseReleaseEvent(self, event):
        if self.status == "locked": return
        if self.underMouse():
            self.shadow.setYOffset(8)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), 20, 20)
        
        painter.setClipPath(path)
        
        # Перерисовка фона внутри QPainter
        if self.status == "locked":
            bg_color = QColor(43, 43, 43)
        else:
            bg_color = QColor(255, 255, 255) if self.underMouse() else QColor(252, 252, 252)
            
        painter.fillPath(path, QBrush(bg_color))

        # Градиентная заливка прогресса снизу
        if self._progress > 0 and self.status != "locked":
            h = int(rect.height() * self._progress)
            prog_rect = QRect(0, rect.height() - h, rect.width(), h)
            grad = QLinearGradient(0, rect.height(), 0, rect.height() - h)
            
            alpha = 90 if self.underMouse() else 50
            
            if self.status == "completed":
                grad.setColorAt(0, QColor(40, 167, 69, alpha)) 
                grad.setColorAt(1, QColor(30, 120, 50, alpha // 2))
            else:
                grad.setColorAt(0, QColor(63, 139, 222, alpha)) 
                grad.setColorAt(1, QColor(41, 104, 192, alpha // 2))
                
            painter.fillRect(prog_rect, QBrush(grad))
            
        painter.setClipping(False)