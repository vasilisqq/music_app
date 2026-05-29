#!/usr/bin/env python3
"""
Сборщик GUI-клиента в единый исполняемый файл через PyInstaller.

Запуск:
    .venv/bin/python build.py

Результат:
    dist/music_app     — готовый бинарник
    (если --onedir, то папка dist/music_app/ со всеми зависимостями)
"""

import os
import sys

# Путь к корню проекта
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Настройки сборки
ENTRY_POINT = os.path.join(PROJECT_ROOT, "launcher.py")
APP_NAME = "music_app"
# --onefile = один файл; --onedir = папка (быстрее запускается, меньше антивирусных проблем)
MODE = ["--onefile"]  # поменяй на ["--onedir"] если будут проблемы с запуском

# Дополнительные пути для анализа импортов (чтобы PyInstaller нашёл app/ и schemas)
paths = [PROJECT_ROOT, os.path.join(PROJECT_ROOT, "app")]

# Данные, которые нужно упаковать внутрь бандла
# формат: "src:dst" — src относительно PROJECT_ROOT, dst — путь внутри бандла
add_data = [
    f"app/photos{os.pathsep}app/photos",
    f"schemas{os.pathsep}schemas",
    f"single-piano-note-c4_100bpm_C_major.wav{os.pathsep}.",
    f"piano_cache.pkl{os.pathsep}.",
    # .env не бандлим — пользователь должен положить его рядом с exe
]

# Скрытые импорты, которые PyInstaller может пропустить (динамические импорты через sys.path)
hidden_imports = [
    "schemas",
    "schemas.auth",
    "schemas.lesson",
    "schemas.topic",
    "schemas.admin_stats",
    "schemas.profile_stats",
    "schemas.role",
    "pydantic_settings",
    "pydantic.deprecated.decorator",
    # Mido загружает backend динамически — PyInstaller пропускает
    "mido.backends.rtmidi",
    "mido.backends.pygame",
    "rtmidi",
]

# Собираем аргументы для PyInstaller
cmd = [
    ENTRY_POINT,
    "--name", APP_NAME,
    "--noconfirm",
    "--clean",
    "--windowed",  # без консоли (Linux/macOS игнорирует, на Windows точно убирает окно cmd)
    *MODE,
]

for p in paths:
    cmd.extend(["--paths", p])

for item in add_data:
    cmd.extend(["--add-data", item])

for imp in hidden_imports:
    cmd.extend(["--hidden-import", imp])

# Для PyQt6: явно подключаем platform plugins и стили (иногда PyInstaller их теряет)
cmd.extend([
    "--collect-submodules", "PyQt6.QtCore",
    "--collect-submodules", "PyQt6.QtGui",
    "--collect-submodules", "PyQt6.QtWidgets",
    "--collect-submodules", "PyQt6.QtNetwork",
    "--collect-submodules", "PyQt6.QtSvg",
    "--collect-submodules", "PyQt6.QtSvgWidgets",
])

if __name__ == "__main__":
    print("Сборка с аргументами:")
    for a in cmd:
        print("  ", a)

    # Запускаем PyInstaller
    import PyInstaller.__main__

    PyInstaller.__main__.run(cmd)

    print(f"\n✅ Сборка завершена! Результат в dist/{APP_NAME}")
    print("   Не забудь положить .env рядом с исполняемым файлом:")
    print(f"   API_BASE_URL=http://your-server.com:8000")
