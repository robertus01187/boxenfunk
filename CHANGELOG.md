# Changelog

Format nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/), Versionierung nach SemVer.

## [0.3.1] – 2026-11-14
### Behoben (nach Roberts erstem Test in LMU)
- Relative: Abstände werden jetzt gemessen (wann war das andere Auto an meiner Stelle) statt aus
  Streckenabstand × Rundenzeit geschätzt. Abgleich mit den Spielwerten (Bahrain-Aufnahme):
  Mitte 0,02 s, 9 von 10 Werten unter 0,15 s daneben (vorher bis 1 s und mehr).
- Input-Graph und Delta ruckelten (20 Bilder/s, ganze Datenkopie pro Bild): eigener schneller Weg,
  60-mal pro Sekunde nur die eigenen Eingaben direkt aus dem Spielspeicher.
- Standings: Platz-Spalte breiter (rutschte in die Platzgewinne), gewonnene Plätze ab dem echten
  Startplatz in der Klasse (auch wenn Boxenfunk erst im Rennen gestartet wird), grüne Bestzeit-Linie
  nicht mehr in Runde 1, Trend-Spalten wachsen von links (1, 2, dann 3 Runden), „–“ für Runden ohne
  gültige Zeit.

### Hinzugefügt
- Knopf „Nach Update suchen“: lädt die neueste Boxenfunk.exe von GitHub, tauscht sie aus und
  startet neu; Einstellungen bleiben. Beim Start wird leise nach einer neuen Version gesucht.
- Abgleich-Werkzeug `python -m boxenfunk.core.abgleich <Aufnahme>`: vergleicht Relative- und
  Standings-Abstände mit den Werten, die LMU selbst berechnet.

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
