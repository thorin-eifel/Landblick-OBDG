# O4 Export und Auslieferung: Bericht

Stand 25. Oktober 2026. Gemessen am echten Export aus dem O3-Lauf (Privatmodus, 38 Quellen), Fläche Ostbelgien plus 20 km. Die Radrouten fehlen in diesem Stand, weil Overpass in O3 nicht geantwortet hat; mit ihnen wird der Export größer, siehe unten.

## Ergebnis in Kürze

- **Raster 0,25 Grad statt 0,5.** Die Region hat damit 22 Zellen statt 8. Das Raster steht jetzt in `region.yaml` (`zellen_grad`) und nicht mehr im Code; das Frontend liest es aus dem Manifest.
- **Linien je Zelle zugeschnitten.** Routen und Stromleitungen wanderten bisher ganz in jede Zelle, die sie berühren. Jetzt bekommt jede Zelle nur ihr Stück.
- **Kein Rand ab Zoom 12.** Bei 0,25 Grad ist eine Zelle ab Zoom 12 größer als der Bildausschnitt; eine Zelle Rand hätte die Ladung verdreifacht, ohne dass man etwas davon sieht.
- **Budgets.** Zelldatei weiter 500 KB, Startpaket von 2 MB auf 512 KB gesenkt.
- **Auslieferung.** Im Repository gibt es keinen Upload; das Projekt läuft lokal. Was ein Upload beachten muss, steht im Manifest und unten.

## Messungen

### Raster und Rand

Ladung je Ansicht, aus dem Export berechnet (alle Zelldateien, die das Frontend für den Ausschnitt anfordert, 1920 × 1080 Pixel):

| Ansicht | 0,5 Grad, eine Zelle Rand | 0,25 Grad, Rand bis Zoom 11 |
|---|---|---|
| Eupen, Zoom 15 | 1,9 MB | 178 KB |
| Aachen, Zoom 13 | 1,9 MB | 354 KB |

Bei 0,5 Grad holte selbst die Straßenansicht in Eupen fast die ganze Region: acht Zellen, und der Rand umfasst sie alle. Das Raster war für Rheinland-Pfalz gebaut, wo eine Zelle ein Bruchteil der Fläche ist.

0,125 Grad ist nicht gemessen. Es würde die Zahl der Dateien und Anfragen etwa vervierfachen; bei 177 KB für die Straßenansicht gibt es dafür keinen Anlass. `region.yaml` erlaubt 0,125, 0,25, 0,5 und 1 Grad; andere Werte lehnt `app/region.py` ab, weil Zellkennungen ganze Zahlen bleiben müssen.

### Linien

| Routen | Größe |
|---|---|
| flach (`routen.json`) | 967 KB |
| in den Zellen, ungeschnitten | 2 020 KB |
| in den Zellen, zugeschnitten | 1 002 KB |

Eine Wanderroute durch fünf Zellen lag fünfmal vollständig im Export. Zugeschnitten wird auf das Zellrechteck plus 0,002 Grad (rund 200 m), damit an der Grenze keine Lücke sichtbar wird; zusammenhängende Abschnitte bleiben eine Linie (`app/cells.py`, `clip_lines`). Jede Zelle führt ihr Stück unter `<id>@<zelle>`, damit das Frontend die Stücke nicht gegeneinander austauscht. Punkte (Haltestellen, Umspannwerke) liegen weiter in genau einer Zelle.

### Export, Endstand

| | |
|---|---|
| Zellen | 22 |
| Zelldateien | 115 |
| Summe der Zelldateien | 2 072 KB |
| größte Zelldatei | 247 KB |
| Startpaket | 41 KB |
| Warnungen zu Budgets | keine |
| Laufzeit des Exports | 1,5 s |

### Im Browser

Abgerufene Zelldateien je Ansicht, Chromium, 1920 × 1080, gegen den lokalen Dienst:

