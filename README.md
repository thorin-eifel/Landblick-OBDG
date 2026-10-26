# Landblick - OBDG

Ein Lagebild aus offenen Daten für Ostbelgien: Warnungen, Wetter, Pegel, Verkehr, Luft und Strahlung auf einer Karte, mit Quelle, Alter und Lizenz an jedem Datum. Es zeigt Orte, Zeiten und Zahlen, keine Personen. Kein Tracking, keine Drittanbieter, keine US-Cloud.

Gebiet: die Deutschsprachige Gemeinschaft Belgiens mit ihren neun Gemeinden (Eupen, Kelmis, Lontzen, Raeren, Amel, Büllingen, Burg-Reuland, Bütgenbach, Sankt Vith) und 20 km rundum. Damit liegen Aachen, Verviers, Malmedy, Vielsalm, das Ösling, die Eifel um Prüm und Monschau sowie Süd-Limburg mit im Bild. Die Weser kümmert sich nicht um Sprachgrenzen, das Hochwasser auch nicht.

Privates Open-Source-Projekt von Thorsten Schleicher. Kontakt: thorin.eifel@icloud.com. Entstanden aus [Landblick-RLP](https://github.com/thorin-eifel/Landblick-RLP), dessen Technik es übernimmt. Kein amtliches Warnsystem: im Notfall 112, in Belgien BE-Alert, in Deutschland NINA und KATWARN.

## Schnellstart

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q && node --test tests/js/*.test.mjs

cp .env.example .env && chmod 600 .env     # LANDBLICK_CONTACT prüfen
python -m app.collect --once               # alle fälligen Quellen einmal abrufen
python -m app.export                       # schreibt web/data/*.json
python tools/serve-local.py --dir web      # http://localhost:8080
```

Die Karte braucht eigene Kacheln (`web/tiles/`, nicht im Repository). `tools/kartenbasis.sh` baut Basiskarte, Relief und Suchindex in wenigen Minuten (rund 205 MB, braucht die Werkzeug-venv aus `requirements-tools.txt`). Ohne Kacheln zeigt die Seite Daten und Grenzen auf leerem Grund. Messwerte: `docs/obdg/o2-kartenbasis.md`.

## Das Gebiet

`region.yaml` legt die Fläche fest: Polygon aus `app/data/region/obdg_plus20.json`, Bezugspunkt für Entfernungen Eupen. `python -m app.region` zeigt es an, ein anderes Gebiet geht über `LANDBLICK_REGION=<Datei>`.

Gebaut wird das Polygon in zwei Schritten aus OpenStreetMap:

```bash
pip install -r requirements-tools.txt                      # eigene venv, siehe Kommentar in der Datei
python tools/fetch_osm_grenzen.py --out-dir build/osm-grenzen --contact betreiber@example.org
python tools/build_region.py --raw build/osm-grenzen --buffer-km 20
```

Der erste Schritt fragt Nominatim in einem 3-km-Raster ab (rund 750 Punkte, eine Anfrage je Sekunde, gut eine Viertelstunde) und löst belgische Teilgemeinden zu ihren Gemeinden auf. Der zweite puffert die Grenze der DG, schneidet die Gebiete zu und schreibt Region, Gebietsliste, Kartengrenze und den Umriss für die Ortsnamen. Gliederung: Gemeinden in Belgien, Luxemburg und den Niederlanden, Kreise in Deutschland, je mit der zweiten Sprachform aus OSM (Waimes/Weismes, Amel/Amblève). Ein älterer Abruf ohne diese Namen lässt sich mit `--nur-namen` ergänzen, ohne das Raster zu wiederholen. Begründung in `docs/adr/0001-region-obdg.md`.

## So hängt es zusammen

```
Quellen → Sammler (app/collectors) → Geofilter (app/region.py) → SQLite → Export (JSON, Raumzellen) → statisches Frontend (web/)
```

Alles läuft auf dem eigenen Rechner: Die Sammler rufen die Quellen ab und schreiben fertige JSON-Dateien, ein lokaler Dienst auf 127.0.0.1 liefert die Oberfläche und diese Dateien aus. Fällt eine Quelle aus, bleibt der Rest stehen und die Kachel sagt es. Ausführlich mit Betrieb und Desktop-App: `docs/betrieb.md`.

## Regeln, die nicht verhandelt werden

- Ereignisse statt Personen. Keine Klarnamen, Profile, Adressen oder Bilder von Personen.
- Keine Quelle ohne Eintrag in `sources.yaml` (Lizenz, Namensnennung, Intervall, Ratenlimit, Datenschutzrisiko). Unklare Bedingungen heißen: Quelle bleibt aus. Kandidaten stehen in `docs/obdg/quellen-kandidaten.md`.
- Jede Kachel zeigt Quelle, Abrufzeit und Alter. Alte Daten werden als alt markiert.
- KI-Auswertung ist gekennzeichnet und optional. Keine Warnung, die nur ein Modell behauptet.
- Keine externen Skripte, Schriften oder Kacheln, keine Cookies außer technisch nötigen.
- Zugangsdaten nur in `.env`, nie im Repository.
- Belgische Quellen bleiben in ihrer Sprache, wo es keine deutsche Fassung gibt. Es wird nicht maschinell übersetzt.

## Stand

<!-- stand:start -->

<!-- Dieser Block wird von tools/update_readme.py erzeugt. Nicht von Hand ändern. -->

### Region

- Aktiv (`region.yaml`): Ostbelgien plus 20 km: Polygon aus `app/data/region/obdg_plus20.json`, Bezugspunkt Eupen

### Phasen

| Phase | Inhalt | Stand | Pull Request |
|---|---|---|---|
| O0 | Gerüst aus Landblick-RLP | fertig | [#1](https://github.com/thorin-eifel/Landblick-OBDG/pull/1) |
| O1 | Raumabstraktion | fertig | [#1](https://github.com/thorin-eifel/Landblick-OBDG/pull/1) |
| O2 | Kartenbasis | fertig | [#2](https://github.com/thorin-eifel/Landblick-OBDG/pull/2) |
| O3 | Datenpipeline | fertig | [#3](https://github.com/thorin-eifel/Landblick-OBDG/pull/3) |
| O4 | Export und Auslieferung | fertig | [#4](https://github.com/thorin-eifel/Landblick-OBDG/pull/4) |
| O5 | Frontend | fertig | [#5](https://github.com/thorin-eifel/Landblick-OBDG/pull/5) |
| O6 | Betrieb und Härtung | offen |  |
| O7 | Abnahme | offen |  |

Plan und Begründung: `docs/obdg/plan.md`. Entscheidung: `docs/adr/0001-region-obdg.md`.

### Zahlen

- Quellen im Register: 37, davon aktiv: 37
- Sammler (Module in `app/collectors/`): 39
- Tests: 537 Python, 158 JavaScript

### Quellen und Lizenzen

| Kennung | Quelle | Lizenz | Intervall | aktiv |
|---|---|---|---|---|
| `nina` | NINA / BBK | Nutzungsbedingungen NINA/BBK | 5 min | ja |
| `dwd_warnungen` | DWD | GeoNutzV (DWD Open Data) | 5 min | ja |
| `brightsky` | DWD via Bright Sky | DWD GeoNutzV; Bright Sky Software MIT | 15 min | ja |
| `autobahn` | Autobahn GmbH | Nutzungsbedingungen Autobahn GmbH (zu bestätigen) | 5 min | ja |
| `adsblol` | adsb.lol | ODbL 1.0 (laut Betreiber-Dokumentation) | 15 s | ja |
| `lbm_baustellen` | Mobilitätsatlas RLP | nicht angegeben (zu klären) | 10 min | ja |
| `hochwasser_rlp` | Hochwasser RLP | nicht angegeben (zu klären) | 15 min | ja |
| `bfs_odl` | BfS ODL | Datenlizenz Deutschland – Namensnennung – Version 2.0 (nach Kenntnisstand) | 30 min | ja |
| `uba_luft` | UBA Luftdaten | Datenlizenz Deutschland – Namensnennung – Version 2.0 (nach Kenntnisstand) | 30 min | ja |
| `emsc` | EMSC | CC BY 4.0 (laut Dienstseite) | 15 min | ja |
| `dwd_radar` | DWD Radar | GeoNutzV (Geodatennutzungsverordnung), Quellenvermerk Deutscher Wetterdienst | 5 min | ja |
| `dwd_icon_d2_wind` | DWD Wind | GeoNutzV (Geodatennutzungsverordnung), Quellenvermerk Deutscher Wetterdienst | 1 h | ja |
| `eumetsat_li` | EUMETSAT Blitze | EUMETSAT-Datenpolitik, Quellenvermerk EUMETSAT (Bedingungen für MTG-LI über EUMETView nicht abschließend geprüft) | 5 min | ja |
| `nasa_firms` | NASA FIRMS | NASA Earthdata-Datennutzungsrichtlinie (frei, auch kommerziell), Quellenangabe NASA FIRMS | 30 min | ja |
| `gtfs_static` | GTFS Fahrplan | CC BY 4.0 (Luxemburg laut Datensatz, Deutschland laut gtfs.de "Creative Commons 4.0") | 168 h | ja |
| `gtfs_rt_de` | ÖPNV Echtzeit | CC BY-SA 4.0 (Namensnennung, Weitergabe unter gleichen Bedingungen), ohne Gewähr | 10 min | ja |
| `osm_natur` | Landmarken | ODbL 1.0 (© OpenStreetMap-Mitwirkende) | 168 h | ja |
| `osm_infra` | Infrastruktur | ODbL 1.0 (© OpenStreetMap-Mitwirkende) | 168 h | ja |
| `sgdnord_energie` | Wind und Solar (SGD Nord) | Datenlizenz Deutschland Namensnennung 2.0 (dl-de/by-2.0) | 24 h | ja |
| `osm_energie` | Energie | ODbL 1.0 (© OpenStreetMap-Mitwirkende) | 168 h | ja |
| `osm_anbau` | Anbauflächen | ODbL 1.0 (© OpenStreetMap-Mitwirkende) | 168 h | ja |
| `osm_routen` | Routen | ODbL 1.0 (© OpenStreetMap-Mitwirkende) | 168 h | ja |
| `metno` | MET Norway | CC BY 4.0 | 1 h | ja |
| `sensor_community` | Sensor.Community | Datenbank ODbL 1.0, Inhalte DbCL 1.0 (laut Betreiberangabe, zu bestätigen) | 10 min | ja |
| `lu_pegel` | Pegel Luxemburg | CC0 1.0 | 15 min | ja |
| `dwd_waldbrand` | DWD Waldbrandindex | CC BY 4.0 | 3 h | ja |
| `dwd_gesundheit` | DWD Pollen/UV | GeoNutzV (Namensnennung DWD), Bedingungen laut Open-Data-Hinweisen des DWD | 1 h | ja |
| `tankerkoenig` | Tankerkönig | CC BY 4.0 | 2 min | ja |
| `nrw_pegel` | Pegel NRW | Datenlizenz Deutschland – Zero – Version 2.0 (dl-de/zero-2-0) | 3 h | ja |
| `brf` | BRF | keine offene Lizenz; nur Überschrift, Zeit und Link, kein Text, kein Bild | 15 min | ja |
| `meteoalarm` | MeteoAlarm | laut Anbieter gleichwertig CC BY 4.0 mit zusätzlichen Auflagen für die Weiterverbreitung | 10 min | ja |
| `statec_sprit` | Höchstpreise Luxemburg | CC0 1.0 | 1 h | ja |
| `osm_tankstellen_lu` | Tankstellen Luxemburg | ODbL 1.0 (© OpenStreetMap-Mitwirkende) | 168 h | ja |
| `dwd_stationen` | DWD-Stationen | DWD GeoNutzV; Bright Sky Software MIT | 30 min | ja |
| `irceline` | IRCEL-CELINE | CC BY 4.0 | 30 min | ja |
| `kmi_stationen` | KMI-Stationen | CC BY 4.0 | 30 min | ja |
| `lhp_hochwasser` | LHP Hochwasser | Creative Commons Namensnennung 4.0 (CC BY 4.0) | 10 min | ja |

Vollständig mit Namensnennung: `sources.yaml` und die Seite „Quellen und Lizenzen“ der Anwendung.

### Dokumente

- `docs/betrieb.md`
- `docs/dsfa-entwurf.md`
- `docs/obdg/` (Plan, Status, offene Punkte, Quellenkandidaten)
- `docs/adr/` (Entscheidungen)

<!-- stand:end -->

## Mitarbeiten

Je Phase ein Branch `obdg/o<N>-<kurzname>` und ein Pull Request. Vor jedem Push: Tests grün, `docs/obdg/status.yaml` nachführen und `python tools/update_readme.py` ausführen. Die CI prüft mit `--check`, ob der Stand-Block zur Wirklichkeit passt. Was noch nicht stimmt: `docs/obdg/offen.md`.

## Lizenz und Nachweise

Code und Texte: MIT (`LICENSE`); zur Frage GPL-3.0 aus Landblick-RLP siehe `docs/obdg/offen.md`. Daten haben ihre eigenen Lizenzen (Block oben, vollständig in `sources.yaml`). Kartendaten und Grenzen: © OpenStreetMap-Mitwirkende (ODbL), Protomaps.
