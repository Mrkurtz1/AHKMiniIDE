"""Main application window with dockable tool panels."""

from __future__ import annotations

import os
import sys
from functools import partial

from PyQt6.QtCore import QByteArray, Qt
from PyQt6.QtGui import QAction, QColor, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDockWidget,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ahk_mini_ide.editor.editor_widget import CodeEditor, FindReplaceDialog
from ahk_mini_ide.editor.output_pane import OutputPane
from ahk_mini_ide.editor.runner import AHKRunner, RunState
from ahk_mini_ide.hotkeys.codegen import (
    gen_click,
    gen_drag,
    gen_pixel_loop,
    gen_win_activate,
)
from ahk_mini_ide.hotkeys.global_hotkeys import HotkeyID, HotkeyManager
from ahk_mini_ide.inspector.inspector_widget import InspectorWidget
from ahk_mini_ide.project.explorer import ProjectExplorer
from ahk_mini_ide.project.manager import ProjectManager
from ahk_mini_ide.settings import Settings

_STATE_COLORS = {
    RunState.IDLE: "#6A8759",
    RunState.RUNNING: "#6897BB",
    RunState.ERROR: "#FF6B68",
}


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings):
        super().__init__()
        self._settings = settings
        self.setWindowTitle("AHK Mini IDE")
        self.resize(1280, 800)

        # -- core objects --------------------------------------------
        self._project_mgr = ProjectManager(settings, self)
        self._runner = AHKRunner(self)
        self._hotkey_mgr = HotkeyManager(self)

        # Drag capture state  (two-step)
        self._drag_start: tuple[int, int] | None = None

        # Pending insertions (captured while editor not focused)
        self._pending_insertions: list[str] = []

        # -- widgets -------------------------------------------------
        self._build_central()
        self._build_docks()
        self._build_menus()
        self._build_toolbar()
        self._connect_signals()
        self._register_hotkeys()
        self._restore_layout()

        # AHK exe check
        if not settings.get("ahk_exe_path"):
            self._statusBar_msg(
                "AutoHotkey v2 not found. Set the path via Edit > Settings."
            )

    # ================================================================
    #  Central widget (editor + runner toolbar + output)
    # ================================================================
    def _build_central(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._editor = CodeEditor()
        layout.addWidget(self._editor, stretch=3)

        # Runner bar
        runner_bar = QHBoxLayout()
        runner_bar.setContentsMargins(4, 2, 4, 2)

        self._btn_run = QPushButton("Run")
        self._btn_run.setFixedWidth(70)
        self._btn_run.clicked.connect(self._on_run)
        runner_bar.addWidget(self._btn_run)

        self._btn_stop = QPushButton("Stop")
        self._btn_stop.setFixedWidth(70)
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._on_stop)
        runner_bar.addWidget(self._btn_stop)

        self._status_indicator = QFrame()
        self._status_indicator.setFixedSize(16, 16)
        self._status_indicator.setFrameShape(QFrame.Shape.Circle)
        self._set_run_status(RunState.IDLE)
        runner_bar.addWidget(self._status_indicator)

        self._status_label = QLabel("Idle")
        runner_bar.addWidget(self._status_label)
        runner_bar.addStretch()

        layout.addLayout(runner_bar)

        self._output = OutputPane()
        layout.addWidget(self._output, stretch=1)

        self.setCentralWidget(central)

    # ================================================================
    #  Dock widgets
    # ================================================================
    def _build_docks(self) -> None:
        # --- Project Explorer ---
        self._explorer = ProjectExplorer()
        dock_proj = QDockWidget("Project Explorer", self)
        dock_proj.setObjectName("dock_project")
        dock_proj.setWidget(self._explorer)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock_proj)

        # --- Inspector ---
        self._inspector = InspectorWidget(self._settings)
        dock_insp = QDockWidget("Inspector", self)
        dock_insp.setObjectName("dock_inspector")
        dock_insp.setWidget(self._inspector)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock_insp)

        self._dock_proj = dock_proj
        self._dock_insp = dock_insp

    # ================================================================
    #  Menus
    # ================================================================
    def _build_menus(self) -> None:
        mb = self.menuBar()

        # -- File ----------------------------------------------------
        file_menu = mb.addMenu("&File")

        act_new_proj = file_menu.addAction("New Project...")
        act_new_proj.triggered.connect(self._on_new_project)

        act_open_proj = file_menu.addAction("Open Project...")
        act_open_proj.triggered.connect(self._on_open_project)

        self._recent_menu = file_menu.addMenu("Recent Projects")
        self._rebuild_recent_menu()

        file_menu.addSeparator()

        act_new_file = file_menu.addAction("New File")
        act_new_file.setShortcut("Ctrl+N")
        act_new_file.triggered.connect(self._on_new_file)

        act_open_file = file_menu.addAction("Open File...")
        act_open_file.setShortcut("Ctrl+O")
        act_open_file.triggered.connect(self._on_open_file)

        act_save = file_menu.addAction("Save")
        act_save.setShortcut("Ctrl+S")
        act_save.triggered.connect(self._on_save)

        act_save_as = file_menu.addAction("Save As...")
        act_save_as.setShortcut("Ctrl+Shift+S")
        act_save_as.triggered.connect(self._on_save_as)

        file_menu.addSeparator()

        act_exit = file_menu.addAction("Exit")
        act_exit.triggered.connect(self.close)

        # -- Edit ----------------------------------------------------
        edit_menu = mb.addMenu("&Edit")

        act_undo = edit_menu.addAction("Undo")
        act_undo.setShortcut("Ctrl+Z")
        act_undo.triggered.connect(self._editor.undo)

        act_redo = edit_menu.addAction("Redo")
        act_redo.setShortcut("Ctrl+Y")
        act_redo.triggered.connect(self._editor.redo)

        edit_menu.addSeparator()

        act_find = edit_menu.addAction("Find / Replace...")
        act_find.setShortcut("Ctrl+H")
        act_find.triggered.connect(self._on_find_replace)

        edit_menu.addSeparator()

        act_settings = edit_menu.addAction("Settings...")
        act_settings.triggered.connect(self._on_settings)

        # -- View ----------------------------------------------------
        view_menu = mb.addMenu("&View")
        view_menu.addAction(self._dock_proj.toggleViewAction())
        view_menu.addAction(self._dock_insp.toggleViewAction())

    def _rebuild_recent_menu(self) -> None:
        self._recent_menu.clear()
        for path in self._settings.recent_projects:
            act = self._recent_menu.addAction(path)
            act.triggered.connect(partial(self._open_project_path, path))
        if not self._settings.recent_projects:
            self._recent_menu.addAction("(none)").setEnabled(False)

    # ================================================================
    #  Toolbar
    # ================================================================
    def _build_toolbar(self) -> None:
        tb = self.addToolBar("Main")
        tb.setObjectName("main_toolbar")
        tb.setMovable(False)

        tb.addAction("New", self._on_new_file)
        tb.addAction("Open", self._on_open_file)
        tb.addAction("Save", self._on_save)
        tb.addSeparator()
        tb.addAction("Run", self._on_run)
        tb.addAction("Stop", self._on_stop)

    # ================================================================
    #  Signals
    # ================================================================
    def _connect_signals(self) -> None:
        # Runner
        self._runner.state_changed.connect(self._set_run_status)
        self._runner.stdout_ready.connect(lambda t: self._output.append_text(t))
        self._runner.stderr_ready.connect(lambda t: self._output.append_text(t, error=True))
        self._runner.finished.connect(self._on_runner_finished)

        # Project explorer
        self._explorer.file_activated.connect(self._open_file_in_editor)
        self._explorer.set_active_target.connect(self._project_mgr.set_active_target)
        self._project_mgr.project_opened.connect(
            lambda proj: self._explorer.set_project(proj)
        )

        # Hotkeys
        self._hotkey_mgr.hotkey_triggered.connect(self._on_hotkey)

        # Apply pending insertions when editor gains focus
        self._editor.installEventFilter(self)

    def eventFilter(self, obj, event):  # noqa: N802
        """Apply pending code insertions when the editor regains focus."""
        from PyQt6.QtCore import QEvent
        if obj is self._editor and event.type() == QEvent.Type.FocusIn:
            self._flush_pending()
        return super().eventFilter(obj, event)

    # ================================================================
    #  Hotkey registration
    # ================================================================
    def _register_hotkeys(self) -> None:
        bindings = {
            HotkeyID.CLICK: self._settings.get("hotkey_click", "K"),
            HotkeyID.DRAG: self._settings.get("hotkey_drag", "D"),
            HotkeyID.PIXEL_LOOP: self._settings.get("hotkey_pixel_loop", "L"),
            HotkeyID.WIN_ACTIVATE: self._settings.get("hotkey_win_activate", "A"),
        }
        errors = self._hotkey_mgr.register_all(bindings)
        for err in errors:
            self._statusBar_msg(err)

    # ================================================================
    #  Hotkey dispatch
    # ================================================================
    def _on_hotkey(self, hid: HotkeyID) -> None:
        snap = self._inspector.snapshot
        coord_mode = self._settings.get("default_coord_mode", "Window")

        # Choose coordinates based on coord mode
        if coord_mode == "Screen":
            x, y = snap.coords.screen_x, snap.coords.screen_y
        elif coord_mode == "Client":
            x, y = snap.coords.client_x, snap.coords.client_y
        else:
            x, y = snap.coords.window_x, snap.coords.window_y

        code: str | None = None

        if hid == HotkeyID.WIN_ACTIVATE:
            w = snap.window
            code = gen_win_activate(w.hwnd, w.title, w.class_name, w.process_name)

        elif hid == HotkeyID.CLICK:
            code = gen_click(x, y, coord_mode=coord_mode)

        elif hid == HotkeyID.DRAG:
            if self._drag_start is None:
                # First press → capture start
                self._drag_start = (x, y)
                self._statusBar_msg(f"Drag start captured: {x}, {y} — press again for end point")
                return
            else:
                x1, y1 = self._drag_start
                self._drag_start = None
                code = gen_drag(x1, y1, x, y, coord_mode=coord_mode)

        elif hid == HotkeyID.PIXEL_LOOP:
            color_hex = snap.color.hex_rgb
            variation = self._settings.get("color_slack", 5)
            code = gen_pixel_loop(x, y, color_hex,
                                  coord_mode=coord_mode,
                                  variation=variation)

        if code is not None:
            self._insert_or_pend(code)

    def _insert_or_pend(self, code: str) -> None:
        """Insert into editor if it has focus, otherwise cache for later."""
        if self._editor.hasFocus():
            self._editor.insert_code(code)
        else:
            self._pending_insertions.append(code)
            self._statusBar_msg(f"Code captured (pending insertion: {len(self._pending_insertions)})")

    def _flush_pending(self) -> None:
        if self._pending_insertions:
            for code in self._pending_insertions:
                self._editor.insert_code(code)
            self._pending_insertions.clear()

    # ================================================================
    #  Runner actions
    # ================================================================
    def _on_run(self) -> None:
        ahk_exe = self._settings.get("ahk_exe_path", "")
        if not ahk_exe:
            QMessageBox.warning(
                self, "AHK Not Configured",
                "AutoHotkey v2 executable path is not set.\n"
                "Please configure it via Edit > Settings.",
            )
            return

        script_path = self._editor.file_path
        unsaved_text: str | None = None

        if not script_path and not self._editor.toPlainText().strip():
            QMessageBox.information(self, "Nothing to Run", "Open or write a script first.")
            return

        if self._editor.is_modified:
            if script_path:
                btn = QMessageBox.question(
                    self, "Unsaved Changes",
                    "The editor has unsaved changes.\n\n"
                    "Run saved file, or run current buffer as temp file?",
                    QMessageBox.StandardButton.Save
                    | QMessageBox.StandardButton.Apply
                    | QMessageBox.StandardButton.Cancel,
                )
                if btn == QMessageBox.StandardButton.Save:
                    self._on_save()
                elif btn == QMessageBox.StandardButton.Apply:
                    unsaved_text = self._editor.toPlainText()
                else:
                    return
            else:
                unsaved_text = self._editor.toPlainText()

        wd_mode = self._settings.get("working_dir_mode", "script")
        working_dir = ""
        if wd_mode == "project" and self._project_mgr.project:
            working_dir = str(self._project_mgr.project.root)

        self._output.clear_output()
        self._runner.run(
            ahk_exe=ahk_exe,
            script_path=script_path or "",
            flags=self._settings.get("ahk_flags", ""),
            args=self._settings.get("ahk_args", ""),
            working_dir=working_dir,
            unsaved_text=unsaved_text,
        )

    def _on_stop(self) -> None:
        timeout = self._settings.get("graceful_kill_timeout_ms", 2000)
        self._runner.stop(graceful_timeout_ms=timeout)

    def _on_runner_finished(self, code: int, msg: str) -> None:
        self._output.append_info(f"\n[{msg}]\n")

    def _set_run_status(self, state: RunState) -> None:
        color = _STATE_COLORS.get(state, "#888888")
        self._status_indicator.setStyleSheet(
            f"background-color: {color}; border-radius: 8px;"
        )
        self._status_label.setText(state.name.capitalize())
        self._btn_run.setEnabled(state != RunState.RUNNING)
        self._btn_stop.setEnabled(state == RunState.RUNNING)

    # ================================================================
    #  File actions
    # ================================================================
    def _on_new_file(self) -> None:
        if not self._check_unsaved():
            return
        self._editor.clear()
        self._editor.file_path = None
        self.setWindowTitle("AHK Mini IDE — [new]")

    def _on_open_file(self) -> None:
        if not self._check_unsaved():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Open AHK Script", "",
            "AHK Scripts (*.ahk *.ah2);;All Files (*)",
        )
        if path:
            self._open_file_in_editor(path)

    def _open_file_in_editor(self, path: str) -> None:
        if not self._check_unsaved():
            return
        try:
            self._editor.load_file(path)
            self.setWindowTitle(f"AHK Mini IDE — {os.path.basename(path)}")
        except OSError as exc:
            QMessageBox.critical(self, "Error", f"Cannot open file:\n{exc}")

    def _on_save(self) -> None:
        if self._editor.file_path:
            self._editor.save_file()
        else:
            self._on_save_as()

    def _on_save_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save AHK Script", "",
            "AHK Scripts (*.ahk);;All Files (*)",
        )
        if path:
            self._editor.save_file(path)
            self.setWindowTitle(f"AHK Mini IDE — {os.path.basename(path)}")

    def _check_unsaved(self) -> bool:
        """Return True if safe to proceed (saved or user chose to discard)."""
        if not self._editor.is_modified:
            return True
        btn = QMessageBox.question(
            self, "Unsaved Changes",
            "Save changes before proceeding?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if btn == QMessageBox.StandardButton.Save:
            self._on_save()
            return True
        return btn == QMessageBox.StandardButton.Discard

    # ================================================================
    #  Project actions
    # ================================================================
    def _on_new_project(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Project Folder")
        if folder:
            self._project_mgr.create_project(folder)
            self._rebuild_recent_menu()

    def _on_open_project(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Open Project Folder")
        if folder:
            self._open_project_path(folder)

    def _open_project_path(self, folder: str) -> None:
        self._project_mgr.open_project(folder)
        self._rebuild_recent_menu()

    # ================================================================
    #  Find / Replace
    # ================================================================
    def _on_find_replace(self) -> None:
        dlg = FindReplaceDialog(self._editor, self)
        dlg.setModal(False)
        dlg.show()

    # ================================================================
    #  Settings dialog
    # ================================================================
    def _on_settings(self) -> None:
        from ahk_mini_ide.settings_dialog import SettingsDialog
        dlg = SettingsDialog(self._settings, self)
        if dlg.exec():
            # Re-register hotkeys with new bindings
            self._hotkey_mgr.unregister_all()
            self._register_hotkeys()

    # ================================================================
    #  Layout persistence
    # ================================================================
    def _save_layout(self) -> None:
        self._settings.set("window_geometry", self.saveGeometry().toHex().data().decode())
        self._settings.set("window_state", self.saveState().toHex().data().decode())

    def _restore_layout(self) -> None:
        geo = self._settings.get("window_geometry")
        if geo:
            self.restoreGeometry(QByteArray.fromHex(geo.encode()))
        state = self._settings.get("window_state")
        if state:
            self.restoreState(QByteArray.fromHex(state.encode()))

    def closeEvent(self, event):  # noqa: N802
        if not self._check_unsaved():
            event.ignore()
            return
        self._save_layout()
        self._hotkey_mgr.unregister_all()
        self._inspector.stop()
        self._runner.stop()
        super().closeEvent(event)

    # ================================================================
    #  Helpers
    # ================================================================
    def _statusBar_msg(self, text: str, ms: int = 5000) -> None:
        self.statusBar().showMessage(text, ms)
