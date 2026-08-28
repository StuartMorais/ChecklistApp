from __future__ import annotations

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.main_window import ChecklistMainWindow
from app.resources import resource_path


APP_USER_MODEL_ID = "ChecklistPython.Desktop.Scanner"


def set_windows_app_user_model_id() -> None:
    """Give Windows a stable taskbar identity for the packaged EXE/icon."""
    if sys.platform != "win32":
        return

    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        # This is cosmetic; the application should still start if Windows rejects it.
        pass


def main() -> int:
    set_windows_app_user_model_id()

    app = QApplication(sys.argv)

    icon_path = resource_path("assets/icon.ico")

    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = ChecklistMainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
