# Changelog

Format nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/), Versionierung nach SemVer.

## [0.3.0] – 2026-11-14
### Hinzugefügt
- Overlay-Prototyp für Le Mans Ultimate in `Boxenfunk.exe`: Standings, Relative, Delta, Inputs,
  VE & Sprit live über dem Spiel (durchsichtig, im Rennen klickt man hindurch). Startfenster mit
  Widgets an/aus, Größe S–XL, „Overlays verschieben“ (Positionen werden gespeichert), Logo-Ordner.
- Datenschicht (Teil von T2): gemeinsames Datenmodell `RaceState`, LMU-Übersetzer (live und aus
  Aufnahme gleich), Verlauf `SessionTracker` (Runden, Trend, Startplätze, VE-/Sprit-Verbrauch),
  Wiedergabe von Aufnahmen (`--abspielen`, `--tempo`, `--ab-rennen`).
- Schrift Exo 2 (SIL Open Font License) im Programm enthalten.
- Anleitung `docs/anleitung-prototyp.md`.

## [0.2.1] – 2026-11-13
### Geändert
- LMU-Recorder heißt jetzt `Boxenfunk-LMU-Recorder.exe` (vorher `Boxenfunk-Recorder.exe`), damit er
  neben dem iRacing-Recorder eindeutig ist. Funktion unverändert; Aufnahmen landen weiter in
  `Boxenfunk-Aufnahmen`.

## [0.2.0] – 2026-11-13
### Hinzugefügt
- `Boxenfunk-iRacing-Recorder.exe`: zeichnet iRacing-Daten (iRacing SDK über `pyirsdk`, nur lesend) auf:
  alle Autos mit Position, Abstand, Rundenzeiten, Box-Status, Klasse, Auto/Marke, dazu Session-Infos,
  Wetter und eigenes Auto. Gleiches Dateiformat wie der LMU-Recorder, eigener Ordner
  `Boxenfunk-Aufnahmen-iRacing`.
- Auswertung einer iRacing-Aufnahme (`pruefen` oder Datei auf die exe ziehen): Endstand je Klasse,
  Rundenzeiten aller Autos, Boxenbesuche, eigene Runden mit Sprit.
- Anleitung `docs/anleitung-iracing.md`.

### Unverändert
- LMU-Recorder (`Boxenfunk-Recorder.exe`): kein Code geändert.

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
