# Quellenkandidaten für Ostbelgien

Stand 25. Oktober 2026, nach O3. Ein Kandidat kommt erst ins Register (`sources.yaml`), wenn Lizenz, Ratenlimit und Endpunkt an der Primärquelle bestätigt sind. Unklar heißt aus. Die Spalte „Befund“ sagt, was geprüft wurde und woran es hängt.

## In O3 geprüft

| Kandidat | Ergebnis | Befund |
|---|---|---|
| Hochwasserportal NRW (LANUK, OpenHygon) | **angebunden** als `nrw_pegel` | dl-de/zero-2.0 laut OpenGeodata.NRW und open.nrw. Tagesdatei gegen 5 Uhr, 15-Minuten-Werte der letzten sieben Tage, 18 Pegel in der Region. Kein Echtzeitstrom; die Echtzeit-Klassen bleiben bei `lhp_hochwasser`. |
| SPW Hydrométrie (schon im Register) | **nur privat** | Mentions légales verbieten Weitergabe an Dritte und öffentliche Verbreitung ohne schriftliche Zustimmung. Anfrage vorbereitet: `anfrage-spw.md`. |
| KMI SYNOP (schon im Register) | **bestätigt** | Metadatensatz RMI_DATASET_SYNOP im belgischen Geoportal: keine Zugangsbeschränkung, Creative Commons Namensnennung. |
| IRCEL-CELINE (schon im Register) | **bestätigt** | GetCapabilities des WFS nennt CC BY 4.0. |
| BRF (schon im Register) | **umgestellt** auf den Regionalfeed | Lizenz weiter ungeklärt (nur Titel und Link). Regionalfeed liefert sechs von zehn Meldungen mit Ort in der Region statt null. |
| TEC (Busse in der DG), GTFS | **aus** | Datei frei abrufbar (opendata.tec-wl.be, 81 MB). Das Portal data.belgianmobility.io nennt CC BY 4.0 („Source: [PTO] – Open Data – [Datum]“), verlangt für manche Downloads aber zusätzlich die Annahme von Nutzungsbedingungen; die Open-Data-Seite des TEC antwortete mit 403. Die Bedingungen lesen, dann als weiterer Feed in `gtfs_static` (der Sammler kann das schon). |
| SNCB/NMBS, GTFS | **aus** | Eigene Lizenz mit unterschriebenem Vertrag, Weitergabe der Rohdaten ausgeschlossen. Das Portal nennt CC BY 4.0; der Widerspruch ist nicht geklärt. |
| Höchstpreise Kraftstoff Belgien (FÖD Wirtschaft) | **aus** | Kein Datensatz mit Lizenz gefunden (weder auf data.gov.be noch beim FÖD). Veröffentlicht wird täglich auf economie.fgov.be; Wiederverwendung beim FÖD erfragen. |
| Waterschap Limburg (Geul) | **aus** | Keine offene Schnittstelle und keine Lizenz gefunden. |
| Rijkswaterstaat | **nicht nötig** | Keine Messstelle in der Region; die Maas liegt außerhalb. |
| KNMI | **zurückgestellt** | CC BY 4.0, aber Schlüssel nötig, und die nächste Station (Maastricht/Beek) liegt außerhalb. |
| Grenzecho | **aus** | Keine offene Lizenz; wie BRF nur nach Erlaubnis des Verlags. |

## Weiterhin offen

| Bereich | Kandidat | Betreiber | Stand |
|---|---|---|---|
| Warnungen | BE-Alert | Nationales Krisenzentrum | keine offene Schnittstelle bekannt; im Notfall auf be-alert.be verweisen |
| Wetterwarnungen | KMI direkt | KMI | MeteoAlarm deckt das ab |
| UV-Index | KMI-UV | KMI | näher als DWD Bonn; Lizenz wie SYNOP prüfen |
| Verkehr | Trafiroutes (E40, E42, N-Straßen) | SPW Mobilité et Infrastructures | Schnittstelle und Bedingungen erfragen |
| Baustellen | WalOnMap, Chantiers | SPW | Bedingungen wie bei der Hydrometrie befürchten, prüfen |
| Strahlung | Telerad | FANC/AFCN | unbekannt |
| Gelände | Relief Wallonien (MNT, LIDAR) | SPW | Geoportail Wallonie nennt für einzelne Datensätze CC BY 4.0, für dieses prüfen |
| Gelände | DGM1 NRW | Geobasis NRW | dl-de/zero-2.0 |
| Gebäude | PICC | SPW | prüfen |
| Ortsteile | Statistische Sektoren, Teilgemeinden | Statbel | Open Data, prüfen |
| Verkehr | Straßen.NRW Baustellen | Straßen.NRW | prüfen |
| Verkehr | NDW (DATEX II) | Nationaal Dataportaal Wegverkeer | A76 bei Heerlen am Rand |
