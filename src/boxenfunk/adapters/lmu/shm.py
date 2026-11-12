"""Nur-lesender Zugriff auf den eingebauten Shared Memory von Le Mans Ultimate (``LMU_Data``).

Vorgehen wie bei TinyPedal (GPLv3): Speicherbereich öffnen, und nur dann eine Kopie ziehen,
wenn das Spiel gerade frische Daten gemeldet hat und Scoring- und Telemetrie-Teil zur selben
Fahrzeuganzahl passen. So vermeiden wir halb aktualisierte Daten.
In den Spielspeicher wird nie geschrieben.
"""

from __future__ import annotations

import ctypes
import mmap
import sys

from . import lmu_data as d

SHM_NAME = d.LMUConstants.LMU_SHARED_MEMORY_FILE
SIZE = ctypes.sizeof(d.LMUObjectOut)
FORCE_AFTER = 10


def _open(name: str, size: int) -> mmap.mmap:
    if sys.platform == "win32":
        # Öffnet den Bereich des Spiels; läuft das Spiel noch nicht, entsteht ein leerer Bereich,
        # den das Spiel beim Start übernimmt (identisches Verhalten wie TinyPedal).
        return mmap.mmap(-1, size, name)
    # Linux (nur Entwicklung/Tests): Datei in /dev/shm
    path = f"/dev/shm/{name}"
    with open(path, "a+b") as f:
        if f.tell() != size:
            f.truncate(0)
            f.write(b"\0" * size)
            f.flush()
        return mmap.mmap(f.fileno(), size)


def is_consistent(data: d.LMUObjectOut) -> bool:
    ev = data.generic.events
    return bool(ev.SME_UPDATE_SCORING or ev.SME_UPDATE_TELEMETRY) and (
        data.scoring.scoringInfo.mNumVehicles == data.telemetry.activeVehicles
    )


class LmuSharedMemory:
    """Hält eine stabile Kopie der Spieldaten in ``self.data``."""

    def __init__(self, name: str = SHM_NAME) -> None:
        self._mm = _open(name, SIZE)
        self._live = d.LMUObjectOut.from_buffer(self._mm)
        self._buf = bytearray(SIZE)
        self.data = d.LMUObjectOut.from_buffer(self._buf)
        self.skipped = 0
        self.forced = 0
        self._miss_in_row = 0

    def update(self) -> bool:
        """Kopiert frische Daten. False = diesmal keine stimmige Kopie (alte bleibt erhalten).

        Sicherheitsnetz: Ist die Prüfung 10-mal hintereinander nicht erfüllt, wird trotzdem
        kopiert, damit eine Aufnahme nie wegen einer zu strengen Prüfung leer bleibt.
        """
        if is_consistent(self._live) or self._miss_in_row >= FORCE_AFTER:
            if self._miss_in_row >= FORCE_AFTER:
                self.forced += 1
            self._miss_in_row = 0
            self._buf[:] = self._mm
            return True
        self._miss_in_row += 1
        self.skipped += 1
        return False
