# Anleitung: Overlay-Prototyp in Le Mans Ultimate ausprobieren

Ab Version 0.3.0 zeigt `Boxenfunk.exe` die ersten Overlays live über LMU:
**Standings, Relative, Delta, Inputs und VE & Sprit**. Das ist ein Prototyp: Aussehen nach den
Entwürfen aus dem Design-Thread, aber noch ohne Einstellungsfenster je Widget, ohne Taste zum
Ein-/Ausblenden und nur für LMU.

## Einmalig vorbereiten

1. Auf der [Release-Seite](https://github.com/robertus01187/boxenfunk/releases/latest) die Datei
   **`Boxenfunk.exe`** herunterladen und in deinen Boxenfunk-Ordner legen (z. B. `C:\Boxenfunk\`).
2. Herstellerlogos (optional): den Ordner **`Boxenfunk-Logos`** (bekommst du im Projekt-Chat als ZIP)
   direkt neben die exe legen. Ohne Logos stehen dort Kürzel wie „POR“ oder „BMW“.
3. In LMU muss **„Enable Plugins“** an sein (wie beim Recorder, siehe `anleitung-aufnahme.md`).
4. In LMU unter **Einstellungen → Grafik → Anzeigemodus** „**Rahmenloses Fenster**“ (Borderless)
   wählen. Im echten Vollbild liegen die Overlays hinter dem Spiel.

## Ausprobieren

1. `Boxenfunk.exe` starten (Windows-Warnung: „Weitere Informationen“ → „Trotzdem ausführen“).
   Es öffnet sich das kleine Boxenfunk-Fenster mit „Warte auf Le Mans Ultimate …“.
2. LMU starten und auf die Strecke fahren. Sobald du im Auto sitzt, erscheinen die Overlays und im
   Boxenfunk-Fenster steht „LMU verbunden“.
3. **Verschieben:** Im Boxenfunk-Fenster auf **„Overlays verschieben“** klicken. Die Overlays
   bekommen einen gelben gestrichelten Rahmen und lassen sich mit der Maus ziehen. Danach
   **„Fertig – Positionen festsetzen“** klicken. Die Positionen werden gespeichert.
   Tipp: Zum Verschieben im Spiel kurz mit Alt+Tab zum Boxenfunk-Fenster wechseln.
4. **Größe:** S, M, L oder XL im Boxenfunk-Fenster.
5. **Einzelne Widgets aus:** Haken im Boxenfunk-Fenster entfernen.
6. **Beenden:** Boxenfunk-Fenster schließen.

## Was die Widgets zeigen

- **Standings:** je Klasse die Spitze, in deiner Klasse zusätzlich die Autos um dich herum.
  Spalten: Klassenplatz, gewonnene/verlorene Plätze seit dem Start, Startnummer, Fahrer, Marke,
  Abstand zur Klassenspitze (GAP), zum Auto davor (INT), letzte Runde (lila Strich = schnellste der
  Klasse, grün = eigene Bestzeit), Reifen, VE in %, Box-Status (BOX = Stopp angefordert, PIT = in der
  Box, sonst Runden seit dem letzten Stopp), Anzahl Stopps, Trend: Rundenzeit-Unterschied der letzten
  3 Runden zu dir (grün = du warst schneller, nur deine Klasse).
- **Relative:** die 3 Autos vor und hinter dir auf der Strecke, Abstand in Sekunden. Rot = liegt
  Runden vor dir, blau = liegt Runden hinter dir (überrundet), weiß = gleiche Runde.
- **Delta:** Abstand zu deiner Bestzeit in dieser Session, Pfeil = gewinnst/verlierst du gerade,
  darunter die geschätzte Rundenzeit.
- **Inputs:** Gas (grün) und Bremse (rot, gelb wenn ABS eingreift) der letzten 8 Sekunden, Balken,
  Gang, Tempo, Lenkrad. Leisten links: ABS (gelb) und TC (blau) leuchten, wenn sie eingreifen.
- **VE & Sprit:** Stand und Restrunden (Durchschnitt der letzten 5 sauberen Runden), der knappere
  Wert gelb markiert. Kasten „+1 Runde“: wie viel du pro Runde verbrauchen darfst, um eine Runde
  länger zu fahren, und wie viel du dafür sparen musst.

## Was ich wissen möchte

- Erscheinen die Overlays über LMU und bleibt das Spiel flüssig?
- Klickt man im Rennen durch die Overlays hindurch (Maus ins Spiel)?
- Stimmen Plätze und Abstände ungefähr mit der Anzeige im Spiel oder TinyPedal überein?
- Was stört am Aussehen oder fehlt dir zuerst?

## Für die Entwicklung (nicht nötig zum Ausprobieren)

Ohne Spiel lässt sich eine Aufnahme abspielen:
`Boxenfunk.exe --abspielen <Aufnahme-Ordner> --ab-rennen --tempo 4`
