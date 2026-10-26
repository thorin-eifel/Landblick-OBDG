"""Zellenexport: teilt die Nutzdaten in Raumzellen, schreibt Startpaket und Manifest.

Zweck:      Das Frontend lädt zuerst `start.json` (klein), liest daraus und aus `manifest.json`, welche Zellen es gibt,
            und holt nur die Zellen im Bildausschnitt nach (`z/<x>_<y>/<art>.json`). Zellraster: app/cells.py (region.yaml → zellen_grad).
Dateien:    manifest.json              Version, Zellenliste, je Datei Größe und Prüfsumme, Warnungen zu Größenbudgets
            start.json                 Startpaket: Meta, Warnband, Quellenzustand, Zählwerte je Zelle (unter 512 KB)
            z/<x>_<y>/<art>.json       Arten: events, gewaesser, umwelt, haltestellen, landmarks, infrastruktur, sakral, energie, routen, anbau, kraftstoff
Kontrakt:   Jede Zellendatei trägt `source`/`sources` (Betreiber, Lizenz, Namensnennung), `stand` (wann sich der Inhalt zuletzt
            geändert hat) und `cell`. Zeitabhängiges (Alter, Status "veraltet", Abrufzeit je Lauf) steht NICHT in den Zellen,
            sonst änderte sich jede Datei bei jedem Lauf und der inkrementelle Upload wäre sinnlos. Das Alter rechnet das Frontend
            aus `start.json` (je Quelle `last_success` und `interval_s`) gegen die Uhr des Betrachters, nach derselben Regel wie
            `source_status` (web/js/rules.js).
Stabilität: Der Inhalt wird um flüchtige Felder bereinigt und gehasht. Ändert sich der Hash nicht, bleibt die Datei Byte für Byte
            wie zuvor (auch `stand`). Zustand dafür: `<out>/.export-state.json`.
Budgets:    Zelle je Datei 500 KB, Startpaket 512 KB. Überschreitung wird nicht abgeschnitten, sondern im Manifest und im Log gemeldet.
Linien:     Routen und Leitungen über mehrere Zellen werden je Zelle zugeschnitten (cells.clip_lines), Kennung dann "<id>@<zelle>".
"""
from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Callable

from . import cells as cellmod
from . import payloads
from . import region as regionmod
from .db import Storage
from .models import iso, utcnow
from .registry import Registry

log = logging.getLogger("landblick.export.cells")

CELL_BUDGET_BYTES = 500 * 1024
# Ostbelgien: Startpaket rund 41 KB (22 Zellen). Die 2 MB aus Landblick-RLP hätten ein Wachstum um das Fünfzigfache
# durchgelassen; 512 KB meldet einen Ausreißer früh und lässt Platz für Warnlagen.
START_BUDGET_BYTES = 512 * 1024
MANIFEST_VERSION = 1
STATE_NAME = ".export-state.json"
EVENT_LIMIT = 50000
ITEM_VOLATILE = {"age_s", "source_status", "fetched_at"}
SEV_RANK = {"info": 0, "notice": 1, "warning": 2, "critical": 3}


def _cells_point(item: dict[str, Any]) -> set[cellmod.Cell]:
    return cellmod.cells_for_point(item.get("lat"), item.get("lon"))


def _cells_feature(item: dict[str, Any]) -> set[cellmod.Cell]:
    return cellmod.cells_for_geometry(item.get("geometry"))


def _cells_route(item: dict[str, Any]) -> set[cellmod.Cell]:
    return cellmod.cells_for_lines(item.get("lines") or [])


def _cells_anbau(item: dict[str, Any]) -> set[cellmod.Cell]:
    return cellmod.cells_for_geometry(item.get("geometry"))


def _cells_energie(item: dict[str, Any]) -> set[cellmod.Cell]:
    """Punkte (Kraftwerk, Umspannwerk, Solarpark) nach Koordinate, Leitungen nach allen berührten Zellen."""
    return _cells_route(item) if item.get("lines") else _cells_point(item)


