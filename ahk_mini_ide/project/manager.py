"""Project management — create, open, remember, active target."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal

from ahk_mini_ide.settings import Settings

_PROJECT_META = ".ahkminiide.json"


class Project:
    """Represents an AHK project rooted at a directory."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self._meta_path = self.root / _PROJECT_META
        self._meta: dict[str, Any] = {}
        self._load_meta()

    def _load_meta(self) -> None:
        if self._meta_path.exists():
            try:
                with open(self._meta_path, "r", encoding="utf-8") as fh:
                    self._meta = json.load(fh)
            except (json.JSONDecodeError, OSError):
                self._meta = {}

    def _save_meta(self) -> None:
        with open(self._meta_path, "w", encoding="utf-8") as fh:
            json.dump(self._meta, fh, indent=2)

    @property
    def name(self) -> str:
        return self.root.name

    @property
    def active_target(self) -> str | None:
        """Relative path of the script marked as active run target."""
        return self._meta.get("active_target")

    @active_target.setter
    def active_target(self, rel_path: str | None) -> None:
        if rel_path is None:
            self._meta.pop("active_target", None)
        else:
            self._meta["active_target"] = rel_path
        self._save_meta()

    @property
    def active_target_abs(self) -> str | None:
        rel = self.active_target
        if rel is None:
            return None
        return str(self.root / rel)


class ProjectManager(QObject):
    """Manages the currently open project."""

    project_opened = pyqtSignal(object)   # Project
    project_closed = pyqtSignal()
    active_target_changed = pyqtSignal(str)  # absolute path

    def __init__(self, settings: Settings, parent: QObject | None = None):
        super().__init__(parent)
        self._settings = settings
        self._project: Project | None = None

    @property
    def project(self) -> Project | None:
        return self._project

    def create_project(self, folder: str | Path) -> Project:
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        proj = Project(folder)
        self._open(proj)
        return proj

    def open_project(self, folder: str | Path) -> Project:
        proj = Project(folder)
        self._open(proj)
        return proj

    def _open(self, proj: Project) -> None:
        self._project = proj
        self._settings.add_recent_project(proj.root)
        self.project_opened.emit(proj)

    def close_project(self) -> None:
        self._project = None
        self.project_closed.emit()

    def set_active_target(self, abs_path: str) -> None:
        if self._project is None:
            return
        try:
            rel = str(Path(abs_path).relative_to(self._project.root))
        except ValueError:
            rel = abs_path
        self._project.active_target = rel
        self.active_target_changed.emit(abs_path)
