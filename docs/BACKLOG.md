# Wunschliste (Backlog) Boxenfunk

> Hier landen alle Funktionswünsche: von Robert und Vorschläge von Claude.
> Gepflegt im Thread „Funktionswünsche sammeln und bewerten“. Stand: 2026-11-12 (Nachtrag: Standings-Vorlage aus dem Design-Thread)

## So läuft ein Wunsch durch

1. **Wunsch nennen:** Robert beschreibt im Thread, was er sich wünscht (gern mit Screenshot oder Beispiel aus einer anderen App).
2. **Prüfen:** Claude klärt, ob das Spiel die nötigen Daten liefert (LMU und iRacing getrennt), wie viel Arbeit es ist und was es kostet (z. B. Rechenlast, Risiko).
3. **Einordnen:** Der Wunsch bekommt eine Phase (T2 bis T7 oder „nach 1.0“) und eine Wichtigkeit.
4. **Robert entscheidet:** angenommen, später oder verworfen.
5. **Umsetzen:** Wenn die Phase dran ist, holt sich der zuständige Thread die angenommenen Wünsche aus dieser Liste.

## Zeichen

| Status | Bedeutung |
|---|---|
| 💡 | Idee, wartet auf Roberts Entscheidung |
| ✅ | angenommen und einer Phase zugeordnet |
| 🔨 | wird gerade gebaut |
| ✔️ | fertig |
| ⏸️ | später / zurückgestellt |
| ❌ | verworfen |

**Machbarkeit:** ja · teilweise · nein · offen (muss mit Aufnahme geprüft werden)
**Aufwand:** klein (≈ 1 Tag) · mittel (einige Tage) · groß (eigene Phase)

## Phasen (Kurzfassung)

| Phase | Inhalt |
|---|---|
| T2 | Datenschicht: Spieldaten einheitlich lesen (LMU + iRacing) |
| T3 | Overlay-Grundgerüst: Fenster, Verschieben, Hotkey |
| T4 | Standings und Relative |
| T5 | Sprit-/VE-Rechner |
| T6 | Strategie-Rechner (Undercut/Normal, Wiedereinstieg, Verkehr) |
| T7 | Einstellungen, Feinschliff, Version 1.0 |
| nach 1.0 | Erweiterungen |

## Wünsche

