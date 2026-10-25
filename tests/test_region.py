"""Tests für app/region.py: Kreis (Prüffläche), Polygon Ostbelgien plus 20 km, Löcher, Gliederung, Geschwindigkeit."""
from __future__ import annotations

import json
import random
import time
from pathlib import Path

import pytest

from app import region
from app.region import Gliederung, PolygonIndex

BASE = Path(__file__).resolve().parent.parent
REG = region.load(BASE / "region.yaml")


# ---------------------------------------------------------------- Kreis: Prüffläche der Sammlertests (aus Landblick-RLP)
def test_radius_region_matches_old_constants():
    r = region.load(BASE / "tests" / "fixtures" / "region-irrel-120.yaml")
    assert r.mode == "radius" and r.radius_km == 120.0
    assert r.bbox == (48.76, 4.78, 50.93, 8.13)          # alter Wert von config.BBOX
    assert (r.ref_lat, r.ref_lon) == (49.84615562322509, 6.456057281843173)
    assert r.contains(49.85, 6.45) and r.contains(49.61, 6.13)         # Irrel, Luxemburg-Stadt
    assert not r.contains(48.58, 7.75)                                  # Straßburg: 130 km
    assert not r.contains(50.93, 4.78)                                  # Kastenecke: im Kasten, außerhalb des Kreises


def test_radius_edge_points():
    r = region.load(BASE / "tests" / "fixtures" / "region-irrel-120.yaml")
    d_lat = 120 / 111.195
    assert r.contains(r.ref_lat + d_lat * 0.995, r.ref_lon) and not r.contains(r.ref_lat + d_lat * 1.005, r.ref_lon)


def test_center_override_by_env(monkeypatch):
    monkeypatch.setenv("LANDBLICK_CENTER_LAT", "50.0")
    monkeypatch.setenv("LANDBLICK_CENTER_LON", "8.0")
    r = region.load(BASE / "tests" / "fixtures" / "region-irrel-120.yaml")
    assert (r.ref_lat, r.ref_lon) == (50.0, 8.0) and r.contains(50.0, 8.0) and not r.contains(49.0, 5.5)


# ---------------------------------------------------------------- Polygon: Ostbelgien plus 20 km
POLY_FILE = BASE / "app/data/region/obdg_plus20.json"


@pytest.mark.parametrize("name,lat,lon", [
    ("Eupen", 50.6295, 6.0353), ("Kelmis", 50.7167, 6.0000), ("Raeren", 50.6731, 6.1153), ("Lontzen", 50.6833, 6.0167),
    ("Bütgenbach", 50.4256, 6.2050), ("Büllingen", 50.4083, 6.2556), ("Amel", 50.3528, 6.1736), ("Sankt Vith", 50.2833, 6.1269),
    ("Burg-Reuland", 50.1972, 6.1389), ("Ouren (Dreiländereck)", 50.1400, 6.1350),
    ("Malmedy", 50.4256, 6.0277), ("Verviers", 50.5891, 5.8624), ("Aachen", 50.7753, 6.0839), ("Monschau", 50.5550, 6.2400),
    ("Vaals", 50.7706, 6.0186), ("Clervaux", 50.0547, 6.0314), ("Prüm", 50.2098, 6.4194), ("Vielsalm", 50.2847, 5.9150),
])
def test_polygon_contains_core_and_buffer(name, lat, lon):
    assert REG.contains(lat, lon), name


@pytest.mark.parametrize("name,lat,lon", [
    ("Lüttich", 50.6326, 5.5797), ("Maastricht", 50.8514, 5.6910), ("Düren", 50.8000, 6.4833), ("Bitburg", 49.9747, 6.5256),
    ("Luxemburg-Stadt", 49.6116, 6.1319), ("Bastogne", 50.0036, 5.7186), ("Köln", 50.9375, 6.9603), ("Irrel", 49.8462, 6.4561),
])
def test_polygon_excludes_far_places(name, lat, lon):
    assert not REG.contains(lat, lon), name


def test_polygon_is_one_area_bridging_both_parts_of_the_dg():
    """Eupener Land und Belgische Eifel hängen erst über den Puffer zusammen: die Region ist eine Fläche ohne Löcher."""
    data = json.loads(POLY_FILE.read_text(encoding="utf-8"))
    assert len(data["polygons"]) == 1 and len(data["polygons"][0]) == 1


def test_polygon_edges_just_inside_and_outside():
    """An den äußersten Eckpunkten: 0,01° (ca. 1 km) nach innen liegt drin, 0,01° nach außen nicht."""
    data = json.loads(POLY_FILE.read_text(encoding="utf-8"))
    pts = [p for poly in data["polygons"] for ring in poly for p in ring]
    n, s = max(pts, key=lambda p: p[1]), min(pts, key=lambda p: p[1])
    e, w = max(pts, key=lambda p: p[0]), min(pts, key=lambda p: p[0])
    assert REG.contains(n[1] - 0.01, n[0]) and not REG.contains(n[1] + 0.01, n[0])
    assert REG.contains(s[1] + 0.01, s[0]) and not REG.contains(s[1] - 0.01, s[0])
    assert REG.contains(e[1], e[0] - 0.01) and not REG.contains(e[1], e[0] + 0.01)
    assert REG.contains(w[1], w[0] + 0.01) and not REG.contains(w[1], w[0] - 0.01)


def test_polygon_bbox_and_query_circle_cover_everything():
    lat0, lon0, lat1, lon1 = REG.bbox
    assert 49.9 < lat0 < 50.0 and 50.9 < lat1 < 51.0 and 5.6 < lon0 < 5.75 and 6.6 < lon1 < 6.75
    data = json.loads(POLY_FILE.read_text(encoding="utf-8"))
    assert all(region.haversine_km(REG.query_lat, REG.query_lon, p[1], p[0]) <= REG.query_radius_km
               for poly in data["polygons"] for ring in poly for p in ring)
    assert REG.radius_km is None and "OpenStreetMap" in REG.attribution
    assert (REG.ref_name, round(REG.ref_lat, 2), round(REG.ref_lon, 2)) == ("Eupen", 50.63, 6.04)


