from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget


class LessonListItemWidget(QWidget):
    def __init__(
        self,
        *,
        title: str,
        difficulty: int,
        icon: str,
        locked: bool,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        title_color = "rgba(26, 26, 26, 0.45)" if locked else "#1a1a1a"
        filled_star_color = "rgba(245, 179, 1, 0.45)" if locked else "#f5b301"
        empty_star_color = (
            "rgba(26, 26, 26, 0.18)" if locked else "rgba(26, 26, 26, 0.22)"
        )
        card_background = "rgba(243, 243, 243, 0.96)" if locked else "#f3f8ff"
        card_border = "rgba(0, 0, 0, 0.10)" if locked else "rgba(63, 139, 222, 0.35)"

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        self.card = QWidget(self)
        self.card.setObjectName("lessonCard")
        self.card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.card.setStyleSheet(
            f"QWidget#lessonCard {{ background: {card_background}; border: 2px solid {card_border}; border-radius: 14px; }}"
        )
        outer_layout.addWidget(self.card)

        self._icon_label = QLabel(icon)
        self._icon_label.setStyleSheet("font-size: 18px; background: transparent;")
        self._icon_label.setFixedSize(32, 32)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._title_label = QLabel(title)
        self._title_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        self._title_label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )
        self._title_label.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {title_color}; background: transparent;"
        )
        self._title_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        stars = max(0, min(int(difficulty or 0), 5))
        self._difficulty_label = QLabel(
            f'<span style="color: {filled_star_color};">{"★" * stars}</span>'
            f'<span style="color: {empty_star_color};">{"★" * (5 - stars)}</span>'
        )
        self._difficulty_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        self._difficulty_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._difficulty_label.setStyleSheet(
            "font-size: 18px; font-weight: 700; background: transparent;"
        )
        self._difficulty_label.setMinimumWidth(104)

        layout = QHBoxLayout(self.card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)
        layout.addWidget(self._icon_label, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._title_label, 1, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(
            self._difficulty_label,
            0,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
        )

        self.setMinimumHeight(72)

        if locked:
            self.setEnabled(False)


def truncate(text: str, max_len: int) -> str:
    s = (text or "").strip()
    if len(s) <= max_len:
        return s
    return s[: max(0, max_len - 1)].rstrip() + "…"
