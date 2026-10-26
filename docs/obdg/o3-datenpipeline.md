# O3 Datenpipeline: Bericht

Stand 25. Oktober 2026. Live-Lauf aller Quellen gegen die echte Fläche Ostbelgien plus 20 km, aus einer Cloud-Sitzung (Abend, ruhige Wetterlage). Was hier „0“ heißt, heißt meist „nichts los“, nicht „kaputt“; die Spalte Befund sagt, welches von beiden.

## Ergebnis in Kürze

- **Neu:** Pegel NRW (`nrw_pegel`, 18 Stationen an Rur, Inde, Vicht, Wurm, Urft, Olef), dl-de/zero-2.0.
- **Umgestellt:** BRF auf den Regionalfeed (sechs von zehn Meldungen verortet statt null), UV-Index auf die DWD-Station Bonn (statt Hahn).
- **Lizenzen bestätigt:** KMI (CC BY), IRCEL-CELINE (CC BY 4.0), am Dienst bzw. im belgischen Geoportal.
- **Lizenzfund mit Folgen:** Die Pegel Wallonien dürfen ohne schriftliche Zustimmung des SPW nicht öffentlich verbreitet werden. Die Quelle läuft deshalb nur noch im Privatmodus (`LANDBLICK_MODE=privat`). Entwurf einer Anfrage: `anfrage-spw.md`.
- **Strukturelle Lücke:** Für den belgischen Teil gibt es keine offene Quelle für Verkehr und keine für Bevölkerungswarnungen. Alle Ereignisse des Live-Laufs (90) stammen aus Deutschland und Luxemburg.

## Live-Lauf je Quelle

| Quelle | Ergebnis | Befund |
|---|---|---|
| `wallonie_pegel` | 46 Stationen, 1 051 Werte | Weser/Vesdre, Helle, Amel/Amblève, Warche, Salm, Our, Göhl/Gueule; nur privat (siehe oben) |
| `nrw_pegel` | 18 Stationen, 2 124 Werte | neu; Tagesdatei, neuester Wert 03:45 UTC |
| `hochwasser_rlp` | 27 Stationen | Prüm, Our, Kyll, Nims, Oos, kommunale Messstellen |
| `lu_pegel` | 4 Stationen | Our |
| `lhp_hochwasser` | 0 | richtig: liefert nur Hochwasserklassen über 0; 18 NRW-Pegel in der Region vorhanden |
| `kmi_stationen` | Mont Rigi, Spa | Elsenborn meldet seit August nichts |
| `dwd_stationen` | 27 Stationen | |
| `brightsky`, `metno` | Vorhersage für Eupen | |
| `sensor_community` | 7 Rasterzellen | |
| `irceline` | 20 Werte | Stationen der Wallonie |
| `uba_luft` | 136 Werte | NRW, RLP |
| `bfs_odl` | 17 Messstellen | |
| `dwd_radar`, `dwd_icon_d2_wind`, `eumetsat_li` | Bild bzw. Gitter | Blitze: 1 von 9 Zeitschritten fehlte, 92 s Laufzeit |
| `emsc` | 0 | keine Beben in sieben Tagen |
| `dwd_warnungen`, `nina`, `meteoalarm` | 0 | keine Warnlage (MeteoAlarm: 329 belgische, 12 luxemburgische Einträge gelesen, keiner in der Region aktiv) |
| `dwd_waldbrand` | 4 Stationen, keine ab Stufe 3 | |
| `dwd_gesundheit` | Pollen 2 Teilregionen, UV Bonn | |
| `autobahn` | 34 Meldungen | A4, A44, A60 |
| `lbm_baustellen` | 56 Meldungen | Eifelkreis, Vulkaneifel, Ösling |
| `adsblol` | 4 Flugzeuge | |
| `gtfs_static` | 242 Haltestellen LU, 65 DE | belgische Fahrpläne fehlen (TEC, SNCB: siehe Kandidaten) |
| `gtfs_rt_de` | 43 Fahrten in der Region, 15 Meldungen | im zweiten Lauf, nach dem Index aus `gtfs_static`; keine Störungsmeldungen |
| `brf` | 6 Meldungen | Walhorn, Sourbrodt, Hergenrath, St. Vith, Aachen, Verviers |
| `statec_sprit` | Höchstpreise LU | |
| `sgdnord_energie` | 367 Windräder, 62 Solarparks | im Zwischenspeicher, keine Ereignisse |
| `osm_tankstellen_lu` | Tankstellen im Ösling | |
| `osm_anbau`, `osm_routen` | teilweise | nach rund 12 Minuten Wiederholungen: ein Viertel der Anbauflächen und die Radrouten fehlen, letzter Stand bleibt; Overpass überlastet (429, 502, 504, Abbrüche) |
| `osm_energie` | 117 Objekte, teilweise | nach 25 Minuten Wiederholungen; Leitungen fehlen |
| `osm_natur`, `osm_infra` | abgebrochen | nach 28 Minuten durch die Zeitgrenze des Laufs beendet, Overpass antwortete bis zuletzt nicht (ReadTimeout) |
| `tankerkoenig`, `nasa_firms` | – | brauchen Zugangsschlüssel (`.env`) |

Gebietszuordnung im Export: Städteregion Aachen 26, Eifelkreis Bitburg-Prüm 36, Landkreis Vulkaneifel 15, Ösling 13 Meldungen. Pegel im Export: 95 Stationen aus vier Quellen.

## Änderungen am Code

- `app/collectors/nrw_pegel.py` neu, mit Tests gegen gekürzte echte Dateien (`tests/test_nrw_pegel.py`). Die Metadatei des Landes ist Windows-1252 kodiert; ein UTF-8-Lesen hätte Umlaute in Gewässernamen verstümmelt.
- `rss_brf`: Regionalfeed; neue Testdatei vom 25.10.2026, auf Titel, Link, Datum und Schlagwörter gekürzt (die alte ebenso).
- Ortsverzeichnis: „St. Vith“ als Schreibweise des BRF.
- `sources.yaml`: `nrw_pegel` neu; `wallonie_pegel` mit `nutzung: privat`; KMI und IRCEL bestätigt; UV Bonn; BRF-Adresse.
- `tests/conftest.py`: Tests laufen im Privatmodus, damit alle Sammler geprüft werden.

## Was noch fehlt

- Testdaten aus Ostbelgien für die übrigen Sammler. Die Fixtures stammen weiter aus Landblick-RLP und laufen auf der Prüffläche um Irrel; für die Mechanik reicht das.
- Ein zweiter Live-Lauf mit Overpass, Zugangsschlüsseln und bei echter Warnlage.
- Zustimmung des SPW, sonst bleibt die DG im öffentlichen Betrieb ohne eigene Pegel. Die Our-Pegel aus Luxemburg und Rheinland-Pfalz und die NRW-Pegel bleiben öffentlich.
