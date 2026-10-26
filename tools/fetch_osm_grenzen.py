#!/usr/bin/env python3
"""Lädt die Grenze der Deutschsprachigen Gemeinschaft und die Gebiete im Umkreis aus OpenStreetMap (Nominatim).

Zweck:      Rohdaten für tools/build_region.py. Schreibt zwei GeoJSON-Dateien in --out-dir:
            kern.geojson    die Kernfläche (OSM-Relation, Standard 2425209 = Deutschsprachige Gemeinschaft)
            gebiete.geojson Verwaltungsgebiete im Umkreis: Gemeinden in Belgien, Luxemburg und den Niederlanden,
                            Kreise in Deutschland (dort wäre die Gemeindeebene für ein Filtermenü zu fein)
            Läuft einmal pro Jahr oder nach Gebietsreformen, nicht im Betrieb.
Quelle:     Nominatim (nominatim.openstreetmap.org), Daten © OpenStreetMap-Mitwirkende, ODbL 1.0.
            Nutzungsregeln: höchstens 1 Anfrage je Sekunde, eindeutiger User-Agent mit Kontakt, keine Dauerabfragen.
            Overpass wäre eleganter, ist für einen einmaligen Bau aber oft überlastet (429/502/504).
Verfahren:  Ein Raster von Prüfpunkten (Standard 3 km) über den Kasten um die Kernfläche plus Puffer. Je Punkt ein
            Reverse-Geocoding auf Gemeindeebene (zoom 10), in Deutschland zusätzlich auf Kreisebene (zoom 8). Die
            gefundenen Relationen werden danach gebündelt mit Umriss abgerufen. In Belgien liefert zoom 10 oft die
            Teilgemeinde (admin_level 9, z. B. Eynatten statt Raeren); solche Treffer löst ein zweiter Schritt über
            die Adresshierarchie (/details) zur Gemeinde (admin_level 8) auf, je NIS-Code nur einmal.
            Gemeinden, die kleiner als eine Rasterzelle sind, können durchrutschen; --extra nimmt Relationen von Hand dazu.
Parameter:  --relation   OSM-Relation der Kernfläche
            --buffer-km  Puffer, für den die Gebiete gesammelt werden (Standard 20, mit 3 km Zuschlag)
            --step-km    Rasterweite
            --extra      zusätzliche Relationen, z. B. --extra 2425330 2425331
            --contact    Kennung für den User-Agent (Pflicht laut Nominatim-Regeln): Mailadresse oder Projektadresse
                         (https://…), sonst LANDBLICK_CONTACT
            --nur-aufloesen  kein Raster, nur den zweiten Schritt auf ein vorhandenes gebiete.geojson anwenden
            --nur-namen  kein Raster, nur die Namen in allen Sprachen (namedetails) an ein vorhandenes gebiete.geojson hängen
Beispiel:   python tools/fetch_osm_grenzen.py --out-dir build/osm-grenzen --contact betreiber@example.org
Abhängig:   requirements-tools.txt (httpx, shapely, pyproj)
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
import time
from pathlib import Path

import httpx
from pyproj import Transformer
import numpy as np
import shapely
from shapely.geometry import Point, shape

log = logging.getLogger("fetch_osm_grenzen")

NOMINATIM = "https://nominatim.openstreetmap.org"
PAUSE_S = 1.1
# Lokale transversale Mercator-Projektion um die Region: Strecken in Metern ohne Zonengrenze (UTM 31/32 läuft bei 6° Ost
# mitten durch Ostbelgien). Verzerrung bis 60 km vom Mittelmeridian unter 0,005 Prozent.
LOCAL_TM = "+proj=tmerc +lat_0=50.4 +lon_0=6.1 +k=1 +x_0=0 +y_0=0 +ellps=GRS80 +units=m +no_defs"
# Verwaltungsebene, die als Gebiet zählt: Gemeinde (8) in Belgien, Luxemburg, Niederlande; Kreis (6) in Deutschland.
ZIEL_EBENE = {"be": 8, "lu": 8, "nl": 8, "de": 6}


class Nominatim:
    """Dünner Client mit fester Pause zwischen den Anfragen und einfacher Wiederholung bei 429/5xx."""

    def __init__(self, contact: str):
        self._client = httpx.Client(timeout=60, headers={"User-Agent": f"Landblick-OBDG Regionsbau ({contact})"})
        self._last = 0.0

    def get(self, path: str, params: dict) -> object:
        for attempt in range(4):
            wait = self._last + PAUSE_S - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            r = self._client.get(f"{NOMINATIM}/{path}", params=params)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 500, 502, 503, 504):
                log.warning("%s: HTTP %s, neuer Versuch in %d s", path, r.status_code, 2 ** (attempt + 1))
                time.sleep(2 ** (attempt + 1))
                continue
            r.raise_for_status()
        raise RuntimeError(f"Nominatim {path}: nach 4 Versuchen keine Antwort")


def lookup(nom: Nominatim, relations: list[int]) -> list[dict]:
    """Relationen mit Umriss und Adressangaben, in Bündeln zu 20 (Grenze der Lookup-Schnittstelle: 50)."""
    feats = []
    for i in range(0, len(relations), 20):
        chunk = relations[i:i + 20]
        data = nom.get("lookup", {"osm_ids": ",".join(f"R{r}" for r in chunk), "format": "geojson",
                                  "polygon_geojson": 1, "addressdetails": 1, "extratags": 1, "namedetails": 1})
        feats.extend(data.get("features", []))
    return feats


def _country(feat: dict) -> str:
    return ((feat.get("properties", {}).get("address") or {}).get("country_code") or "").lower()


def _level(feat: dict) -> int | None:
    lvl = (feat.get("properties", {}).get("extratags") or {}).get("admin_level")
    return int(lvl) if str(lvl or "").isdigit() else None


def aufloesen(nom: Nominatim, feats: list[dict]) -> list[dict]:
    """Ersetzt Treffer unterhalb der Zielebene (Teilgemeinden) durch die Gemeinde bzw. den Kreis darüber."""
    keep: dict[int, dict] = {}
    parents: set[int] = set()
    done_keys: set[str] = set()
    for f in feats:
        cc, lvl = _country(f), _level(f)
        ziel = ZIEL_EBENE.get(cc)
        osm_id = int(f["properties"]["osm_id"])
        if ziel is None or lvl == ziel:
            keep[osm_id] = f
            continue
        if lvl is not None and lvl < ziel:
            continue   # größer als die Zielebene (Provinz, Land): kein Gebiet
        nis = ((f["properties"].get("extratags") or {}).get("ref:INS") or "")[:5]
        key = f"{cc}:{nis}" if nis else f"{cc}:R{osm_id}"
        if key in done_keys:
            continue
        done_keys.add(key)
        det = nom.get("details", {"osmtype": "R", "osmid": osm_id, "addressdetails": 1, "format": "json"})
        for a in (det.get("address") or []) if isinstance(det, dict) else []:
            if a.get("osm_type") == "R" and a.get("admin_level") == ziel:
                parents.add(int(a["osm_id"]))
                break
    neu = [r for r in sorted(parents) if r not in keep]
    log.info("Auflösung: %d Treffer auf Zielebene, %d übergeordnete Gebiete nachgeladen", len(keep), len(neu))
    return list(keep.values()) + lookup(nom, neu)


def namen_nachtragen(nom: Nominatim, feats: list[dict]) -> None:
    """Hängt namedetails (name, name:de, name:fr, …) an Features eines älteren Abrufs, der sie noch nicht hatte."""
    ids = [int(f["properties"]["osm_id"]) for f in feats]
    namen: dict[int, dict] = {}
    for i in range(0, len(ids), 20):
        data = nom.get("lookup", {"osm_ids": ",".join(f"R{r}" for r in ids[i:i + 20]), "format": "json", "namedetails": 1})
        for hit in data if isinstance(data, list) else []:
            namen[int(hit["osm_id"])] = hit.get("namedetails") or {}
    for f in feats:
        f["properties"]["namedetails"] = namen.get(int(f["properties"]["osm_id"]), {})
    log.info("Namen für %d von %d Gebieten nachgetragen", len(namen), len(feats))


def _write_gebiete(out_dir: Path, feats: list[dict]) -> None:
    keep = [f for f in feats if f.get("geometry", {}).get("type") in ("Polygon", "MultiPolygon")]
    log.info("%d Gebiete mit Umriss (%d ohne Fläche verworfen)", len(keep), len(feats) - len(keep))
    (out_dir / "gebiete.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": keep},
                                                        ensure_ascii=False), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--relation", type=int, default=2425209)
    ap.add_argument("--buffer-km", type=float, default=20.0)
    ap.add_argument("--step-km", type=float, default=3.0)
    ap.add_argument("--extra", type=int, nargs="*", default=[])
    ap.add_argument("--contact", default=os.environ.get("LANDBLICK_CONTACT", ""))
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--nur-aufloesen", action="store_true")
    ap.add_argument("--nur-namen", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(message)s")
    if "@" not in args.contact and not args.contact.startswith("https://"):
        log.error("--contact (oder LANDBLICK_CONTACT) muss eine Mailadresse oder eine Projektadresse (https://…) sein, Nominatim verlangt eine Kennung")
        return 2

    nom = Nominatim(args.contact)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    if args.nur_namen:
        path = args.out_dir / "gebiete.geojson"
        data = json.loads(path.read_text(encoding="utf-8"))
        namen_nachtragen(nom, data["features"])
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return 0
    if args.nur_aufloesen:
        feats = json.loads((args.out_dir / "gebiete.geojson").read_text(encoding="utf-8"))["features"]
        _write_gebiete(args.out_dir, aufloesen(nom, feats))
        return 0
    kern = lookup(nom, [args.relation])
    if not kern:
        log.error("Relation %s nicht gefunden", args.relation)
        return 1
    (args.out_dir / "kern.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": kern},
                                                          ensure_ascii=False), encoding="utf-8")
    to_m = Transformer.from_crs("EPSG:4326", LOCAL_TM, always_xy=True).transform
    to_ll = Transformer.from_crs(LOCAL_TM, "EPSG:4326", always_xy=True).transform
    kern_m = shapely.transform(shape(kern[0]["geometry"]), lambda xy: np.column_stack(to_m(xy[:, 0], xy[:, 1])))
    zone_m = kern_m.buffer((args.buffer_km + 3) * 1000)
    minx, miny, maxx, maxy = zone_m.bounds
    step = args.step_km * 1000
    punkte = [(x, y) for x in _frange(minx, maxx, step) for y in _frange(miny, maxy, step) if zone_m.contains(Point(x, y))]
    log.info("Kernfläche %.0f km², %d Prüfpunkte im Raster %.1f km", kern_m.area / 1e6, len(punkte), args.step_km)

    found: dict[int, str] = {r: "extra" for r in args.extra}
    for n, (x, y) in enumerate(punkte, 1):
        lon, lat = to_ll(x, y)
        hit = nom.get("reverse", {"lat": f"{lat:.5f}", "lon": f"{lon:.5f}", "zoom": 10, "format": "jsonv2",
                                  "addressdetails": 1})
        if not isinstance(hit, dict) or "error" in hit:
            continue
        cc = (hit.get("address") or {}).get("country_code", "")
        if cc == "de":
            hit = nom.get("reverse", {"lat": f"{lat:.5f}", "lon": f"{lon:.5f}", "zoom": 8, "format": "jsonv2"})
        if isinstance(hit, dict) and hit.get("osm_type") == "relation":
            found.setdefault(int(hit["osm_id"]), cc)
        if n % 50 == 0:
            log.info("%d/%d Punkte, %d Gebiete", n, len(punkte), len(found))
    found.pop(args.relation, None)
    _write_gebiete(args.out_dir, aufloesen(nom, lookup(nom, sorted(found))))
    meta = {"quelle": "Nominatim / OpenStreetMap", "lizenz": "ODbL 1.0", "relation": args.relation,
            "buffer_km": args.buffer_km, "step_km": args.step_km, "abgerufen": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    (args.out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("fertig: %s", args.out_dir)
    return 0


def _frange(a: float, b: float, step: float):
    n = int(math.floor((b - a) / step)) + 1
    return (a + i * step for i in range(n))


if __name__ == "__main__":
    sys.exit(main())
