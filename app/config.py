from PyQt6.QtGui import QPen, QBrush, QPainter, QColor
from PyQt6.QtCore import Qt

LINE_SPACING = 12
X0 = 40
Y0 = 118
WIDTH=400
BACKGROUND_SCENE_COLOR = QColor(255, 255, 255)
LINE_WIDTH = 1.2
SCENE_WIDTH = 1000

NORMAL_PEN  =  QPen(Qt.GlobalColor.black, LINE_WIDTH, Qt.PenStyle.SolidLine)

NORMAL_STYLE = """
QLineEdit { 
    padding: 15px 20px; border: 2px solid #eee; border-radius: 15px; font-size: 16px; 
    background: rgba(255,255,255,0.95); color: #333; 
}
QLineEdit:focus { 
    background: rgba(255,255,255,1); border: 3px solid #3f8bde; 
    padding: 14px 19px; 
}
"""

ERROR_STYLE = """
QLineEdit { 
    padding: 15px 20px; border: 3px solid #ff4444; border-radius: 15px; 
    font-size: 16px; background: rgba(255,220,220,0.95); color: #333; 
}
"""