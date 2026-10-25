# ADR 0001: Region Ostbelgien plus 20 km

Status: vorgeschlagen am 25. Oktober 2026, wartet auf Freigabe durch den Betreiber

## Kontext

Landblick-RLP zeigt ein Lagebild aus offenen Daten für Rheinland-Pfalz plus 80 km. Der Betreiber will dasselbe für die Deutschsprachige Gemeinschaft Belgiens (DG) und 20 km rundum, als eigenes Projekt Landblick-OBDG. Die Architektur von Landblick-RLP ist schon flächenneutral: Die Region kommt aus `region.yaml`, der Geofilter aus `app/region.py`, der Export zerlegt in Raumzellen. Was nicht passt, sind die Landesbezüge: Grenzdaten aus BKG VG250 (nur Deutschland), Werkzeuge für das Landes-DGM1 und die Hausumringe von Rheinland-Pfalz, die Kartendienste des Geoportals RLP, Quellen aus Baden-Württemberg und Frankreich.

Die DG hat neun Gemeinden in zwei Teilen: das Eupener Land im Norden (Eupen, Kelmis, Lontzen, Raeren) und die Belgische Eifel im Süden (Amel, Büllingen, Burg-Reuland, Bütgenbach, Sankt Vith). Zusammen rund 846 km². Mit 20 km Puffer berührt die Region vier Staaten: Belgien (Wallonien, Provinz Lüttich und Luxemburg), Deutschland (Städteregion Aachen, Kreise Düren, Euskirchen und Heinsberg in NRW, Eifelkreis Bitburg-Prüm und Landkreis Vulkaneifel in Rheinland-Pfalz), Luxemburg (Ösling) und die Niederlande (Süd-Limburg), dazu ein Zipfel Flanderns (Voeren).

## Entscheidungen

1. Die Fläche ist ein Polygon: Grenze der DG (OpenStreetMap-Relation 2425209) plus 20 km. Beide Teile der DG wachsen mit dem Puffer zu einer Fläche zusammen.
2. Grenzen kommen aus OpenStreetMap (ODbL), nicht aus nationalen Katastern. Es gibt keinen amtlichen Datensatz, der Belgien, Deutschland, Luxemburg und die Niederlande in einem Format abdeckt. `tools/fetch_osm_grenzen.py` holt sie über Nominatim, `tools/build_region.py` baut daraus Region, Gliederung und Kartengrenzen.
3. Die Gliederung für Filter und Zuordnung ist gemischt: Gemeinden in Belgien, Luxemburg und den Niederlanden, Kreise in Deutschland. Deutsche Gemeinden wären neben belgischen Gemeinden zu fein und für die Warnlage (DWD, NINA) ohne Nutzen.
4. Der Gebietsschlüssel trägt ein Landespräfix (`BE-63023`, `DE-05334`, `NL-GM0981`). Das Feld heißt weiter `ars`, damit Export und Frontend aus Landblick-RLP unverändert bleiben.
5. Die DG gilt im Filter als eigenes „Land“ (`BE-DG`), getrennt vom übrigen Wallonien (`BE-WAL`). Staatsrechtlich ist sie eine Gemeinschaft innerhalb der Region Wallonien; für ein Lagebild der DG zählt die Sprachgrenze.
6. Bezugspunkt für Entfernungen ist Eupen (Sitz von Parlament und Regierung der DG). Startansicht ist die ganze Region.
7. Rheinland-Pfalz-spezifische Werkzeuge (DGM1, Hausumringe, Hangneigung, Felswände, Verwaltungsflächen, LGB- und Geoportal-Kataloge) entfallen. Die Mechanik dahinter (optionale Kachelpakete für Gebäude, Felswände, Hang) bleibt im Frontend, bis Ostbelgien eigene Daten bekommt.
8. Neue Quellen aus Belgien, den Niederlanden und NRW werden einzeln auf Lizenz geprüft, bevor ein Sammler entsteht. Bis dahin stehen sie in `docs/obdg/quellen-kandidaten.md`, nicht im Register.
9. SQLite, Raumzellen, statische Auslieferung und Desktop-App bleiben wie in Landblick-RLP.

## Alternativen

- Statbel-Gemeindegrenzen plus BKG plus CBS plus ACT: amtlich, aber vier Formate, vier Lizenzen, vier Stände. Für eine Fläche von rund 4 000 km² nicht verhältnismäßig.
- Nur die DG ohne Puffer: Die Lage endet nicht an der Gemeindegrenze. Hochwasser an der Weser kommt aus dem Hohen Venn, der Verkehr auf der E40 aus Aachen.
- Kreis um Eupen: Sankt Vith und Burg-Reuland lägen am Rand oder draußen; die DG ist 70 km lang und 15 km schmal.

## Folgen

Kleinere Fläche, weniger Daten, schnellere Exporte. Die Quellenlage ist dünner als in Rheinland-Pfalz: Belgien veröffentlicht Warnungen (BE-Alert) und Verkehr (Wallonien) nicht offen maschinenlesbar. Das Lagebild hat dort Lücken, und die Seite sagt das. Die Phasen O0 bis O7 stehen in `docs/obdg/plan.md`.