| Nr. | Wunsch | Von | LMU | iRacing | Aufwand | Phase | Status |
|---|---|---|---|---|---|---|---|
| W-01 | Fahrerwechsel und Double-Stints im Strategie-Rechner berücksichtigen, möglichst automatisch erkennen | Robert | ja | ja | mittel | T5/T6 | ✅ |
| W-02 | Spar-Ziel: „Spare X % VE pro Runde, dann sparst du einen Stopp“ | Claude | ja | ja | klein | T5 | ✅ |
| W-03 | Warnung „schnellere Klasse kommt von hinten“ → aufgegangen in W-07 (blaue Flagge mit Meterangabe) | Claude | ja | ja | klein | T4 | ✅ |
| W-04 | Gegner-Energie in Standings: VE-Stand und „muss noch X-mal an die Box“ | Claude | ja | nein | klein | T4/T6 | ✅ |
| W-05 | Stint-Übersicht: Runden, Ø-Zeit und Verbrauch je Stint und je Fahrer | Claude | ja | ja | mittel | nach 1.0 | ⏸️ |
| W-06 | Session-Leiste: Restzeit **und bereits gefahrene Zeit**, Runde, geschätzte Runden bis Rennende, Uhrzeit im Spiel | Claude/Robert | ja | ja | klein | T4 | ✅ |
| W-07 | Flaggen: Gelb im Sektor, Full Course Yellow, Blaue Flagge (schnellere Klasse oder Überrundung). Bei Gelb und Blau einstellbar mit Abstand in Metern: „+120 m“ = vor mir, „−80 m“ = hinter mir | Claude/Robert | ja | ja | mittel | T4/T7 | ✅ |
| W-08 | Wetter: Luft- und Streckentemperatur, Regen, Nässe der Strecke in % (wenn nicht trocken), **Vorhersage mit Regenwahrscheinlichkeit** | Claude/Robert | teilweise | offen | mittel | T7 | ✅ |
| W-09 | Delta-Balken zur eigenen Bestrunde | Claude/Robert | ja | ja | klein | T7 | ✅ |
| W-10 | Reifen: Verschleiß, Temperatur, Druck | Claude | ja | teilweise | mittel | nach 1.0 | ⏸️ |
| W-11 | Radar: Autos direkt neben dir | Claude | ja | teilweise | mittel | nach 1.0 | ⏸️ |
| W-12 | Streckenkarte mit allen Autos | Claude | ja | teilweise | mittel | nach 1.0 | ⏸️ |
| W-13 | Team-Ansicht im Browser für Mitfahrer (Stand, Strategie, Stint-Plan) | Claude | ja | ja | groß | nach 1.0 | ⏸️ |
| W-18 | Einstellungsfenster je Widget: Reiter oben (Allgemein, Kopfzeile, Fahrerzeile, Animation, Hintergrund, Sonstiges) und darunter eine Live-Vorschau mit Beispieldaten (Training/Quali, Rennen, Animation) | Robert | ja | ja | groß | T3 Gerüst, T7 Ausbau | ✅ |
| W-19 | Position und Größe jedes Widgets per Maus direkt auf dem Bildschirm ziehen (nicht im Einstellungsfenster) | Robert | ja | ja | mittel | T3 | ✅ |
| W-20 | Baukasten: Kopfzeile und Fahrerzeile selbst zusammenstellen, Infoblöcke per Ziehen in eine Ablagefläche legen und umsortieren | Robert | ja | ja | groß | T4/T7 | ✅ |
| W-21 | Standings-Aufbau: Anzahl Zeilen oben (Spitze) und um mich herum, je Klasse getrennte Blöcke, eigene Zeile hervorgehoben | Robert | ja | ja | mittel | T4 | ✅ |
| W-22 | Standings-Fahrerzeile: Platz, gewonnene/verlorene Plätze (Pfeil), Startnummer, Name, Hersteller-Logo, Abstand zum Führenden und zum Vordermann, letzte Runde (grün = persönliche Bestzeit, lila = Bestzeit aller), Reifenmischung, Boxenstatus (PIT + Runden seit Stopp), Zahl der Stopps | Robert | ja | ja | mittel | T4 | ✅ |
| W-23 | Lizenz/Safety Rating und iRating mit erwarteter Änderung, Feldstärke (SOF) in der Kopfzeile | Robert | offen | ja | mittel | T4 (iRacing), LMU prüfen | 💡 |
| W-24 | Kopfzeile: Session-Art, Restzeit/Uhrzeit, Runde/geschätzte Rundenzahl, Strafpunkte/Limit (z. B. 28/34; iRacing ja, LMU nur Strafen-Anzahl, prüfen), Feldstärke, Fahrzeug, Luft- und Streckentemperatur, Regen-/Nässe-Anteil | Robert | ja | ja | klein | T4 | ✅ |
| W-25 | Darstellung einstellbar: Schriftart, schmale Schrift, Größe der Kopf- und Fahrerzeilen (XS bis L), Ausrichtung, Farben für Gewinn/Verlust, Deckkraft, abwechselnd helle/dunkle Zeilen, Tönung der eigenen Zeile, „zurücksetzen“-Knopf | Robert | ja | ja | mittel | T3/T7 | ✅ |
| W-26 | Animation bei Platzwechseln, Tempo getrennt für Fahrt und Wiederholung (aus, schnell, normal, langsam) | Robert | ja | ja | mittel | T7 | ✅ |
| W-27 | „Live-Standings“: Positionen laufend auf der Strecke statt nur an der Ziellinie neu sortieren | Robert | ja | ja | klein | T4 | ✅ |
| W-28 | Rundenvergleich rechts in jeder Zeile: Differenz der letzten 3 Rundenzeiten dieses Autos zu meiner jeweiligen Runde, grün = ich war schneller, rot = langsamer (von Robert bestätigt). Neueste Runde rechts, älteste fällt links raus. Eigene Zeile zeigt ∞ | Robert | ja | ja | klein | T4 | ✅ |
| W-29 | Eigene Standings-Ansicht für Training/Quali (nach Bestzeit sortiert, Abstand zur Bestzeit) | Robert | ja | ja | klein | T4 | ✅ |
| W-30 | Spiel automatisch erkennen (LMU oder iRacing) und das passende Overlay-Preset laden. Beide Presets vorher getrennt einstellbar; im Einstellungsfenster werden nur Bausteine angeboten, die das jeweilige Spiel liefern kann (andere ausgegraut mit Hinweis) | Robert | ja | ja | mittel | T2 Erkennung, T3/T7 Presets | ✅ |
| W-31 | Herstellerlogos statt Kürzel: App wird ohne Logos ausgeliefert, lädt sie aus einem Logo-Ordner, den der Nutzer selbst füllt (eine Datei pro Marke); fehlt ein Logo, wird das Kürzel gezeigt. Braucht Zuordnung Fahrzeug → Marke | Design-Thread / Robert | ja | ja | klein | T4 | 💡 |
| W-32 | Sektorzeiten: je Sektor die Zeit, farbig mit +/−-Wert: grün = schneller als meine Bestzeit, rot = langsamer, lila = schnellster Sektor im Feld | Robert | ja | ja | mittel | T4/T7 | ✅ |
| W-14 | Lenkradknopf statt Tastatur zum Ein-/Ausblenden | Projektplan | ja | ja | klein | T7 | ✅ |
| W-15 | Boxenverlust je Strecke lernen und speichern | Projektplan | ja | ja | mittel | T6 | ✅ |
| W-16 | Overcut als dritte Strategie, Safety-Car-/FCY-Modus | Projektplan | ja | ja | mittel | nach 1.0 | ⏸️ |
| W-17 | VR-Anzeige | Projektplan | offen | offen | groß | nach 1.0 | ⏸️ |