| Ansicht | Abrufe | Größe | Zellen | Fehler |
|---|---|---|---|---|
| Startansicht (ganze Region) | 43 | 493 KB | 19 | 0 |
| Sankt Vith, Zoom 12 | 31 | 669 KB | 6 | 0 |
| Eupen, Zoom 13 | 12 | 329 KB | 2 | 0 |
| Eupen, Zoom 15 | 6 | 177 KB | 1 | 0 |

Sankt Vith liegt an einer Zellecke, deshalb sechs Zellen. Der Layouttest (`tests/e2e/layout.e2e.mjs`) läuft durch, 15 von 15.

## Budgets

Die Zelldatei bleibt bei 500 KB. Die größte liegt bei 247 KB, aber ohne Radrouten, deren Umfang für diese Fläche noch niemand gemessen hat. Wird es eng, ist der erste Hebel die Vereinfachung der Linien im Sammler, nicht ein feineres Raster.

Das Startpaket liegt für Ostbelgien bei 41 KB. Ein Budget, das ein Wachstum um das Fünfzigfache durchlässt, meldet nichts mehr. 512 KB lassen Platz für eine Warnlage mit vielen Einträgen im Warnband und schlagen an, wenn etwas aus dem Ruder läuft.

Überschreitungen schneiden nichts ab. Sie stehen im Manifest (`warnings`, je Datei `over_budget`) und als Warnung im Protokoll des Exports.

## Auslieferung

Landblick-OBDG läuft als lokaler Dienst auf 127.0.0.1 und in der Desktop-App; einen Upload gibt es im Repository nicht. Wer `web/` auf einen Server legt, findet im Manifest, was dafür nötig ist:

- `upload: always` für `manifest.json` und `start.json`, `on_change` für alles andere, entschieden über `sha256` je Datei. Zellen tragen keine Abrufzeit und ändern sich deshalb nur, wenn sich ihr Inhalt ändert.
- Reihenfolge (Empfehlung, nicht im Code erzwungen): erst Zellen und Flachdateien, zuletzt `start.json` und `manifest.json`. Sonst sieht ein Browser kurz ein Manifest, dessen Dateien noch nicht da sind.
- Der Upload löscht nichts. Alte Zellordner (etwa nach dem Wechsel von 0,5 auf 0,25 Grad) räumt der Export nur lokal ab; auf dem Server bleiben sie liegen, schaden aber nicht, weil das Manifest sie nicht nennt.
- Kacheln (`web/tiles/*.pmtiles`) brauchen einen Server mit Range-Anfragen; prüfen mit `tools/check_range.py <URL>`.

Für die Desktop-App ändert sich nichts: sie liest den Export aus ihrem Datenordner.

## Änderungen am Code

- `region.yaml`: `zellen_grad: 0.25`. `app/region.py` liest und prüft den Wert, `app/cells.py` rechnet damit.
- `app/cells.py`: `clip_lines` schneidet Linien auf eine Zelle zu.
- `app/export_cells.py`: Zuschnitt für Routen und Energie; das Manifest nennt das Raster (`grid.cell_deg`, `grid.per_deg`); Startbudget 512 KB.
- `web/js/zellen.js`: Raster aus dem Manifest (`setGrid`), Zellmitte für die Rangfolge (`cellCenter`). Ohne Angabe im Manifest bleibt es bei 0,5 Grad, ältere Exporte laufen weiter.
- `web/js/lage/zellenlauf.js`: Rand nur von Zoom 9 bis 11.
- Tests: Zuschnitt, Raster aus `region.yaml`, Raster im Frontend, Kennungen zugeschnittener Leitungen.

## Was noch fehlt

- Ein Export mit Radrouten und vollständigen OSM-Quellen, sobald Overpass antwortet. Dann die größte Zelle erneut messen.
- Messung der Bildrate (O5): Eupen, Sankt Vith, Aachen, Startansicht.
- Ein Upload, falls Landblick-OBDG öffentlich ausgeliefert werden soll. Das ist eine Entscheidung über den Betrieb, keine Frage des Exports.
