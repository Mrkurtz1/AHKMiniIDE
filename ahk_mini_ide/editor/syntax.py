"""Syntax highlighter for AutoHotkey v2 scripts."""

from __future__ import annotations

import re

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat, QTextDocument


def _fmt(color: str, *, bold: bool = False, italic: bool = False) -> QTextCharFormat:
    fmt = QTextCharFormat()
    fmt.setForeground(QColor(color))
    if bold:
        fmt.setFontWeight(QFont.Weight.Bold)
    if italic:
        fmt.setFontItalic(True)
    return fmt


# AHK v2 keywords / built-ins (representative subset)
_KEYWORDS = (
    "if|else|while|for|loop|return|break|continue|switch|case|default|"
    "try|catch|finally|throw|class|extends|new|global|local|static|"
    "true|false|unset"
)

_BUILTINS = (
    "MsgBox|InputBox|ToolTip|TrayTip|FileAppend|FileRead|FileDelete|"
    "Run|RunWait|Send|SendInput|SendEvent|SendPlay|"
    "Click|MouseClick|MouseClickDrag|MouseMove|MouseGetPos|"
    "WinActivate|WinClose|WinExist|WinActive|WinWait|WinWaitActive|"
    "WinGetTitle|WinGetClass|WinGetPID|WinGetProcessName|WinGetPos|"
    "PixelGetColor|PixelSearch|ImageSearch|"
    "Sleep|ExitApp|Reload|Persistent|"
    "CoordMode|SetTimer|Hotkey|"
    "RegRead|RegWrite|RegDelete|"
    "StrLen|StrSplit|StrReplace|SubStr|InStr|Trim|"
    "Abs|Ceil|Floor|Round|Mod|Min|Max|"
    "Array|Map|Object|Buffer|"
    "A_ScriptDir|A_ScriptFullPath|A_WorkingDir|A_ProgramFiles|"
    "A_Desktop|A_AppData|A_Temp|A_Now|A_TickCount"
)

_DIRECTIVES = (
    "#Include|#Requires|#SingleInstance|#Warn|#HotIf|#MaxThreadsPerHotkey"
)


class AHKHighlighter(QSyntaxHighlighter):
    """Simple regex-based syntax highlighter for AHK v2."""

    def __init__(self, parent: QTextDocument | None = None):
        super().__init__(parent)

        self._rules: list[tuple[re.Pattern[str], QTextCharFormat]] = []

        # Directives  (#Include, etc.)
        self._rules.append((
            re.compile(rf"\b({_DIRECTIVES})\b", re.IGNORECASE),
            _fmt("#CC7832", bold=True),
        ))

        # Keywords
        self._rules.append((
            re.compile(rf"\b({_KEYWORDS})\b", re.IGNORECASE),
            _fmt("#CC7832", bold=True),
        ))

        # Built-in functions / variables
        self._rules.append((
            re.compile(rf"\b({_BUILTINS})\b"),
            _fmt("#FFC66D"),
        ))

        # Strings (double-quoted)
        self._rules.append((
            re.compile(r'"[^"]*"'),
            _fmt("#6A8759"),
        ))

        # Strings (single-quoted)
        self._rules.append((
            re.compile(r"'[^']*'"),
            _fmt("#6A8759"),
        ))

        # Numbers
        self._rules.append((
            re.compile(r"\b0[xX][0-9A-Fa-f]+\b|\b\d+\.?\d*\b"),
            _fmt("#6897BB"),
        ))

        # Hotkey definitions  (e.g.  ^!k::)
        self._rules.append((
            re.compile(r"^[^\s;]+::"),
            _fmt("#A9B7C6", bold=True),
        ))

        # Comments (single-line ;)
        self._comment_fmt = _fmt("#808080", italic=True)
        self._rules.append((
            re.compile(r";.*$"),
            self._comment_fmt,
        ))

        # Block comment markers
        self._block_start = re.compile(r"/\*")
        self._block_end = re.compile(r"\*/")

    # -----------------------------------------------------------------
    def highlightBlock(self, text: str) -> None:  # noqa: N802
        # Apply single-line rules
        for pattern, fmt in self._rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)

        # Block comments  /* ... */
        self.setCurrentBlockState(0)
        start = 0
        if self.previousBlockState() != 1:
            m = self._block_start.search(text)
            start = m.start() if m else -1
        else:
            start = 0

        while start >= 0:
            m_end = self._block_end.search(text, start)
            if m_end is None:
                self.setCurrentBlockState(1)
                length = len(text) - start
            else:
                length = m_end.end() - start
            self.setFormat(start, length, self._comment_fmt)
            m_next = self._block_start.search(text, start + length)
            start = m_next.start() if m_next else -1
