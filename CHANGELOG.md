# Changelog

Format nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/), Versionierung nach SemVer.

## [0.1.0] – 2026-11-12
### Hinzugefügt
- `Boxenfunk-Recorder.exe`: zeichnet Le-Mans-Ultimate-Daten (Shared Memory, nur lesend) für spätere
  Auswertung auf; Statusanzeige, stündliche Dateien, absturzsicher.
- Auswertung einer Aufnahme (`pruefen` oder Datei auf die exe ziehen): Endstand, Runden, VE, Boxenstopps.
- ADR-002 (Aufnahmeformat), Anleitung `docs/anleitung-aufnahme.md`.

### Geändert
- exe enthält jetzt die Versionsnummer korrekt (Metadaten werden mitgepackt).

## [0.0.1] – 2026-11-12
### Hinzugefügt
- Projektgerüst (Python 3.12, PySide6), Ordnerstruktur für Adapter, Modell, Kern, Strategie, Overlays, Recorder.
- Leere App mit Statusfenster, `--version` und `--quit-after`.
- CI: ruff + pytest auf Ubuntu und Windows.
- Release-Workflow: Windows-`.exe` per PyInstaller, Release wird bei neuer Versionsnummer automatisch angelegt.
- ADR-001 (Architektur), STATUS.md, GPLv3-Lizenz.
