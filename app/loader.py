import os
import sys

from PyQt6.QtCore import QSettings

settings = QSettings("MyCompany", "music_app")


def resource_path(relative_path: str) -> str:
    """
    Возвращает абсолютный путь к ресурсу.
    Работает как при обычном запуске, так и внутри сборки PyInstaller.
    """
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller распаковывает ресурсы во временную папку _MEIPASS
        base_path = sys._MEIPASS
    else:
        # В режиме разработки путь отсчитывается от корня проекта
        # (loader.py лежит в app/, поднимаемся на уровень выше)
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)
