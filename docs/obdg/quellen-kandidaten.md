# Quellenkandidaten für Ostbelgien

Stand 25. Oktober 2026. Hier steht, was für Ostbelgien plus 20 km fehlt und woher es kommen könnte. Nichts davon ist geprüft oder angebunden. Ein Kandidat kommt erst ins Register (`sources.yaml`), wenn Lizenz, Ratenlimit und Endpunkt an der Primärquelle bestätigt sind. Bis dahin gilt: unklar heißt aus.

Die Angaben zu Lizenzen sind Kenntnisstand, keine Prüfung. Jede Zeile braucht vor dem Bau einen Blick auf die Nutzungsbedingungen des Anbieters.

## Belgien

| Bereich | Kandidat | Betreiber | Lizenz nach Kenntnis | Stand |
|---|---|---|---|---|
| Warnungen | BE-Alert | Nationales Krisenzentrum | keine offene Schnittstelle bekannt | vermutlich nicht machbar; im Notfall auf be-alert.be verweisen |
| Wetterwarnungen | KMI/IRM Warnungen (direkt, nicht über MeteoAlarm) | Königliches Meteorologisches Institut | KMI-Opendata, Bedingungen prüfen | MeteoAlarm deckt das heute ab |
| Wettervorhersage | KMI ALARO/AROME Opendata | KMI | prüfen | Alternative zu Bright Sky/MET Norway für den belgischen Teil |
| Verkehr | Trafiroutes / Verkehrszentrum Wallonien (E40, E42, N-Straßen) | SPW Mobilité et Infrastructures | unbekannt | Schnittstelle und Bedingungen erfragen |
| Baustellen | WalOnMap, Chantiers | SPW | Licence ouverte Wallonie (prüfen) | |
| Kraftstoff | Offizielle Höchstpreise (Programmvertrag) | FÖD Wirtschaft | öffentliche Bekanntmachung, Wiederverwendung prüfen | täglich, ein Wert je Sorte für ganz Belgien, wie STATEC in Luxemburg |
| Strahlung | Telerad | FANC/AFCN | unbekannt | Messnetz um Kernanlagen; Tihange außerhalb der Region |
| ÖPNV | GTFS SNCB/NMBS | SNCB | eigene Nutzungsbedingungen, prüfen | Bahnhöfe Eupen, Welkenraedt, Verviers |
| ÖPNV | GTFS TEC | TEC (Busse in der DG) | prüfen | |
| Medien | Grenzecho | Grenzecho | keine offene Lizenz; wie BRF nur Schlagzeile, Zeit, Link | Erlaubnis beim Verlag erfragen |
| Gelände | Relief Wallonien (MNT, LIDAR) | SPW | prüfen, Wallonien veröffentlicht viel unter CC BY 4.0 | für Höhenkacheln und Felswände |
| Gebäude | PICC (Projet informatique de cartographie continue) | SPW | prüfen | für eine Gebäudeebene wie die Hausumringe in RLP |
| Ortsteile | Statbel Statistische Sektoren, Teilgemeinden | Statbel | Open Data (prüfen) | für Ortsteile im Rechtsklick (Eynatten, Hergenrath, Elsenborn …) |

## Niederlande (Süd-Limburg)

| Bereich | Kandidat | Betreiber | Lizenz nach Kenntnis | Stand |
|---|---|---|---|---|
| Pegel | Waterinfo / Water Webservices | Rijkswaterstaat | CC0 (prüfen) | Maas liegt außerhalb; Geul und Gulp über Waterschap Limburg |
| Pegel | Waterschap Limburg | Waterschap Limburg | prüfen | Geul (Hochwasser Juli 2021) |
| Wetter | KNMI Data Platform | KNMI | CC BY 4.0 (prüfen), Schlüssel nötig | Station Maastricht/Beek liegt knapp außerhalb |
| Verkehr | NDW (DATEX II) | Nationaal Dataportaal Wegverkeer | offen (prüfen) | A76 bei Heerlen am Rand |
| Warnungen | MeteoAlarm Niederlande | KNMI über EUMETNET | wie MeteoAlarm BE | NUTS- oder EMMA-Gebiete prüfen |

## Deutschland (NRW)

| Bereich | Kandidat | Betreiber | Lizenz nach Kenntnis | Stand |
|---|---|---|---|---|
| Pegel | Hochwasserportal NRW / ELWAS | LANUK NRW | dl-de/zero-2.0 (prüfen) | Rur, Inde, Vicht, Urft; heute nur über das Länderportal |
| Gelände | DGM1 NRW | Geobasis NRW | dl-de/zero-2.0 | |
| Verkehr | Straßen.NRW Baustellen | Straßen.NRW | prüfen | Landes- und Bundesstraßen um Monschau |
