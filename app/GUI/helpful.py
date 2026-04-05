from PyQt6.QtWidgets import QGraphicsView
from PyQt6.QtCore import Qt



class ScalableGraphicsView(QGraphicsView):
    def __init__(self, parent=None):  # ✅ Стандартный parent!
        super().__init__(parent)  # НЕ scene!
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
    
    def resizeEvent(self, event):
        center = None
        if self.scene():
            center = self.mapToScene(self.viewport().rect().center())
            self.fitInView(self.scene().sceneRect(), 
                          Qt.AspectRatioMode.KeepAspectRatioByExpanding)
        super().resizeEvent(event)
        if center is not None:
            self.centerOn(center)