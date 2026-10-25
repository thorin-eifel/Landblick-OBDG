#!/usr/bin/env python3
"""Abfragepunkte für Tankerkönig (Umkreissuche, höchstens 25 km) über die deutsche Fläche der Region legen.

Zweck:    Die Umkreissuche liefert höchstens 25 km je Abfrage. Ein Sechseckgitter mit Abstand 43 km (Radius 24,8 km je Zelle)
          deckt die Fläche lückenlos; behalten werden Punkte, deren Kreis (23 km, etwas knapper gerechnet) deutsches Gebiet
          innerhalb der Region berührt. Belgien, Luxemburg und die Niederlande fehlen in der Quelle und bekommen keine Punkte.
Eingabe:  Polygon der aktiven Region (region.yaml → polygon_file) und app/data/region/gebiete.json (OSM, ODbL)
Ausgabe:  app/data/region/tank_grid.json: {"radius_km": 25, "spacing_km": 43, "points": [{"lat", "lon", "rad"}], ...}
Aufruf:   python tools/build_tank_grid.py [--out PFAD] [--spacing-km 43]
Rechnung: lokale Ebene in km (Mitte Eupen); Verzerrung über einen Breitengrad unter 1 %, durch den knappen Radius abgefangen.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import yaml
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent.parent
LAT0, LON0 = 50.63, 6.04
KX, KY = 111.32 * math.cos(math.radians(50.45)), 111.2


def to_km(lon: float, lat: float) -> tuple[float, float]:
    return (lon - LON0) * KX, (lat - LAT0) * KY


def to_deg(x: float, y: float) -> tuple[float, float]:
    return LAT0 + y / KY, LON0 + x / KX


def polys(rings_list: list) -> list[Polygon]:
    return [Polygon([to_km(*p) for p in rings[0]], [[to_km(*p) for p in r] for r in rings[1:]]) for rings in rings_list]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "app" / "data" / "region" / "tank_grid.json")
    ap.add_argument("--spacing-km", type=float, default=43.0)
    ap.add_argument("--cover-km", type=float, default=23.0, help="Radius, mit dem ein Punkt deutsches Gebiet berühren muss")
    a = ap.parse_args()
    poly_file = yaml.safe_load((ROOT / "region.yaml").read_text(encoding="utf-8"))["polygon_file"]
    region = unary_union(polys(json.loads((ROOT / poly_file).read_text())["polygons"]))
    kreise = json.loads((ROOT / "app/data/region/gebiete.json").read_text())
    de = unary_union([p for k in kreise["kreise"] if k["land"].startswith("DE") for p in polys(k["polygons"])]).intersection(region)
    minx, miny, maxx, maxy = de.bounds
    d = a.spacing_km
    rows = int((maxy - miny) / (d * math.sqrt(3) / 2)) + 3
    cols = int((maxx - minx) / d) + 3
    pts = []
    for j in range(-1, rows):
        for i in range(-1, cols):
            x = minx + i * d + (d / 2 if j % 2 else 0)
            y = miny + j * d * math.sqrt(3) / 2
            if de.distance(Point(x, y)) <= a.cover_km:
                lat, lon = to_deg(x, y)
                pts.append({"lat": round(lat, 4), "lon": round(lon, 4), "rad": 25})
    out = {"radius_km": 25, "spacing_km": d, "cover_km": a.cover_km, "points": pts,
           "source": "Gitter über die deutsche Fläche der Region (Grenzen © OpenStreetMap-Mitwirkende, ODbL)", "built_by": "tools/build_tank_grid.py"}
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(pts)} Punkte, Abstand {d} km, deutsche Fläche {de.area:.0f} km² → {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
