"""AHK v2 script runner — launch, stop, and capture output."""

from __future__ import annotations

import os
import tempfile
from enum import Enum, auto

from PyQt6.QtCore import QObject, QProcess, QTimer, pyqtSignal


class RunState(Enum):
    IDLE = auto()
    RUNNING = auto()
    ERROR = auto()


class AHKRunner(QObject):
    """Manages a single AHK v2 child process."""

    state_changed = pyqtSignal(RunState)
    stdout_ready = pyqtSignal(str)
    stderr_ready = pyqtSignal(str)
    finished = pyqtSignal(int, str)  # exit_code, message

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._process: QProcess | None = None
        self._state = RunState.IDLE
        self._temp_file: str | None = None
        self._kill_timer: QTimer | None = None

    @property
    def state(self) -> RunState:
        return self._state

    def _set_state(self, s: RunState) -> None:
        self._state = s
        self.state_changed.emit(s)

    # ----------------------------------------------------------------
    def run(self, *,
            ahk_exe: str,
            script_path: str,
            flags: str = "",
            args: str = "",
            working_dir: str = "",
            unsaved_text: str | None = None) -> None:
        """Launch the AHK script.

        If *unsaved_text* is provided a temporary file is created and
        executed instead of *script_path*.
        """
        if self._process is not None and self._process.state() != QProcess.ProcessState.NotRunning:
            return  # already running

        target = script_path
        if unsaved_text is not None:
            fd, tmp = tempfile.mkstemp(suffix=".ahk", prefix="ahkmini_")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(unsaved_text)
            self._temp_file = tmp
            target = tmp

        if not working_dir:
            working_dir = os.path.dirname(target)

        cmd_parts = [ahk_exe]
        if flags:
            cmd_parts.extend(flags.split())
        cmd_parts.append(target)
        if args:
            cmd_parts.extend(args.split())

        self._process = QProcess(self)
        self._process.setWorkingDirectory(working_dir)
        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.readyReadStandardError.connect(self._on_stderr)
        self._process.finished.connect(self._on_finished)

        program = cmd_parts[0]
        arguments = cmd_parts[1:]

        self._set_state(RunState.RUNNING)
        self.stdout_ready.emit(f">> {' '.join(cmd_parts)}\n")

        self._process.start(program, arguments)
        if not self._process.waitForStarted(3000):
            self._set_state(RunState.ERROR)
            self.finished.emit(-1, "Failed to start AHK process")

    # ----------------------------------------------------------------
    def stop(self, graceful_timeout_ms: int = 2000) -> None:
        """Stop the running process (graceful then hard-kill)."""
        if self._process is None or self._process.state() == QProcess.ProcessState.NotRunning:
            return

        # Attempt graceful close
        self._process.terminate()

        self._kill_timer = QTimer(self)
        self._kill_timer.setSingleShot(True)
        self._kill_timer.timeout.connect(self._hard_kill)
        self._kill_timer.start(graceful_timeout_ms)

    def _hard_kill(self) -> None:
        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.kill()

    # ----------------------------------------------------------------
    def _on_stdout(self) -> None:
        if self._process:
            data = self._process.readAllStandardOutput().data().decode("utf-8", errors="replace")
            self.stdout_ready.emit(data)

    def _on_stderr(self) -> None:
        if self._process:
            data = self._process.readAllStandardError().data().decode("utf-8", errors="replace")
            self.stderr_ready.emit(data)

    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        if self._kill_timer:
            self._kill_timer.stop()
            self._kill_timer = None

        # Clean up temp file
        if self._temp_file and os.path.exists(self._temp_file):
            try:
                os.remove(self._temp_file)
            except OSError:
                pass
            self._temp_file = None

        if exit_code == 0:
            self._set_state(RunState.IDLE)
            self.finished.emit(exit_code, "Process exited normally")
        else:
            self._set_state(RunState.ERROR)
            label = "crashed" if exit_status == QProcess.ExitStatus.CrashExit else "exited"
            self.finished.emit(exit_code, f"Process {label} with code {exit_code}")
