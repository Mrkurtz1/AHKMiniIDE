"""AHK v2 code generation for global-hotkey actions."""

from __future__ import annotations


def gen_win_activate(hwnd: int,
                     title: str = "",
                     class_name: str = "",
                     process: str = "") -> str:
    """Generate a WinActivate line targeting *hwnd* with a comment."""
    parts = []
    if title:
        parts.append(f"Title: {title}")
    if class_name:
        parts.append(f"Class: {class_name}")
    if process:
        parts.append(f"Process: {process}")
    comment = f"  ; {', '.join(parts)}" if parts else ""
    return f'WinActivate "ahk_id {hex(hwnd)}"{comment}'


# ------------------------------------------------------------------
# Click
# ------------------------------------------------------------------

def gen_click(x: int, y: int, *,
              button: str = "Left",
              count: int = 1,
              coord_mode: str = "Window") -> str:
    """Generate a Click statement.

    AHK v2 Click syntax:
        Click x, y                          ; single left
        Click x, y, "Right"                 ; right click
        Click x, y,, 2                      ; double left
        Click x, y, "Right", 2              ; double right
    """
    header = f'CoordMode "Mouse", "{coord_mode}"\n'
    if button == "Left" and count == 1:
        return f"{header}Click {x}, {y}"
    if button == "Left" and count > 1:
        return f"{header}Click {x}, {y},, {count}"
    if count == 1:
        return f'{header}Click {x}, {y}, "{button}"'
    return f'{header}Click {x}, {y}, "{button}", {count}'


# ------------------------------------------------------------------
# Drag
# ------------------------------------------------------------------

def gen_drag(x1: int, y1: int, x2: int, y2: int, *,
             button: str = "Left",
             coord_mode: str = "Window") -> str:
    """Generate a MouseClickDrag statement."""
    header = f'CoordMode "Mouse", "{coord_mode}"\n'
    return f'{header}MouseClickDrag "{button}", {x1}, {y1}, {x2}, {y2}'


# ------------------------------------------------------------------
# Pixel loop
# ------------------------------------------------------------------

def gen_pixel_loop(x: int, y: int,
                   target_color: str, *,
                   coord_mode: str = "Window",
                   variation: int = 5,
                   use_pixel_search: bool = False) -> str:
    """Generate a polling loop that waits for a color match.

    *target_color* should be a hex string like ``"0xFF8800"``.
    """
    header = f'CoordMode "Pixel", "{coord_mode}"\n'

    if use_pixel_search:
        return (
            f"{header}"
            f"Loop {{\n"
            f'    if PixelSearch(&FoundX, &FoundY, {x}, {y}, {x}, {y}, "{target_color}", {variation})\n'
            f"        break\n"
            f"    Sleep 100\n"
            f"}}"
        )

    return (
        f"{header}"
        f"Loop {{\n"
        f"    CurrentColor := PixelGetColor({x}, {y})\n"
        f'    if (CurrentColor = "{target_color}")\n'
        f"        break\n"
        f"    Sleep 100\n"
        f"}}"
    )
