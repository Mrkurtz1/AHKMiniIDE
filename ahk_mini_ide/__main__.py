"""Package entry point for python -m ahk_mini_ide."""

import sys

from PyQt6.QtWidgets import QApplication

from ahk_mini_ide.app import MainWindow
from ahk_mini_ide.settings import Settings


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("AHK Mini IDE")
    app.setOrganizationName("AHKMiniIDE")

    settings = Settings()
    window = MainWindow(settings)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
