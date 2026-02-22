import sys
from PyQt6.QtWidgets import QApplication
from controllers.auth import Auth
from app.controllers.creator import CreatorController
from PyQt6.QtCore import QSysInfo, QStorageInfo

def main() -> None:
    app = QApplication(sys.argv)
    window = CreatorController()
    window.show()
    # Создаем и отображаем главное окно
    # auth = Auth()
    # auth.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()