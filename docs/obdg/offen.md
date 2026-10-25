# Offene Punkte

Stand 25. Oktober 2026. Was im Gerüst noch nicht stimmt oder nicht geprüft ist. Neue Quellen stehen getrennt in `quellen-kandidaten.md`.

## Lizenz und Recht

- **Lizenz des Codes.** Das neue Repository wurde mit einer MIT-Lizenz angelegt, der übernommene Code stand in Landblick-RLP unter GPL-3.0. Das geht, solange der Betreiber alleiniger Urheber ist. Vor dem ersten Release entscheiden und die Zeile in der README angleichen.
- **Prüfvermerke im Register.** `zuletzt_geprüft` und `lizenz_hinweis` stammen aus Landblick-RLP. Sie gelten für den Dienst, nicht für diese Fläche. Je Quelle neu prüfen.
- **Impressum und Datenschutz.** Verantwortlicher und Anschrift sind aus Landblick-RLP übernommen. Prüfen, ob für ein Angebot mit Schwerpunkt Belgien zusätzliche Angaben nötig sind.
- **DSFA.** `docs/dsfa-entwurf.md` ist der Entwurf aus Landblick-RLP und nennt dessen Fläche. Für Ostbelgien neu fassen (O7).

## Daten und Karte

Stand nach O2 (`o2-kartenbasis.md`).

- **Karte gebaut, nicht versioniert.** Basiskarte, Relief, Suchindex und Gewässernetz entstehen mit `tools/kartenbasis.sh` und liegen nicht im Repository. Für den Windows-Installer fehlt noch ein Release `kacheln-1` mit den Paketen.
- **Höhen.** Nur Mapzen (rund 30 m), bis Zoom 12. Wallonien und NRW haben feinere Modelle (Kandidaten).
- **Gebäude, Felswände, Hangneigung.** Die Mechanik im Frontend ist da, Daten für Ostbelgien fehlen. Ohne Kacheln zeigt die Karte die OSM-Gebäude und OSM-Klippen.
- **Ortsteile.** Der Rechtsklick nennt Gemeinde bzw. Kreis und Land, keine Ortsteile. Belgische Teilgemeinden kämen aus Statbel oder OSM (admin_level 9).
- **Ortsverzeichnis.** Zuschnitt des RLP-Verzeichnisses mit deutschen Namensformen. Frisch aus Overpass nachbauen (`python tools/build_gazetteer.py`), sobald Overpass antwortet.
- **Pegel NRW.** Das Länderportal (`lhp_hochwasser`) liefert für Rur, Inde und Vicht nichts. Hochwasser NRW direkt anbinden (O3).
- **UV-Index.** `dwd_gesundheit` nutzt die Station Hahn (Hunsrück, gut 120 km weg). Nächste DWD-UV-Station klären oder KMI-UV nehmen.
- **Symbole.** `tools/fetch_icons.sh` muss lokal laufen (UXWing-Lizenz verbietet Weitergabe im Repository).

## Quellen im Register, die genauer hingehören

- `lbm_baustellen` und `hochwasser_rlp` liefern Rheinland-Pfalz; in der Region nur den Eifelkreis Bitburg-Prüm (Prüm, Bleialf, Dasburg). Bleiben, weil die Our Grenzfluss ist.
- `sgdnord_energie` liefert Windräder im Norden von Rheinland-Pfalz; in der Region nur den Eifelkreis.
- `gtfs_static` lädt Deutschland und Luxemburg. Belgische Fahrpläne fehlen (Kandidaten).
- `brf` ordnet Schlagzeilen über das Ortsverzeichnis zu; mit dem neuen Verzeichnis prüfen.

## Technik

- **Raumzellen.** 0,5 Grad ergeben für die Region nur rund acht Zellen. Prüfen, ob 0,25 Grad besser lädt (O4).
- **Desktop-App.** Bezeichner und Paketnamen sind umgestellt, das Nachladepaket von Landblick-RLP ist abgeschaltet (O2). Ein Installer für Ostbelgien wurde noch nicht gebaut.
- **Handbuch.** `docs/handbuch/` ist inhaltlich noch das Handbuch von Landblick-RLP mit angepasstem Titel. Kapitel 1, 4 und 9 neu schreiben.
