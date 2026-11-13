"""Boxenfunk-LMU-Recorder: zeichnet die LMU-Live-Daten in Dateien auf.

Bedienung für Endnutzer: ``Boxenfunk-LMU-Recorder.exe`` doppelklicken, Rennen fahren,
danach Fenster schließen. Die Dateien liegen im Ordner ``Boxenfunk-Aufnahmen`` neben der exe.
"""

from __future__ import annotations

import argparse
import contextlib
import ctypes
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from boxenfunk import __version__
from boxenfunk.adapters.lmu import lmu_data as d
from boxenfunk.recorder import snapshot as snap_mod
from boxenfunk.recorder.delta import DeltaEncoder
from boxenfunk.recorder.files import RotatingWriter

FORMAT_VERSION = 1

SESSION_NAMES = {0: "Testtag", 9: "Warm-up"}
SESSION_NAMES.update({i: f"Training {i}" for i in range(1, 5)})
SESSION_NAMES.update({i: f"Qualifying {i - 4}" for i in range(5, 9)})
SESSION_NAMES.update({i: f"Rennen {i - 9}" for i in range(10, 14)})


class Source(Protocol):
    data: d.LMUObjectOut

    def update(self) -> bool: ...


def session_name(code: int) -> str:
    return SESSION_NAMES.get(code, f"Session {code}")


def player_summary(snap: dict[str, Any]) -> dict[str, Any] | None:
    """Kurze Zusammenfassung des eigenen Autos aus einem Momentzustand."""
    cars = snap["c"]
    me = next((c for c in cars.values() if c["s"].get("mIsPlayer")), None)
    if me is None:
        return None
    s = me["s"]
    cls = s.get("mVehicleClass", "")
    class_place = 1 + sum(
        1
        for c in cars.values()
        if c["s"].get("mVehicleClass") == cls and 0 < c["s"].get("mPlace", 0) < s.get("mPlace", 0)
    )
    v = me.get("v", {})
    return {
        "place": s.get("mPlace"),
        "class": cls,
        "class_place": class_place,
        "laps": s.get("mTotalLaps"),
        "ve": v.get("mVirtualEnergy"),
        "fuel": v.get("mFuel"),
        "in_pits": s.get("mInPits"),
    }


def status_text(snap: dict[str, Any], writer: RotatingWriter, src: Source) -> str:
    i = snap["i"]
    parts = [
        f"Strecke: {i.get('mTrackName') or '?'}",
        session_name(i.get("mSession", -1)),
        f"{len(snap['c'])} Autos",
    ]
    p = player_summary(snap)
    if p:
        parts.append(
            f"Du: P{p['place']} gesamt, P{p['class_place']} in {p['class']}, Runde {p['laps']}"
        )
        if p["ve"] is not None:
            parts.append(f"VE {p['ve'] * 100:.1f} %".replace(".", ","))
        if p["fuel"] is not None:
            parts.append(f"Sprit {p['fuel']:.1f} l".replace(".", ","))
    else:
        parts.append("kein eigenes Auto auf der Strecke")
    mb = writer.size_bytes() / 1e6
    parts.append(f"Datei {mb:.1f} MB".replace(".", ","))
    if getattr(src, "forced", 0):
        parts.append(f"(Hinweis: {src.forced}x ungeprüft kopiert)")
    return " | ".join(parts)


class Recorder:
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
        self.writer = RotatingWriter(folder, rotate_s=rotate_s)
        self.encoder = DeltaEncoder()
        self.frames = 0
        self.alive = False
        self._last_et: tuple[float, float] | None = None
        self._last_change = -1e18
        self._last_key = -1e18
        self._last_raw = -1e18
        self._last_status = -1e18
        self._waiting_msg_at = -1e18
        self.last_snapshot: dict[str, Any] | None = None

    def _header(self, data: d.LMUObjectOut) -> dict[str, Any]:
        return {
            "typ": "boxenfunk-aufnahme",
            "format": FORMAT_VERSION,
            "recorder": __version__,
            "sim": "LMU",
            "hz": self.hz,
            "gameVersion": data.generic.gameVersion,
            "struct_sizes": {
                "LMUObjectOut": ctypes.sizeof(d.LMUObjectOut),
                "LMUVehicleScoring": ctypes.sizeof(d.LMUVehicleScoring),
                "LMUVehicleTelemetry": ctypes.sizeof(d.LMUVehicleTelemetry),
                "LMUScoringInfo": ctypes.sizeof(d.LMUScoringInfo),
            },
            "start": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }

    def _is_alive(self, data: d.LMUObjectOut, now: float) -> bool:
        """Läuft das Spiel und ändern sich die Daten? (Menü/Pause/Spiel aus = nein)"""
        ets = (
            data.scoring.scoringInfo.mCurrentET,
            data.telemetry.telemInfo[0].mElapsedTime if data.telemetry.activeVehicles else 0.0,
        )
        if ets != self._last_et:
            if self._last_et is not None or any(ets):
                self._last_change = now
            self._last_et = ets
        return now - self._last_change <= self.alive_timeout_s

    def step(self) -> bool:
        """Einen Messpunkt nehmen. True = es wurde etwas geschrieben."""
        now = self.clock()
        self.src.update()
        data = self.src.data
        alive = self._is_alive(data, now)
        if alive != self.alive:
            self.alive = alive
            if alive:
                self.log("Verbunden: Daten von Le Mans Ultimate kommen an. Aufnahme läuft.")
            else:
                self.log("Keine neuen Daten (Menü, Pause oder Spiel beendet). Warte ...")
                self.writer.flush()
        if not alive:
            if now - self._waiting_msg_at >= 30 and self.frames == 0:
                self._waiting_msg_at = now
                self.log(
                    "Warte auf Le Mans Ultimate ... (Spiel starten und auf die Strecke fahren. "
                    "Falls das so bleibt: in LMU unter Einstellungen > Gameplay 'Enable Plugins' einschalten.)"
                )
            return False

        if self.writer.needs_new_file(now):
            path = self.writer.open_next(now, self._header(data))
            self.encoder.reset()
            self._last_key = now
            self._last_raw = -1e18
            self.log(f"Schreibe in: {path}")
        elif now - self._last_key >= self.keyframe_s:
            self.encoder.reset()
            self._last_key = now

        snap = snap_mod.snapshot(data)
        self.last_snapshot = snap
        frame = self.encoder.encode(snap, now)
        wrote = False
        if frame is not None:
            self.writer.write(frame, now)
            self.frames += 1
            wrote = True

        if now - self._last_raw >= self.raw_s:
            self.writer.write_raw(snap_mod.anonymized_raw(data), now)
            self._last_raw = now

        if now - self._last_status >= self.status_s:
            self._last_status = now
            self.log(time.strftime("%H:%M:%S ") + status_text(snap, self.writer, self.src))
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
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "Boxenfunk-Aufnahmen"
    return Path.cwd() / "recordings"


