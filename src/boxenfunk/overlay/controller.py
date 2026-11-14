"""Steuerung des Prototyps: Datenquelle abfragen, Overlays füttern, Startfenster, Einstellungen.

Startfenster (vereinfacht nach dem Muster „Grundriss A“): Status, Widgets an/aus, Größe,
„Overlays verschieben“. Positionen und Auswahl werden gespeichert und beim nächsten Start geladen.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from boxenfunk import __version__
from boxenfunk.core.tracker import SessionTracker
from boxenfunk.overlay.base import Overlay
from boxenfunk.overlay.widgets import (
    DeltaOverlay,
    EnergyOverlay,
    InputsOverlay,
    Logos,
    RelativeOverlay,
    StandingsOverlay,
)

SCALES = {"S": 0.8, "M": 1.0, "L": 1.25, "XL": 1.5}

# Startpositionen als Anteil der Bildschirmgröße (links/oben)
DEFAULT_POS = {
    "standings": (0.02, 0.05),
    "relative": (0.70, 0.55),
    "delta": (0.44, 0.04),
    "inputs": (0.40, 0.84),
    "energie": (0.72, 0.30),
}

CONTROL_STYLE = """
QWidget { background:#1b1d21; color:#e9ecf1; font-family:'Segoe UI',sans-serif; font-size:13px; }
QLabel#title { font-size:18px; font-weight:600; }
QLabel#status { background:#23262c; border:1px solid #3a3f48; border-radius:4px; padding:6px 8px; }
QLabel#hint { color:#9aa3b0; font-size:12px; }
QPushButton { background:#2c3038; border:1px solid #3a3f48; border-radius:4px; padding:6px 12px; }
QPushButton:checked { background:#4a6fb3; border-color:#4a6fb3; }
QPushButton:hover { border-color:#6f9fd6; }
QCheckBox { spacing:8px; padding:3px 0; }
"""


def app_dir() -> Path:
    """Ordner der exe (bzw. aktueller Ordner beim Entwickeln)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def config_path() -> Path:
    base = os.environ.get("APPDATA")
    root = Path(base) / "Boxenfunk" if base else Path.home() / ".config" / "boxenfunk"
    return root / "prototyp.json"


def load_config(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_config(path: Path, cfg: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    except OSError:
        pass


class Controller(QObject):
    def __init__(self, source, cfg_path: Path | None = None, logo_dir: Path | None = None) -> None:
        super().__init__()
        self.source = source
        self.tracker = SessionTracker()
        self.cfg_path = cfg_path or config_path()
        self.cfg = load_config(self.cfg_path)
        self.logo_dir = logo_dir or (app_dir() / "Boxenfunk-Logos")
        logos = Logos(self.logo_dir)
        scale = SCALES.get(self.cfg.get("groesse", "M"), 1.0)
        self.overlays: list[Overlay] = [
            StandingsOverlay(scale, logos),
            RelativeOverlay(scale, logos),
            DeltaOverlay(scale),
            InputsOverlay(scale),
            EnergyOverlay(scale),
        ]
        self.enabled = {o.key: self.cfg.get("an", {}).get(o.key, True) for o in self.overlays}
        self.has_data = False
        self._place_overlays()
        for o in self.overlays:
            o.moved.connect(self._save)
        self.window = self._build_window()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(50)  # 20-mal pro Sekunde

    # -- Fenster --

    def _place_overlays(self) -> None:
        screen = QGuiApplication.primaryScreen()
        geo = screen.availableGeometry() if screen else None
        saved = self.cfg.get("positionen", {})
        for o in self.overlays:
            o.relayout()
            if o.key in saved:
                x, y = saved[o.key]
            elif geo is not None:
                fx, fy = DEFAULT_POS.get(o.key, (0.1, 0.1))
                x, y = geo.x() + int(geo.width() * fx), geo.y() + int(geo.height() * fy)
            else:
                x, y = 100, 100
            o.move(int(x), int(y))

    def _build_window(self) -> QWidget:
        w = QWidget()
        w.setObjectName("control")
        w.setWindowTitle(f"Boxenfunk {__version__} – Prototyp")
        w.setStyleSheet(CONTROL_STYLE)
        lay = QVBoxLayout(w)
        title = QLabel("Boxenfunk – Prototyp für Le Mans Ultimate")
        title.setObjectName("title")
        lay.addWidget(title)
        self.status = QLabel("Starte …")
        self.status.setObjectName("status")
        lay.addWidget(self.status)

        lay.addWidget(QLabel("Widgets"))
        for o in self.overlays:
            cb = QCheckBox(o.title.replace("&", "&&"))
            cb.setChecked(self.enabled[o.key])
            cb.toggled.connect(lambda on, k=o.key: self._toggle(k, on))
            lay.addWidget(cb)

        row = QHBoxLayout()
        row.addWidget(QLabel("Größe"))
        grp = QButtonGroup(w)
        cur = self.cfg.get("groesse", "M")
        for name in SCALES:
            b = QPushButton(name)
            b.setCheckable(True)
            b.setChecked(name == cur)
            b.clicked.connect(lambda _=False, n=name: self._set_scale(n))
            grp.addButton(b)
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)

        self.move_btn = QPushButton("Overlays verschieben")
        self.move_btn.setCheckable(True)
        self.move_btn.toggled.connect(self._toggle_move)
        lay.addWidget(self.move_btn)

        logo_btn = QPushButton("Logo-Ordner öffnen")
        logo_btn.clicked.connect(self._open_logos)
        lay.addWidget(logo_btn)

        hint = QLabel(
            "LMU im Modus „Rahmenloses Fenster“ (Borderless) starten, sonst liegen die Overlays "
            "hinter dem Spiel.\n„Overlays verschieben“ drücken, Widgets mit der Maus ziehen, "
            "nochmal drücken zum Festsetzen. Im Rennen klickt man durch die Overlays hindurch.\n"
            "Dieses Fenster schließen = Boxenfunk beenden."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        lay.addWidget(hint)
        w.resize(440, 520)
        return w

    def _toggle(self, key: str, on: bool) -> None:
        self.enabled[key] = on
        self._save()
        self._refresh_visibility()

    def _set_scale(self, name: str) -> None:
        self.cfg["groesse"] = name
        for o in self.overlays:
            o.set_scale(SCALES[name])
        self._save()

    def _toggle_move(self, on: bool) -> None:
        self.move_btn.setText("Fertig – Positionen festsetzen" if on else "Overlays verschieben")
        for o in self.overlays:
            o.set_locked(not on)
        self._refresh_visibility()
        if not on:
            self._save()

    def _open_logos(self) -> None:
        self.logo_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.logo_dir)))

    def _save(self) -> None:
        self.cfg["positionen"] = {o.key: [o.x(), o.y()] for o in self.overlays}
        self.cfg["an"] = dict(self.enabled)
        save_config(self.cfg_path, self.cfg)

    def _refresh_visibility(self) -> None:
        moving = self.move_btn.isChecked()
        for o in self.overlays:
            show = self.enabled[o.key] and (self.has_data or moving)
            if show and not o.isVisible():
                o.show()
            elif not show and o.isVisible():
                o.hide()

    # -- Datenschleife --

    def tick(self) -> None:
        try:
            st = self.source.poll()
        except Exception as e:  # Overlay soll bei Lesefehlern nicht abstürzen
            st = None
            self.status.setText(f"Fehler beim Lesen: {e}")
        if st is not None:
            self.tracker.update(st)
        self.has_data = st is not None
        for o in self.overlays:
            if self.enabled[o.key]:
                o.set_data(st, self.tracker if st is not None else None)
        self._refresh_visibility()
        self.status.setText(getattr(self.source, "status", ""))

    def show(self) -> None:
        self.window.show()
        self._refresh_visibility()

    def close(self) -> None:
        self.timer.stop()
        self._save()
        for o in self.overlays:
            o.close()


def make_source(replay: str | None, speed: float, skip_to_race: bool):
    if replay:
        from boxenfunk.adapters.sources import ReplaySource

        return ReplaySource(Path(replay), speed=speed, skip_to_race=skip_to_race)
    from boxenfunk.adapters.sources import LmuLiveSource

    return LmuLiveSource()
