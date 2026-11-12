# Design-Grundlage für alle Overlays

Stand: 2026-11-12. Vorlage von Robert: Standings-Einstellungsfenster (Screenshots im Design-Thread).
Klickbares Muster: [`standings-muster.html`](standings-muster.html) (im Browser öffnen).

Diese Regeln gelten für **jedes** Widget (Standings, Relative, Sprit/VE, Strategie …).

## 1. Aufbau: jedes Widget hat ein eigenes Einstellungsfenster

- Fenstertitel: `<Widget> — Einstellungen`.
- Oben eine Reihe Reiter. Feste Reiter für alle Widgets, wo sinnvoll:
  `Allgemein · Kopfzeile · <Inhalt> · Animation · Hintergrund · Sonstiges`
  (bei Standings heißt `<Inhalt>` „Fahrerzeile“).
- Unter den Einstellungen immer eine **Live-Vorschau** mit Beispieldaten. Jede Änderung
  wirkt sofort in der Vorschau.
- Vorschau-Modi als kleiner Schalter oben links: `Quali · Rennen · Animation`.
- Der Vorschau-Hintergrund ist ein blaues Rautenmuster = „hier ist später das Spiel zu sehen“
  (zeigt Durchsichtigkeit).
- **Position und Größe** des Widgets werden NICHT im Einstellungsfenster eingestellt, sondern
  später direkt auf dem Bildschirm per Maus (Ziehen) – siehe `docs/BACKLOG.md`.

## 2. Bausteine per Ziehen (Kopfzeile, Spalten)

- Oben eine gestrichelte **Ablage**: Bausteine, die dort liegen, sind ausgeblendet.
- Darunter die aktive Reihe: Reihenfolge = Reihenfolge im Overlay.
- Ziehen zum Umsortieren / Ein- und Ausblenden; Doppelklick schaltet ein/aus.
- Jeder Baustein zeigt beim Drüberfahren, was er bedeutet.

## 3. Farben

| Zweck | Wert |
|---|---|
| Fenster-Hintergrund | `#1b1d21` |
| Bedienelement | `#2c3038`, aktiv `#4a6fb3` |
| Linien | `#3a3f48` |
| Text / gedimmt | `#e9ecf1` / `#9aa3b0` |
| Overlay-Zeile ungerade / gerade | dunkles Blaugrau, Helligkeit 12 % / 17 % (einstellbar) |
| Kopfzeile Overlay | Blaugrau, Helligkeit 8 % (einstellbar) |
| Deckkraft Overlay | 88 % (einstellbar 30–100 %) |
| Eigene Zeile | Petrol `#1e8b96`-Ton + Balken links `#38c6d4` (Stärke einstellbar) |
| Gewinn / Verlust | `#52e05a` / `#ff7a62` (einstellbar) |
| Eigene Bestzeit | Unterstrich grün `#1fbf4a` |
| Schnellste Runde im Feld | Unterstrich lila `#b23cff` |
| Box: lange her / mittel | Rot-Verlauf + Unterstrich `#e2493b` / Gelb-Verlauf + `#d4ae2c` |
| Aktueller Stint | Text gelb `#f1c84b` |
| Lizenz R/D/C/B/A/P/W | `#e8312a` `#ff7a1a` `#ffd21a` `#33c72e` `#1f74ff` `#9a3cff` `#d6d6d6` |
| Reifen Soft/Medium/Hard/Regen | `#ffd21a` `#d8d8d8` `#ff6a4d` `#2fa8ff` (Ring) |

## 4. Schrift und Größen

- Overlay-Schrift: **Exo 2** (Auswahl: Exo 2, Rajdhani, Titillium Web, Barlow Condensed),
  Zahlen immer gleich breit (tabellarische Ziffern), halbfett. Option „Schmal“ = enger Zeichenabstand.
- Bedienoberfläche: Roboto bzw. Systemschrift, Beschriftungen fett.
- Größenstufen XS / S / M / L = 13 / 15 / 17 / 19 px, getrennt für Kopfzeile und Zeilen.
  Zeilenhöhe = Schriftgröße × 1,75.
