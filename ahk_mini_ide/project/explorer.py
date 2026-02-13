"""Project Explorer — tree view of project files."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileSystemModel,
    QMenu,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from ahk_mini_ide.project.manager import Project


class ProjectExplorer(QWidget):
    """Tree view of the current project directory."""

    file_activated = pyqtSignal(str)        # absolute path of double-clicked file
    set_active_target = pyqtSignal(str)     # user chose "Set as Active Target"

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._model = QFileSystemModel()
        self._model.setNameFilters(["*.ahk", "*.ah2", "*.txt", "*.ini", "*.json"])
        self._model.setNameFilterDisables(False)

        self._tree = QTreeView()
        self._tree.setModel(self._model)
        self._tree.setHeaderHidden(True)
        # Hide size, type, date columns
        for col in (1, 2, 3):
            self._tree.hideColumn(col)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._context_menu)
        self._tree.doubleClicked.connect(self._on_double_click)

        layout.addWidget(self._tree)

    def set_project(self, project: Project) -> None:
        root = str(project.root)
        self._model.setRootPath(root)
        self._tree.setRootIndex(self._model.index(root))

    def clear(self) -> None:
        self._model.setRootPath("")

    def _on_double_click(self, index) -> None:
        path = self._model.filePath(index)
        if path and not self._model.isDir(index):
            self.file_activated.emit(path)

    def _context_menu(self, pos) -> None:
        index = self._tree.indexAt(pos)
        if not index.isValid():
            return
        path = self._model.filePath(index)
        if not path or self._model.isDir(index):
            return

        menu = QMenu(self)
        act_open = menu.addAction("Open")
        act_target = menu.addAction("Set as Active Target")

        chosen = menu.exec(self._tree.viewport().mapToGlobal(pos))
        if chosen == act_open:
            self.file_activated.emit(path)
        elif chosen == act_target:
            self.set_active_target.emit(path)
