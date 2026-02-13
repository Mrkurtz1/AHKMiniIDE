"""Global hotkey registration and dispatch.

On Windows, uses RegisterHotKey / WM_HOTKEY via a Qt native event filter.
On other platforms, hotkeys are unavailable (stubs).
"""

from __future__ import annotations

import sys
from enum import IntEnum, auto

from PyQt6.QtCore import QAbstractNativeEventFilter, QObject, pyqtSignal

_IS_WINDOWS = sys.platform == "win32"

if _IS_WINDOWS:
    import ctypes
    import ctypes.wintypes as wintypes

    user32 = ctypes.windll.user32

    MOD_CONTROL = 0x0002
    MOD_SHIFT = 0x0004
    MOD_NOREPEAT = 0x4000
    WM_HOTKEY = 0x0312


class HotkeyID(IntEnum):
    """Fixed IDs for each registered global hotkey."""
    CLICK = 1
    DRAG = 2
    PIXEL_LOOP = 3
    WIN_ACTIVATE = 4


class HotkeyManager(QObject):
    """Register/unregister global hotkeys and emit signals on activation."""

    hotkey_triggered = pyqtSignal(int)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._registered: dict[int, int] = {}  # id -> vk
        self._filter: _NativeFilter | None = None

    # ----------------------------------------------------------------
    def register_all(self, bindings: dict[HotkeyID, str]) -> list[str]:
        """Register hotkeys.  *bindings* maps HotkeyID → letter (e.g. 'K').

        Returns a list of error messages (empty on full success).
        """
        if not _IS_WINDOWS:
            return ["Global hotkeys require Windows"]

        errors: list[str] = []
        for hid, letter in bindings.items():
            vk = ord(letter.upper())
            mods = MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT
            ok = user32.RegisterHotKey(0, int(hid), mods, vk)
            if ok:
                self._registered[int(hid)] = vk
            else:
                errors.append(f"Failed to register Ctrl+Shift+{letter} (id={hid.name})")

        # Install native event filter
        if self._filter is None:
            self._filter = _NativeFilter(self)
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                app.installNativeEventFilter(self._filter)

        return errors

    def unregister_all(self) -> None:
        if not _IS_WINDOWS:
            return
        for hid in list(self._registered):
            user32.UnregisterHotKey(0, hid)
        self._registered.clear()

        if self._filter is not None:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                app.removeNativeEventFilter(self._filter)
            self._filter = None

    def _dispatch(self, hotkey_id: int) -> None:
        try:
            hid = HotkeyID(hotkey_id)
        except ValueError:
            return
        self.hotkey_triggered.emit(hid)


# ====================================================================
if _IS_WINDOWS:

    class _NativeFilter(QAbstractNativeEventFilter):
        """Intercepts WM_HOTKEY messages from the Windows message queue."""

        def __init__(self, manager: HotkeyManager):
            super().__init__()
            self._manager = manager

        def nativeEventFilter(self, event_type: bytes, message):  # noqa: N802
            if event_type == b"windows_generic_MSG":
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == WM_HOTKEY:
                    self._manager._dispatch(msg.wParam)
                    return True, 0
            return False, 0

else:

    class _NativeFilter(QAbstractNativeEventFilter):
        """Stub for non-Windows platforms."""

        def __init__(self, manager: HotkeyManager):
            super().__init__()

        def nativeEventFilter(self, event_type: bytes, message):  # noqa: N802
            return False, 0
