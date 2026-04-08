from PyQt6.QtWidgets import QMainWindow
from GUI.main_window import Ui_MainWindow  # Убедись, что импортируешь правильный класс из сгенерированного файла
import sys

class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        # Зафиксированная ширина панели — меню всегда открыто
        self.expanded_width = 220

        # Применяем фиксированную ширину
        self.ui.drawerWidget.setMinimumWidth(self.expanded_width)
        self.ui.drawerWidget.setMaximumWidth(self.expanded_width)