"""Code editor widget with line numbers, find/replace, and AHK v2 highlighting."""

from __future__ import annotations

from PyQt6.QtCore import QRect, QSize, Qt
from PyQt6.QtGui import QAction, QColor, QFont, QPainter, QTextCursor, QTextDocument
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QCheckBox,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ahk_mini_ide.editor.syntax import AHKHighlighter


# ====================================================================
#  Line-number area (gutter)
# ====================================================================

class _LineNumberArea(QWidget):
    def __init__(self, editor: "CodeEditor"):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event):  # noqa: N802
        self._editor.paint_line_numbers(event)


# ====================================================================
#  Code editor
# ====================================================================

class CodeEditor(QPlainTextEdit):
    """QPlainTextEdit subclass with line numbers and AHK syntax highlighting."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self._line_area = _LineNumberArea(self)
        self.blockCountChanged.connect(self._update_line_area_width)
        self.updateRequest.connect(self._update_line_area)
        self._update_line_area_width()

        self._highlighter = AHKHighlighter(self.document())

        self._current_path: str | None = None

    # -- properties ---------------------------------------------------
    @property
    def file_path(self) -> str | None:
        return self._current_path

    @file_path.setter
    def file_path(self, path: str | None) -> None:
        self._current_path = path

    @property
    def is_modified(self) -> bool:
        return self.document().isModified()

    # -- public API ---------------------------------------------------
    def load_file(self, path: str) -> None:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            self.setPlainText(fh.read())
        self.document().setModified(False)
        self._current_path = path

    def save_file(self, path: str | None = None) -> str:
        path = path or self._current_path
        if not path:
            raise ValueError("No file path specified")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.toPlainText())
        self.document().setModified(False)
        self._current_path = path
        return path

    def insert_code(self, code: str) -> None:
        """Insert *code* at the current cursor position."""
        cursor = self.textCursor()
        # If cursor is mid-line, move to end of line first
        if not cursor.atBlockEnd():
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
        # Ensure we start on a fresh line
        if cursor.block().text().strip():
            cursor.insertText("\n")
        cursor.insertText(code)
        cursor.insertText("\n")
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    # -- line numbers -------------------------------------------------
    def line_number_area_width(self) -> int:
        digits = max(1, len(str(self.blockCount())))
        return 10 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_line_area_width(self, _=0) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self._line_area.scroll(0, dy)
        else:
            self._line_area.update(0, rect.y(), self._line_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_area_width()

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def paint_line_numbers(self, event) -> None:
        painter = QPainter(self._line_area)
        painter.fillRect(event.rect(), QColor("#2B2B2B"))
        painter.setPen(QColor("#606366"))

        block = self.firstVisibleBlock()
        block_num = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.drawText(
                    0, top, self._line_area.width() - 4,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight, str(block_num + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_num += 1

        painter.end()


# ====================================================================
#  Find / Replace dialog
# ====================================================================

class FindReplaceDialog(QDialog):
    """Simple modeless find/replace dialog."""

    def __init__(self, editor: CodeEditor, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Find / Replace")
        self._editor = editor

        layout = QVBoxLayout(self)

        # Find row
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Find:"))
        self._find_edit = QLineEdit()
        row1.addWidget(self._find_edit)
        btn_next = QPushButton("Next")
        btn_next.clicked.connect(self._find_next)
        row1.addWidget(btn_next)
        layout.addLayout(row1)

        # Replace row
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Replace:"))
        self._replace_edit = QLineEdit()
        row2.addWidget(self._replace_edit)
        btn_replace = QPushButton("Replace")
        btn_replace.clicked.connect(self._replace)
        row2.addWidget(btn_replace)
        btn_all = QPushButton("All")
        btn_all.clicked.connect(self._replace_all)
        row2.addWidget(btn_all)
        layout.addLayout(row2)

        # Options
        row3 = QHBoxLayout()
        self._case_cb = QCheckBox("Case sensitive")
        row3.addWidget(self._case_cb)
        layout.addLayout(row3)

    def _flags(self) -> QTextDocument.FindFlag:
        flags = QTextDocument.FindFlag(0)
        if self._case_cb.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        return flags

    def _find_next(self) -> bool:
        text = self._find_edit.text()
        if not text:
            return False
        found = self._editor.find(text, self._flags())
        if not found:
            # Wrap around
            cursor = self._editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self._editor.setTextCursor(cursor)
            found = self._editor.find(text, self._flags())
        return found

    def _replace(self) -> None:
        cursor = self._editor.textCursor()
        if cursor.hasSelection() and cursor.selectedText() == self._find_edit.text():
            cursor.insertText(self._replace_edit.text())
        self._find_next()

    def _replace_all(self) -> None:
        text = self._find_edit.text()
        replacement = self._replace_edit.text()
        if not text:
            return
        cursor = self._editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self._editor.setTextCursor(cursor)
        count = 0
        cursor.beginEditBlock()
        while self._editor.find(text, self._flags()):
            tc = self._editor.textCursor()
            tc.insertText(replacement)
            count += 1
        cursor.endEditBlock()
