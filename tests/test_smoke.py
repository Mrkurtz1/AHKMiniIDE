"""Startup smoke tests — verify all imports resolve and widgets construct.

Run with:  python -m pytest tests/test_smoke.py -v
Or without pytest:  python tests/test_smoke.py
"""

from __future__ import annotations

import ast
import importlib
import os
import pathlib
import sys
import unittest


# ====================================================================
#  Static analysis: catch attribute-before-assignment bugs
# ====================================================================

class _InitOrderChecker(ast.NodeVisitor):
    """Walk a class __init__ and flag self.X accesses that happen before assignment."""

    def __init__(self):
        self.assigned: set[str] = set()
        self.errors: list[str] = []

    def visit_Assign(self, node: ast.Assign) -> None:  # noqa: N802
        for target in node.targets:
            if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                if target.value.id == "self":
                    self.assigned.add(target.attr)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            if node.func.value.id == "self":
                method_name = node.func.attr
                # Check args that reference self.X
                for arg in list(node.args) + [kw.value for kw in node.keywords]:
                    self._check_expr(arg, f"call to self.{method_name}")
        self.generic_visit(node)

    def _check_expr(self, node: ast.AST, context: str) -> None:
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "self" and node.attr not in self.assigned:
                self.errors.append(
                    f"  self.{node.attr} used in {context} "
                    f"but may not be assigned yet"
                )


def _check_init_ordering(filepath: pathlib.Path) -> list[str]:
    """Parse a Python file and check all __init__ methods for order bugs."""
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(filepath))
    all_errors: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                    checker = _InitOrderChecker()
                    for stmt in item.body:
                        checker.visit(stmt)
                    if checker.errors:
                        all_errors.append(f"{filepath}:{node.name}.__init__:")
                        all_errors.extend(checker.errors)
    return all_errors


# ====================================================================
#  Import chain tests
# ====================================================================

class TestImports(unittest.TestCase):
    """Verify every module in the package can be imported."""

    def test_all_modules_importable(self):
        """Every .py file under ahk_mini_ide/ should parse without SyntaxError."""
        pkg_root = pathlib.Path(__file__).resolve().parent.parent / "ahk_mini_ide"
        for pyfile in pkg_root.rglob("*.py"):
            with self.subTest(file=str(pyfile)):
                source = pyfile.read_text(encoding="utf-8")
                ast.parse(source, filename=str(pyfile))

    def test_no_init_ordering_bugs(self):
        """No __init__ method should access self.X before assigning it."""
        pkg_root = pathlib.Path(__file__).resolve().parent.parent / "ahk_mini_ide"
        all_errors: list[str] = []
        for pyfile in pkg_root.rglob("*.py"):
            all_errors.extend(_check_init_ordering(pyfile))
        if all_errors:
            self.fail(
                "Potential attribute-before-assignment bugs:\n"
                + "\n".join(all_errors)
            )

    def test_import_settings(self):
        from ahk_mini_ide.settings import Settings, DEFAULT_SETTINGS
        self.assertIn("ahk_exe_path", DEFAULT_SETTINGS)
        self.assertIn("inspector_cadence_ms", DEFAULT_SETTINGS)

    def test_import_codegen(self):
        from ahk_mini_ide.hotkeys.codegen import (
            gen_click, gen_drag, gen_pixel_loop, gen_win_activate,
        )
        # Verify generated code is syntactically reasonable
        code = gen_click(100, 200)
        self.assertIn("Click 100, 200", code)
        self.assertIn("CoordMode", code)

        code = gen_drag(10, 20, 30, 40)
        self.assertIn("MouseClickDrag", code)

        code = gen_win_activate(0x123, title="Test")
        self.assertIn('WinActivate "ahk_id 0x123"', code)

        code = gen_pixel_loop(50, 60, "0xFF0000")
        self.assertIn("PixelGetColor", code)

        code = gen_pixel_loop(50, 60, "0xFF0000", use_pixel_search=True)
        self.assertIn("PixelSearch", code)

    def test_import_win_info(self):
        from ahk_mini_ide.inspector.win_info import (
            InspectorSnapshot, WindowInfo, MouseCoords, ControlInfo, PixelColor,
            capture_snapshot, is_modifier_held,
        )
        # Stubs should return safe defaults on non-Windows
        snap = capture_snapshot()
        self.assertIsInstance(snap, InspectorSnapshot)
        self.assertEqual(snap.window.hwnd, 0)
        self.assertEqual(snap.color.hex_rgb, "0x000000")

    def test_import_runner(self):
        from ahk_mini_ide.editor.runner import AHKRunner, RunState
        self.assertEqual(RunState.IDLE.name, "IDLE")

    def test_import_hotkeys(self):
        from ahk_mini_ide.hotkeys.global_hotkeys import HotkeyID, HotkeyManager
        self.assertEqual(HotkeyID.CLICK, 1)
        self.assertEqual(HotkeyID.WIN_ACTIVATE, 4)

    def test_import_project_manager(self):
        from ahk_mini_ide.project.manager import Project, ProjectManager


