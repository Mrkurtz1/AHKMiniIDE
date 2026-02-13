"""Settings dialog for configuring all application preferences."""

from __future__ import annotations

import os

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from ahk_mini_ide.settings import Settings


class SettingsDialog(QDialog):
    """Modal dialog for editing application settings."""

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        self._settings = settings

        layout = QVBoxLayout(self)

        # == AHK Executable ==========================================
        grp_ahk = QGroupBox("AutoHotkey v2")
        form_ahk = QFormLayout()

        row_exe = QHBoxLayout()
        self._exe_edit = QLineEdit(settings.get("ahk_exe_path", ""))
        row_exe.addWidget(self._exe_edit)
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._browse_exe)
        row_exe.addWidget(btn_browse)
        form_ahk.addRow("Executable:", row_exe)

        self._flags_edit = QLineEdit(settings.get("ahk_flags", ""))
        form_ahk.addRow("Flags:", self._flags_edit)

        self._args_edit = QLineEdit(settings.get("ahk_args", ""))
        form_ahk.addRow("Script args:", self._args_edit)

        self._wd_combo = QComboBox()
        self._wd_combo.addItems(["script", "project"])
        self._wd_combo.setCurrentText(settings.get("working_dir_mode", "script"))
        form_ahk.addRow("Working dir:", self._wd_combo)

        self._kill_spin = QSpinBox()
        self._kill_spin.setRange(500, 10000)
        self._kill_spin.setSingleStep(500)
        self._kill_spin.setSuffix(" ms")
        self._kill_spin.setValue(settings.get("graceful_kill_timeout_ms", 2000))
        form_ahk.addRow("Kill timeout:", self._kill_spin)

        grp_ahk.setLayout(form_ahk)
        layout.addWidget(grp_ahk)

        # == Inspector ===============================================
        grp_insp = QGroupBox("Inspector")
        form_insp = QFormLayout()

        self._cadence_spin = QSpinBox()
        self._cadence_spin.setRange(50, 2000)
        self._cadence_spin.setSingleStep(50)
        self._cadence_spin.setSuffix(" ms")
        self._cadence_spin.setValue(settings.get("inspector_cadence_ms", 500))
        form_insp.addRow("Refresh cadence:", self._cadence_spin)

        self._coord_combo = QComboBox()
        self._coord_combo.addItems(["Screen", "Window", "Client"])
        self._coord_combo.setCurrentText(settings.get("default_coord_mode", "Window"))
        form_insp.addRow("Coord mode:", self._coord_combo)

        grp_insp.setLayout(form_insp)
        layout.addWidget(grp_insp)

        # == Color ===================================================
        grp_color = QGroupBox("Color")
        form_color = QFormLayout()

        self._slack_spin = QSpinBox()
        self._slack_spin.setRange(0, 255)
        self._slack_spin.setValue(settings.get("color_slack", 5))
        form_color.addRow("Color slack (variation):", self._slack_spin)
        form_color.addRow("", QLabel("0 = exact match, 255 = any color"))

        grp_color.setLayout(form_color)
        layout.addWidget(grp_color)

        # == Hotkey bindings =========================================
        grp_hk = QGroupBox("Global Hotkeys (Ctrl+Shift + letter)")
        form_hk = QFormLayout()

        self._hk_click = QLineEdit(settings.get("hotkey_click", "K"))
        self._hk_click.setMaxLength(1)
        self._hk_click.setFixedWidth(40)
        form_hk.addRow("Click:", self._hk_click)

        self._hk_drag = QLineEdit(settings.get("hotkey_drag", "D"))
        self._hk_drag.setMaxLength(1)
        self._hk_drag.setFixedWidth(40)
        form_hk.addRow("Drag:", self._hk_drag)

        self._hk_pixel = QLineEdit(settings.get("hotkey_pixel_loop", "L"))
        self._hk_pixel.setMaxLength(1)
        self._hk_pixel.setFixedWidth(40)
        form_hk.addRow("Pixel Loop:", self._hk_pixel)

        self._hk_activate = QLineEdit(settings.get("hotkey_win_activate", "A"))
        self._hk_activate.setMaxLength(1)
        self._hk_activate.setFixedWidth(40)
        form_hk.addRow("WinActivate:", self._hk_activate)

        grp_hk.setLayout(form_hk)
        layout.addWidget(grp_hk)

        # == Buttons =================================================
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_exe(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select AutoHotkey v2 Executable", "",
            "Executables (*.exe);;All Files (*)",
        )
        if path:
            self._exe_edit.setText(path)

    def _apply(self) -> None:
        s = self._settings
        s.set("ahk_exe_path", self._exe_edit.text().strip())
        s.set("ahk_flags", self._flags_edit.text().strip())
        s.set("ahk_args", self._args_edit.text().strip())
        s.set("working_dir_mode", self._wd_combo.currentText())
        s.set("graceful_kill_timeout_ms", self._kill_spin.value())
        s.set("inspector_cadence_ms", self._cadence_spin.value())
        s.set("default_coord_mode", self._coord_combo.currentText())
        s.set("color_slack", self._slack_spin.value())
        s.set("hotkey_click", self._hk_click.text().upper().strip() or "K")
        s.set("hotkey_drag", self._hk_drag.text().upper().strip() or "D")
        s.set("hotkey_pixel_loop", self._hk_pixel.text().upper().strip() or "L")
        s.set("hotkey_win_activate", self._hk_activate.text().upper().strip() or "A")
        self.accept()
