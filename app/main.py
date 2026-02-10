import sys
from PyQt6.QtWidgets import QApplication
from controllers.auth import Auth


def main() -> None:
    app = QApplication(sys.argv)
    
    # Создаем и отображаем главное окно
    auth = Auth()
    auth.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()