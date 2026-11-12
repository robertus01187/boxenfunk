# ADR-002: Recorder und Aufnahmeformat (LMU)

- Status: angenommen, mit R0 am echten Spiel geprüft (2026-11-12)
- Datum: 2026-11-12

## Kontext

Für T2–T6 brauchen wir echte Renndaten (R0 Practice, R1 8h Bahrain). Claude kann LMU nicht
starten; der Nutzer zeichnet auf und lädt hoch. Die Aufnahme muss ein 8h-Rennen überstehen,
darf das Spiel nicht stören und muss auch nach einem Absturz lesbar sein.

## Entscheidung

1. **Quelle:** nur der eingebaute LMU-Shared-Memory `LMU_Data`, nur lesend. Keine REST-Abfragen
   (kein MFD-Flackern, TinyPedal #116). Strukturen 1:1 aus `pyLMUSharedMemory` (MIT, via
   TinyPedal, Commit e9b71b6) in `adapters/lmu/lmu_data.py`. Größe `LMUObjectOut` = 324 820 Byte.
2. **Konsistenz** wie TinyPedal: Kopie nur, wenn `SME_UPDATE_SCORING/TELEMETRY` gesetzt und
   `mNumVehicles == activeVehicles`. Sicherheitsnetz: nach 10 Fehlversuchen in Folge wird trotzdem
   kopiert (Zähler `forced` in der Statusanzeige), damit eine Aufnahme nie leer bleibt.
3. **Takt 5 Hz.** Telemetrie wird per `mID` dem Scoring-Eintrag zugeordnet (Indizes können abweichen).
4. **Format `.jsonl.gz`**, Version 1: erste Zeile = Kopf (`typ`, `format`, `recorder`, `gameVersion`,
   `struct_sizes`, `start`, `teil`), danach eine Zeile pro Messpunkt mit **nur geänderten Feldern**
   (`g` generic, `i` scoringInfo, `tel` Telemetrie-Kopf, `c` Autos nach mID mit `s`/`v`, `x` entfernte
   Autos). Alle 60 s ein **Keyframe** (`k=1`, vollständig). Kommazahlen gerundet (|x|<10: 6 Stellen,
   sonst 3). NaN/Inf → `null`. Zeilen nur, wenn das Spiel läuft (Spielzeit ändert sich).
5. **Feldauswahl:** Scoring aller Autos fast vollständig; Telemetrie eigenes Auto fast vollständig
   inkl. Reifen (ohne Fahrwerks-Rohdaten); Gegner-Telemetrie nur Energie/Sprit/Reifen/Status.
   Datenschutz: keine Steam-IDs, keine Server-IP, keine Windows-Pfade.
6. **Rohkopie** alle 5 min (`*.roh.gz`, anonymisiert), um bei falsch verstandener Struktur neu
   auswerten zu können.
7. **Rotation** jede Stunde (`<prefix>_<start>_teilNN`), **Durchspülen** alle 5 s (gzip sync flush):
   bei Absturz gehen max. ~5 s verloren, `files.read_lines()` liest abgeschnittene Dateien.
8. **Auswertung** `Boxenfunk-Recorder pruefen <Datei|Ordner>` (`recorder/analyse.py`): Sessions,
   Endstand gesamt/Klasse, eigene Runden mit VE-/Sprit-Verbrauch, Boxenstopps, VE-Einheit.

## Messwerte (synthetisch, 60 Autos)

- ~3,4 ms Rechenzeit pro Messpunkt (≈ 2 % eines Kerns bei 5 Hz).
- ~2,4 MB pro 10 min → ~115 MB für 8 h. Echte Daten haben mehr wechselnde Werte; erwartet 150–400 MB.

## Offene Prüfpunkte (mit R0/R1 zu klären)

| Punkt | Annahme (aus pyLMUSharedMemory/TinyPedal) | Status |
|---|---|---|
| `mVirtualEnergy` (Telemetrie) | Anteil 0–1 | ✅ R0: 1,0 voll, GT3 ≈ 0,040/Runde |
| VE der Gegner im Shared Memory | in Telemetrie aller Autos vorhanden | ✅ R0 online: bei allen Gegnern gefüllt |
| `mFuelFraction` (Scoring) | 0–255 = 0–100 % | ❌ R0 online: immer 0 → nicht nutzbar, Sprit/VE aus Telemetrie |
| Konsistenzprüfung greift | kaum Lücken | ✅ R0: 6864 Messpunkte in 23 min, Median-Abstand 0,20 s |
| Ungültige Runden | `mLapInvalidated` | ❌ immer 0. Stattdessen: `mLastLapTime = -1` für ungültige Runde; `mCountLapFlag` fällt im Lauf der Runde von 2 auf 1; `mTrackLimitsSteps` steigt |
| Max. VE in Joule, Nachfüllmenge | nur über REST → bewusst nicht aufgezeichnet | später (T5) |

## Ergebnis R0 (2026-11-12, Online-Practice Bahrain, Spielversion 14200)

- 25 Autos (7 Hypercar, 18 GT3), Wertung inkl. Klassenplatz vollständig rekonstruierbar.
- Eigenes Auto Porsche 911 GT3 R: ≈ 4,0 % VE und 3,35 l Sprit pro Runde; Tank 117 l (`mFuelCapacity`).
- Stopp: VE 76,5 % → 100 %, Boxengasse ≈ 37 s. Ziellinie liegt in der Boxengasse: Rundenzähler
  springt während des Stopps, Nachfüllen zählt zur Folgerunde.
- `mVehicleClass` in der Telemetrie ist eine Zahl (GT3 = 6), Klassenname steht im Scoring.
- Beim Start aus der Garage steht `mFuel` kurz auf 1,0 (Platzhalter) → erste Runde für Verbrauch ignorieren.

## Konsequenzen

- + Kleine Dateien, trotzdem nahezu vollständige Daten; jede Datei ab Keyframe einzeln lesbar.
- + Rohkopien als Rückversicherung gegen Strukturfehler.
- − Delta-Format braucht den Decoder (`recorder/delta.py`) zum Lesen; der ReplayAdapter (T2) baut darauf auf.
- − Ändert ein LMU-Update die Struktur, muss `lmu_data.py` nachgezogen werden (Kopf enthält `gameVersion` + Strukturgrößen).
