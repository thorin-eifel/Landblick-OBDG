# Offene Punkte

Stand 25. Oktober 2026. Was im Gerüst noch nicht stimmt oder nicht geprüft ist. Neue Quellen stehen getrennt in `quellen-kandidaten.md`.

## Lizenz und Recht

- **Lizenz des Codes.** Das neue Repository wurde mit einer MIT-Lizenz angelegt, der übernommene Code stand in Landblick-RLP unter GPL-3.0. Das geht, solange der Betreiber alleiniger Urheber ist. Vor dem ersten Release entscheiden und die Zeile in der README angleichen.
- **Prüfvermerke im Register.** `zuletzt_geprüft` und `lizenz_hinweis` stammen aus Landblick-RLP. Sie gelten für den Dienst, nicht für diese Fläche. Je Quelle neu prüfen.
- **Impressum und Datenschutz.** Verantwortlicher und Anschrift sind aus Landblick-RLP übernommen. Prüfen, ob für ein Angebot mit Schwerpunkt Belgien zusätzliche Angaben nötig sind.
- **DSFA.** `docs/dsfa-entwurf.md` ist der Entwurf aus Landblick-RLP und nennt dessen Fläche. Für Ostbelgien neu fassen (O7).

## Daten und Karte

- **Karte.** Es gibt noch keine Kacheln für die Region (`web/tiles/` ist leer). Bau in O2.
- **Höhen.** Nur Mapzen (rund 30 m). Wallonien und NRW haben feinere Modelle (Kandidaten).
- **Gebäude, Felswände, Hangneigung.** Die Mechanik im Frontend ist da, Daten für Ostbelgien fehlen. Ohne Kacheln zeigt die Karte die OSM-Gebäude und OSM-Klippen.
- **Ortsteile.** Der Rechtsklick nennt Gemeinde bzw. Kreis und Land, keine Ortsteile. Belgische Teilgemeinden kämen aus Statbel oder OSM (admin_level 9).
- **Ortsverzeichnis.** `app/data/orte.json` ist noch das Verzeichnis aus Landblick-RLP (Region Rheinland-Pfalz plus 80 km, reicht bis Lüttich und Aachen, deckt die DG also ab, ist aber zu groß). Mit `tools/build_gazetteer.py` neu bauen, sobald Overpass antwortet.
- **MeteoAlarm-Gebiete.** `app/data/nuts_meteoalarm.json` enthält noch französische Gebiete. Mit `tools/build_nuts.py` auf BE33, BE34 und LU00 kürzen.
- **Gewässernetz.** `tools/build_gewaessernetz.py` für Weser, Amel, Our, Warche, Rur, Göhl laufen lassen.
- **UV-Index.** `dwd_gesundheit` nutzt die Station Hahn (Hunsrück, gut 120 km weg). Nächste DWD-UV-Station klären oder KMI-UV nehmen.
- **Suchindex.** `web/data/suche_geo.json` entsteht aus den Kacheln (O2).

## Quellen im Register, die genauer hingehören

- `lbm_baustellen` und `hochwasser_rlp` liefern Rheinland-Pfalz; in der Region nur den Eifelkreis Bitburg-Prüm (Prüm, Bleialf, Dasburg). Bleiben, weil die Our Grenzfluss ist.
- `sgdnord_energie` liefert Windräder im Norden von Rheinland-Pfalz; in der Region nur den Eifelkreis.
- `gtfs_static` lädt Deutschland und Luxemburg. Belgische Fahrpläne fehlen (Kandidaten).
- `brf` ordnet Schlagzeilen über das Ortsverzeichnis zu; mit dem neuen Verzeichnis prüfen.

## Technik

- **Raumzellen.** 0,5 Grad ergeben für die Region nur rund acht Zellen. Prüfen, ob 0,25 Grad besser lädt (O4).
- **Desktop-App.** Bezeichner, Paketnamen und die Adresse des Kachelpakets (`PAKETE_MANIFEST` in `app/desktop.py`) zeigen noch auf Landblick-RLP. Vor dem ersten Desktop-Release umstellen.
- **Handbuch.** `docs/handbuch/` ist inhaltlich noch das Handbuch von Landblick-RLP mit angepasstem Titel. Kapitel 1, 4 und 9 neu schreiben.
