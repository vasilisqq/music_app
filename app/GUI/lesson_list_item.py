from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QSizePolicy
from PyQt6.QtCore import Qt


class LessonListItemWidget(QWidget):
    def __init__(self, *, title: str, description: str, icon: str, locked: bool, parent: QWidget | None = None):
        super().__init__(parent)

        self._title_label = QLabel(title)
        self._title_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self._title_label.setStyleSheet("font-size: 16px; font-weight: 700; color: #1a1a1a;")
        self._title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self._icon_label = QLabel(icon)
        self._icon_label.setStyleSheet("font-size: 16px;")
        self._icon_label.setFixedWidth(26)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self._desc_label = QLabel(description)
        self._desc_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self._desc_label.setWordWrap(True)
        self._desc_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._desc_label.setStyleSheet("font-size: 12px; color: rgba(26, 26, 26, 0.65);")
        self._desc_label.setMaximumHeight(36)  # ~2 lines

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)
        top_row.addWidget(self._icon_label)
        top_row.addWidget(self._title_label, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)
        layout.addLayout(top_row)
        layout.addWidget(self._desc_label)

        self.setMinimumHeight(72)

        if locked:
            self.setStyleSheet("background: transparent;")
            self._title_label.setStyleSheet("font-size: 16px; font-weight: 700; color: rgba(26, 26, 26, 0.45);")
            self._desc_label.setStyleSheet("font-size: 12px; color: rgba(26, 26, 26, 0.35);")


def truncate(text: str, max_len: int) -> str:
    s = (text or "").strip()
    if len(s) <= max_len:
        return s
    return s[: max(0, max_len - 1)].rstrip() + "…"
