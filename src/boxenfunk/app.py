"""Einstiegspunkt der App.

T0: zeigt nur ein Statusfenster, damit sich der Build und Start der .exe prüfen lassen.
Die eigentlichen Overlays kommen in T3.
"""

from __future__ import annotations

import argparse
import sys

from boxenfunk import __version__

APP_NAME = "Boxenfunk"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="boxenfunk", description=f"{APP_NAME} Overlay")
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {__version__}")
    parser.add_argument(
        "--quit-after",
        type=int,
        default=0,
        metavar="MS",
        help="Beendet die App nach MS Millisekunden (für Smoke-Tests)",
    )
    return parser.parse_args(argv)


def build_window():
    """Erzeugt das Statusfenster. Import von Qt erst hier, damit --version ohne Qt läuft."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

    window = QWidget()
    window.setWindowTitle(f"{APP_NAME} {__version__}")
    layout = QVBoxLayout(window)
    label = QLabel(f"{APP_NAME} {__version__} läuft.\nOverlays folgen in einer späteren Version.")
    label.setObjectName("statusLabel")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(label)
    window.resize(420, 140)
    return window


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)

    window = build_window()
    window.show()

    if args.quit_after > 0:
        QTimer.singleShot(args.quit_after, app.quit)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
