import sys
from PyQt6.QtWidgets import QApplication
from ui.staff_buttons import MainWindow



def main() -> None:
    app = QApplication(sys.argv)
    
    # Создаем и отображаем главное окно
    main_window = MainWindow()
    main_window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()