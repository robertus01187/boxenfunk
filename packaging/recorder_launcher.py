"""Startskript für den Recorder (PyInstaller, Konsolenprogramm)."""

import sys

from boxenfunk.recorder.recorder import main

if __name__ == "__main__":
    sys.exit(main())
