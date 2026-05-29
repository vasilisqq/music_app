#!/usr/bin/env python3
"""
Launcher для PyInstaller и обычного запуска.
Добавляет папку app/ в sys.path, чтобы относительные импорты
(controllers, workers, GUI и т.д.) работали корректно.
"""

import os
import sys

if getattr(sys, "frozen", False):
    # PyInstaller onefile/onedir: бандл распакован в sys._MEIPASS
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

app_dir = os.path.join(base_dir, "app")
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

# Теперь main.py найдёт controllers, workers, GUI и т.д.
from main import main

if __name__ == "__main__":
    main()
