"""
GUI Configuration Module

Содержит все константы и стили для GUI приложения.
Включает конфигурацию для отрисовки и стилизации элементов интерфейса.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPen

# ============================================================================
# ОТРИСОВКА СЦЕНЫ
# ============================================================================

"""Константы для отрисовки нотного стана на сцене"""

LINE_SPACING: int = 12
"""Расстояние между линиями нотного стана (в пиксели)"""

X0: int = 40
"""Начальная X координата для отрисовки нот"""

Y0: int = 118
"""Начальная Y координата для отрисовки нот"""

WIDTH: int = 400
"""Ширина области для отрисовки нот"""

SCENE_WIDTH: int = 1000
"""Ширина всей сцены"""

BACKGROUND_SCENE_COLOR: QColor = QColor(255, 255, 255)
"""Цвет фона сцены (белый)"""

LINE_WIDTH: float = 1.2
"""Толщина линий нотного стана"""

NORMAL_PEN: QPen = QPen(Qt.GlobalColor.black, LINE_WIDTH, Qt.PenStyle.SolidLine)
"""Стиль пера для обычного рисования линий"""


# ============================================================================
# СТИЛИ ЭЛЕМЕНТОВ ИНТЕРФЕЙСА
# ============================================================================

"""QSS стили (Qt Style Sheets) для различных состояний элементов"""

NORMAL_STYLE: str = """
QLineEdit { 
    padding: 15px 20px; 
    border: 2px solid #eee; 
    border-radius: 15px; 
    font-size: 16px; 
    background: rgba(255,255,255,0.95); 
    color: #333; 
}
QLineEdit:focus { 
    background: rgba(255,255,255,1); 
    border: 3px solid #3f8bde; 
    padding: 14px 19px; 
}
"""
"""Стиль для обычного состояния полей ввода"""

ERROR_STYLE: str = """
QLineEdit { 
    padding: 15px 20px; 
    border: 3px solid #ff4444; 
    border-radius: 15px; 
    font-size: 16px; 
    background: rgba(255,220,220,0.95); 
    color: #333; 
}
"""
"""Стиль для полей ввода с ошибками"""

# Стили для аутентификации
AUTH_NORMAL_STYLE: str = """
QLineEdit { 
    padding: 15px 20px; 
    border: none; 
    border-radius: 15px; 
    font-size: 18px; 
    background: rgba(255,255,255,0.95); 
    color: #333; 
}
QLineEdit:focus { 
    background: rgba(255,255,255,1); 
    border: 3px solid #4facfe; 
    padding: 12px 17px; 
}
"""
"""Стиль для полей ввода на экране аутентификации"""

AUTH_ERROR_STYLE: str = """
QLineEdit { 
    padding: 15px 20px; 
    border: 3px solid #ff4444; 
    border-radius: 15px; 
    font-size: 18px; 
    background: rgba(255,220,220,0.95); 
    color: #333; 
}
"""
"""Стиль для ошибок на экране аутентификации"""
