"""Persistent application settings backed by a JSON file."""

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_SETTINGS: dict[str, Any] = {
    # AutoHotkey executable
    "ahk_exe_path": "",
    "ahk_flags": "",
    "ahk_args": "",
    "working_dir_mode": "script",  # "script" | "project"

    # Inspector
    "inspector_cadence_ms": 500,
    "default_coord_mode": "Window",  # "Screen" | "Window" | "Client"

    # Color
    "color_slack": 5,

    # Hotkey letter bindings (combined with Ctrl+Shift)
    "hotkey_click": "K",
    "hotkey_drag": "D",
    "hotkey_pixel_loop": "L",
    "hotkey_win_activate": "A",

    # Project history
    "recent_projects": [],

    # Window layout (saved/restored by Qt)
    "window_state": None,
    "window_geometry": None,

    # Runner
    "graceful_kill_timeout_ms": 2000,
}

_AHK_DEFAULT_DIRS = [
    os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "AutoHotkey"),
    os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "AutoHotkey"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "AutoHotkey"),
]

_AHK_EXE_NAMES = ["v2/AutoHotkey64.exe", "v2/AutoHotkey32.exe", "AutoHotkey64.exe",
                   "AutoHotkey32.exe", "AutoHotkey.exe"]


def _auto_detect_ahk() -> str:
    """Try to find a v2 AutoHotkey executable in default locations."""
    for base in _AHK_DEFAULT_DIRS:
        for name in _AHK_EXE_NAMES:
            candidate = os.path.join(base, name)
            if os.path.isfile(candidate):
                return candidate
    return ""


class Settings:
    """Read/write application settings as JSON."""

    def __init__(self, path: str | Path | None = None):
        if path is None:
            appdata = os.environ.get("APPDATA", str(Path.home()))
            self._path = Path(appdata) / "AHKMiniIDE" / "settings.json"
        else:
            self._path = Path(path)

        self._data: dict[str, Any] = dict(DEFAULT_SETTINGS)
        self._load()

        # Auto-detect AHK if not set
        if not self._data.get("ahk_exe_path"):
            detected = _auto_detect_ahk()
            if detected:
                self._data["ahk_exe_path"] = detected
                self.save()

    # ------------------------------------------------------------------
    def _load(self) -> None:
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as fh:
                    stored = json.load(fh)
                self._data.update(stored)
            except (json.JSONDecodeError, OSError):
                pass

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2)

    # ------------------------------------------------------------------
    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    # ------------------------------------------------------------------
    def add_recent_project(self, project_path: str | Path) -> None:
        recents: list[str] = self._data.get("recent_projects", [])
        p = str(project_path)
        if p in recents:
            recents.remove(p)
        recents.insert(0, p)
        self._data["recent_projects"] = recents[:10]
        self.save()

    @property
    def recent_projects(self) -> list[str]:
        return list(self._data.get("recent_projects", []))