# Arten mit langen Linien (Routen, Leitungen): über mehrere Zellen wird die Linie je Zelle zugeschnitten statt ganz kopiert.
# Gemessen für Ostbelgien (25.10.2026): Routen 2,0 MB in den Zellen bei 1,0 MB als eine Datei, weil Fernwege durch bis zu
# acht Zellen laufen; eine Zelle lag mit 628 KB über dem Budget.
CLIP_KINDS = {"routen", "energie"}

# Art -> (Schlüssel der Liste in der Nutzlast, Zellenzuordnung)
KINDS: dict[str, tuple[str, Callable[[dict[str, Any]], set[cellmod.Cell]]]] = {
    "events": ("features", _cells_feature),
    "gewaesser": ("stations", _cells_point),
    "umwelt": ("stations", _cells_point),
    "haltestellen": ("stops", _cells_point),
    "landmarks": ("items", _cells_point),
    "infrastruktur": ("items", _cells_point),
    "sakral": ("items", _cells_point),
    "energie": ("items", _cells_energie),
    "routen": ("items", _cells_route),
    "anbau": ("features", _cells_anbau),
    "kraftstoff": ("stations", _cells_point),
}


GEO_KINDS = {"events", "gewaesser", "umwelt", "haltestellen", "kraftstoff"}   # Arten mit Punktbezug, die Kreis und Land tragen
_gliederung: regionmod.Gliederung | None = None
_kreis_cache: dict[tuple[float, float], dict[str, str] | None] = {}


def _gl() -> regionmod.Gliederung:
    global _gliederung
    if _gliederung is None:
        _gliederung = regionmod.Gliederung()
    return _gliederung


def kreis_of(lat: Any, lon: Any) -> dict[str, str] | None:
    """Gebiet (Schlüssel, Name, Land) zu einem Punkt; None außerhalb der Gliederung. Ergebnis wird auf 0,001 Grad (ca. 100 m) gemerkt."""
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        return None
    key = (round(lat, 3), round(lon, 3))
    if key not in _kreis_cache:
        _kreis_cache[key] = _gl().kreis(lat, lon)
    return _kreis_cache[key]


def _tag_geo(item: dict[str, Any]) -> None:
    """Hängt `ars` und `land` an (Ereignisse: in properties). Außerhalb der Gliederung bleibt `ars` leer, `land` kommt aus `region_tag`."""
    holder = item.get("properties") if isinstance(item.get("properties"), dict) else item
    k = kreis_of(holder.get("lat"), holder.get("lon"))
    if k:
        holder["ars"], holder["land"] = k["ars"], k["land"]
    else:
        tag = holder.get("region_tag")
        holder["ars"] = None
        # Standardwert des Modells ist "DE", auch für Punkte außerhalb Deutschlands: ein deutsches Kürzel ohne Gebiet heißt "unbekannt"
        holder["land"] = tag if isinstance(tag, str) and tag and not tag.startswith("DE") else None


def _strip(o: Any) -> Any:
    if isinstance(o, dict):
        return {k: _strip(v) for k, v in o.items() if k not in ITEM_VOLATILE}
    if isinstance(o, list):
        return [_strip(v) for v in o]
    return o


