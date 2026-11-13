"""Startskript für den iRacing-Recorder (PyInstaller, Konsolenprogramm)."""

import sys

from boxenfunk.recorder.iracing_recorder import main

if __name__ == "__main__":
    sys.exit(main())
