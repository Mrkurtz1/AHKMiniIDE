"""Output pane for AHK script stdout/stderr and status messages."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import QPlainTextEdit, QWidget


class OutputPane(QPlainTextEdit):
    """Read-only console that shows run output and status messages."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setReadOnly(True)
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self._fmt_normal = QTextCharFormat()
        self._fmt_normal.setForeground(QColor("#A9B7C6"))

        self._fmt_error = QTextCharFormat()
        self._fmt_error.setForeground(QColor("#FF6B68"))

        self._fmt_info = QTextCharFormat()
        self._fmt_info.setForeground(QColor("#6A8759"))

    # ----------------------------------------------------------------
    def append_text(self, text: str, *, error: bool = False) -> None:
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text, self._fmt_error if error else self._fmt_normal)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def append_info(self, text: str) -> None:
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text, self._fmt_info)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def clear_output(self) -> None:
        self.clear()
