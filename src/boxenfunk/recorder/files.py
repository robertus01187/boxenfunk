"""Schreiben und Lesen der Aufnahmedateien.

- ``*.jsonl.gz``: eine JSON-Zeile pro Messpunkt (erste Zeile = Kopfzeile mit Metadaten).
- ``*.roh.gz``: alle paar Minuten eine anonymisierte Rohkopie des Speicherbereichs.

Absturzsicherheit: Alle paar Sekunden wird der komprimierte Datenstrom „durchgespült“
(gzip sync flush). Stürzt der PC ab oder wird das Fenster geschlossen, gehen höchstens
die letzten Sekunden verloren; der Rest der Datei bleibt lesbar (siehe ``read_lines``).
"""

from __future__ import annotations

import contextlib
import gzip
import json
import struct
import zlib
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

RAW_MAGIC = b"BXRAW1"
RAW_HEAD = struct.Struct("<6sdI")  # magic, Zeitstempel, Länge


class RotatingWriter:
    """Schreibt Zeilen in ``<ordner>/<prefix>_<datum>_teilNN.jsonl.gz``, neue Datei je ``rotate_s``."""

    def __init__(
        self,
        folder: Path,
        prefix: str = "LMU",
        rotate_s: float = 3600.0,
        flush_s: float = 5.0,
    ) -> None:
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.prefix = prefix
        self.rotate_s = rotate_s
        self.flush_s = flush_s
        self.stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.part = 0
        self.path: Path | None = None
        self.raw_path: Path | None = None
        self._f: gzip.GzipFile | None = None
        self._raw: gzip.GzipFile | None = None
        self._opened_at = 0.0
        self._last_flush = 0.0
        self.lines_written = 0

    # -- Datei-Verwaltung --
    def needs_new_file(self, now: float) -> bool:
        return self._f is None or now - self._opened_at >= self.rotate_s

    def open_next(self, now: float, header: dict[str, Any]) -> Path:
        self.close()
        self.part += 1
        base = f"{self.prefix}_{self.stamp}_teil{self.part:02d}"
        self.path = self.folder / f"{base}.jsonl.gz"
        self.raw_path = self.folder / f"{base}.roh.gz"
        self._f = gzip.open(self.path, "wb", compresslevel=6)  # noqa: SIM115
        self._raw = None
        self._opened_at = now
        self._last_flush = now
        self.write({**header, "teil": self.part}, now)
        self.flush()
        return self.path

    def write(self, obj: dict[str, Any], now: float) -> None:
        assert self._f is not None
        self._f.write(json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode() + b"\n")
        self.lines_written += 1
        if now - self._last_flush >= self.flush_s:
            self.flush()
            self._last_flush = now

    def write_raw(self, blob: bytes, now: float) -> None:
        if self._raw is None:
            assert self.raw_path is not None
            self._raw = gzip.open(self.raw_path, "wb", compresslevel=6)  # noqa: SIM115
        self._raw.write(RAW_HEAD.pack(RAW_MAGIC, now, len(blob)) + blob)
        self._raw.flush(zlib.Z_SYNC_FLUSH)

    def flush(self) -> None:
        if self._f is not None:
            self._f.flush(zlib.Z_SYNC_FLUSH)
            self._f.fileobj.flush()  # type: ignore[union-attr]

    def size_bytes(self) -> int:
        total = 0
        for p in self.folder.glob(f"{self.prefix}_{self.stamp}_teil*"):
            with contextlib.suppress(OSError):
                total += p.stat().st_size
        return total

    def close(self) -> None:
        for f in (self._f, self._raw):
            if f is not None:
                with contextlib.suppress(OSError):
                    f.close()
        self._f = None
        self._raw = None


# -- Lesen --


def read_lines(path: Path) -> Iterator[dict[str, Any]]:
    """Liest eine Aufnahmedatei. Verträgt abgeschnittene Dateien (Absturz, Fenster geschlossen)."""
    with gzip.open(path, "rb") as f:
        buf = b""
        while True:
            try:
                chunk = f.read(1 << 16)
            except (EOFError, gzip.BadGzipFile, zlib.error):
                break
            if not chunk:
                break
            buf += chunk
            *lines, buf = buf.split(b"\n")
            for line in lines:
                if line.strip():
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        return


def read_raw(path: Path) -> Iterator[tuple[float, bytes]]:
    """Liest Rohkopien aus einer ``*.roh.gz``-Datei (verträgt abgeschnittene Dateien)."""
    with gzip.open(path, "rb") as f:
        while True:
            try:
                head = f.read(RAW_HEAD.size)
                if len(head) < RAW_HEAD.size:
                    return
                magic, t, n = RAW_HEAD.unpack(head)
                if magic != RAW_MAGIC:
                    return
                blob = f.read(n)
            except (EOFError, gzip.BadGzipFile, zlib.error):
                return
            if len(blob) < n:
                return
            yield t, blob


def recording_files(path: Path) -> list[Path]:
    """Eine Datei oder alle ``*.jsonl.gz`` eines Ordners, sortiert."""
    path = Path(path)
    if path.is_dir():
        return sorted(path.glob("*.jsonl.gz"))
    return [path]
