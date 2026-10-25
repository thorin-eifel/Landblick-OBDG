# Offene Punkte

Stand 25. Oktober 2026. Was im Gerüst noch nicht stimmt oder nicht geprüft ist. Neue Quellen stehen getrennt in `quellen-kandidaten.md`.

## Lizenz und Recht

- **Lizenz des Codes.** Das neue Repository wurde mit einer MIT-Lizenz angelegt, der übernommene Code stand in Landblick-RLP unter GPL-3.0. Das geht, solange der Betreiber alleiniger Urheber ist. Vor dem ersten Release entscheiden und die Zeile in der README angleichen.
- **Pegel Wallonien nur privat.** Die Bedingungen des SPW verbieten die öffentliche Verbreitung ohne schriftliche Zustimmung. `wallonie_pegel` steht auf `nutzung: privat`: in der Desktop-App (Privatmodus als Standard) läuft sie, im öffentlichen Betrieb fehlt sie. Anfrage an den SPW: Entwurf in `anfrage-spw.md`, noch nicht verschickt.
- **Prüfvermerke im Register.** KMI, IRCEL, SPW, BRF und LANUK sind am 25.10.2026 geprüft (O3). Die übrigen `zuletzt_geprüft` und `lizenz_hinweis` stammen aus Landblick-RLP und gelten für den Dienst, nicht für diese Fläche.
- **Impressum und Datenschutz.** Verantwortlicher und Anschrift sind aus Landblick-RLP übernommen. Prüfen, ob für ein Angebot mit Schwerpunkt Belgien zusätzliche Angaben nötig sind.
- **DSFA.** `docs/dsfa-entwurf.md` ist der Entwurf aus Landblick-RLP und nennt dessen Fläche. Für Ostbelgien neu fassen (O7).

## Daten und Karte

Stand nach O2 (`o2-kartenbasis.md`).

- **Karte gebaut, nicht versioniert.** Basiskarte, Relief, Suchindex und Gewässernetz entstehen mit `tools/kartenbasis.sh` und liegen nicht im Repository. Für den Windows-Installer fehlt noch ein Release `kacheln-1` mit den Paketen.
- **Höhen.** Nur Mapzen (rund 30 m), bis Zoom 12. Wallonien und NRW haben feinere Modelle (Kandidaten).
- **Gebäude, Felswände, Hangneigung.** Die Mechanik im Frontend ist da, Daten für Ostbelgien fehlen. Ohne Kacheln zeigt die Karte die OSM-Gebäude und OSM-Klippen.
- **Ortsteile.** Der Rechtsklick nennt Gemeinde bzw. Kreis und Land, keine Ortsteile. Belgische Teilgemeinden kämen aus Statbel oder OSM (admin_level 9).
- **Ortsverzeichnis.** Zuschnitt des RLP-Verzeichnisses mit deutschen Namensformen. Frisch aus Overpass nachbauen (`python tools/build_gazetteer.py`), sobald Overpass antwortet.
- **Pegel NRW.** Angebunden (`nrw_pegel`), aber aus der Tagesdatei des Landes: Werte bis zu einem Tag alt. Echtzeit-Hochwasserklassen kommen über `lhp_hochwasser`.
- **UV-Index.** DWD-Station Bonn (rund 76 km von Eupen). KMI-UV wäre näher, Lizenz prüfen.
- **Belgien ohne Verkehr und Warnungen.** Keine offene Quelle für Verkehr (Wallonien) und keine für Bevölkerungswarnungen (BE-Alert). Belgische Fahrpläne (TEC, SNCB) hängen an Nutzungsbedingungen, siehe `quellen-kandidaten.md`.
- **OSM-Quellen nicht live geprüft.** Overpass war in O2 und O3 durchgehend überlastet.
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
