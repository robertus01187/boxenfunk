"""Boxenfunk-iRacing-Recorder: zeichnet die iRacing-Live-Daten in Dateien auf.

Bedienung für Endnutzer: ``Boxenfunk-iRacing-Recorder.exe`` doppelklicken, Rennen fahren,
danach Fenster schließen. Die Dateien liegen im Ordner ``Boxenfunk-Aufnahmen-iRacing`` neben
der exe (Dateinamen beginnen mit ``iRacing_``).

Gleiches Dateiformat wie der LMU-Recorder (ADR-002): Kopfzeile, Keyframe + Änderungszeilen,
neue Datei pro Stunde, absturzsicher. Zusätzlich steht in manchen Zeilen ``si`` mit den
Session-Infos (Strecke, Sessions, Wertung) – bei jeder Änderung und in jedem Keyframe.
Der LMU-Recorder (``recorder.py``) bleibt davon völlig unberührt.
"""

from __future__ import annotations

import argparse
import contextlib
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from boxenfunk import __version__
from boxenfunk.recorder import iracing_snapshot as snap_mod
from boxenfunk.recorder.delta import DeltaEncoder
from boxenfunk.recorder.files import RotatingWriter
from boxenfunk.recorder.recorder import _install_close_handler, _pause_if_frozen

FORMAT_VERSION = 1
PREFIX = "iRacing"

SESSION_TYPES = {
    "Practice": "Training",
    "Open Practice": "Training",
    "Lone Practice": "Training",
    "Lone Qualify": "Qualifying",
    "Open Qualify": "Qualifying",
    "Qualify": "Qualifying",
    "Warmup": "Warm-up",
    "Race": "Rennen",
    "Heat Race": "Rennen",
    "Offline Testing": "Testfahrt",
}


class Source(Protocol):
    def update(self) -> bool: ...
    def var_names(self) -> list[str]: ...
    def get(self, name: str) -> Any: ...
    def session_info(self) -> dict[str, Any]: ...
    def raw(self) -> bytes | None: ...


def session_label(si: dict[str, Any], session_num: int | None) -> str:
    for ses in (si.get("SessionInfo") or {}).get("Sessions") or []:
        if ses.get("SessionNum") == session_num:
            typ = str(ses.get("SessionType") or ses.get("SessionName") or "")
            return SESSION_TYPES.get(typ, typ or f"Session {session_num}")
    return f"Session {session_num}" if session_num is not None else "?"


def track_name(si: dict[str, Any]) -> str:
    w = si.get("WeekendInfo") or {}
    name = w.get("TrackDisplayName") or w.get("TrackName") or "?"
    cfg = w.get("TrackConfigName")
    return f"{name} ({cfg})" if cfg else str(name)


def player_summary(snap: dict[str, Any]) -> dict[str, Any] | None:
    idx = snap["i"].get("PlayerCarIdx")
    me = snap["c"].get(str(idx)) if idx is not None else None
    if me is None:
        return None
    s, v = me["s"], me["v"]
    return {
        "place": s.get("CarIdxPosition"),
        "class": v.get("CarClassShortName") or "",
        "class_place": s.get("CarIdxClassPosition"),
        "laps": s.get("CarIdxLapCompleted"),
        "fuel": snap["i"].get("FuelLevel"),
        "on_pit_road": s.get("CarIdxOnPitRoad"),
    }


def status_text(snap: dict[str, Any], si: dict[str, Any], writer: RotatingWriter) -> str:
    i = snap["i"]
    cars = [c for c in snap["c"].values() if not c["v"].get("CarIsPaceCar")]
    parts = [
        f"Strecke: {track_name(si)}",
        session_label(si, i.get("SessionNum")),
        f"{len(cars)} Autos",
    ]
    p = player_summary(snap)
    if p and i.get("IsOnTrack"):
        txt = f"Du: P{p['place']} gesamt" if p["place"] else "Du: noch ohne Platz"
        if p["class"] and p["class_place"]:
            txt += f", P{p['class_place']} in {p['class']}"
        if p["laps"] is not None and p["laps"] >= 0:
            txt += f", {p['laps']} Runden fertig"
        parts.append(txt)
        if p["fuel"] is not None:
            parts.append(f"Sprit {p['fuel']:.1f} l".replace(".", ","))
    elif i.get("IsReplayPlaying"):
        parts.append("Wiederholung läuft")
    else:
        parts.append("du sitzt gerade nicht im Auto")
    mb = writer.size_bytes() / 1e6
    parts.append(f"Datei {mb:.1f} MB".replace(".", ","))
    return " | ".join(parts)


