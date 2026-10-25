# O2 Kartenbasis: Bericht

Stand 25. Oktober 2026. Gebaut und gemessen in einer Cloud-Sitzung (Linux, ohne GPU), nicht auf dem Rechner des Betreibers. Die Zahlen für Dauer gelten nur für diese Umgebung; die Größen hängen nur an Fläche und Datenstand.

## Ergebnis

Die Karte für Ostbelgien plus 20 km steht: Basiskarte bis Zoom 15, Relief, Suchindex, Ortsverzeichnis, Warngebiete, Gewässernetz. Die ganze Kette läuft mit einem Befehl:

```bash
tools/kartenbasis.sh                    # Basiskarte, Prüfung, Höhen, Gelände, Suchindex
tools/kartenbasis.sh --mit-gewaesser    # dazu Gewässernetz (vorher python -m app.collect --once && python -m app.export)
```

Die Bauprodukte liegen wie in Landblick-RLP nicht im Repository (`web/tiles/`, `web/data/`). Wer die Karte sehen will, lässt das Skript einmal laufen.

## Gemessen

| Teil | Werkzeug | Umfang | Größe | Dauer |
|---|---|---|---|---|
| Basiskarte Region | `build_region_tiles.py` | Zoom 0 bis 13, 11 Stücke | 42 MB | zusammen unter 1 min |
| Basiskarte Ring | dto. | Zoom 14 außerhalb der Kerne, 1 792 Kacheln | 21 MB | |
| Basiskarte Kerne | dto. | DG, Aachen, Verviers, Malmedy, Zoom 14 und 15, 5 466 Kacheln | 37 MB | |
| Höhenkacheln | `build_dem.py` | Zoom 6 bis 12, 945 Kacheln | 103 MB | rund 1 min |
| Geländefaktoren Wind | `build_terrain.py` | Zoom 10, Raster 170 × 246 | 75 KB | 2 s |
| Suchindex | `build_search_index.py` | 16 409 Einträge, davon 11 648 Straßen | 636 KB | 20 s |
| Ortsverzeichnis | `build_gazetteer.py --zuschnitt` | 2 125 Einträge | 105 KB | 1 s |
| Gewässernetz | `build_gewaessernetz.py` | 25 Zuordnungen, 27 Läufe | 4 KB | 3 s |

Zum Vergleich Landblick-RLP: Basiskarte rund 530 MB, Relief bis 1,5 GB. Ostbelgien braucht zusammen rund 205 MB.

Übertragung je Startansicht (1920 × 1080, komprimierte Vektorkacheln, `check_tiles.py --volume`): Gesamtansicht Zoom 9 1,1 MB, Eupen Zoom 12 2,3 MB, Aachen Zoom 13 1,3 MB.

Stichprobe (`check_tiles.py`): zwölf Orte von Clervaux bis Vaals, je Zoom 8, 13, 14 und in den Kernen 15. Keine Lücke, Gebäude ab Zoom 13 überall vorhanden.

## Entscheidungen in dieser Phase

- **Zoom-15-Kern ist die ganze DG.** Der Kasten der neun Gemeinden kostet 37 MB samt Aachen, Verviers und Malmedy. In Rheinland-Pfalz ging das nur für Städte.
- **Relief endet bei Zoom 12.** Die Quelle (Mapzen: SRTM, EU-DEM) ist rund 30 m fein, ein Bildpunkt bei Zoom 12 misst in Ostbelgien rund 24 m. Zoom 14 hätte 12 972 statt 945 Kacheln gekostet, ohne einen Meter genauer zu sein. `tiles/dem/meta.json` meldet `maxzoom: 12`, `relief.js` vergrößert darüber selbst.
- **Nachladepaket aus.** `PAKETE_MANIFEST` in `app/desktop.py` zeigte noch auf das Höhenpaket von Landblick-RLP (4,3 GB, andere Fläche). Jetzt leer.
- **Karte im Installer.** `desktop/stage-pakete.sh` packt die Basiskarte jetzt standardmäßig mit ein (100 MB statt 1,5 GB in RLP). Felswände, Hang und Gebäude sind optional.
- **Ortsverzeichnis zweisprachig.** Viele Orte am Rand heißen in OSM französisch („Waimes“), der BRF schreibt deutsch („Weismes“). `build_gazetteer.py` nimmt `name:de` als eigenen Eintrag, teilt „Kelmis - La Calamine“ und ergänzt eine kurze Liste deutscher Formen (Weismes, Bleiberg, Welkenrath, Stablo, Ulflingen, Clerf, Wintger). Das Verzeichnis ist ein Zuschnitt des RLP-Verzeichnisses (gleiche OSM-Quelle, Stand Oktober 2026), weil Overpass während der Sitzung nicht antwortete.
- **MeteoAlarm-Gebiete.** BE22 (Limburg, wegen Voeren), BE33 (Lüttich), BE34 (Luxemburg B), LU00. Frankreich entfällt.

## Live-Probe der Pegel

Für das Gewässernetz liefen die vier Pegelquellen einmal gegen die echte Fläche: SPW Wallonien 46 Stationen, Hochwasser RLP 27, AGE Luxemburg 4. Das länderübergreifende Hochwasserportal liefert für den NRW-Teil (Rur, Inde, Vicht) keine Pegel. Das ist ein Punkt für O3 (Hochwasser NRW direkt).

## Was nicht geht oder offen ist

- **Symbole.** Die UXWing-Icons liegen lizenzbedingt nicht im Repository; `tools/fetch_icons.sh` holt sie wie bisher. Ohne sie zeigt die Karte Kreise statt Zeichen.
- **Feineres Gelände, Felswände, Hangneigung, Gebäudefunktion.** Brauchen Daten aus Wallonien und NRW, Lizenzen offen.
- **Ortsverzeichnis frisch aus Overpass.** `python tools/build_gazetteer.py` nachholen, sobald Overpass antwortet; dann kommen `name:de` aller Orte mit.
- **Kachelpakete als Release.** Der Windows-Installer erwartet die Pakete an einem Release `kacheln-1` dieses Repositorys. Das gibt es noch nicht.
- **Bildrate.** Nicht gemessen; das gehört zu O5 und braucht eine Maschine mit GPU.