# ====================================================================
#  Widget construction tests (require PyQt6)
# ====================================================================

def _have_pyqt6() -> bool:
    try:
        from PyQt6.QtWidgets import QApplication
        return True
    except ImportError:
        return False


@unittest.skipUnless(_have_pyqt6(), "PyQt6 not available")
class TestWidgetConstruction(unittest.TestCase):
    """Verify all widgets can be constructed without errors."""

    _app = None

    @classmethod
    def setUpClass(cls):
        from PyQt6.QtWidgets import QApplication
        if QApplication.instance() is None:
            cls._app = QApplication([])

    def test_code_editor_constructs(self):
        from ahk_mini_ide.editor.editor_widget import CodeEditor
        editor = CodeEditor()
        self.assertIsNotNone(editor)
        editor.deleteLater()

    def test_output_pane_constructs(self):
        from ahk_mini_ide.editor.output_pane import OutputPane
        pane = OutputPane()
        self.assertIsNotNone(pane)
        pane.deleteLater()

    def test_project_explorer_constructs(self):
        from ahk_mini_ide.project.explorer import ProjectExplorer
        explorer = ProjectExplorer()
        self.assertIsNotNone(explorer)
        explorer.deleteLater()

    def test_inspector_constructs(self):
        import tempfile
        from ahk_mini_ide.inspector.inspector_widget import InspectorWidget
        from ahk_mini_ide.settings import Settings
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name
        try:
            settings = Settings(path=tmp_path)
            inspector = InspectorWidget(settings)
            inspector.stop()  # stop timer before deleting
            self.assertIsNotNone(inspector)
            inspector.deleteLater()
        finally:
            os.unlink(tmp_path)

    def test_find_replace_constructs(self):
        from ahk_mini_ide.editor.editor_widget import CodeEditor, FindReplaceDialog
        editor = CodeEditor()
        dlg = FindReplaceDialog(editor)
        self.assertIsNotNone(dlg)
        dlg.deleteLater()
        editor.deleteLater()

    def test_settings_dialog_constructs(self):
        import tempfile
        from ahk_mini_ide.settings import Settings
        from ahk_mini_ide.settings_dialog import SettingsDialog
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name
        try:
            settings = Settings(path=tmp_path)
            dlg = SettingsDialog(settings)
            self.assertIsNotNone(dlg)
            dlg.deleteLater()
        finally:
            os.unlink(tmp_path)

    def test_main_window_constructs(self):
        """THE critical test — full MainWindow construction."""
        import tempfile
        from ahk_mini_ide.app import MainWindow
        from ahk_mini_ide.settings import Settings
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name
        try:
            settings = Settings(path=tmp_path)
            window = MainWindow(settings)
            self.assertIsNotNone(window)
            # Verify key sub-widgets exist
            self.assertIsNotNone(window._editor)
            self.assertIsNotNone(window._output)
            self.assertIsNotNone(window._inspector)
            self.assertIsNotNone(window._explorer)
            self.assertIsNotNone(window._status_indicator)
            self.assertIsNotNone(window._status_label)
            self.assertIsNotNone(window._btn_run)
            self.assertIsNotNone(window._btn_stop)
            window.close()
            window.deleteLater()
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    unittest.main()
