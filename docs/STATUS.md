# Projektstatus Boxenfunk

> Einzige Wahrheitsquelle zwischen Threads. Am Ende jedes Threads aktualisieren.

**Stand:** 2026-11-14 · **Version:** 0.3.2 (Prototyp + eingebauter Recorder-Knopf) · **Letzter Thread:** Overlay-Prototyp mit Aufnahmen

## Erledigt
- T0 (abgenommen: exe startet beim Nutzer, Fenster erscheint): Repo-Gerüst, `pyproject.toml`, Ordnerstruktur, leere Qt-App (Statusfenster, `--version`,
  `--quit-after`), CI (ruff + pytest auf ubuntu + windows), Release-Workflow (PyInstaller-exe; neue Version in
  `pyproject.toml` + Push nach main → Release `vX.Y.Z` wird automatisch angelegt, inkl. Smoke-Test der exe), ADR-001, GPLv3-Lizenz.

- T1 (Umsetzung): `Boxenfunk-LMU-Recorder.exe` (Konsole) zeichnet LMU-Shared-Memory mit 5 Hz als
  `.jsonl.gz` auf (nur Änderungen, Keyframe/60 s, Rotation/Stunde, Rohkopie/5 min, absturzsicher).
  Auswertung `Boxenfunk-LMU-Recorder pruefen <Datei|Ordner>` rekonstruiert Standings, eigene Runden/VE,
  Boxenstopps. Format + offene Prüfpunkte: ADR-002. Nutzer-Anleitung: `docs/anleitung-aufnahme.md`.
  Getestet mit simuliertem Multiclass-Rennen (tests/unit/fake_lmu.py), echte Daten fehlen noch.

- iRacing-Recorder (v0.2.0, Branch `claude/project-thread-04uhgp`): `Boxenfunk-iRacing-Recorder.exe`,
  eigenes Programm + eigener Ordner, gleiches Format (ADR-002 Nachtrag), Auswertung per `pruefen`.
  Getestet mit simuliertem Rennen, auch über den echten `pyirsdk`-Lesepfad (Speicherabbild). Anleitung:
  `docs/anleitung-iracing.md`. Echte Aufnahme fehlt noch.

- Overlay-Prototyp (v0.3.0, Branch `claude/project-thread-zmgetj`): `Boxenfunk.exe` zeigt Standings,
  Relative, Delta, Inputs, VE & Sprit live über LMU (Qt, rahmenlose durchklickbare Fenster,
  `overlay/`). Vorgezogener Teil von T2: `model/race_state.py`, `adapters/lmu/translate.py`,
  `adapters/sources.py` (Live + `ReplaySource`), `core/tracker.py`, `core/views.py`.
  Geprüft mit der LMU-Aufnahme eines 1h-Rennens (Bahrain, 38 Autos, Hyper+GT3): VE-Verbrauch je
  Runde stimmt mit der Recorder-Auswertung überein (5,37 %), Abstände über `mTimeBehindNext`.
  Anleitung `docs/anleitung-prototyp.md`. v0.3.0 von Robert live getestet (14.11.): VE/Sprit,
  Delta, Inputs ok; Relative ungenau, Input-Graph ruckelig, Standings-Format → behoben in 0.3.1
  (`core/track_timing.py`, schneller Eingabe-Weg, Update-Knopf `updater.py`, Abgleich
  `core/abgleich.py`). Prüfweg: Robert lässt beim Testen den LMU-Recorder mitlaufen, Abgleich
  läuft dann auf der Aufnahme.

## Entscheidungen
| ID | Entscheidung | Status |
|---|---|---|
| D1 | Python 3.12 + PySide6 | ✅ |
| D2 | exe-Build über GitHub Actions | ✅ |
| D3 | Lizenz GPL-3.0-or-later | ✅ (Nutzer bestätigt 2026-11-12) |
| D4 | Repo öffentlich | ✅ (Nutzer hat es öffentlich angelegt) |

## Nächster Schritt
- **T1-Abnahme:** Nutzer nimmt R0 (Practice, 5–10 Runden) auf und lädt sie hoch → mit
  `pruefen --json` auswerten, offene Prüfpunkte in ADR-002 abhaken (VE-Einheit, Gegner-VE, `forced`).
- R1 (8h Bahrain, 14./15.11.2026) aufnehmen.
- Danach T2 (Adapter + RaceState; ReplayAdapter baut auf `recorder/delta.py` + `files.read_lines` auf).

## Offene Punkte
- Name „Boxenfunk“ behalten?
- Hotkey/Lenkradknopf zum Ein-/Ausblenden
- 8h-Rennen allein oder mit Fahrerwechseln?

## Hinweise für Claude
- Diese Session darf keine Tags pushen und keine Releases per API anlegen → Releases entstehen nur über release.yml beim Push nach main.
- Nutzer ist kein Programmierer: einfache Sprache, keine Fachbegriffe.

## Technische Schulden
- Prototyp: keine Einstellungsfenster je Widget, kein Hotkey, keine Presets je Spiel, nur LMU.
  Relative-Abstand aus Streckenposition × geschätzter Rundenzeit (einfach, ggf. später genauer).
  Live-Quelle baut pro Abfrage den kompletten Snapshot (ca. 3 ms bei 20 Hz), später gezielter lesen.
- iRacing-Recorder: noch keine echte Aufnahme geprüft.
- Recorder-Fenster: Status als neue Zeile alle 10 s (kein schönes Live-Feld).
- exe ist nicht signiert (SmartScreen-Warnung).
- `--onefile` startet etwas langsamer (Entpacken); ggf. später `--onedir`.
