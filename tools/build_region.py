#!/usr/bin/env python3
"""Baut die Region (Kernfläche plus Puffer), die Gebietsgliederung und die Grenzdateien der Karte.

Zweck:      Aus den Rohdaten von tools/fetch_osm_grenzen.py (kern.geojson, gebiete.geojson) entstehen:
              app/data/region/<name>.json   gepuffertes Polygon (lon/lat) für app/region.py
              app/data/region/gebiete.json  Gebiete der Fläche mit Schlüssel, Name, Land für Filter und Zuordnung
              web/geo/kern.geojson          Umriss der Kernfläche (rote Linie auf der Karte)
              web/geo/gebiete.geojson       Gebietsflächen für die Rechtsklick-Auskunft (Name unter dem Zeiger)
              web/js/lage/kern-umriss.js    grober Kernumriss für den Stilausdruck "within" (Ortsnamen der Übersicht)
            Läuft einmal pro Jahresstand der Grenzen, nicht im Betrieb.
Quelle:     OpenStreetMap über Nominatim, © OpenStreetMap-Mitwirkende, ODbL 1.0.
Schlüssel:  Das Feld `ars` heißt aus historischen Gründen so (Amtlicher Regionalschlüssel); hier ist es ein Gebietsschlüssel
            mit Landespräfix: BE-<NIS-Code>, DE-<Regionalschlüssel>, NL-<CBS-Gemeindecode>, LU-<LAU-2-Code>. Fehlt der amtliche
            Code in OSM, steht OSM-R<Relation> da. Das Präfix verhindert Zusammenstöße zwischen den Nummernsystemen.
Länder:     BE-DG Deutschsprachige Gemeinschaft (die neun Gemeinden), BE-WAL übriges Wallonien, BE-VLG Flandern, DE-NW, DE-RP,
            NL-LI, LU. Die DG ist staatsrechtlich eine Gemeinschaft, keine Region; für das Filtermenü zählt sie wie ein Land.
Beispiel:   python tools/build_region.py --raw build/osm-grenzen --buffer-km 20 --name obdg_plus20
Abhängig:   requirements-tools.txt (shapely, pyproj)
Hinweis:    Gerechnet wird in einer lokalen transversalen Mercator-Projektion (Mittelmeridian 6,1° Ost), weil die
            UTM-Zonengrenze 31/32 bei 6° Ost mitten durch Ostbelgien läuft. Die Verzerrung bleibt im Gebiet unter 0,005 Prozent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from pathlib import Path

import shapely
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import unary_union

log = logging.getLogger("build_region")

ROOT = Path(__file__).resolve().parent.parent
LOCAL_TM = "+proj=tmerc +lat_0=50.4 +lon_0=6.1 +k=1 +x_0=0 +y_0=0 +ellps=GRS80 +units=m +no_defs"
ATTRIBUTION = "Grenzen: © OpenStreetMap-Mitwirkende, ODbL 1.0 (über Nominatim, Stand {stand})"

# Die neun Gemeinden der Deutschsprachigen Gemeinschaft (NIS-Codes). Alles andere in Belgien richtet sich nach der Provinz.
DG_NIS = {"63001": "Amel", "63012": "Büllingen", "63087": "Burg-Reuland", "63013": "Bütgenbach", "63023": "Eupen",
          "63040": "Kelmis", "63048": "Lontzen", "63061": "Raeren", "63067": "Sankt Vith"}
DE_LAND = {"05": "DE-NW", "07": "DE-RP"}


def _to(transformer):
    return lambda geom: shapely.transform(geom, lambda xy: _xy(transformer, xy))


def _xy(transformer, xy):
    import numpy as np
    x, y = transformer.transform(xy[:, 0], xy[:, 1])
    return np.column_stack([x, y])


def lonlat_rings(geom, digits: int = 5) -> list[list[list[list[float]]]]:
    """Shapely-Geometrie (lon/lat) → [[Außenring, Loch, ...], ...], Ringe ohne Schlusspunkt, gerundet."""
    polys = [geom] if geom.geom_type == "Polygon" else [g for g in getattr(geom, "geoms", []) if g.geom_type == "Polygon"]
    out = []
    for p in polys:
        rings = []
        for ring in [p.exterior, *p.interiors]:
            rings.append([[round(x, digits), round(y, digits)] for x, y in list(ring.coords)[:-1]])
        out.append(rings)
    return out


def _faltung(s: str) -> str:
    """Vergleichsform ohne Akzente und Groß-/Kleinschreibung: Bütgenbach und Butgenbach gelten als derselbe Name."""
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).casefold()


def andere_namen(name: str, namedetails: dict, land: str) -> dict[str, str]:
    """Die zweite Sprachform eines Gebiets, wenn sie wirklich abweicht: name_fr für die DG (Amel → Amblève),
    name_de für alle anderen außerhalb Deutschlands (Waimes → Weismes). Quelle: OSM name:de bzw. name:fr.
    Die Formen stehen so in OSM; manche sind alt und kaum noch im Gebrauch (Houffalize → Hohenfels). Das Frontend
    zeigt sie deshalb als Zusatz, nie an Stelle des amtlichen Namens."""
    if land.startswith("DE"):
        return {}
    key, tag = ("name_fr", "name:fr") if land == "BE-DG" else ("name_de", "name:de")
    alt = (namedetails or {}).get(tag) or ""
    if not alt or _faltung(alt) in _faltung(name):
        return {}
    return {key: alt}


def gebiet_meta(feat: dict) -> dict[str, str] | None:
    """Schlüssel, Name, Land und Ebene aus einem Nominatim-Feature. None für Flächen, die keine Verwaltungseinheit sind.
    Dazu name_de bzw. name_fr, wenn der Abruf namedetails enthält (andere_namen)."""
    meta = _gebiet_meta(feat)
    if meta is not None:
        meta.update(andere_namen(meta["name"], feat.get("properties", {}).get("namedetails") or {}, meta["land"]))
    return meta


def _gebiet_meta(feat: dict) -> dict[str, str] | None:
    p = feat.get("properties", {})
    tags = p.get("extratags") or {}
    addr = p.get("address") or {}
    cc = (addr.get("country_code") or "").lower()
    name = p.get("name") or p.get("localname") or ""
    rel = f"OSM-R{p.get('osm_id')}"
    if cc == "be":
        nis = tags.get("ref:INS") or ""
        if nis in DG_NIS:
            return {"ars": f"BE-{nis}", "name": DG_NIS[nis], "land": "BE-DG", "ebene": "Gemeinde"}
        land = "BE-VLG" if addr.get("ISO3166-2-lvl4") == "BE-VLG" else "BE-WAL"   # Voeren/Fourons gehört zu Flandern
        return {"ars": f"BE-{nis}" if nis else rel, "name": name, "land": land, "ebene": "Gemeinde"}
    if cc == "de":
        rs = tags.get("de:regionalschluessel") or tags.get("de:amtlicher_gemeindeschluessel") or ""
        land = DE_LAND.get(rs[:2], "DE")
        if land == "DE":
            land = "DE-RP" if "Rheinland" in (addr.get("state") or "") else "DE-NW" if "Nordrhein" in (addr.get("state") or "") else "DE"
        return {"ars": f"DE-{rs[:5]}" if rs else rel, "name": name, "land": land, "ebene": "Kreis"}
    if cc == "nl":
        code = tags.get("ref:gemeentecode") or ""
        return {"ars": f"NL-GM{int(code):04d}" if code.isdigit() else rel, "name": name, "land": "NL-LI", "ebene": "Gemeente"}
    if cc == "lu":
        code = tags.get("ref:lau2") or tags.get("ref") or ""
        return {"ars": f"LU-{code}" if code else rel, "name": name, "land": "LU", "ebene": "Gemeinde"}
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", type=Path, required=True, help="Ordner mit kern.geojson, gebiete.geojson, meta.json")
    ap.add_argument("--buffer-km", type=float, default=20.0)
    ap.add_argument("--simplify-m", type=float, default=50.0, help="Vereinfachung von Region und Gebieten")
    ap.add_argument("--umriss-m", type=float, default=150.0, help="Vereinfachung des JS-Umrisses")
    ap.add_argument("--name", default="obdg_plus20")
    ap.add_argument("--root", type=Path, default=ROOT)
    args = ap.parse_args(argv)
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(message)s")

    kern_raw = (args.raw / "kern.geojson").read_bytes()
    geb_raw = (args.raw / "gebiete.geojson").read_bytes()
    raw_meta = json.loads((args.raw / "meta.json").read_text(encoding="utf-8"))
    stand = raw_meta.get("abgerufen", "")[:10]
    to_m = _to(Transformer.from_crs("EPSG:4326", LOCAL_TM, always_xy=True))
    to_ll = _to(Transformer.from_crs(LOCAL_TM, "EPSG:4326", always_xy=True))

    kern_ll = unary_union([shape(f["geometry"]) for f in json.loads(kern_raw)["features"]])
    kern_m = to_m(kern_ll)
    region_m = kern_m.buffer(args.buffer_km * 1000, quad_segs=32).simplify(args.simplify_m)
    region_ll = to_ll(region_m)
    log.info("Kern %.0f km², Region (Puffer %.0f km) %.0f km²", kern_m.area / 1e6, args.buffer_km, region_m.area / 1e6)

    gebiete, seen = [], set()
    for f in json.loads(geb_raw)["features"]:
        meta = gebiet_meta(f)
        if meta is None:
            continue
        g_m = to_m(shape(f["geometry"])).buffer(0)
        if not g_m.intersects(region_m) or g_m.intersection(region_m).area < 1e5:   # Randberührungen unter 0,1 km² zählen nicht
            continue
        if meta["ars"] in seen:
            continue
        seen.add(meta["ars"])
        gebiete.append({**meta, "polygons": lonlat_rings(to_ll(g_m.simplify(args.simplify_m)))})
    gebiete.sort(key=lambda k: (k["land"], k["name"]))
    dg = [g for g in gebiete if g["land"] == "BE-DG"]
    if len(dg) != len(DG_NIS):
        log.error("DG-Gemeinden gefunden: %d von %d (%s). Fehlende mit --extra in fetch_osm_grenzen.py nachholen.",
                  len(dg), len(DG_NIS), ", ".join(sorted(g["name"] for g in dg)))
        return 1

    meta = {"source": "OpenStreetMap via Nominatim (tools/fetch_osm_grenzen.py)", "stand": stand, "licence": "ODbL-1.0",
            "attribution": ATTRIBUTION.format(stand=stand), "kern_relation": raw_meta.get("relation"),
            "sha256_input": hashlib.sha256(kern_raw + geb_raw).hexdigest(), "buffer_km": args.buffer_km,
            "simplify_m": args.simplify_m, "tool": "tools/build_region.py"}
    out_region = args.root / "app" / "data" / "region"
    out_region.mkdir(parents=True, exist_ok=True)
    _write(out_region / f"{args.name}.json", {**meta, "polygons": lonlat_rings(region_ll)})
    _write(out_region / "gebiete.json", {**meta, "kreise": gebiete})

    kern_simpl = to_ll(kern_m.simplify(20))
    _write(args.root / "web" / "geo" / "kern.geojson", {"type": "FeatureCollection", "attribution": meta["attribution"], "features": [
        {"type": "Feature", "properties": {"name": "Deutschsprachige Gemeinschaft"}, "geometry": shapely.geometry.mapping(kern_simpl)}]})
    _write(args.root / "web" / "geo" / "gebiete.geojson", {"type": "FeatureCollection", "attribution": meta["attribution"], "features": [
        {"type": "Feature", "properties": {k: g[k] for k in ("ars", "name", "name_de", "name_fr", "land", "ebene") if k in g},
         "geometry": {"type": "MultiPolygon", "coordinates": [[ring + ring[:1] for ring in poly] for poly in g["polygons"]]}}
        for g in gebiete]})
    umriss = to_ll(kern_m.buffer(500).simplify(args.umriss_m))
    coords = [[ring + ring[:1] for ring in poly] for poly in lonlat_rings(umriss, 4)]
    n_pts = sum(len(r) for p in coords for r in p)
    js = ("// Erzeugt von tools/build_region.py aus OpenStreetMap (© OpenStreetMap-Mitwirkende, ODbL 1.0). Nicht von Hand ändern.\n"
          f"// Grober Umriss der Deutschsprachigen Gemeinschaft (500 m nach außen) für den Stilausdruck \"within\" ({n_pts} Punkte).\n"
          "export const KERN_UMRISS = " + json.dumps({"type": "MultiPolygon", "coordinates": coords}, separators=(",", ":")) + ";\n")
    (args.root / "web" / "js" / "lage" / "kern-umriss.js").write_text(js, encoding="utf-8")

    by_land: dict[str, int] = {}
    for g in gebiete:
        by_land[g["land"]] = by_land.get(g["land"], 0) + 1
    log.info("Gebiete: %d (%s)", len(gebiete), ", ".join(f"{k} {v}" for k, v in sorted(by_land.items())))
    b = region_ll.bounds
    log.info("Kasten der Region: %.3f–%.3f E, %.3f–%.3f N", b[0], b[2], b[1], b[3])
    return 0


def _write(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    log.info("%s: %d KB", path.relative_to(ROOT) if path.is_relative_to(ROOT) else path, path.stat().st_size // 1024)


if __name__ == "__main__":
    sys.exit(main())
