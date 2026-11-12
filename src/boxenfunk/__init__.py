"""Boxenfunk – Sim-Racing-Overlay für LMU und iRacing."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("boxenfunk")
except PackageNotFoundError:  # z. B. in der PyInstaller-exe ohne Metadaten
    __version__ = "0.0.1"
