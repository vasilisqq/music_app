import sys
from PyQt6.QtWidgets import QApplication
from controllers.auth import Auth
from app.controllers.creator import CreatorController
from controllers.main_window import Main
from loader import settings

def main() -> None:
    app = QApplication(sys.argv)
    # window = CreatorController()
    # window.show()
    # Создаем и отображаем главное окно
    if settings.value("token"):
        window = Main()
    else:
        window = Auth()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()