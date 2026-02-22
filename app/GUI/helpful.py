from PyQt6.QtWidgets import QGraphicsView
from PyQt6.QtCore import Qt



class ScalableGraphicsView(QGraphicsView):
    def __init__(self, parent=None):  # ✅ Стандартный parent!
        super().__init__(parent)  # НЕ scene!
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    
    def resizeEvent(self, event):
        if self.scene():  # Проверяем наличие сцены!
            self.fitInView(self.scene().sceneRect(), 
                          Qt.AspectRatioMode.KeepAspectRatio)
        super().resizeEvent(event)