def test_polygon_input_licence_and_checksum_documented():
    data = json.loads(POLY_FILE.read_text(encoding="utf-8"))
    assert data["licence"] == "ODbL-1.0" and len(data["sha256_input"]) == 64 and data["buffer_km"] == 20.0
    assert data["kern_relation"] == 2425209


# ---------------------------------------------------------------- Löcher, Teilflächen
def test_index_hole_and_second_part():
    outer = [[0, 0], [10, 0], [10, 10], [0, 10]]
    hole = [[4, 4], [6, 4], [6, 6], [4, 6]]
    island = [[20, 0], [22, 0], [22, 2], [20, 2]]
    idx = PolygonIndex([[outer, hole], [island]])
    assert idx.contains(1, 1) and not idx.contains(5, 5)           # Loch (lat 5, lon 5)
    assert idx.contains(1, 21) and not idx.contains(1, 15)         # zweite Teilfläche, Lücke dazwischen
    assert not idx.contains(11, 5) and not idx.contains(-1, 5)


def test_index_rejects_empty():
    with pytest.raises(ValueError):
        PolygonIndex([[[[0, 0], [1, 0]]]])


@pytest.mark.parametrize("cfg,msg", [
    ("mode: kreis\nreference: {lat: 1, lon: 2}\n", "mode"),
    ("mode: radius\nreference: {lat: 1}\nradius_km: 5\n", "reference"),
    ("mode: radius\nreference: {lat: 1, lon: 2}\nradius_km: 0\n", "radius_km"),
])
def test_bad_config_fails_loudly(tmp_path, cfg, msg):
    p = tmp_path / "r.yaml"
    p.write_text(cfg)
    with pytest.raises(ValueError, match=msg):
        region.load(p)


# ---------------------------------------------------------------- Gliederung
def test_gliederung_gebiet_and_land():
    g = Gliederung()
    assert g.kreis(50.6295, 6.0353) == {"ars": "BE-63023", "name": "Eupen", "land": "BE-DG"}
    assert g.kreis(50.2833, 6.1269) == {"ars": "BE-63067", "name": "Sankt Vith", "land": "BE-DG"}
    assert g.kreis(50.4256, 6.0277)["land"] == "BE-WAL"                    # Malmedy: Wallonien, nicht DG
    assert g.kreis(50.7753, 6.0839)["land"] == "DE-NW"                     # Aachen
    assert g.kreis(50.2098, 6.4194)["land"] == "DE-RP"                     # Prüm
    assert g.kreis(50.7706, 6.0186)["land"] == "NL-LI"                     # Vaals
    assert g.kreis(50.0547, 6.0314)["land"] == "LU"                        # Clervaux
    assert g.kreis(49.61, 6.13) is None                                    # Luxemburg-Stadt: außerhalb
    assert "OpenStreetMap" in g.attribution


def test_gliederung_has_all_nine_dg_municipalities_with_unique_keys():
    g = Gliederung()
    dg = sorted(k["name"] for k, _ in g._items if k["land"] == "BE-DG")
    assert dg == sorted(["Amel", "Büllingen", "Burg-Reuland", "Bütgenbach", "Eupen", "Kelmis", "Lontzen", "Raeren", "Sankt Vith"])
    keys = [k["ars"] for k, _ in g._items]
    assert len(keys) == len(set(keys))
    assert all(k[:3] in ("BE-", "DE-", "NL-", "LU-", "OSM") for k in keys)


# ---------------------------------------------------------------- Tempo
def test_contains_speed_after_prefilter():
    rnd = random.Random(7)
    pts = [(rnd.uniform(49.8, 51.1), rnd.uniform(5.5, 6.9)) for _ in range(20000)]
    t = time.perf_counter()
    for la, lo in pts:
        REG.contains(la, lo)
    per_point_us = (time.perf_counter() - t) / len(pts) * 1e6
    assert per_point_us < 20, f"{per_point_us:.1f} µs je Punkt"


# ---------------------------------------------------------------- Regression: Kreis entscheidet wie die alte Formel
def test_radius_region_equals_old_formula_on_random_points():
    r = region.load(BASE / "tests" / "fixtures" / "region-irrel-120.yaml")
    lat0, lon0, lat1, lon1 = 48.76, 4.78, 50.93, 8.13               # alte BBOX
    rnd = random.Random(42)
    diff = 0
    for _ in range(30000):
        la, lo = rnd.uniform(48.5, 51.2), rnd.uniform(4.5, 8.5)
        old = lat0 <= la <= lat1 and lon0 <= lo <= lon1 and region.haversine_km(49.84615562322509, 6.456057281843173, la, lo) <= 120.0
        diff += old != r.contains(la, lo)
    assert diff == 0


def test_margin_extends_radius_and_polygon():
    r = region.load(BASE / "tests" / "fixtures" / "region-irrel-120.yaml")
    d = 120 / 111.195
    assert not r.contains(r.ref_lat + d * 1.02, r.ref_lon) and r.contains(r.ref_lat + d * 1.02, r.ref_lon, margin_km=5)
    data = json.loads(POLY_FILE.read_text(encoding="utf-8"))
    n = max((p for poly in data["polygons"] for ring in poly for p in ring), key=lambda p: p[1])
    assert not REG.contains(n[1] + 0.03, n[0]) and REG.contains(n[1] + 0.03, n[0], margin_km=5)
