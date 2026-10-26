# O5 Frontend: Bericht

Stand 26. Oktober 2026. Geprüft gegen den lokalen Dienst mit dem Export aus O3/O4 (Privatmodus), Chromium 1400 × 900, ohne GPU.

## Ergebnis in Kürze

- **Ortsnamen zweisprachig.** Auf der Karte steht oben der Name vor Ort, darunter kleiner die deutsche Form, wenn sie abweicht: „Waimes / Weismes“, „Robertville / In der Bivelt“. Filter und Rechtsklick zeigen „Waimes (dt. Weismes)“ und „Amel (frz. Amblève)“. Die Suche fand beide Formen schon seit O2.
- **Höhe repariert.** Rechtsklick und Legende zeigten seit O2 keine Höhe. Die Abfrage verlangte Kacheln auf Zoom 14, die Ablage für Ostbelgien reicht bis 12.
- **Reste aus Landblick-RLP entfernt.** Darunter „Station Bonn (Hunsrück)“ beim UV-Index, Frankreich in der Länderauswahl, Mosel, Saar und Sauer als breite Flüsse der Region.
- **Barrierefreiheit.** axe-core (WCAG 2.1 A/AA, Best Practice): alle sechs Seiten ohne Befund, hell und dunkel. Zwei übernommene Fehler behoben.
- **Bildrate.** Gemessen an Eupen, Sankt Vith, Aachen und der Gesamtansicht, aber nur in Software-Rendering. Die Zahlen taugen zum Vergleich der Ansichten, nicht als Bildrate.

## Ortsnamen

Ortsnamen in Belgien haben oft zwei Formen. Welche „richtig“ ist, hängt davon ab, wo man steht. In der DG sind die amtlichen Namen deutsch, in Wallonien französisch. Daneben gibt es deutsche Formen, die ein Eupener ohne Nachdenken benutzt (Weismes, Bleiberg, Welkenrath), und solche aus preußischer oder älterer Zeit, die heute kaum jemand liest (Geilich für Gouvy, Hohenfels für Houffalize, Engelsdorf für Ligneuville).

Der Kartenstil von Protomaps nahm bei deutscher Spracheinstellung die deutsche Form allein. Auf der Karte stand also „Geilich“, wo das Ortsschild „Gouvy“ sagt. Wer nach der Karte fährt, sucht dann ein Schild, das es nicht gibt.

Die Regel jetzt: Der amtliche Name steht vorn, die andere Form dahinter. Es wird nicht ausgewählt, welche deutsche Form noch gilt. Eine solche Auswahl wäre Geschmack und würde in drei Jahren nicht mehr stimmen. Gezeigt wird, was OSM führt, als Zusatz und nie an Stelle des Schilds.

| Stelle | Quelle | Beispiel |
|---|---|---|
| Karte | OSM `name` und `name:de` in den Kacheln (`ORTSNAME` in `stil.js`) | Waimes, darunter klein Weismes |
| Filter, Rechtsklick | `name_de`/`name_fr` in der Gliederung (`build_region.py`, `andere_namen`) | Waimes (dt. Weismes), Amel (frz. Amblève) |
| Suche | Suchindex aus O2, beide Formen als eigene Einträge | „Weismes“ und „Waimes“ führen zum selben Ort |
| Pegelliste | feste Zuordnung in `pegel.js` | Weser (Vesdre), Amel (Amblève), Göhl (Gueule) |

In der DG und in Deutschland sind Name und deutsche Form gleich, dort bleibt es bei einer Zeile. Formen, die sich nur im Akzent oder Umlaut unterscheiden (Bütgenbach/Butgenbach, Putscheid/Pütscheid), gelten als gleich. Ist die deutsche Form schon Teil des Namens, wird sie nicht doppelt gezeigt („Kelmis - La Calamine“). 23 der 70 Gebiete haben eine zweite Form.

Die Namen holt `tools/fetch_osm_grenzen.py` jetzt mit (`namedetails`). Für den vorhandenen Abruf hat `--nur-namen` sie in 4 Anfragen nachgetragen; die Polygone von Region und Gebieten sind unverändert. Nominatim verlangt eine Kennung im User-Agent; das Werkzeug nimmt dafür jetzt auch die Projektadresse statt einer Mailadresse.

Bei den Flüssen gilt die umgekehrte Reihenfolge: deutscher Name zuerst, französischer in Klammern. Die Pegelliste gruppiert nach Fluss, nicht nach Ort, und Weser, Amel und Göhl fließen durch die DG, wo sie so heißen. Der SPW führt sie unter der französischen Form; die Klammer hilft beim Abgleich mit hydrometrie.wallonie.be.

## Höhe

`elevationAt` (Rechtsklick, Höhenanzeige unter dem Zeiger) fragte fest eine Kachel auf Zoom 14 an. Landblick-RLP hatte Höhen bis 14; die Ablage für Ostbelgien reicht bis 12 (Mapzen, rund 30 m, O2). In O2 wurde die Kartenquelle auf den Wert aus `meta.json` umgestellt, die Abfrage nicht. Jede Abfrage scheiterte, und der Rechtsklick zeigte „nicht verfügbar“. Jetzt nimmt sie die feinste vorhandene Stufe bis 14.

Stichprobe: Eupen 276 m, Weismes 489 m, Hohes Venn bei Botrange 644 m. Rechtsklick und Legende zeigen denselben Wert.

