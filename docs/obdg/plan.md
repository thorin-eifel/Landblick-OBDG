# Landblick-OBDG: Ablaufplan

Stand 25. Oktober 2026. Ziel-Repository: github.com/thorin-eifel/Landblick-OBDG. Entscheidung: `docs/adr/0001-region-obdg.md`.

## Ausgangslage

Landblick-OBDG ist aus Landblick-RLP hervorgegangen (Stand `0ba81c2`, 25. Oktober 2026). Übernommen sind Sammler, Datenbank, Export, Frontend, Desktop-App und Betriebswerkzeuge. Neu sind die Region, die Gliederung, das Quellenregister und die Texte. Entfernt ist, was nur für Rheinland-Pfalz taugte. Das ist Phase O0 und O1; der Rest steht unten.

## Zielbild

Die Region ist die Grenze der Deutschsprachigen Gemeinschaft plus 20 km, als ein Polygon. Der Kasten liegt bei rund 49,95 bis 50,93 Grad Nord und 5,67 bis 6,69 Grad Ost, etwa 110 mal 70 km. In Reichweite liegen Aachen, Verviers, Spa, Malmedy, Stavelot, Vielsalm, Gouvy, Clervaux, Troisvierges, Prüm, Hellenthal, Monschau, Vaals und Kerkrade. Lüttich liegt knapp draußen. Bezugspunkt für Entfernungen ist Eupen.

Unverändert gelten die Leitplanken: Ereignisse statt Personen, Quelle, Alter und Lizenz an jedem Datum, kein Tracking, keine Drittanbieter im Browser, unklare Lizenzen bleiben aus.

## Phasen

Eine Einheit ist ein konzentrierter Arbeitstag samt Prüfzeit des Betreibers. Schätzungen, keine Messwerte.

**O0. Gerüst (erledigt mit dem ersten Pull Request).**
Code aus Landblick-RLP übernommen, RLP-Werkzeuge und -Quellen entfernt, Texte auf Ostbelgien, neue README, ADR, dieser Plan. Tests grün.

**O1. Raumabstraktion (erledigt mit dem ersten Pull Request).**
`tools/fetch_osm_grenzen.py` und `tools/build_region.py` bauen Region, Gebietsgliederung (Gemeinden BE/LU/NL, Kreise DE), Grenze der DG für die Karte und den Umriss für die Ortsnamen der Übersicht. `region.yaml` zeigt auf `app/data/region/obdg_plus20.json`. Tests mit Grenzfällen: beide Teile der DG, Aachen, Vaals, Clervaux, Prüm, Lüttich (draußen), Malmedy (drin, Wallonien).

**O2. Kartenbasis (2 Einheiten).**
Protomaps-Kacheln für die Region (`tools/build_region_tiles.py` mit dem Polygon), Städtekerne Zoom 15 für Eupen, Sankt Vith, Kelmis, Aachen, Verviers und Malmedy. Höhenkacheln (`tools/build_dem.py`, Mapzen), später feiner aus dem Relief Walloniens und dem DGM1 NRW, beide offen, Lizenz je prüfen. Suchindex und Ortsverzeichnis (`tools/build_gazetteer.py`, `tools/build_search_index.py`) neu, Gewässernetz für Weser/Vesdre, Amel/Amblève, Our, Warche, Rur, Inde, Göhl/Geul, Ourthe. Läuft auf dem Rechner des Betreibers, Claude Code liefert Skript und Prüfbericht.

**O3. Datenpipeline (3 Einheiten).**
Je Quelle aus dem Register: Lauf gegen die echte Fläche, Fixtures aus der Region, Ausfalltest. Danach die Kandidaten aus `quellen-kandidaten.md` in dieser Reihenfolge, jeweils nach Lizenzprüfung: Hochwasser NRW (Rur, Inde, Vicht), Rijkswaterstaat und Waterschap Limburg (Geul), KNMI-Stationen, offizielle Höchstpreise Kraftstoff Belgien (FÖD Wirtschaft), GTFS der SNCB und des TEC, Grenzecho-Schlagzeilen.

**O4. Export und Auslieferung (1 Einheit).**
Größenbudgets für die kleinere Fläche neu setzen (Startpaket, Zellen), Raumzellen von 0,5 Grad prüfen: die Region hat nur rund acht Zellen, eventuell 0,25 Grad.

**O5. Frontend (2 Einheiten).**
Texte und Menüs zweisprachig denken (Ortsnamen in Belgien haben oft eine französische und eine deutsche Form: Malmedy, Weismes/Waimes, Bleiberg/Plombières). Messpunkte für die Bildrate: Eupen, Sankt Vith, Aachen, Gesamtansicht. Barrierefreiheit wie in Landblick-RLP.

**O6. Betrieb und Härtung (2 Einheiten).**
Zeitplan, Backup, Runbook, Chaos-Test, 7-Tage-Dauerlauf (`tools/dauerlauf.py`).

**O7. Abnahme (1 Einheit).**
Vorführung, Mängelliste, DSFA und Impressum für Belgien prüfen (DSGVO gilt gleich, die belgische Datenschutzbehörde ist eine andere Anlaufstelle), Seite „Quellen und Lizenzen“ vollständig.

## Quellen: was je Bereich ansteht

| Bereich | Übernommen und passend | Fehlt, Kandidat |
|---|---|---|
| Warnungen | MeteoAlarm (BE, LU), DWD und NINA für den deutschen Teil | BE-Alert (keine offene Schnittstelle bekannt), KMI-Warnungen direkt, MeteoAlarm Niederlande |
| Pegel | SPW Wallonien, AGE Luxemburg, Hochwasser RLP (Prüm, Our), Hochwasserportal der Länder (NRW) | Hochwasser NRW direkt, Waterschap Limburg, Rijkswaterstaat |
| Verkehr | Autobahn GmbH (A4, A44, A60), Mobilitätsatlas RLP | Wallonien (Trafiroutes, E40/E42), NDW Niederlande |
| Wetter | KMI-Stationen, DWD, Bright Sky, MET Norway | KMI-Vorhersage, KNMI |
| Luft, Strahlung | IRCEL-CELINE, UBA, BfS ODL, Sensor.Community | Telerad (FANC), Tihange liegt rund 70 km westlich, außerhalb |
| Tanken | Tankerkönig (deutscher Teil), Höchstpreise Luxemburg | Höchstpreise Belgien (FÖD Wirtschaft) |
| ÖPNV | GTFS Deutschland und Luxemburg | SNCB/NMBS, TEC (Busse in der DG) |
| Medien | BRF | Grenzecho (nur Schlagzeile, Lizenz klären) |

## Risiken

- **Dünne Quellenlage in Belgien.** Warnungen und Verkehr fehlen offen. Das Lagebild sagt es, statt Lücken zu füllen.
- **Sprachen.** Belgische Quellen liefern Französisch oder Niederländisch. Übersetzt wird nicht automatisch; Titel bleiben im Original, wo die Quelle keine deutsche Fassung hat.
- **OSM-Grenzen.** Sie sind gut gepflegt, aber nicht amtlich. Für Filter und Zuordnung reicht das, für Rechtsfragen nicht.
- **Nominatim.** Der Grenzabruf ist ein einmaliger Bau mit 1 Anfrage je Sekunde. Bei Gebietsreformen neu laufen lassen.
