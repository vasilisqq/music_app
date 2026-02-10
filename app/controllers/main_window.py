from PyQt6.QtWidgets import QMainWindow,QMessageBox
from GUI.main_window import Ui_Main


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Main()
        self.ui.setupUi(self)
        