## Reste aus Landblick-RLP

| Stelle | vorher | jetzt |
|---|---|---|
| UV-Index | „Station Bonn (Hunsrück)“ | „Station Bonn“ |
| Länderauswahl | immer auch „FR“, als nacktes Kürzel | Belgien, Luxemburg, Niederlande als Rückfall (wie `AUSLAND` im Export) |
| Breite Flüsse (Wellenfeld) | Mosel, Saar, Sauer | dazu Maas/Meuse, gestaut (Staustufe Lixhe bei Visé) |
| Zeichenerklärung Fließrichtung | „Mosel, Saar, Sauer“ | „Maas bei Visé“ |
| Kartenbeschreibung für Screenreader | „Land und Landkreis“ | „Land und Gemeinde oder Kreis“ |
| Quellenseite, Pegel | Wallonien ohne Hinweis, NRW fehlte | NRW (LANUK) genannt; Wallonien nur in der Desktop-App |
| Testdaten Gebietsfilter | Trier, Saarbrücken | Eupen, Amel, Städteregion Aachen |

## Barrierefreiheit

axe-core 4.10 über alle Seiten (Lage, Status, Quellen, Impressum, Datenschutz, Einrichtung), Regeln WCAG 2.1 A und AA plus Best Practice. Die dunkle Ansicht schaltet die Seite selbst um (`data-ansicht`), nicht die Systemeinstellung; geprüft wurde sie über den Schalter „Dunkel“.

Befunde und Behebung, beide aus Landblick-RLP übernommen:

- Das grüne „OK“ auf Status- und Quellenseite hatte 3,2:1 Kontrast (verlangt 4,5:1). Neue Textfarbe `--success-text`; die Farbfläche der Laufbalken bleibt.
- Die Lauf-Historie trug ein `aria-label` auf einem `span` ohne Rolle; Screenreader lasen es nicht vor. Jetzt `role="img"` und ein Text, der etwas sagt: „letzte 12 Läufe: 11 erfolgreich, 1 mit Fehler“ statt „letzte 12 Läufe“.

Danach: kein Befund, hell und dunkel.

Von Hand geprüft: Das erste Tab-Ziel ist „Zum Inhalt springen“. `/` setzt den Fokus in die Suche, „Weismes“ und Enter springen dorthin, die Karte ist per Tab erreichbar. Mit reduzierter Bewegung kommen keine Fehler. Ein Test mit Screenreader steht aus; axe prüft nur, was sich automatisch prüfen lässt.

## Bildrate

`tools/perf_messung.py` misst jetzt an Eupen, Sankt Vith und Aachen je bei Zoom 10, 13 und 15, dazu die Gesamtansicht (Zoom 8,5). Gemessen wird das Bildintervall bei Dauer-Neuzeichnen (40 Bilder) und die Ladelast der Zellen.

| Ansicht | Bild, Mittel | Bild, 95 % | Zellen | Dateien | KB |
|---|---|---|---|---|---|
| Eupen, Zoom 10 | 496 ms | 600 ms | 19 | 70 | 1 464 |
| Eupen, Zoom 13 | 260 ms | 350 ms | 2 | 12 | 328 |
| Eupen, Zoom 15 | 433 ms | 550 ms | 1 | 6 | 176 |
| Sankt Vith, Zoom 10 | 447 ms | 567 ms | 18 | 63 | 1 242 |
| Sankt Vith, Zoom 13 | 257 ms | 350 ms | 1 | 3 | 70 |
| Sankt Vith, Zoom 15 | 378 ms | 467 ms | 1 | 3 | 70 |
| Aachen, Zoom 10 | 453 ms | 533 ms | 14 | 53 | 1 127 |
| Aachen, Zoom 13 | 279 ms | 350 ms | 1 | 6 | 158 |
| Aachen, Zoom 15 | 481 ms | 583 ms | 1 | 6 | 158 |
| Gesamtansicht, Zoom 8,5 | 294 ms | 400 ms | 19 | 43 | 459 |

Die Sitzung hat keine GPU, Chromium rendert in Software (SwiftShader). 250 bis 500 ms je Bild heißen hier nichts über einen echten Rechner. Was die Zahlen zeigen: Zoom 13 ist überall die leichteste Stufe. Zoom 15 kostet bei wenig Daten mehr Zeichenzeit, vermutlich durch Gebäude und Hausnummern (nicht einzeln gemessen). Zoom 10 trägt die meisten Daten, weil dort noch eine Zelle Rand mitlädt und damit fast die ganze Region kommt. Eine Vergleichsmessung aus Landblick-RLP unter denselben Bedingungen gibt es nicht.

Die eigentliche Messung braucht einen Rechner mit Grafikkarte:

```bash
python tools/perf_messung.py --url http://127.0.0.1:8099/ --out perf.json --gpu
```

## Was noch fehlt

- Bildrate auf echter Hardware (siehe oben).
- Zoom 10 lädt mit Rand 1,1 bis 1,5 MB. Ob der Rand dort nötig ist, sollte die Messung mit GPU klären; ohne ihn lädt beim Schwenken mehr nach.
- Ein Durchgang mit Screenreader (NVDA oder VoiceOver).
- Das Handbuch ist inhaltlich noch das von Landblick-RLP (offen.md); hier sind nur die Stellen zum Gebietsfilter nachgezogen.
