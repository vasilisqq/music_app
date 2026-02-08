from PyQt6.QtWidgets import QMainWindow
from GUI.auth import Ui_AuthWindow

class Auth(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_AuthWindow()
        self.ui.setupUi(self)
