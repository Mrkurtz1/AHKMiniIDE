# AHK Mini IDE

A Windows 11 desktop application (Python / PyQt6) that provides a real-time **Inspector** (Window Spy mimic for AutoHotkey v2), a project-based **Script Editor/Runner**, and **Global Hotkey code generation** for common automation actions.

Built for [AutoHotkey v2](https://www.autohotkey.com/) — Windows automation software.

---

## Table of Contents

- [Features](#features)
- [Screenshots](#screenshots)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Application Layout](#application-layout)
- [Inspector (Window Spy Mimic)](#inspector-window-spy-mimic)
- [Editor / Runner](#editor--runner)
- [Project System](#project-system)
- [Global Hotkeys & Code Generation](#global-hotkeys--code-generation)
- [Settings](#settings)
- [Architecture](#architecture)
- [Known Limitations](#known-limitations)
- [License](#license)

---

## Features

| Area | Capability |
|------|-----------|
| **Inspector** | Real-time window title, class, process, HWND, PID, exe path |
| | Mouse coordinates in Screen, Window, and Client modes |
| | Pixel color under cursor (RGB decimal + hex) with color swatch |
| | Control under mouse (ClassNN + HWND) |
| | Follow Mouse toggle, Freeze on Ctrl/Shift |
| | Configurable refresh cadence (50–2000 ms) |
| **Editor** | AHK v2 syntax highlighting (keywords, built-ins, directives, strings, comments) |
| | Line numbers, undo/redo, find & replace |
| | Monospace font, no-wrap, 4-space tabs |
| **Runner** | Run saved file or unsaved buffer (temp file) |
| | Graceful shutdown with configurable timeout, then hard-kill |
| | Live stdout/stderr capture in color-coded output pane |
| | Visual status indicator (Idle / Running / Error) |
| **Projects** | Create / open / recent project history |
| | File tree explorer with double-click open and context menu |
| | Mark any `.ahk` file as the Active Run Target |
| **Hotkeys** | System-wide hotkeys work even when another app is focused |
| | Generate `WinActivate`, `Click`, `MouseClickDrag`, `PixelGetColor`/`PixelSearch` loops |
| | Pending insertion queue — code captured globally, inserted when editor regains focus |
| **Settings** | AHK exe path auto-detection, flags, args, working directory mode |
| | Coordinate mode, color variation, hotkey letter bindings |
| | Window layout persistence between sessions |

---

## Screenshots

*(Application runs on Windows 11. The main window contains dockable panels for the Project Explorer, Editor, Inspector, and Output pane.)*

---

## Requirements

- **OS:** Windows 11
- **Python:** 3.10 or later
- **AutoHotkey:** v2 (installed separately — [download here](https://www.autohotkey.com/))
- **Python package:** PyQt6 >= 6.5.0

---

## Installation

```bash
# Clone the repository
git clone https://github.com/Mrkurtz1/AHKMiniIDE.git
cd AHKMiniIDE

# Create a virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Quick Start

```bash
# Run the application
python run.py

# Or as a module
python -m ahk_mini_ide
```

On first launch the app attempts to auto-detect AutoHotkey v2 in standard install locations:

- `C:\Program Files\AutoHotkey\v2\AutoHotkey64.exe`
- `C:\Program Files\AutoHotkey\v2\AutoHotkey32.exe`
- `C:\Program Files (x86)\AutoHotkey\...`
- `%LOCALAPPDATA%\Programs\AutoHotkey\...`

If not found, configure the path manually via **Edit > Settings**.

---

## Application Layout

The window uses Qt dock widgets. The default arrangement is:

```
+-------------------+---------------------+-------------------+
|                   |                     |                   |
|  Project Explorer |      Editor         |    Inspector      |
|  (left dock)      |   (central area)    |   (right dock)    |
|                   |                     |                   |
|                   +---------------------+                   |
|                   | [Run] [Stop] ● Idle |                   |
|                   +---------------------+                   |
|                   |    Output Pane      |                   |
|                   |   (stdout/stderr)   |                   |
+-------------------+---------------------+-------------------+
```

All dock panels can be **detached** (floating), **moved** to different dock areas, or **hidden** via the View menu. Layout is saved and restored between sessions.

---

## Inspector (Window Spy Mimic)

The Inspector panel mirrors key functionality of AutoHotkey's Window Spy:

### Window Identity Panel

| Field | Description |
|-------|-------------|
| **Title** | Window title text |
| **Class** | Window class name |
| **Process** | Process name (e.g. `notepad.exe`) |
| **HWND** | Window handle in hex (e.g. `0x001A0B3C`) |
| **PID** | Process ID |
| **Exe Path** | Full path to the executable |

### Mouse Position

Coordinates are displayed simultaneously in three systems:

| Mode | Description |
|------|-------------|
| **Screen** | Absolute position on the virtual screen |
| **Window** | Relative to the target window's top-left corner |
| **Client** | Relative to the target window's client area |

### Control Under Mouse

Displays the **ClassNN** identifier and **HWND** of the child control directly under the cursor.

### Pixel Color

Shows the color of the pixel under the cursor as:
- **RGB** — decimal components (e.g. `255, 136, 0`)
- **Hex** — AHK-compatible hex (e.g. `0xFF8800`)
- **Swatch** — visual color preview

### Follow Mouse

| State | Behavior |
|-------|----------|
| **ON** (default) | Inspector tracks whatever window/control is under the cursor |
| **OFF** | Inspector stays locked on the last captured window |

### Freeze (Ctrl / Shift)

Holding **Ctrl** or **Shift** freezes all inspector updates. A red **[FROZEN]** label appears in the controls row. This lets you inspect transient UI without the values changing under you.

### Refresh Cadence

Configurable from 50 ms to 2000 ms (default: **500 ms**). Adjust via the spin box in the Inspector panel header or in **Edit > Settings**.

> **Note:** Cadences below ~100 ms may noticeably increase CPU usage.

---

## Editor / Runner

### Editor Features

- **Syntax highlighting** for AHK v2 — keywords, built-in functions/variables, directives, strings, numbers, hotkey definitions, single-line (`;`) and block (`/* ... */`) comments
- **Line numbers** in a dark gutter
- **Undo / Redo** — Ctrl+Z / Ctrl+Y
- **Find / Replace** — Ctrl+H (supports case-sensitive matching and replace-all)
- **No word wrap** by default for script readability

### Running Scripts

| Button | Action |
|--------|--------|
| **Run** | Launch the current script with AutoHotkey v2 |
| **Stop** | Graceful terminate, then hard-kill after timeout |

When the editor has **unsaved changes**, clicking Run presents a choice:

1. **Save** — save the file first, then run the saved file
2. **Apply** — run the current buffer as a temporary `.ahk` file (auto-cleaned on exit)
3. **Cancel** — abort

### Status Indicator

A colored circle next to the Run/Stop buttons:

| Color | State |
|-------|-------|
| Green | Idle — no script running |
| Blue | Running — script is active |
| Red | Error — last run failed or crashed |

### Output Pane

Captures and displays:
- The launch command used
- **stdout** in normal text
- **stderr** in red
- Exit code and termination message in green

---

## Project System

### Creating a Project

**File > New Project...** — select (or create) a folder. The app writes a `.ahkminiide.json` metadata file to the project root.

### Opening a Project

**File > Open Project...** — browse to an existing project folder.

### Recent Projects

**File > Recent Projects** — up to 10 most recently opened projects, ordered by last access.

### Active Run Target

Right-click any `.ahk` file in the Project Explorer and choose **Set as Active Target**. This marks which script the Run button will execute.

### File Filters

The Project Explorer tree shows: `*.ahk`, `*.ah2`, `*.txt`, `*.ini`, `*.json`.

---

## Global Hotkeys & Code Generation

Global hotkeys work **system-wide** — even when another application has focus. Generated code is inserted into the editor, or queued for insertion when the editor regains focus.

### Default Bindings

| Hotkey | Action | Generated AHK v2 Code |
|--------|--------|----------------------|
| **Ctrl+Shift+A** | WinActivate | `WinActivate "ahk_id 0x..."` |
| **Ctrl+Shift+K** | Click at cursor | `Click x, y` |
| **Ctrl+Shift+D** | Drag (two-step) | `MouseClickDrag "Left", x1, y1, x2, y2` |
| **Ctrl+Shift+L** | Pixel color loop | `PixelGetColor` / `PixelSearch` loop |

The letter keys (A, K, D, L) are configurable via **Edit > Settings** to avoid collisions with other software.

### WinActivate (Ctrl+Shift+A)

Inserts a `WinActivate` targeting the window currently shown in the Inspector, using the stable `ahk_id` format:

```autohotkey
WinActivate "ahk_id 0x001A0B3C"  ; Title: Untitled - Notepad, Class: Notepad, Process: notepad.exe
```

### Click (Ctrl+Shift+K)

Inserts a click at the current cursor coordinates using the configured coordinate mode:

```autohotkey
CoordMode "Mouse", "Window"
Click 350, 220
```

Supports all mouse buttons and double-click. Generated forms:

| Action | Code |
|--------|------|
| Single left click | `Click x, y` |
| Right click | `Click x, y, "Right"` |
| Middle click | `Click x, y, "Middle"` |
| Double left click | `Click x, y,, 2` |
| Double right click | `Click x, y, "Right", 2` |

### Drag (Ctrl+Shift+D) — Two-Step Capture

1. **First press** — captures the start point; status bar shows `Drag start captured: x, y`
2. **Second press** — captures the end point and inserts the drag code:

```autohotkey
CoordMode "Mouse", "Window"
MouseClickDrag "Left", 100, 200, 400, 350
```

### Pixel Color Loop (Ctrl+Shift+L)

Inserts a polling loop that waits for a specific pixel color at the current coordinates.

**Default template (PixelGetColor):**

```autohotkey
CoordMode "Pixel", "Window"
Loop {
    CurrentColor := PixelGetColor(350, 220)
    if (CurrentColor = "0xFF8800")
        break
    Sleep 100
}
```

**Alternative template (PixelSearch with variation):**

```autohotkey
CoordMode "Pixel", "Window"
Loop {
    if PixelSearch(&FoundX, &FoundY, 350, 220, 350, 220, "0xFF8800", 5)
        break
    Sleep 100
}
```

The `variation` parameter (0–255) uses the configured **Color Slack** setting. `0` = exact match, higher values allow more tolerance per RGB component.

### Pending Insertion Queue

When a hotkey fires while another application has focus:

1. The generated code is cached in a pending queue
2. The status bar shows `Code captured (pending insertion: N)`
3. When the editor regains focus, all pending code is automatically inserted in order

---

## Settings

All settings persist in `%APPDATA%\AHKMiniIDE\settings.json`.

Open the settings dialog via **Edit > Settings**.

| Category | Setting | Default | Range |
|----------|---------|---------|-------|
| **AHK v2** | Executable path | *(auto-detected)* | File path |
| | Command-line flags | *(empty)* | Free text |
| | Script arguments | *(empty)* | Free text |
| | Working directory | `script` | `script` / `project` |
| | Kill timeout | 2000 ms | 500–10000 ms |
| **Inspector** | Refresh cadence | 500 ms | 50–2000 ms |
| | Coordinate mode | `Window` | `Screen` / `Window` / `Client` |
| **Color** | Color slack (variation) | 5 | 0–255 |
| **Hotkeys** | Click letter | K | Single letter |
| | Drag letter | D | Single letter |
| | Pixel Loop letter | L | Single letter |
| | WinActivate letter | A | Single letter |

**Working directory modes:**
- `script` — run scripts with CWD set to the script's own directory (supports project-relative `#Include`)
- `project` — run scripts with CWD set to the project root

---

## Architecture

```
ahk_mini_ide/
├── __init__.py              Package version
├── __main__.py              Entry point (QApplication + MainWindow)
├── app.py                   MainWindow — docks, menus, toolbar, hotkey dispatch
├── settings.py              JSON-backed settings with AHK auto-detection
├── settings_dialog.py       Settings UI dialog
├── project/
│   ├── manager.py           Project create/open/recent, active target
│   └── explorer.py          QTreeView file browser
├── editor/
│   ├── editor_widget.py     CodeEditor (line numbers) + FindReplaceDialog
│   ├── syntax.py            AHK v2 syntax highlighter
│   ├── runner.py            QProcess-based AHK launcher
│   └── output_pane.py       Color-coded stdout/stderr console
├── inspector/
│   ├── win_info.py          Win32 ctypes API wrappers (30+ functions)
│   └── inspector_widget.py  Inspector panel with live updates
└── hotkeys/
    ├── global_hotkeys.py    RegisterHotKey via Qt native event filter
    └── codegen.py           AHK v2 code generators
```

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| GUI framework | PyQt6 | Native dock widget support, mature, cross-compile ready |
| Windows API | ctypes | Zero extra dependencies beyond Python stdlib |
| Settings format | JSON | Human-readable, easy to hand-edit if needed |
| Global hotkeys | `RegisterHotKey` + `WM_HOTKEY` | OS-level registration, works when app is not focused |
| Follow Mouse OFF | Targets last captured window | More predictable than "active window" which changes constantly |
| Code insertion | Pending queue | Hotkeys work globally; code waits for editor focus |
| Temp file execution | Auto-cleaned on process exit | No stale temp files left behind |

### Non-Windows Development

The `win_info.py` module returns safe default values on non-Windows platforms, allowing the UI to load and be developed/tested on Linux or macOS (inspector data will be empty).

---

## Known Limitations

- **Windows 11 only** — Inspector and global hotkeys use Win32 APIs via ctypes.
- **Two-finger trackpad click** — Supported only to the extent that Windows surfaces it as a standard right-click event. If the trackpad driver does not emit a standard mouse button event, it is out of scope.
- **Two-finger trackpad drag** — Supported only if representable as standard mouse button + motion. Otherwise unsupported.
- **X1/X2 mouse buttons** — Click code generation supports them where the OS reports them as standard button events.
- **PixelSearch variation** — Uses AHK v2 semantics: "allowed shades of variation" per RGB component, 0–255.

---

## License

[MIT](LICENSE) — Copyright (c) 2026 Mrkurtz1
