"""Startskript für PyInstaller (absoluter Import, damit das Paket sauber eingebunden wird)."""

import sys

from boxenfunk.app import main

if __name__ == "__main__":
    sys.exit(main())