- Blöcke (Top-Gruppe, Gruppe um mich) haben 4 px Rundung und 6 px Abstand zueinander.

## 5. Animation

- Einstellung getrennt „Im Auto“ und „In der Wiederholung“: Aus / Schnell / Normal / Langsam
  (0 / 0,25 / 0,5 / 0,9 s). Positionswechsel gleiten an den neuen Platz, kurz aufgehellt.

## 6. Standings: Inhalt

Kopfzeile (Bausteine): Sitzung (Q/R) · Zeit gefahren/≈Rest · Runden/≈gesamt · Strafpunkte/Limit ·
SOF · (ausgeblendet: Auto, Luft-, Streckentemperatur, Nässe).

Fahrerzeile (Spalten, Standardreihenfolge): Platz · Plätze ± seit Start · Startnummer · Name ·
Hersteller · Lizenz+Sicherheit / Rating + erwartete Änderung · Abstand Führender · Abstand
Vordermann · Letzte Runde · Reifen · Box-Info · Trend (3 Werte).

Trend = Rundenzeit-Unterschied zu diesem Auto in den letzten 3 Runden, neueste Runde ganz rechts
(die älteste fällt links raus). Grün = ich war so viel schneller, rot = so viel langsamer.
In der eigenen Zeile stehen drei ∞. Gewünscht für LMU und iRacing.

Kein Kronen-Symbol (aus der Vorlage gestrichen, Robert 2026-11-12).

Zeilen: „Zeilen 3 | 5“ = 3 Führende + 5 um mich herum; fehlt ein Platz dazwischen, werden zwei
Blöcke gezeigt. „Andere Klassen 1 | 3“ = gleiches Prinzip für jede weitere Klasse.

Lizenz/Rating: vorerst ausgeblendet (siehe Abschnitt 7).

## 7. Zwei Voreinstellungen: LMU und iRacing

- Jedes Einstellungsfenster hat oben links den Schalter „Voreinstellung für LMU | iRacing“.
  Beide Voreinstellungen werden getrennt eingestellt und gespeichert.
- Boxenfunk erkennt später, welches Spiel läuft, und lädt automatisch die passende Voreinstellung.
- Bausteine, die es im gewählten Spiel nicht gibt, liegen durchgestrichen und blass in der Ablage
  und lassen sich nicht hineinziehen.
- Bekannt (Standings): nur iRacing = Strafpunkte/Limit, SOF, Lizenz/Rating. Alles andere: beide.
  Wird mit echten Aufnahmen weiter geprüft.
- Lizenz/Rating ist laut Robert (2026-11-12) vorerst bei beiden ausgeblendet.

## 8. Relative (Entwurf 2026-11-12)

Muster: Artifact „Boxenfunk Relative“ (Quelle im Projektordner `design/relative-einstellungen.html`;
wegen der Herstellerlogos nicht im Repo).

- Reiter: Allgemein · Kopfzeile · Fußzeile · Animation · Hintergrund · Sonstiges.
- Fahrerzeile fest: Platz · Startnummer · Name · Marke · Abstand (s; − = vor mir, + = hinter mir).
- Einstellbar: Autos vor/hinter mir (Standard 3/3), Autos in der Box zeigen, Kopf-/Fußzeile an/aus,
  Breite, Farben.
- Kopf- und Fußzeile: Infos per Ziehen aus der Ablage, je Spiel eigene Auswahl. Kopfzeile
  linksbündig, Fußzeile über die ganze Breite verteilt (links, Mitte, rechts).
  Standard Kopf: Öl, Wasser, Sprit %. Standard Fuß: Runde, Uhrzeit, Sitzung + Restzeit
  (iRacing zusätzlich Strafpunkte und SOF).
- Farben: eigene Zeile: ganzer Balken in der gewählten Farbe (Standard Bernstein `#ffb21e`, Stärke per Regler „Meine Zeile“), Schrift weiß, Auto Runde(n) vor mir
  rot `#ff8a7a`, Runde(n) hinter mir blau `#7fb8ff`, gleiche Runde weiß. Auto in der Box: blass + „BOX“.
