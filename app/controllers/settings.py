from __future__ import annotations

import re

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QMessageBox
import mido
from loader import settings


_DEVICE_ID_SUFFIX = re.compile(r"\s+\d+:\d+$")
_DEVICE_PORT_SUFFIX = re.compile(r"\s+port\s+\d+$", re.IGNORECASE)
_DEVICE_EXTRA_SPACES = re.compile(r"\s+")


def _is_virtual_midi_input(name: str) -> bool:
    normalized = _normalize_midi_device_name(name).casefold()
    return normalized.startswith("midi through")


def _normalize_midi_device_name(name: str) -> str:
    normalized = (name or "").strip()
    normalized = _DEVICE_ID_SUFFIX.sub("", normalized)
    normalized = _DEVICE_PORT_SUFFIX.sub("", normalized)
    normalized = _DEVICE_EXTRA_SPACES.sub(" ", normalized)
    return normalized


def _device_sort_key(name: str) -> tuple[int, str]:
    normalized = _normalize_midi_device_name(name)
    return (0 if "bluetooth" in normalized.lower() else 1, normalized.lower())


def _display_midi_device_name(name: str) -> str:
    return _normalize_midi_device_name(name)


def _dedupe_midi_inputs(input_names: list[str]) -> list[str]:
    unique_inputs: dict[str, str] = {}
    for name in sorted(input_names, key=_device_sort_key):
        if _is_virtual_midi_input(name):
            continue
        key = _normalize_midi_device_name(name).casefold()
        unique_inputs.setdefault(key, name)
    return list(unique_inputs.values())


def _count_hidden_duplicates(input_names: list[str]) -> int:
    return max(0, len(input_names) - len(_dedupe_midi_inputs(input_names)))


class SettingsController(QObject):
    MIDI_INPUT_KEY = "midi/input_device_name"
    _BT_PATTERN = re.compile(r"bluetooth|ble|\bbt\b|wireless|air", re.IGNORECASE)


class SettingsController(QObject):
    MIDI_INPUT_KEY = "midi/input_device_name"
    _BT_PATTERN = re.compile(r"bluetooth|ble|\bbt\b|wireless|air", re.IGNORECASE)

    def __init__(self, ui):
        super().__init__()
        self.ui = ui
        self.ui.refreshMidiDevicesBtn.clicked.connect(self.refresh_midi_inputs)
        self.ui.verifyMidiDeviceBtn.clicked.connect(self.verify_selected_midi_input)
        self.ui.midiInputCombo.currentIndexChanged.connect(self._on_midi_input_changed)
        self.refresh_midi_inputs()

    def refresh_midi_inputs(self):
        saved_name = settings.value(self.MIDI_INPUT_KEY, None)
        current_name = self.ui.midiInputCombo.currentData()

        raw_input_names = list(mido.get_input_names())
        input_names = _dedupe_midi_inputs(raw_input_names)
        available_names = set(input_names)
        if saved_name and saved_name not in available_names:
            settings.remove(self.MIDI_INPUT_KEY)
            saved_name = None
        if current_name and current_name not in available_names:
            current_name = None

        self.ui.midiInputCombo.blockSignals(True)
        self.ui.midiInputCombo.clear()
        self.ui.midiInputCombo.addItem("Не выбрано", None)

        for name in input_names:
            prefix = "[Bluetooth]" if self._is_bluetooth_device(name) else "[Кабель]"
            display_name = _display_midi_device_name(name)
            self.ui.midiInputCombo.addItem(f"{prefix} {display_name}", name)

        hidden_duplicates = _count_hidden_duplicates(raw_input_names)
        self.ui.midiSettingsHint.setText(
            "Используется один общий список подключённых MIDI-входов. "
            "Если устройство подключено позже, обнови список."
            + (f" Скрыто дополнительных портов: {hidden_duplicates}." if hidden_duplicates else "")
        )

        selected_name = current_name or saved_name
        selected_index = self.ui.midiInputCombo.findData(selected_name)
        if selected_index < 0:
            selected_index = 0
        self.ui.midiInputCombo.setCurrentIndex(selected_index)
        self.ui.midiInputCombo.blockSignals(False)

        current_device = self.ui.midiInputCombo.currentData()
        if current_device:
            settings.setValue(self.MIDI_INPUT_KEY, current_device)
        else:
            settings.remove(self.MIDI_INPUT_KEY)

        self._update_status_label()

    def get_selected_midi_input_name(self) -> str | None:
        return self.ui.midiInputCombo.currentData()

    def _on_midi_input_changed(self, _index: int):
        device_name = self.get_selected_midi_input_name()
        if device_name:
            settings.setValue(self.MIDI_INPUT_KEY, device_name)
        else:
            settings.remove(self.MIDI_INPUT_KEY)
        self._update_status_label()

    def verify_selected_midi_input(self):
        device_name = self.get_selected_midi_input_name()
        if not device_name:
            QMessageBox.information(self.ui.centralwidget, "Проверка MIDI", "Сначала выбери подключённое MIDI-устройство.")
            return
        try:
            with mido.open_input(device_name):
                pass
        except OSError as exc:
            QMessageBox.warning(
                self.ui.centralwidget,
                "Проверка MIDI",
                f"Не удалось открыть устройство:\n{device_name}\n\n{exc}"
            )
            return
        except Exception as exc:
            import logging
            logging.error(f"Неожиданная ошибка при проверке MIDI: {exc}")
            QMessageBox.warning(
                self.ui.centralwidget,
                "Ошибка",
                f"Неожиданная ошибка: {exc}"
            )
            return

        QMessageBox.information(
            self.ui.centralwidget,
            "Проверка MIDI",
            f"Устройство доступно и успешно открылось:\n{device_name}",
        )

    def _update_status_label(self):
        device_name = self.get_selected_midi_input_name()
        if device_name:
            self.ui.midiSettingsStatusLabel.setText(f"Выбрано подключённое устройство: {device_name}")
        else:
            self.ui.midiSettingsStatusLabel.setText("Подключённое MIDI-устройство не выбрано")

    def _is_bluetooth_device(self, name: str) -> bool:
        return bool(self._BT_PATTERN.search(name or ""))