class IRacingRecorder:
    """Eine Aufnahme. ``step()`` nimmt einen Messpunkt; ``run()`` wiederholt das im Takt."""

    def __init__(
        self,
        source: Source,
        folder: Path,
        hz: float = 5.0,
        rotate_s: float = 3600.0,
        keyframe_s: float = 60.0,
        raw_s: float = 300.0,
        alive_timeout_s: float = 3.0,
        clock: Callable[[], float] = time.time,
        log: Callable[[str], None] = print,
        status_s: float = 10.0,
    ) -> None:
        self.src = source
        self.hz = hz
        self.keyframe_s = keyframe_s
        self.raw_s = raw_s
        self.alive_timeout_s = alive_timeout_s
        self.clock = clock
        self.log = log
        self.status_s = status_s
        self.writer = RotatingWriter(folder, prefix=PREFIX, rotate_s=rotate_s)
        self.encoder = DeltaEncoder()
        self.frames = 0
        self.alive = False
        self._last_mark: tuple[Any, ...] | None = None
        self._last_change = -1e18
        self._last_key = -1e18
        self._last_raw = -1e18
        self._last_status = -1e18
        self._waiting_msg_at = -1e18
        self._last_si: dict[str, Any] | None = None
        self.last_snapshot: dict[str, Any] | None = None

    def _header(self, si: dict[str, Any]) -> dict[str, Any]:
        w = si.get("WeekendInfo") or {}
        return {
            "typ": "boxenfunk-aufnahme",
            "format": FORMAT_VERSION,
            "recorder": __version__,
            "sim": "iRacing",
            "hz": self.hz,
            "gameVersion": w.get("BuildVersion"),
            "start": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }

    def _is_alive(self, connected: bool, now: float) -> bool:
        """Läuft das Spiel und ändern sich die Daten? (Menü, Pause, Spiel aus = nein)"""
        if not connected:
            self._last_mark = None
            self._last_change = -1e18
            return False
        mark = (
            self.src.get("SessionNum"),
            self.src.get("SessionTime"),
            self.src.get("ReplayFrameNum"),
        )
        if mark != self._last_mark:
            self._last_change = now
            self._last_mark = mark
        return now - self._last_change <= self.alive_timeout_s

    def step(self) -> bool:
        """Einen Messpunkt nehmen. True = es wurde etwas geschrieben."""
        now = self.clock()
        connected = self.src.update()
        alive = self._is_alive(connected, now)
        if alive != self.alive:
            self.alive = alive
            if alive:
                self.log("Verbunden: Daten von iRacing kommen an. Aufnahme läuft.")
            else:
                self.log("Keine neuen Daten (Menü, Pause oder Spiel beendet). Warte ...")
                self.writer.flush()
        if not alive:
            if now - self._waiting_msg_at >= 30 and self.frames == 0:
                self._waiting_msg_at = now
                self.log("Warte auf iRacing ... (Spiel starten und einer Session beitreten.)")
            return False

        si_full = self.src.session_info()
        if self.writer.needs_new_file(now):
            path = self.writer.open_next(now, self._header(si_full))
            self.encoder.reset()
            self._last_key = now
            self._last_raw = -1e18
            self.log(f"Schreibe in: {path}")
        elif now - self._last_key >= self.keyframe_s:
            self.encoder.reset()
            self._last_key = now

        snap = snap_mod.snapshot(self.src)
        self.last_snapshot = snap
        frame = self.encoder.encode(snap, now)
        si = snap_mod.session_rest(si_full)
        if (frame is not None and frame.get("k")) or si != self._last_si:
            frame = frame if frame is not None else {"t": round(now, 3)}
            frame["si"] = si
            self._last_si = si
        wrote = False
        if frame is not None:
            self.writer.write(frame, now)
            self.frames += 1
            wrote = True

        if now - self._last_raw >= self.raw_s:
            blob = self.src.raw()
            if blob:
                self.writer.write_raw(blob, now)
            self._last_raw = now

        if now - self._last_status >= self.status_s:
            self._last_status = now
            self.log(time.strftime("%H:%M:%S ") + status_text(snap, si_full, self.writer))
        return wrote

    def run(self, duration_s: float = 0.0, stop: threading.Event | None = None) -> None:
        stop = stop or threading.Event()
        period = 1.0 / self.hz
        start = time.monotonic()
        next_t = start
        try:
            while not stop.is_set():
                self.step()
                if duration_s and time.monotonic() - start >= duration_s:
                    break
                next_t += period
                delay = next_t - time.monotonic()
                if delay < -1.0:  # stark verspätet (z. B. PC war im Standby): Takt neu ansetzen
                    next_t = time.monotonic()
                    delay = 0
                if delay > 0:
                    stop.wait(delay)
        finally:
            self.close()

    def close(self) -> None:
        self.writer.close()


