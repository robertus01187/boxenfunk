# Anleitung: Rennen aufzeichnen mit dem Boxenfunk-LMU-Recorder

Der Recorder liest nur mit, was Le Mans Ultimate (LMU) ohnehin für Overlays bereitstellt.
Er verändert nichts am Spiel und hat keinen Einfluss auf dein Rennen.

> Früher hieß die Datei `Boxenfunk-Recorder.exe`. Hast du die schon, funktioniert sie genauso weiter.

## Einmalig vorbereiten

1. **Herunterladen:** Auf der [Release-Seite](https://github.com/robertus01187/boxenfunk/releases/latest)
   die Datei **`Boxenfunk-LMU-Recorder.exe`** herunterladen.
2. Am besten in einen eigenen Ordner legen, z. B. `C:\Boxenfunk\`. Die Aufnahmen landen später
   in einem Unterordner **`Boxenfunk-Aufnahmen`** direkt daneben.
3. **In LMU die Datenschnittstelle einschalten:** Im Spiel **Einstellungen → Gameplay** öffnen und
   **„Enable Plugins“** auf **An** stellen. (Wenn TinyPedal bei dir in LMU funktioniert, ist das
   schon an.) Danach LMU einmal neu starten.

## Aufnehmen

1. `Boxenfunk-LMU-Recorder.exe` doppelklicken. Beim ersten Mal warnt Windows evtl. („Der Computer wurde
   durch Windows geschützt“): **„Weitere Informationen“ → „Trotzdem ausführen“**.
2. Ein schwarzes Fenster geht auf. Reihenfolge egal: Recorder vor oder nach LMU starten.
3. Sobald du auf der Strecke bist, erscheint **„Verbunden … Aufnahme läuft“** und alle 10 Sekunden
   eine Zeile wie
   `Strecke: Bahrain … | 42 Autos | Du: P12 gesamt, P5 in GT3, Runde 7 | VE 63,2 % | Datei 3,1 MB`
4. Fenster einfach offen lassen (darf hinter dem Spiel liegen). TinyPedal kann parallel laufen.
5. **Beenden:** Nach dem Rennen das Fenster schließen (oder Strg+C drücken).

Steht dort länger nur **„Warte auf Le Mans Ultimate …“**, obwohl du fährst: „Enable Plugins“
prüfen (siehe oben) und LMU neu starten.

## Dateien schicken

- Im Ordner `Boxenfunk-Aufnahmen` liegen Dateien wie `LMU_2026-11-14_13-00-05_teil01.jsonl.gz`
  (eine pro Stunde) und dazu `… .roh.gz` (Sicherheitskopien). **Bitte alle schicken.**
- Kurzer Test (5–10 Runden): wenige MB, direkt im Projekt-Chat hochladen.
- 8h-Rennen: einige 100 MB. Den ganzen Ordner z. B. in Google Drive oder OneDrive hochladen und den
  Freigabe-Link schicken.

## Selbst nachschauen (optional)

Eine Aufnahmedatei mit der Maus **auf `Boxenfunk-LMU-Recorder.exe` ziehen**. Dann zeigt der Recorder eine
Zusammenfassung: Endstand, deine Runden mit VE-Verbrauch und deine Boxenstopps.