## Details

### W-01 Fahrerwechsel und Double-Stints ✅
- **Wunsch (Robert, 12.11.2026):** Die App soll erkennen, ob ein Fahrerwechsel ansteht oder ob doppelt gefahren wird, und das in der Strategie berücksichtigen (8h-Rennen mit 3 Fahrern).
- **Machbarkeit:** LMU meldet den Namen des aktuellen Fahrers für jedes Auto. Wechselt der Name beim Stopp, war es ein Fahrerwechsel. Der Recorder zeichnet das schon auf, die 8h-Aufnahme liefert echte Beispiele. iRacing meldet den Fahrer im Teamrennen ebenfalls.
- **Was die App daraus macht:** Standzeit mit Fahrerwechsel getrennt lernen; anzeigen „nächster Stopp: mit/ohne Wechsel“; Fahrzeit je Fahrer mitzählen (wichtig bei Mindest-/Höchstfahrzeiten).
- **Offen:** Ob der Fahrerwechsel vorher erkennbar ist (z. B. aus dem Boxenmenü) oder erst beim Stopp. Klärt sich mit der 8h-Aufnahme.

### W-02 Spar-Ziel 💡
- Rechnet aus, wie viel Energie pro Runde gespart werden muss, damit ein Stopp wegfällt oder der Stint eine Runde länger hält. Kennt man aus Go Fast und ähnlichen Rechnern.
- Machbar mit denselben Daten wie der Sprit-/VE-Rechner, daher wenig Mehraufwand in T5.

### W-03 Warnung schnellere Klasse 💡
- Für GT3 im Multiclass-Rennen: kleiner Hinweis „Hypercar 2,5 s hinter dir“, auf Wunsch mit Seite (links/rechts nicht sicher, nur Abstand).
- Daten kommen aus der Relative-Berechnung (T4), daher wenig Mehraufwand.

### W-04 Gegner-Energie 💡
- Nur LMU: Das Spiel zeigt den Energiestand aller Autos. Daraus: „Auto vor dir muss in 4 Runden an die Box“. In iRacing gibt es diese Daten nicht.

### W-13 Team-Ansicht für Mitfahrer 💡
- Hintergrund: Der Recorder und die App laufen nur auf Roberts PC. Wenn ein Teamkollege fährt, sieht nur Robert die Strategie. Eine kleine Webseite (im Heimnetz oder übers Internet) könnte den Stand für das Team zeigen, ähnlich „LMU Pitwall“.
- Groß, weil Netzwerk und Sicherheit dazukommen. Erst nach Version 1.0 sinnvoll.

