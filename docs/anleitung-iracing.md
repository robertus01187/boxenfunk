# Anleitung: iRacing-Rennen aufzeichnen

Der iRacing-Recorder liest nur mit, was iRacing ohnehin für Overlays bereitstellt (so wie es auch
andere Overlay-Programme tun). Er verändert nichts am Spiel und hat keinen Einfluss auf dein Rennen.
In iRacing musst du **nichts einstellen**.

Der LMU-Recorder (`Boxenfunk-LMU-Recorder.exe`) bleibt davon unberührt. Für iRacing gibt es ein
eigenes Programm.

## Einmalig

1. Auf der [Release-Seite](https://github.com/robertus01187/boxenfunk/releases/latest) die Datei
   **`Boxenfunk-iRacing-Recorder.exe`** herunterladen.
2. In denselben Ordner legen wie den LMU-Recorder, z. B. `C:\Boxenfunk\`.

## Aufnehmen

1. `Boxenfunk-iRacing-Recorder.exe` doppelklicken. Falls Windows warnt: **„Weitere Informationen“ →
   „Trotzdem ausführen“**.
2. Ein schwarzes Fenster geht auf. Reihenfolge egal: vor oder nach iRacing starten.
3. Sobald du in einer Session bist (Training, Quali oder Rennen), erscheint
   **„Verbunden … Aufnahme läuft“** und alle 10 Sekunden eine Zeile wie
   `Strecke: Spa … | Rennen | 24 Autos | Du: P5 gesamt, P3 in GT3, 7 Runden fertig | Sprit 45,2 l | Datei 3,1 MB`
4. Fenster einfach offen lassen (darf hinter dem Spiel liegen). Andere Overlays können parallel laufen.
5. **Beenden:** Nach dem Rennen das Fenster schließen.

Aufgezeichnet werden alle Autos: Positionen, Abstände, Rundenzeiten, Boxenbesuche, Klassen und
Autos/Marken, dazu dein Sprit und Wetter. Rennen ohne Boxenstopp sind völlig in Ordnung.

## Dateien schicken

- Die Aufnahmen landen im Ordner **`Boxenfunk-Aufnahmen-iRacing`** neben der exe (getrennt von den
  LMU-Aufnahmen). Dateien wie `iRacing_2026-11-13_20-00-05_teil01.jsonl.gz` (eine pro Stunde) und
  `… .roh.gz` (Sicherheitskopien). **Bitte alle schicken.**
- Ein normales iRacing-Rennen (20–60 Minuten) ergibt nur einige MB: einfach im Projekt-Chat hochladen.

## Selbst nachschauen (optional)

Eine Aufnahmedatei (oder den ganzen Ordner) mit der Maus **auf `Boxenfunk-iRacing-Recorder.exe`
ziehen**. Dann siehst du den Endstand je Klasse mit bester Runde und Boxenbesuchen sowie deine
eigenen Runden mit Spritverbrauch.
