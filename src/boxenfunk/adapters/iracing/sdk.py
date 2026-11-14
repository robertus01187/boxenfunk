"""Zugriff auf die iRacing-Live-Daten (iRacing SDK, Shared Memory) über ``pyirsdk`` (MIT-Lizenz).

Die Klasse kapselt das Verbinden/Trennen, damit der Recorder nur fragen muss:
„Gibt es gerade frische Daten?“ (``update``) und dann die Werte liest.
"""

from __future__ import annotations

import contextlib
import io
import re
import time
from collections.abc import Callable
from typing import Any

# Abschnitte der Session-Infos (YAML), die aufgezeichnet werden.
# Nicht dabei: CarSetup (eigenes Setup), RadioInfo/CameraInfo (für uns uninteressant).
SESSION_INFO_SECTIONS = (
    "WeekendInfo",
    "SessionInfo",
    "QualifyResultsInfo",
    "SplitTimeInfo",
    "DriverInfo",
)

_USER_ID = re.compile(rb"(UserID: )(-?\d+)")


def anonymize_raw(blob: bytes) -> bytes:
    """iRacing-Kundennummern (UserID) in einer Rohkopie mit Nullen überschreiben (Länge bleibt gleich)."""
    return _USER_ID.sub(lambda m: m.group(1) + b"0" * len(m.group(2)), blob)


def _make_irsdk() -> Any:
    import irsdk  # pyirsdk

    return irsdk.IRSDK()


class IRacingSource:
    """Verbindung zu iRacing. ``update()`` liefert True, wenn ein frischer Datenstand bereitliegt."""

    def __init__(
        self,
        ir: Any | None = None,
        test_file: str | None = None,
        retry_s: float = 2.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.ir = ir if ir is not None else _make_irsdk()
        self.test_file = test_file
        self.retry_s = retry_s
        self.clock = clock
        self._last_try = -1e18
        self._si_update: int | None = None
        self._si_cache: dict[str, Any] = {}
        self._names: list[str] | None = None

    # -- Verbindung --
    def _connect(self) -> bool:
        now = self.clock()
        if now - self._last_try < self.retry_s:
            return False
        self._last_try = now
        # pyirsdk schreibt bei fehlendem Spiel Meldungen auf die Konsole; die sollen nicht stören.
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                ok = bool(self.ir.startup(test_file=self.test_file))
            except Exception:
                ok = False
        if not ok:
            self._disconnect()
        return ok

    def _disconnect(self) -> None:
        with contextlib.suppress(Exception):
            self.ir.shutdown()
        self._si_update = None
        self._si_cache = {}
        self._names = None

    def close(self) -> None:
        self._disconnect()

    def update(self) -> bool:
        ir = self.ir
        try:
            if ir.is_initialized and not ir.is_connected:
                self._disconnect()
            if not ir.is_initialized and not self._connect():
                return False
            if not ir.is_connected:
                return False
            ir.freeze_var_buffer_latest()
            return True
        except Exception:  # Spiel beendet, Speicher weg o. ä.: neu verbinden
            self._disconnect()
            return False

    # -- Werte --
    def var_names(self) -> list[str]:
        if self._names is None:
            self._names = list(self.ir.var_headers_names or [])
        return self._names

    def get(self, name: str) -> Any:
        try:
            return self.ir[name]
        except Exception:
            return None

    def session_info(self) -> dict[str, Any]:
        """Session-Infos (YAML) als Dict; wird nur neu gelesen, wenn iRacing sie geändert hat."""
        try:
            upd = self.ir.session_info_update
        except Exception:
            return self._si_cache
        if upd != self._si_update:
            info = {}
            for sec in SESSION_INFO_SECTIONS:
                val = self.get(sec)
                if val is not None:
                    info[sec] = val
            self._si_cache = info
            self._si_update = upd
        return self._si_cache

    def raw(self) -> bytes | None:
        """Rohkopie des ganzen Speicherbereichs (anonymisiert), als Sicherheitsnetz."""
        mem = getattr(self.ir, "_shared_mem", None)
        if mem is None:
            return None
        try:
            return anonymize_raw(bytes(mem[:]))
        except Exception:
            return None
