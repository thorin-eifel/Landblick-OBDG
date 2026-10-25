# Änderungen

## [0.1.0-alpha.1] – unveröffentlicht

### Neu

- Landblick-OBDG: Lagebild für die Deutschsprachige Gemeinschaft Belgiens plus 20 km, entstanden aus Landblick-RLP (Stand `0ba81c2`, 25. Oktober 2026).
- Region als Polygon aus OpenStreetMap: `tools/fetch_osm_grenzen.py` (Nominatim) und `tools/build_region.py` (Puffer, Gebietsgliederung, Kartengrenze der DG, Umriss für die Ortsnamen).
- Gebietsgliederung über vier Staaten: Gemeinden in Belgien, Luxemburg und den Niederlanden, Kreise in Deutschland; die DG als eigenes Land `BE-DG` im Filter.
- Rechtsklick-Auskunft nennt Gebiet und Land aus `web/geo/gebiete.geojson`.
- Bezugspunkt Eupen; Wetter- und Entfernungsangaben nennen ihn aus `region.yaml` statt fest verdrahtet.
- Radar, Wind und Blitze mit höherer Bildauflösung für die kleine Fläche.
- Plan O0 bis O7, ADR 0001, offene Punkte und Quellenkandidaten in `docs/obdg/`.

### Entfernt (nur für Rheinland-Pfalz)

- Werkzeuge für Landes-DGM1, Hausumringe, Hangneigung, Felswände, Verwaltungsflächen, Landesgrenze, LGB- und Geoportal-Kataloge, synthetischer RLP-Datenstand.
- Menüs „LGB Daten“ und „Landesdaten“ samt Fremdservern in der Content-Security-Policy.
- Quellen außerhalb der Fläche: PEGELONLINE, MeteoLux, CITA, Hub'Eau, Bison Futé, MobiData BW, Volksfreund sowie die abgeschalteten Presseportal und Themenradar.