### W-18 bis W-27 Standings-Vorlage (Robert, 12.11.2026, aus dem Design-Thread) ✅
- **Herkunft:** Robert hat sechs Screenshots eines Standings-Einstellungsfensters als Vorlage geschickt. Das Aussehen baut der Design-Thread nach; hier stehen die **Funktionen**, die in den Bildern stecken. Diese Vorlage gilt als Grundlage für **alle** Widgets: jedes bekommt ein solches Einstellungsfenster mit Vorschau.
- **Vorschau (W-18):** Die Vorschau kann mit Ausschnitten aus echten Aufnahmen (R0/R1) laufen, das passt gut zur Replay-Technik aus T2.
- **Position/Größe (W-19):** ausdrücklich per Maus auf dem Bildschirm, nicht im Einstellungsfenster. War für T3 schon geplant.
- **Lizenz/iRating/SOF (W-23):** iRacing liefert das. LMU hat zwar Fahrer- und Sicherheitswertungen, ob sie im Shared Memory stehen, ist offen (eventuell nur über die REST-Schnittstelle). Wenn nicht verfügbar, wird der Block in LMU ausgeblendet.
- **Reifenmischung (W-22):** LMU zeichnet der Recorder für alle Autos auf; ob die Mischung der Gegner stimmt, wird mit R1 geprüft. iRacing liefert sie für alle Autos.
- **Drei farbige Zahlen rechts:** geklärt, siehe W-28. Beide Spiele liefern die letzte Rundenzeit jedes Autos, die App merkt sich die letzten drei.
- **Krone im Fahrer-Reiter:** entfällt (Robert, 12.11.2026).

### W-30 Spiel erkennen und Preset laden (Robert, 12.11.2026) ✅
- **Erkennung:** Die App schaut regelmäßig nach, welche Datenquelle offen ist (LMU-Shared-Memory oder iRacing-Schnittstelle). Das gehört zur Datenschicht (T2) und ist einfach.
- **Presets:** Für jedes Spiel eigene Einstellungen und Positionen der Widgets. Beim Spielwechsel wird automatisch umgeschaltet (T3 Grundlage, T7 Ausbau).
- **Nur Machbares anzeigen:** Jeder Baustein bekommt die Info „gibt es in LMU / iRacing“ (siehe Spalten LMU/iRacing in dieser Liste). Nicht verfügbare Bausteine sind im Preset des jeweiligen Spiels ausgegraut, z. B. Gegner-Energie nur LMU, iRating nur iRacing.

### W-31 Herstellerlogos 💡 (Robert entscheidet noch)
- **Warum ein eigener Ordner:** Die App ist öffentlich (GPL). Echte Markenlogos sind geschützt und dürfen nicht einfach mitverteilt werden. Darum bringt der Nutzer sie selbst mit.
- **Zuordnung:** LMU meldet Fahrzeug- und Klassenname, iRacing den Fahrzeugnamen je Auto. Daraus wird per kleiner Tabelle die Marke (z. B. „Porsche 911 GT3 R“ → Porsche). Unbekannte Autos zeigen das Kürzel.

### Auswahl aus Claudes Vorschlägen (Robert, 12.11.2026)
- Angenommen: W-02, W-03 (in W-07), W-04, W-06, W-07, W-08, W-09, neu W-32. Zurückgestellt (gemerkt, keine Priorität): W-05, W-10, W-11, W-12, W-13.

### W-07 Flaggen mit Meterangabe ✅
- **Blau:** Abstand zum schnelleren Auto hinter mir aus den Streckenpositionen, in beiden Spielen gut machbar.
- **Gelb:** Die Spiele melden nur „Gelb in Sektor X“, nicht die Stelle. Die App sucht darum das langsame oder stehende Auto im Sektor und rechnet den Abstand dazu aus. Klappt meistens; gibt es kein erkennbares Auto, wird nur der Sektor angezeigt.

### W-08 Wetter ✅
- Jetzige Werte (Temperaturen, Regen, Nässe) liefern beide Spiele direkt.
- **Vorhersage:** In LMU nur über die REST-Schnittstelle (wird selten abgefragt, damit das Spielmenü nicht flackert). Für iRacing muss ich noch prüfen, ob es eine Vorhersage gibt; wenn nicht, wird sie dort ausgeblendet.

### W-32 Sektorzeiten ✅
- LMU liefert Sektorzeiten für alle Autos. iRacing liefert keine fertigen Sektorzeiten; die App misst sie selbst über die Position auf der Strecke (Sektorgrenzen stehen in den Session-Infos).
