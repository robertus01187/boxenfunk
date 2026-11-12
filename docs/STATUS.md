# Projektstatus Boxenfunk

> Einzige Wahrheitsquelle zwischen Threads. Am Ende jedes Threads aktualisieren.

**Stand:** 2026-11-12 · **Version:** 0.0.1 · **Letzter Thread:** T0 Kickoff & Setup

## Erledigt
- T0: Repo-Gerüst, `pyproject.toml`, Ordnerstruktur, leere Qt-App (Statusfenster, `--version`,
  `--quit-after`), CI (ruff + pytest auf ubuntu + windows), Release-Workflow (PyInstaller-exe bei Tag
  `v*`, mit Smoke-Test der exe), ADR-001, GPLv3-Lizenz.

## Entscheidungen
| ID | Entscheidung | Status |
|---|---|---|
| D1 | Python 3.12 + PySide6 | ✅ |
| D2 | exe-Build über GitHub Actions | ✅ |
| D3 | Lizenz GPL-3.0-or-later | ✅ (vorläufig, Bestätigung Nutzer ausstehend) |
| D4 | Repo öffentlich | ⏳ Nutzer |

## Nächster Schritt
- **T1 Recorder & Datenverifikation (dringend, vor dem Wochenende).** Ziel: R0 (LMU Practice) aufnehmen,
  VE-Felder/Einheiten verifizieren (ADR-002).

## Offene Punkte
- Name „Boxenfunk“ behalten?
- Hotkey/Lenkradknopf zum Ein-/Ausblenden
- 8h-Rennen allein oder mit Fahrerwechseln?

## Technische Schulden
- exe ist nicht signiert (SmartScreen-Warnung).
- `--onefile` startet etwas langsamer (Entpacken); ggf. später `--onedir`.
