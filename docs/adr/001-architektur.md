# ADR-001: Architektur mit Sim-Adaptern, gemeinsamem RaceState und Replay

- Status: angenommen
- Datum: 2026-11-12

## Kontext

Boxenfunk soll LMU und iRacing unterstützen. Entwickelt und getestet wird überwiegend in einer
Linux-Umgebung ohne Spiele. Live-Daten gibt es nur unter Windows mit laufendem Spiel.

## Entscheidung

1. **Python 3.12 + PySide6 (Qt).** Gleiches Ökosystem wie TinyPedal, Logik unter Linux testbar.
2. **Sim-Adapter** (`adapters/`) lesen die Rohdaten (iRacing SDK, `LMU_Data` Shared Memory, optional
   gedrosselte LMU-REST-API) und übersetzen sie in ein **gemeinsames Datenmodell `RaceState`**
   (`model/`), ca. 10 Hz.
3. Alles dahinter (Analyse-Kern `core/`, Strategie `strategy/`, Overlays `overlay/`) kennt **nur
   `RaceState`**, keine sim-spezifischen Felder.
4. Ein **`ReplayAdapter`** spielt Aufzeichnungen (`.jsonl.gz`, vom Recorder) ab und liefert dasselbe
   `RaceState`. Damit sind Replay-Tests gegen echte Rennen in der CI möglich.
5. Energie wird abstrakt modelliert („Energie-Ressource“): VE in LMU-Hypercar/GT3, Sprit sonst.
6. Datenzugriff ist **nur lesend**; REST nur gedrosselt und optional (MFD-Flackern, TinyPedal #116).
7. **Lizenz GPL-3.0-or-later**, damit TinyPedal-Code (GPLv3) übernommen werden darf.
8. Die Windows-`.exe` wird mit **PyInstaller auf GitHub Actions** (`windows-latest`) gebaut.

## Konsequenzen

- + Logik einmal schreiben, mit synthetischen Daten und Recordings testen.
- + Neue Sims brauchen nur einen neuen Adapter.
- − `RaceState` muss den kleinsten gemeinsamen Nenner treffen; sim-exklusive Daten (z. B.
  Gegner-VE in LMU) sind optionale Felder, die Logik muss ohne sie auskommen.
- − Live-Verhalten (Overlay-Fenster, Hotkeys, Fokus) lässt sich nur durch den Nutzer im Spiel testen.
