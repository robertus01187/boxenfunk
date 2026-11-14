"""Datenquellen, die ``RaceState`` liefern: live aus LMU oder aus einer Aufnahme.

Beide haben dieselbe Schnittstelle ``poll() -> RaceState | None`` und einen Text ``status``.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

from boxenfunk.adapters.lmu.translate import speed_kmh, to_race_state
from boxenfunk.model.race_state import PlayerState, RaceState


class LmuLiveSource:
    """Liest den Shared Memory von Le Mans Ultimate (nur lesend)."""

    def __init__(self, name: str | None = None) -> None:
        from boxenfunk.adapters.lmu.shm import LmuSharedMemory

        self._shm = LmuSharedMemory(name) if name else LmuSharedMemory()
        self._last_et: float | None = None
        self._last_change = 0.0
        self.status = "Warte auf Le Mans Ultimate …"

    def poll_inputs(self, pl: PlayerState) -> bool:
        """Schneller Weg nur fürs eigene Auto (Pedale, Gang, Tempo, Delta), direkt aus dem Speicher.

        Liest wenige Werte ohne die ganze Datenkopie, damit Input-Graph und Delta flüssig laufen.
        """
        tel = self._shm._live.telemetry
        idx = tel.playerVehicleIdx
        if not tel.playerHasVehicle or not 0 <= idx < len(tel.telemInfo):
            return False
        t = tel.telemInfo[idx]
        et = float(t.mElapsedTime)
        if pl.input_time is not None and et == pl.input_time:
            return False
        pl.input_time = et
        pl.throttle = float(t.mFilteredThrottle)
        pl.brake = float(t.mFilteredBrake)
        pl.steering = float(t.mFilteredSteering)
        pl.clutch = float(t.mFilteredClutch)
        pl.gear = int(t.mGear)
        v = t.mLocalVel
        pl.speed_kmh = speed_kmh({"x": v.x, "y": v.y, "z": v.z})
        pl.rpm = float(t.mEngineRPM)
        pl.abs_active = bool(t.mABSActive)
        pl.tc_active = bool(t.mTCActive)
        pl.delta_best = float(t.mDeltaBest)
        return True

    def poll(self) -> RaceState | None:
        from boxenfunk.recorder.snapshot import snapshot

        self._shm.update()
        data = self._shm.data
        si = data.scoring.scoringInfo
        if si.mNumVehicles <= 0 or not data.telemetry.playerHasVehicle:
            self.status = "Warte auf Le Mans Ultimate … (kein Auto auf der Strecke)"
            return None
        et = si.mCurrentET
        now = time.time()
        if et != self._last_et:
            self._last_et = et
            self._last_change = now
        elif now - self._last_change > 3:
            self.status = "LMU verbunden, Spiel pausiert oder im Menü"
        snap = snapshot(data)
        snap["t"] = now
        # Lenkung/Kupplung lässt der Recorder weg; live wollen wir sie fürs Input-Widget.
        idx = data.telemetry.playerVehicleIdx
        if 0 <= idx < len(data.telemetry.telemInfo):
            t = data.telemetry.telemInfo[idx]
            for c in snap["c"].values():
                if c["s"].get("mIsPlayer") and "v" in c:
                    c["v"]["mFilteredSteering"] = float(t.mFilteredSteering)
                    c["v"]["mFilteredClutch"] = float(t.mFilteredClutch)
        st = to_race_state(snap)
        if now - self._last_change <= 3:
            self.status = f"LMU verbunden · {st.track}"
        return st


class ReplaySource:
    """Spielt eine Aufnahme (Datei oder Ordner mit ``*.jsonl.gz``) in Echtzeit × ``speed`` ab."""

    def __init__(self, path: Path, speed: float = 1.0, skip_to_race: bool = False) -> None:
        self.path = Path(path)
        self.speed = speed
        self._frames = self._iter()
        self._next: RaceState | None = None
        self._rec_t0: float | None = None
        self._wall_t0: float | None = None
        self._state: RaceState | None = None
        self.finished = False
        self.status = f"Wiedergabe: {self.path.name}"
        if skip_to_race:
            self._skip_to_race()

    def _iter(self) -> Iterator[RaceState]:
        from boxenfunk.recorder.delta import DeltaDecoder
        from boxenfunk.recorder.files import read_lines, recording_files

        dec = DeltaDecoder()
        for f in recording_files(self.path):
            for line in read_lines(f):
                if line.get("typ"):
                    continue
                st = dec.apply(line)
                # Der Decoder ändert sein Dict laufend, deshalb sofort übersetzen.
                if st is not None and st["c"]:
                    yield to_race_state(st)

    def _skip_to_race(self) -> None:
        from boxenfunk.model.race_state import Phase, SessionKind

        for st in self._frames:
            if st.session_kind == SessionKind.RENNEN and st.phase != Phase.GARAGE:
                self._state = st
                return

    def frames(self) -> Iterator[RaceState]:
        """Alle Messpunkte so schnell wie möglich (für Tests und Auswertungen)."""
        if self._state is not None:
            yield self._state
        yield from self._frames

    def poll_inputs(self, pl: PlayerState) -> bool:
        return False  # Aufnahme hat nur 5 Messpunkte pro Sekunde, die liefert poll()

    def poll(self) -> RaceState | None:
        now = time.monotonic()
        if self._state is None:
            self._state = next(self._frames, None)
            if self._state is None:
                self.finished = True
                return None
        if self._rec_t0 is None:
            self._rec_t0 = self._state.wall_time
            self._wall_t0 = now
        target = self._rec_t0 + (now - self._wall_t0) * self.speed
        while True:
            if self._next is None:
                self._next = next(self._frames, None)
                if self._next is None:
                    self.finished = True
                    self.status = "Wiedergabe beendet"
                    break
            if self._next.wall_time > target:
                break
            self._state = self._next
            self._next = None
        return self._state