- Nur iRacing: Strafpunkte, SOF, iRating. Nur LMU: Virtuelle Energie.

## 9. Input-Graph, Wetter, Delta-Balken (Entwürfe 2026-11-12)

Muster als Artifacts „Boxenfunk Inputs“, „Boxenfunk Wetter“, „Boxenfunk Delta“
(Quellen im Projektordner `design/`). Alle mit LMU/iRacing-Schalter und gleichem Fensteraufbau.

- **Inputs:** laufender Graph (Zeitfenster 3–15 s) für Gas grün `#3ddc54`, Bremse rot `#ff4141`,
  Kupplung blau `#4aa3ff`, Lenkung grau `#d6d6d6` (je an/aus, Farbe frei). Bremslinie wird gelb
  `#ffd21a`, wenn ABS eingreift; Gaslinie ebenso bei TC (vorerst nur LMU). Rechts Balken in %,
  daneben Gang, Tempo (km/h oder mph) und ein Lenkrad, das mitdreht: Form Rund, F1 oder GT, Größe per Regler.
- **Wetter:** Kacheln, per Ziehen wählbar: Wetter jetzt (Symbol), Luft, Strecke, Nässe (mit Balken),
  Regen, Wind (Pfeil relativ zum Auto), Bewölkung, Luftfeuchte, Vorhersage (vorerst nur LMU),
  Verlauf Streckentemperatur. Waagerecht oder senkrecht. Regen-Warnung lässt das Overlay kurz
  blau aufleuchten; Nässe wird ab einstellbarem Wert hervorgehoben.
- **Delta:** große Zahl (grün schneller / rot langsamer) mit Trendpfeil, Balken ab der Mitte
  (Richtung einstellbar), Skala ±0,5/1/2 s, 3 Sektor-Striche, Vergleichszeit und Prognose.
  Vergleich mit: eigene Bestzeit, letzte Runde, Beste im Feld, optimale Runde.

## 10. Globale Schrift-Einstellungen (Wunsch W-34)

Schriftart und Schriftgröße gibt es auch global für alle Widgets. Im Widget-Fenster muss sichtbar
sein, ob ein Wert vom globalen Standard kommt oder eigen ist (z. B. kleiner Punkt/„Standard“-Hinweis),
mit Knopf „zurück auf Standard“. Noch nicht im Muster umgesetzt.

## 11. Spielsituation (W-35) und Datenprüfung (2026-11-12)

- Jedes Einstellungsfenster hat unter dem Titel den Schalter „Spielsituation“:
  Training · Quali · Rennen · Wiederholung · Garage, plus Haken „In dieser Situation zeigen“.
  Einstellungen gelten je Spiel **und** Situation. Standard: überall an, außer Garage.
  Ist ein Widget ausgeblendet, zeigt die Vorschau einen Hinweis statt des Widgets.
- Nässe: LMU in Prozent, iRacing nur als Stufe (trocken, meist trocken, kaum feucht,
  leicht feucht, feucht, sehr nass, extrem nass).
- Fehlerpunkte „X“ (W-36, nur eigenes Auto, Kopfzeile): LMU „X 1,5/4“ (Track-Limits-Punkte / Strafe ab),
  iRacing „X 6/17/25“ (Strafpunkte / Strafe ab / Disqualifikation ab).
- Offene Strafe je Auto (W-37): rotes Schild „PEN“, bei LMU mit Anzahl („PEN 2“). SG/DT nicht anzeigen.
- Box-Status je Auto (W-39), in der Box-Spalte bzw. als Schild beim Namen: „PIT req“ (gelber Rahmen,
  nur LMU), „PIT in“ (blau blass), „PIT“ (blau), „PIT out“ (grün blass); einzeln abschaltbar.
  Neue Spalte „Stopps“ (Anzahl Boxenstopps). Team/Fahrer (W-38) und DNF (W-40) nicht gewünscht.
- Wettervorhersage nur LMU (bestätigt).