def _source_ref(src: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(src, dict) or not src.get("id"):
        return None
    keep = ("id", "name", "short_name", "betreiber", "interval_s", "attribution", "license", "license_verified")
    return {k: src.get(k) for k in keep}


def _envelope(kind: str, payload: dict[str, Any], list_key: str, registry: Registry, used_ids: set[str]) -> dict[str, Any]:
    env: dict[str, Any] = {"kind": kind}
    refs: dict[str, dict[str, Any]] = {}
    one = _source_ref(payload.get("source"))
    if one:
        refs[one["id"]] = one
    for s in payload.get("sources") or []:
        r = _source_ref(s)
        if r:
            refs[r["id"]] = r
    for sid in used_ids:
        if sid not in refs:
            try:
                e = registry.get(sid)
            except KeyError:
                continue
            refs[sid] = {"id": e.id, "name": e.name, "short_name": e.kurzname or e.name, "betreiber": e.betreiber,
                         "interval_s": e.intervall, "attribution": e.namensnennung, "license": e.lizenz, "license_verified": e.lizenz_geprueft}
    env["sources"] = sorted(refs.values(), key=lambda r: r["id"])
    return env


def _item_source_id(item: dict[str, Any]) -> str | None:
    if isinstance(item.get("properties"), dict):
        return item["properties"].get("source_id")
    return item.get("source_id")


def split_payload(kind: str, payload: dict[str, Any], registry: Registry) -> dict[cellmod.Cell, dict[str, Any]]:
    """Eine Nutzlast → Inhalt je Zelle (ohne `stand` und `cell`, die setzt der Aufrufer)."""
    list_key, locate = KINDS[kind]
    buckets: dict[cellmod.Cell, list[Any]] = {}
    sources_by_cell: dict[cellmod.Cell, set[str]] = {}
    for item in payload.get(list_key) or []:
        try:
            cs = locate(item)
        except ValueError as exc:
            log.warning("%s: %s (%s), Eintrag fehlt im Export", kind, exc, item.get("id") or item.get("name"))
            continue
        sid = _item_source_id(item)
        if kind in GEO_KINDS:
            item = copy.deepcopy(item)
            _tag_geo(item)
        clip = kind in CLIP_KINDS and len(cs) > 1 and isinstance(item.get("lines"), list) and item["lines"]
        for c in cs:
            entry = _strip(item)
            if clip:   # Linie über mehrere Zellen: je Zelle nur ihr Stück, Kennung je Zelle eindeutig (das Frontend führt nach Kennung zusammen)
                pieces = cellmod.clip_lines(item["lines"], c)
                if not pieces:
                    continue
                entry = {**entry, "lines": pieces, "id": f"{item.get('id')}@{cellmod.cell_id(c)}"}
            buckets.setdefault(c, []).append(entry)
            if sid:
                sources_by_cell.setdefault(c, set()).add(sid)
    out: dict[cellmod.Cell, dict[str, Any]] = {}
    for c, items in buckets.items():
        env = _envelope(kind, payload, list_key, registry, sources_by_cell.get(c, set()))
        if kind == "events" or payload.get("type") == "FeatureCollection":
            env["type"] = "FeatureCollection"
        env[list_key] = items
        out[c] = env
    return out


def _dumps(o: Any) -> bytes:
    return json.dumps(o, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def load_state(out: Path) -> dict[str, Any]:
    try:
        d = json.loads((out / STATE_NAME).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def flat_payloads(storage: Storage, registry: Registry) -> dict[str, dict[str, Any]]:
    """Die Nutzlasten, die in Zellen zerlegt werden (ungekürzt, Ereignisse bis EVENT_LIMIT)."""
    return {
        "events": payloads.events_payload(storage, registry, within="7d", exclude_types=("aircraft",), limit=EVENT_LIMIT),
        "gewaesser": payloads.gewaesser_payload(storage, registry, series_step=4),
        "umwelt": payloads.umwelt_payload(storage, registry),
        "haltestellen": payloads.haltestellen_payload(storage, registry),
        "landmarks": payloads.landmarks_payload(storage, registry),
        "infrastruktur": payloads.infrastruktur_payload(storage, registry),
        "sakral": payloads.sakral_payload(storage, registry),
        "energie": payloads.energie_payload(storage, registry),
        "routen": payloads.routen_payload(storage, registry),
        "anbau": payloads.anbau_payload(storage, registry),
        "kraftstoff": payloads.kraftstoff_payload(storage, registry),
    }


def build_cell_files(flat: dict[str, dict[str, Any]], registry: Registry, now_iso: str, prev: dict[str, Any], out: Path) -> tuple[dict[str, bytes], dict[str, Any], dict[str, Any]]:
    files: dict[str, bytes] = {}
    info: dict[str, Any] = {}
    state: dict[str, Any] = {}
    prev_files = prev.get("files", {}) if isinstance(prev, dict) else {}
    for kind, payload in flat.items():
        for c, content in split_payload(kind, payload, registry).items():
            rel = f"z/{cellmod.cell_id(c)}/{kind}.json"
            chash = _sha(_dumps(content))
            old = prev_files.get(rel)
            raw: bytes | None = None
            stand = now_iso
            if old and old.get("content_hash") == chash:
                try:
                    raw = (out / rel).read_bytes()
                    if _sha(raw) == old.get("sha256"):
                        stand = old.get("stand", now_iso)
                    else:
                        raw = None
                except OSError:
                    raw = None
            if raw is None:
                raw = _dumps({**content, "cell": cellmod.cell_id(c), "stand": stand})
            files[rel] = raw
            n = len(content.get(KINDS[kind][0], []))
            info[rel] = {"bytes": len(raw), "sha256": _sha(raw), "kind": kind, "cell": cellmod.cell_id(c), "items": n,
                         "over_budget": len(raw) > CELL_BUDGET_BYTES}
            state[rel] = {"content_hash": chash, "sha256": info[rel]["sha256"], "stand": stand}
    return files, info, state


def build_start(storage: Storage, registry: Registry, cell_info: dict[str, Any], events_payload: dict[str, Any], fuel_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Startpaket: alles, was die Seite beim ersten Bild braucht. Klein halten, kein Verlauf, keine Listen von Messstellen."""
    st = payloads.statuses(storage, registry)
    sources = [{"id": s["id"], "name": s["name"], "short_name": s["short_name"], "status": s["status"], "last_success": s["last_success"],
                "last_attempt": s["last_attempt"], "interval_s": s["interval_s"], "failing_since": s["failing_since"],
                "consecutive_failures": s["consecutive_failures"], "attribution": s["attribution"], "license": s["license"]}
               for s in st.values() if s["status"] != "disabled"]
    rank = {"ok": 0, "pending": 1, "degraded": 2, "stale": 3, "down": 4}
    overall = max((s["status"] for s in sources), key=lambda x: rank.get(x, 0), default="ok")
    warn = []
    sev_by_cell: dict[str, int] = {}
    for f in events_payload.get("features", []):
        p = f["properties"]
        r = SEV_RANK.get(p["severity"], 0)
        cs = sorted(cellmod.cell_id(c) for c in cellmod.cells_for_geometry(f.get("geometry")))
        for c in cs:
            sev_by_cell[c] = max(sev_by_cell.get(c, 0), r)
        if r >= 2 and p["type"] != "aircraft":
            kr = kreis_of(p.get("lat"), p.get("lon"))
            warn.append({"ars": kr["ars"] if kr else None, "land": kr["land"] if kr else p.get("region_tag"), **{"id": p["id"], "title": p["title"], "severity": p["severity"], "type": p["type"], "source_id": p["source_id"],
                         "source_short": p["source_short"], "valid_from": p["valid_from"], "valid_to": p["valid_to"],
                         "lat": p["lat"], "lon": p["lon"], "region_tag": p["region_tag"], "cells": cs[:12]}})
    warn.sort(key=lambda w: (-SEV_RANK[w["severity"]], w["title"]))
    cells: dict[str, dict[str, Any]] = {}
    totals: dict[str, int] = {}
    for rel, i in cell_info.items():
        c = cells.setdefault(i["cell"], {"counts": {}, "bytes": 0, "bbox": [round(v, 3) for v in cellmod.cell_bbox(cellmod.parse_cell_id(i["cell"]))]})
        c["counts"][i["kind"]] = i["items"]
        c["bytes"] += i["bytes"]
        totals[i["kind"]] = totals.get(i["kind"], 0) + i["items"]
    inv = {v: k for k, v in SEV_RANK.items()}
    for cid, c in cells.items():
        if cid in sev_by_cell:
            c["max_severity"] = inv[sev_by_cell[cid]]
    return {
        "version": MANIFEST_VERSION, "generated_at": iso(utcnow()), "meta": payloads.meta_payload(storage),
        "overall": overall, "sources": sources, "warnband": warn[:300], "warnband_total": len(warn),
        "counts": totals, "cells": cells, "kreise": kreise_table(), "einheiten": build_einheiten(events_payload.get("features", [])),
        "kraftstoff": {"stats": (fuel_payload or {}).get("stats"), "lu": (fuel_payload or {}).get("lu")},   # landesweit, nicht an Zellen gebunden
        "disclaimer": payloads.DISCLAIMER,
    }


def kreise_table() -> list[dict[str, str]]:
    """Alle Gebiete (Schlüssel, Name, Land, dazu name_de bzw. name_fr, wo es sie gibt) für das Filtermenü; ändert sich nur mit
    der Gliederungsdatei."""
    return sorted(({key: k[key] for key in ("ars", "name", "name_de", "name_fr", "land") if k.get(key)} for k, _ in _gl()._items),
                  key=lambda r: (r["land"], r["name"]))


# --- Verwaltungseinheiten für die Übersichtskarte -------------------------------------------------------------------------------
# Unter Zoom 8 zeigt die Karte keine Rasterzellen, sondern Zählwerte je Land und je Kreis (Lage = Mittelpunkt der Fläche), damit die
# Darstellung dem Land folgt und nicht dem technischen Raster. Die Zellen bleiben Sache des Backends.
LAND_NAMEN = {"BE-DG": "Deutschsprachige Gemeinschaft", "BE-WAL": "Wallonien", "BE-VLG": "Flandern", "DE-NW": "Nordrhein-Westfalen",
              "DE-RP": "Rheinland-Pfalz", "LU": "Luxemburg", "NL-LI": "Niederlande (Limburg)", "BE": "Belgien", "NL": "Niederlande"}
# Rückfall für Punkte ohne Gebiet (knapp außerhalb der Gliederung): feste Lage (Lon, Lat) und grober Rahmen (W, S, O, N) des Landesteils
# in der Region. Mit der Gliederung aus tools/build_region.py ist die Region lückenlos belegt; das hier fängt Grenzfälle.
AUSLAND = {"LU": ((6.00, 50.05), (5.75, 49.95, 6.20, 50.18)), "BE": ((5.90, 50.45), (5.67, 49.95, 6.45, 50.80)),
           "NL": ((5.95, 50.82), (5.75, 50.75, 6.10, 50.93))}
_kreis_geo: dict[str, dict[str, Any]] | None = None


def _ring_centroid(ring: list[list[float]]) -> tuple[float, float, float]:
    """(Fläche, Lon, Lat) des Schwerpunkts eines Rings; Fläche in Grad², vorzeichenlos."""
    a = cx = cy = 0.0
    for i in range(len(ring)):
        x1, y1 = ring[i][:2]
        x2, y2 = ring[(i + 1) % len(ring)][:2]
        w = x1 * y2 - x2 * y1
        a += w
        cx += (x1 + x2) * w
        cy += (y1 + y2) * w
    if abs(a) < 1e-12:
        return 0.0, ring[0][0], ring[0][1]
    return abs(a) / 2, cx / (3 * a), cy / (3 * a)


def kreis_geo() -> dict[str, dict[str, Any]]:
    """ARS → {name, land, lon, lat, bbox}. Der Punkt liegt in der Fläche des Kreises und in keiner anderen (Ringkreise um kreisfreie Städte)."""
    global _kreis_geo
    if _kreis_geo is not None:
        return _kreis_geo
    gl = _gl()
    out: dict[str, dict[str, Any]] = {}
    for k, idx in gl._items:
        parts = [_ring_centroid(poly[0]) for poly in k["polygons"] if poly]
        tot = sum(a for a, _, _ in parts) or 1.0
        lon0, lat0 = sum(a * x for a, x, _ in parts) / tot, sum(a * y for a, _, y in parts) / tot
        pt = (lon0, lat0)
        if (gl.kreis(lat0, lon0) or {}).get("ars") != k["ars"]:
            best = None
            n = 21
            for i in range(n):
                for j in range(n):
                    lon = idx.lon_min + (idx.lon_max - idx.lon_min) * (i + 0.5) / n
                    lat = idx.lat_min + (idx.lat_max - idx.lat_min) * (j + 0.5) / n
                    if (gl.kreis(lat, lon) or {}).get("ars") == k["ars"]:
                        d = (lon - lon0) ** 2 + (lat - lat0) ** 2
                        if best is None or d < best[0]:
                            best = (d, lon, lat)
            if best:
                pt = (best[1], best[2])
        out[k["ars"]] = {"name": k["name"], "land": k["land"], "lon": round(pt[0], 4), "lat": round(pt[1], 4),
                         "bbox": [round(v, 3) for v in (idx.lon_min, idx.lat_min, idx.lon_max, idx.lat_max)], "w": tot}
    _kreis_geo = out
    return out


def build_einheiten(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Zählwerte je Land und je Kreis für die Übersichtskarte: {key, level, name, land, n, sev, lon, lat, bbox}. Flugzeuge zählen nicht.

    Ein Punkt gehört zu seinem Kreis (deutsche Länder) oder zu seinem Auslandskürzel (region_tag); Punkte ohne beides bleiben ungezählt."""
    geo = kreis_geo()
    kreise: dict[str, list[int]] = {}
    laender: dict[str, list[int]] = {}
    inv = {v: k for k, v in SEV_RANK.items()}
    for f in features:
        p = f.get("properties") or {}
        if p.get("type") == "aircraft":
            continue
        r = SEV_RANK.get(p.get("severity"), 0)
        kr = kreis_of(p.get("lat"), p.get("lon"))
        if kr:
            c = kreise.setdefault(kr["ars"], [0, 0]); c[0] += 1; c[1] = max(c[1], r)
            c = laender.setdefault(kr["land"], [0, 0]); c[0] += 1; c[1] = max(c[1], r)
        else:
            tag = p.get("region_tag")
            if isinstance(tag, str) and tag in AUSLAND:
                c = laender.setdefault(tag, [0, 0]); c[0] += 1; c[1] = max(c[1], r)
    out: list[dict[str, Any]] = []
    for ars, (n, r) in kreise.items():
        g = geo[ars]
        out.append({"key": f"kreis:{ars}", "level": "kreis", "name": g["name"], "land": g["land"], "n": n, "sev": inv[r], "lon": g["lon"], "lat": g["lat"], "bbox": g["bbox"]})
    for land, (n, r) in laender.items():
        if land in AUSLAND:
            (lon, lat), bbox = AUSLAND[land]
        else:   # Schwerpunkt der Kreise des Landes, gewichtet nach Fläche
            ks = [g for g in geo.values() if g["land"] == land]
            tot = sum(g["w"] for g in ks) or 1.0
            lon, lat = sum(g["w"] * g["lon"] for g in ks) / tot, sum(g["w"] * g["lat"] for g in ks) / tot
            bbox = [min(g["bbox"][0] for g in ks), min(g["bbox"][1] for g in ks), max(g["bbox"][2] for g in ks), max(g["bbox"][3] for g in ks)]
        out.append({"key": f"land:{land}", "level": "land", "name": LAND_NAMEN.get(land, land), "land": land, "n": n, "sev": inv[r],
                    "lon": round(lon, 4), "lat": round(lat, 4), "bbox": [round(v, 3) for v in bbox]})
    out.sort(key=lambda e: (e["level"], e["key"]))
    return out


HASH_DROP = {"generated_at", "age_s", "last_attempt", "last_success", "fetched_at", "source_status", "status", "failing_since",
             "consecutive_failures", "last_error_or_note", "circuit_open_until", "active_events", "recent_runs"}
ALWAYS = {"start.json", "meta.json", "status.json", "aircraft.json"}     # Herzschlag: ändert sich je Lauf, klein
LEGACY_MAX_AGE_S = 1800                                                  # Flachdatei wird spätestens nach 30 Minuten neu hochgeladen


def _drop(o: Any) -> Any:
    if isinstance(o, dict):
        return {k: _drop(v) for k, v in o.items() if k not in HASH_DROP}
    if isinstance(o, list):
        return [_drop(v) for v in o]
    return o


def content_hash(name: str, raw: bytes) -> str:
    """Prüfsumme über den Inhalt ohne Zeitabhängiges (nur für JSON); Bilder und alles andere über die Bytes."""
    if name.endswith(".json"):
        try:
            return _sha(_dumps(_drop(json.loads(raw))))
        except ValueError:
            pass
    return _sha(raw)


def build_manifest(cell_info: dict[str, Any], other: dict[str, bytes], start_raw: bytes, now_iso: str, data_version: int, legacy: set[str]) -> dict[str, Any]:
    files: dict[str, Any] = {}
    for rel, i in cell_info.items():
        files[rel] = {**i, "content_hash": i["sha256"], "upload": "on_change"}
    for name, raw in other.items():
        files[name] = {"bytes": len(raw), "sha256": _sha(raw), "content_hash": content_hash(name, raw), "kind": "legacy" if name in legacy else "global",
                       "upload": "always" if name in ALWAYS else "on_change", "max_age_s": LEGACY_MAX_AGE_S}
    files["start.json"] = {"bytes": len(start_raw), "sha256": _sha(start_raw), "content_hash": _sha(start_raw), "kind": "start", "upload": "always",
                           "over_budget": len(start_raw) > START_BUDGET_BYTES}
    warnings = []
    for rel, i in files.items():
        if i.get("over_budget"):
            budget = START_BUDGET_BYTES if rel == "start.json" else CELL_BUDGET_BYTES
            warnings.append(f"{rel}: {i['bytes'] // 1024} KB über dem Budget von {budget // 1024} KB")
    return {
        "version": MANIFEST_VERSION, "generated_at": now_iso, "data_version": data_version,
        "grid": {"cell_deg": cellmod.CELL_DEG, "per_deg": cellmod.PER_DEG, "x": f"floor(lon*{cellmod.PER_DEG})",
                 "y": f"floor(lat*{cellmod.PER_DEG})", "path": "z/<x>_<y>/<art>.json"},
        "budgets": {"cell_bytes": CELL_BUDGET_BYTES, "start_bytes": START_BUDGET_BYTES},
        "cells": sorted({i["cell"] for i in cell_info.values()}),
        "files": files, "warnings": warnings,
    }


def write_atomic(out: Path, rel: str, raw: bytes) -> None:
    target = out / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.tmp")
    try:
        tmp.write_bytes(raw)
        os.replace(tmp, target)
    except OSError:
        tmp.unlink(missing_ok=True)   # Platte voll: halbe Temp-Datei nicht liegen lassen, die alte Zieldatei bleibt unberührt
        raise


def remove_stale(out: Path, keep: set[str]) -> int:
    """Zellendateien löschen, die der neue Stand nicht mehr kennt (nur lokal; der Upload löscht nie)."""
    n = 0
    zdir = out / "z"
    if not zdir.exists():
        return 0
    for p in zdir.rglob("*.json"):
        if p.relative_to(out).as_posix() not in keep:
            p.unlink()
            n += 1
    for d in sorted((p for p in zdir.rglob("*") if p.is_dir()), reverse=True):
        try:
            d.rmdir()
        except OSError:
            pass
    return n
