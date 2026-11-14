"""Einstiegspunkt der App.

Prototyp (0.3.0): liest Le Mans Ultimate live und zeigt die ersten Overlays (Standings,
Relative, Delta, Inputs, VE & Sprit). Zum Entwickeln ohne Spiel lässt sich stattdessen eine
Aufnahme abspielen (``--abspielen``).
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
    parser.add_argument(
        "--abspielen",
        metavar="AUFNAHME",
        help="Statt LMU live eine Aufnahme (.jsonl.gz oder Ordner) abspielen",
    )
    parser.add_argument("--tempo", type=float, default=1.0, help="Abspieltempo (z. B. 4 = 4-fach)")
    parser.add_argument(
        "--ab-rennen", action="store_true", help="Beim Abspielen direkt zum Rennstart springen"
    )
    parser.add_argument("--einstellungen", metavar="DATEI", help="Andere Einstellungsdatei nutzen")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    from pathlib import Path

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from boxenfunk.overlay.controller import Controller, make_source

    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)

    source = make_source(args.abspielen, args.tempo, args.ab_rennen)
    ctl = Controller(
        source,
        Path(args.einstellungen) if args.einstellungen else None,
        check_updates=args.quit_after == 0,
    )
    app.aboutToQuit.connect(ctl.close)
    ctl.show()

    if args.quit_after > 0:
        QTimer.singleShot(args.quit_after, app.quit)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
