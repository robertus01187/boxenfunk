"""Boxenfunk – Sim-Racing-Overlay für LMU und iRacing."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("boxenfunk")
except PackageNotFoundError:  # nur falls die exe ohne Metadaten gebaut wurde
    __version__ = "unbekannt"
