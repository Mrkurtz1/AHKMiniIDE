"""Windows API helpers for the Inspector (Window Spy mimic).

Uses ctypes to call Win32 APIs.  On non-Windows platforms every function
returns safe default values so the rest of the UI can still be loaded.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

_IS_WINDOWS = sys.platform == "win32"

if _IS_WINDOWS:
    import ctypes
    import ctypes.wintypes as wintypes
    from ctypes import POINTER, byref, create_unicode_buffer

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    gdi32 = ctypes.windll.gdi32

    # ---- structures ------------------------------------------------
    class POINT(ctypes.Structure):
        _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", wintypes.LONG), ("top", wintypes.LONG),
            ("right", wintypes.LONG), ("bottom", wintypes.LONG),
        ]

    # ---- user32 prototypes -----------------------------------------
    user32.GetCursorPos.argtypes = [POINTER(POINT)]
    user32.GetCursorPos.restype = wintypes.BOOL

    user32.WindowFromPoint.argtypes = [POINT]
    user32.WindowFromPoint.restype = wintypes.HWND

    user32.GetWindowTextW.argtypes = [wintypes.HWND, ctypes.c_wchar_p, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int

    user32.GetClassNameW.argtypes = [wintypes.HWND, ctypes.c_wchar_p, ctypes.c_int]
    user32.GetClassNameW.restype = ctypes.c_int

    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD

    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND

    user32.ScreenToClient.argtypes = [wintypes.HWND, POINTER(POINT)]
    user32.ScreenToClient.restype = wintypes.BOOL

    user32.GetWindowRect.argtypes = [wintypes.HWND, POINTER(RECT)]
    user32.GetWindowRect.restype = wintypes.BOOL

    user32.GetClientRect.argtypes = [wintypes.HWND, POINTER(RECT)]
    user32.GetClientRect.restype = wintypes.BOOL

    user32.ClientToScreen.argtypes = [wintypes.HWND, POINTER(POINT)]
    user32.ClientToScreen.restype = wintypes.BOOL

    user32.RealChildWindowFromPoint.argtypes = [wintypes.HWND, POINT]
    user32.RealChildWindowFromPoint.restype = wintypes.HWND

    user32.GetForegroundWindow.argtypes = []
    user32.GetForegroundWindow.restype = wintypes.HWND

    user32.GetDC.argtypes = [wintypes.HWND]
    user32.GetDC.restype = wintypes.HDC

    user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    user32.ReleaseDC.restype = ctypes.c_int

    gdi32.GetPixel.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
    gdi32.GetPixel.restype = wintypes.COLORREF

    # ---- kernel32 prototypes ---------------------------------------
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE

    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, ctypes.c_wchar_p, POINTER(wintypes.DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL

    GA_ROOT = 2

    # ---- keyboard state (for freeze check) -------------------------
    user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
    user32.GetAsyncKeyState.restype = ctypes.c_short

    VK_CONTROL = 0x11
    VK_SHIFT = 0x10


# ====================================================================
#  Data structures
# ====================================================================

@dataclass
class WindowInfo:
    title: str = ""
    class_name: str = ""
    hwnd: int = 0
    pid: int = 0
    process_name: str = ""
    exe_path: str = ""


@dataclass
class MouseCoords:
    screen_x: int = 0
    screen_y: int = 0
    window_x: int = 0
    window_y: int = 0
    client_x: int = 0
    client_y: int = 0


@dataclass
class ControlInfo:
    class_nn: str = ""
    hwnd: int = 0


@dataclass
class PixelColor:
    r: int = 0
    g: int = 0
    b: int = 0

    @property
    def hex_rgb(self) -> str:
        return f"0x{self.r:02X}{self.g:02X}{self.b:02X}"

    @property
    def decimal_str(self) -> str:
        return f"{self.r}, {self.g}, {self.b}"


@dataclass
class InspectorSnapshot:
    window: WindowInfo = field(default_factory=WindowInfo)
    coords: MouseCoords = field(default_factory=MouseCoords)
    control: ControlInfo = field(default_factory=ControlInfo)
    color: PixelColor = field(default_factory=PixelColor)


# ====================================================================
#  API wrappers (Windows)
# ====================================================================

if _IS_WINDOWS:

    def _get_cursor_pos() -> tuple[int, int]:
        pt = POINT()
        user32.GetCursorPos(byref(pt))
        return pt.x, pt.y

    def _window_from_point(x: int, y: int) -> int:
        pt = POINT(x, y)
        hwnd = user32.WindowFromPoint(pt)
        return hwnd or 0

    def _get_root_window(hwnd: int) -> int:
        return user32.GetAncestor(hwnd, GA_ROOT) or hwnd

    def _get_window_text(hwnd: int) -> str:
        buf = create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, buf, 512)
        return buf.value

    def _get_class_name(hwnd: int) -> str:
        buf = create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, buf, 256)
        return buf.value

    def _get_pid(hwnd: int) -> int:
        pid = wintypes.DWORD(0)
        user32.GetWindowThreadProcessId(hwnd, byref(pid))
        return pid.value

    def _get_exe_path(pid: int) -> str:
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return ""
        try:
            buf = create_unicode_buffer(1024)
            size = wintypes.DWORD(1024)
            if kernel32.QueryFullProcessImageNameW(handle, 0, buf, byref(size)):
                return buf.value
            return ""
        finally:
            kernel32.CloseHandle(handle)

    def _get_process_name(exe_path: str) -> str:
        if not exe_path:
            return ""
        import ntpath
        return ntpath.basename(exe_path)

    def _screen_to_window(hwnd: int, sx: int, sy: int) -> tuple[int, int]:
        rect = RECT()
        user32.GetWindowRect(hwnd, byref(rect))
        return sx - rect.left, sy - rect.top

    def _screen_to_client(hwnd: int, sx: int, sy: int) -> tuple[int, int]:
        pt = POINT(sx, sy)
        user32.ScreenToClient(hwnd, byref(pt))
        return pt.x, pt.y

    def _get_control_at(hwnd: int, sx: int, sy: int) -> ControlInfo:
        pt = POINT(sx, sy)
        user32.ScreenToClient(hwnd, byref(pt))
        child = user32.RealChildWindowFromPoint(hwnd, POINT(pt.x, pt.y))
        if child and child != hwnd:
            cn = _get_class_name(child)
            return ControlInfo(class_nn=cn, hwnd=child)
        return ControlInfo()

    def _get_pixel_color(sx: int, sy: int) -> PixelColor:
        hdc = user32.GetDC(0)  # screen DC
        if not hdc:
            return PixelColor()
        try:
            colorref = gdi32.GetPixel(hdc, sx, sy)
            if colorref == 0xFFFFFFFF:
                return PixelColor()
            r = colorref & 0xFF
            g = (colorref >> 8) & 0xFF
            b = (colorref >> 16) & 0xFF
            return PixelColor(r, g, b)
        finally:
            user32.ReleaseDC(0, hdc)

    def is_modifier_held() -> bool:
        """Return True if Ctrl or Shift is currently pressed."""
        ctrl = user32.GetAsyncKeyState(VK_CONTROL) & 0x8000
        shift = user32.GetAsyncKeyState(VK_SHIFT) & 0x8000
        return bool(ctrl or shift)

    def get_foreground_window() -> int:
        return user32.GetForegroundWindow() or 0

    def capture_snapshot(follow_mouse: bool = True,
                         last_hwnd: int = 0) -> InspectorSnapshot:
        """Capture a complete inspector snapshot."""
        sx, sy = _get_cursor_pos()

        if follow_mouse:
            raw_hwnd = _window_from_point(sx, sy)
            root_hwnd = _get_root_window(raw_hwnd)
        else:
            root_hwnd = last_hwnd if last_hwnd else get_foreground_window()

        pid = _get_pid(root_hwnd)
        exe = _get_exe_path(pid)

        win = WindowInfo(
            title=_get_window_text(root_hwnd),
            class_name=_get_class_name(root_hwnd),
            hwnd=root_hwnd,
            pid=pid,
            exe_path=exe,
            process_name=_get_process_name(exe),
        )

        wx, wy = _screen_to_window(root_hwnd, sx, sy)
        cx, cy = _screen_to_client(root_hwnd, sx, sy)
        coords = MouseCoords(
            screen_x=sx, screen_y=sy,
            window_x=wx, window_y=wy,
            client_x=cx, client_y=cy,
        )

        control = _get_control_at(root_hwnd, sx, sy)
        color = _get_pixel_color(sx, sy)

        return InspectorSnapshot(window=win, coords=coords,
                                 control=control, color=color)

else:
    # ----------------------------------------------------------------
    #  Non-Windows stubs — allow the UI to load for development
    # ----------------------------------------------------------------
    def is_modifier_held() -> bool:      # noqa: D401
        return False

    def get_foreground_window() -> int:
        return 0

    def capture_snapshot(follow_mouse: bool = True,
                         last_hwnd: int = 0) -> InspectorSnapshot:
        return InspectorSnapshot()
