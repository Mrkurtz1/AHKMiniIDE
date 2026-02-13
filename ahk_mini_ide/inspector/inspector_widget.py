"""Inspector panel — real-time Window Spy mimic for AHK v2."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ahk_mini_ide.inspector.win_info import (
    InspectorSnapshot,
    capture_snapshot,
    is_modifier_held,
)
from ahk_mini_ide.settings import Settings


def _readonly_line(text: str = "") -> QLineEdit:
    le = QLineEdit(text)
    le.setReadOnly(True)
    le.setFrame(False)
    font = QFont("Consolas", 10)
    font.setStyleHint(QFont.StyleHint.Monospace)
    le.setFont(font)
    return le


def _section(title: str) -> QGroupBox:
    gb = QGroupBox(title)
    gb.setStyleSheet("QGroupBox { font-weight: bold; }")
    return gb


class InspectorWidget(QWidget):
    """Real-time inspector that mirrors key Window Spy functionality."""

    # Emitted with the latest snapshot every tick (unless frozen).
    snapshot_updated = pyqtSignal(object)  # InspectorSnapshot

    def __init__(self, settings: Settings, parent: QWidget | None = None):
        super().__init__(parent)
        self._settings = settings
        self._frozen = False
        self._follow_mouse = True
        self._last_hwnd: int = 0
        self._snapshot: InspectorSnapshot = InspectorSnapshot()

        self._build_ui()
        self._setup_timer()

    # ================================================================
    #  UI construction
    # ================================================================
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)

        # -- controls row --------------------------------------------
        ctrl_row = QHBoxLayout()
        self._follow_cb = QCheckBox("Follow Mouse")
        self._follow_cb.setChecked(True)
        self._follow_cb.toggled.connect(self._on_follow_toggled)
        ctrl_row.addWidget(self._follow_cb)

        self._frozen_label = QLabel("")
        self._frozen_label.setStyleSheet("color: #FF6B68; font-weight: bold;")
        ctrl_row.addWidget(self._frozen_label)
        ctrl_row.addStretch()

        ctrl_row.addWidget(QLabel("Refresh (ms):"))
        self._cadence_spin = QSpinBox()
        self._cadence_spin.setRange(50, 2000)
        self._cadence_spin.setSingleStep(50)
        self._cadence_spin.setValue(self._settings.get("inspector_cadence_ms", 500))
        self._cadence_spin.valueChanged.connect(self._on_cadence_changed)
        ctrl_row.addWidget(self._cadence_spin)

        root.addLayout(ctrl_row)

        # -- window identity -----------------------------------------
        grp_win = _section("Window Identity")
        form_win = QFormLayout()
        self._f_title = _readonly_line()
        self._f_class = _readonly_line()
        self._f_process = _readonly_line()
        self._f_hwnd = _readonly_line()
        self._f_pid = _readonly_line()
        self._f_exe = _readonly_line()
        form_win.addRow("Title:", self._f_title)
        form_win.addRow("Class:", self._f_class)
        form_win.addRow("Process:", self._f_process)
        form_win.addRow("HWND:", self._f_hwnd)
        form_win.addRow("PID:", self._f_pid)
        form_win.addRow("Exe Path:", self._f_exe)
        grp_win.setLayout(form_win)
        root.addWidget(grp_win)

        # -- mouse position ------------------------------------------
        grp_mouse = _section("Mouse Position")
        form_mouse = QFormLayout()
        self._f_screen = _readonly_line()
        self._f_window = _readonly_line()
        self._f_client = _readonly_line()
        form_mouse.addRow("Screen:", self._f_screen)
        form_mouse.addRow("Window:", self._f_window)
        form_mouse.addRow("Client:", self._f_client)
        grp_mouse.setLayout(form_mouse)
        root.addWidget(grp_mouse)

        # -- control under mouse -------------------------------------
        grp_ctrl = _section("Control Under Mouse")
        form_ctrl = QFormLayout()
        self._f_ctrl_class = _readonly_line()
        self._f_ctrl_hwnd = _readonly_line()
        form_ctrl.addRow("ClassNN:", self._f_ctrl_class)
        form_ctrl.addRow("HWND:", self._f_ctrl_hwnd)
        grp_ctrl.setLayout(form_ctrl)
        root.addWidget(grp_ctrl)

        # -- pixel color ---------------------------------------------
        grp_color = _section("Pixel Color")
        color_layout = QHBoxLayout()
        form_color = QFormLayout()
        self._f_rgb = _readonly_line()
        self._f_hex = _readonly_line()
        form_color.addRow("RGB:", self._f_rgb)
        form_color.addRow("Hex:", self._f_hex)
        color_layout.addLayout(form_color)

        self._color_swatch = QFrame()
        self._color_swatch.setFixedSize(48, 48)
        self._color_swatch.setFrameShape(QFrame.Shape.Box)
        self._color_swatch.setStyleSheet("background-color: #000000;")
        color_layout.addWidget(self._color_swatch)

        grp_color.setLayout(color_layout)
        root.addWidget(grp_color)

        root.addStretch()

    # ================================================================
    #  Timer / refresh
    # ================================================================
    def _setup_timer(self) -> None:
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(self._settings.get("inspector_cadence_ms", 500))

    def _on_cadence_changed(self, ms: int) -> None:
        self._settings.set("inspector_cadence_ms", ms)
        self._timer.setInterval(ms)

    def _on_follow_toggled(self, checked: bool) -> None:
        self._follow_mouse = checked

    # ================================================================
    #  Tick — capture and display
    # ================================================================
    def _tick(self) -> None:
        # Freeze check
        if is_modifier_held():
            if not self._frozen:
                self._frozen = True
                self._frozen_label.setText("[FROZEN]")
            return
        else:
            if self._frozen:
                self._frozen = False
                self._frozen_label.setText("")

        snap = capture_snapshot(
            follow_mouse=self._follow_mouse,
            last_hwnd=self._last_hwnd,
        )
        self._snapshot = snap

        if snap.window.hwnd:
            self._last_hwnd = snap.window.hwnd

        self._update_display(snap)
        self.snapshot_updated.emit(snap)

    def _update_display(self, s: InspectorSnapshot) -> None:
        w = s.window
        self._f_title.setText(w.title)
        self._f_class.setText(w.class_name)
        self._f_process.setText(w.process_name)
        self._f_hwnd.setText(hex(w.hwnd) if w.hwnd else "")
        self._f_pid.setText(str(w.pid) if w.pid else "")
        self._f_exe.setText(w.exe_path)

        c = s.coords
        self._f_screen.setText(f"{c.screen_x}, {c.screen_y}")
        self._f_window.setText(f"{c.window_x}, {c.window_y}")
        self._f_client.setText(f"{c.client_x}, {c.client_y}")

        ctrl = s.control
        self._f_ctrl_class.setText(ctrl.class_nn)
        self._f_ctrl_hwnd.setText(hex(ctrl.hwnd) if ctrl.hwnd else "")

        clr = s.color
        self._f_rgb.setText(clr.decimal_str)
        self._f_hex.setText(clr.hex_rgb)
        self._color_swatch.setStyleSheet(
            f"background-color: rgb({clr.r},{clr.g},{clr.b});"
        )

    # ================================================================
    #  Public accessors
    # ================================================================
    @property
    def snapshot(self) -> InspectorSnapshot:
        return self._snapshot

    def start(self) -> None:
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
