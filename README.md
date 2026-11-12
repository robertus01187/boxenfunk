# Boxenfunk

Kostenloses Sim-Racing-Overlay für **Le Mans Ultimate** und **iRacing** mit Standings, Relative,
Sprit-/VE-Rechner und Strategie-Rechner (Undercut vs. Normal, Rejoin-Prognose, Verkehrslage).

> Status: **v0.0.1 – Projektgerüst.** Die App zeigt bisher nur ein Statusfenster.
> Aktueller Stand: [docs/STATUS.md](docs/STATUS.md)

## Installation (Windows)

1. Unter [Releases](../../releases) die neueste `Boxenfunk.exe` herunterladen.
2. Starten. Windows SmartScreen meldet evtl. „Unbekannter Herausgeber“ → „Weitere Informationen“ → „Trotzdem ausführen“ (die exe ist nicht signiert).
3. Das Spiel im Modus **Randlos/Borderless** laufen lassen, sonst sind Overlays nicht sichtbar.

## Entwicklung

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest            # unter Linux ohne Display: QT_QPA_PLATFORM=offscreen pytest
ruff check .
python -m boxenfunk.app
```

Neue Version: Versionsnummer in `pyproject.toml` erhöhen und nach `main` pushen → GitHub Actions baut die `.exe` und legt das Release `vX.Y.Z` an.

Architektur: [docs/adr/001-architektur.md](docs/adr/001-architektur.md)

## Datenzugriff

Nur **lesend** über die offiziellen Schnittstellen (iRacing SDK, LMU Shared Memory). Kein Eingriff ins
Spiel, keine Online-Dienste.

## Lizenz

GPL-3.0-or-later, siehe [LICENSE](LICENSE). Teile des LMU-Datenzugriffs orientieren sich an
[TinyPedal](https://github.com/TinyPedal/TinyPedal) (GPLv3).