# --- Kommandozeile -------------------------------------------------------------


def default_folder() -> Path:
    """Eigener Ordner, damit sich iRacing- und LMU-Aufnahmen nie vermischen."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "Boxenfunk-Aufnahmen-iRacing"
    return Path.cwd() / "recordings-iracing"


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="Boxenfunk-iRacing-Recorder",
        description="Zeichnet iRacing-Daten auf. "
        "'Boxenfunk-iRacing-Recorder pruefen <Datei oder Ordner>' zeigt eine Zusammenfassung.",
    )
    p.add_argument(
        "--version", action="version", version=f"Boxenfunk-iRacing-Recorder {__version__}"
    )
    p.add_argument("--ordner", type=Path, default=None, help="Zielordner für die Aufnahmen")
    p.add_argument("--hz", type=float, default=5.0, help="Messpunkte pro Sekunde (Standard 5)")
    p.add_argument(
        "--dauer", type=float, default=0.0, help="Nach so vielen Sekunden beenden (Test)"
    )
    p.add_argument("--ohne-pause", action="store_true", help="Am Ende nicht auf Enter warten")
    p.add_argument("--testdatei", default=None, help=argparse.SUPPRESS)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    for stream in (sys.stdout, sys.stderr):  # exotische Fahrernamen dürfen nie zum Absturz führen
        with contextlib.suppress(AttributeError, ValueError):
            stream.reconfigure(errors="replace")

    # "pruefen <pfad>" oder Datei/Ordner per Drag & Drop auf die exe gezogen
    if argv and (argv[0] == "pruefen" or Path(argv[0]).exists()):
        from boxenfunk.recorder.iracing_analyse import main as analyse_main

        target = argv[1:] if argv[0] == "pruefen" else argv
        rc = analyse_main(target)
        _pause_if_frozen()
        return rc

    args = parse_args(argv)
    folder = args.ordner or default_folder()

    from boxenfunk.adapters.iracing.sdk import IRacingSource

    print(f"Boxenfunk-iRacing-Recorder {__version__}")
    print("Liest nur mit, verändert nichts am Spiel. Beenden: Fenster schließen oder Strg+C.")
    print(f"Aufnahmen landen in: {folder}\n")

    stop = threading.Event()
    done = threading.Event()
    closing = threading.Event()
    _keep = _install_close_handler(stop, done, closing)  # noqa: F841

    src = IRacingSource(test_file=args.testdatei)
    rec = IRacingRecorder(src, folder, hz=args.hz)
    try:
        rec.run(duration_s=args.dauer, stop=stop)
    except KeyboardInterrupt:
        rec.close()
    finally:
        src.close()
        done.set()
    print(f"\nAufnahme beendet. {rec.frames} Messpunkte gespeichert in: {folder}")
    if not closing.is_set() and not args.ohne_pause:
        _pause_if_frozen()
    return 0


if __name__ == "__main__":
    sys.exit(main())