def _install_close_handler(
    stop: threading.Event, done: threading.Event, closing: threading.Event
) -> Any:
    """Windows: Bei Strg+C oder beim Schließen des Fensters die Datei noch sauber abschließen."""
    if sys.platform != "win32":
        return None
    try:
        handler_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)

        def handler(event: int) -> bool:
            if event >= 2:  # Fenster schließen, Abmelden, Herunterfahren
                closing.set()
            stop.set()
            if event < 2:
                return True  # Strg+C/Strg+Pause: selbst erledigt
            done.wait(4.0)
            return False  # Windows beendet das Programm danach

        cb = handler_type(handler)
        ctypes.windll.kernel32.SetConsoleCtrlHandler(cb, True)
        return cb  # Referenz behalten, sonst räumt Python den Callback weg
    except Exception:  # reine Komfortfunktion, darf nie stören
        return None


def _pause_if_frozen() -> None:
    if getattr(sys, "frozen", False):
        with contextlib.suppress(EOFError, KeyboardInterrupt):
            input("\nEnter drücken zum Schließen ...")


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="Boxenfunk-LMU-Recorder",
        description="Zeichnet Le-Mans-Ultimate-Daten auf. "
        "'Boxenfunk-LMU-Recorder pruefen <Datei oder Ordner>' zeigt eine Zusammenfassung einer Aufnahme.",
    )
    p.add_argument("--version", action="version", version=f"Boxenfunk-LMU-Recorder {__version__}")
    p.add_argument("--ordner", type=Path, default=None, help="Zielordner für die Aufnahmen")
    p.add_argument("--hz", type=float, default=5.0, help="Messpunkte pro Sekunde (Standard 5)")
    p.add_argument(
        "--dauer", type=float, default=0.0, help="Nach so vielen Sekunden beenden (Test)"
    )
    p.add_argument("--ohne-pause", action="store_true", help="Am Ende nicht auf Enter warten")
    p.add_argument(
        "--quelle", default=d.LMUConstants.LMU_SHARED_MEMORY_FILE, help=argparse.SUPPRESS
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    for stream in (sys.stdout, sys.stderr):  # exotische Fahrernamen dürfen nie zum Absturz führen
        with contextlib.suppress(AttributeError, ValueError):
            stream.reconfigure(errors="replace")

    # "pruefen <pfad>" oder Datei/Ordner per Drag & Drop auf die exe gezogen
    if argv and (argv[0] == "pruefen" or Path(argv[0]).exists()):
        from boxenfunk.recorder.analyse import main as analyse_main

        target = argv[1:] if argv[0] == "pruefen" else argv
        rc = analyse_main(target)
        _pause_if_frozen()
        return rc

    args = parse_args(argv)
    folder = args.ordner or default_folder()

    from boxenfunk.adapters.lmu.shm import LmuSharedMemory

    print(f"Boxenfunk-LMU-Recorder {__version__}")
    print("Liest nur mit, verändert nichts am Spiel. Beenden: Fenster schließen oder Strg+C.")
    print(f"Aufnahmen landen in: {folder}\n")

    stop = threading.Event()
    done = threading.Event()
    closing = threading.Event()
    _keep = _install_close_handler(stop, done, closing)  # noqa: F841

    rec = Recorder(LmuSharedMemory(args.quelle), folder, hz=args.hz)
    try:
        rec.run(duration_s=args.dauer, stop=stop)
    except KeyboardInterrupt:
        rec.close()
    finally:
        done.set()
    print(f"\nAufnahme beendet. {rec.frames} Messpunkte gespeichert in: {folder}")
    if not closing.is_set() and not args.ohne_pause:
        _pause_if_frozen()
    return 0


if __name__ == "__main__":
    sys.exit(main())
