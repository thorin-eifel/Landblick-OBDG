#!/usr/bin/env python3
"""Ortsverzeichnis für die Ortszuordnung von Meldungen bauen (app/data/orte.json).

Zweck:     Meldungen nennen Orte ("Unfall in Weismes"), keine Koordinaten. Damit wir sie ohne externen
           Geocoder verorten können, liegt ein kleines Verzeichnis aus OpenStreetMap-Ortsknoten im Repository.
Quelle:    OpenStreetMap-Mitwirkende, ODbL 1.0 (Overpass-Abfrage place=city|town|village|hamlet|suburb)
Aufruf:    python tools/build_gazetteer.py                # holt Daten über Overpass-Spiegel
           python tools/build_gazetteer.py --input places.json   # liest eine vorhandene Overpass-Antwort
           python tools/build_gazetteer.py --zuschnitt alt.json  # schneidet ein vorhandenes orte.json auf die Region zu
Ergebnis:  app/data/orte.json: [{"n": Name, "lat": .., "lon": .., "k": Rang}], nur Orte in der Region plus 5 km Rand.
Namen:     In Ostbelgien und am Rand sind viele Orte zweisprachig. Neben `name` kommt `name:de` als eigener Eintrag dazu,
           zusammengesetzte Namen ("Kelmis - La Calamine") werden geteilt, und ALIASE ergänzt deutsche Formen, die in OSM
           nur unter name:de stehen (für den Zuschnitt ohne Tags). Meldungen des BRF schreiben "Weismes", nicht "Waimes".
Gespeichert werden nur Name, Koordinate und Rang. Keine weiteren Tags.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import config, geo  # noqa: E402

log = logging.getLogger("gazetteer")
MIRRORS = ("https://overpass.private.coffee/api/interpreter", "https://overpass-api.de/api/interpreter")
RANK = {"city": 1, "town": 2, "village": 3, "suburb": 4, "hamlet": 5}
QUERY = ('[out:json][timeout:80];node["place"~"^(city|town|village|hamlet|suburb)$"]["name"](%s,%s,%s,%s);'
         "out tags center;")
# Deutsche Formen zweisprachiger Orte in und um Ostbelgien (OSM: name:de). Nur Orte, deren `name` französisch ist.
ALIASE = {"Waimes": "Weismes", "Plombières": "Bleiberg", "Welkenraedt": "Welkenrath", "Stavelot": "Stablo",
          "Troisvierges": "Ulflingen", "Clervaux": "Clerf", "Wincrange": "Wintger"}


def namen(name: str, name_de: str = "") -> list[str]:
    """Alle Namensformen eines Orts: name, name:de, Teile von "A - B" bzw. "A / B", deutsche Form aus ALIASE."""
    out = [name]
    for sep in (" - ", " / "):
        if sep in name:
            out += [p.strip() for p in name.split(sep) if p.strip()]
    for extra in (name_de, ALIASE.get(name, "")):
        if extra:
            out.append(extra)
    seen: list[str] = []
    for n in out:
        if n not in seen:
            seen.append(n)
    return seen


def fetch() -> dict:
    s, w, n, e = config.BBOX
    body = urllib.parse.urlencode({"data": QUERY % (s, w, n, e)}).encode()
    last: Exception | None = None
    for url in MIRRORS:
        try:
            req = urllib.request.Request(url, data=body, headers={"User-Agent": f"Landblick/1.0 (+{config.CONTACT})"})
            with urllib.request.urlopen(req, timeout=120) as r:  # noqa: S310 (feste https-Ziele)
                return json.load(r)
        except Exception as exc:  # noqa: BLE001
            log.warning("%s: %s", url, exc)
            last = exc
    raise SystemExit(f"Overpass nicht erreichbar: {last}")


def build(data: dict) -> list[dict]:
    out, seen = [], set()
    for el in data.get("elements", []):
        t = el.get("tags") or {}
        name, kind = (t.get("name") or "").strip(), t.get("place")
        if not name or kind not in RANK or "lat" not in el:
            continue
        lat, lon = float(el["lat"]), float(el["lon"])
        if not geo.in_region(lat, lon, margin_km=5):
            continue
        for n in namen(name, (t.get("name:de") or "").strip()):
            key = (n, round(lat, 3), round(lon, 3))
            if key in seen:
                continue
            seen.add(key)
            out.append({"n": n, "lat": round(lat, 4), "lon": round(lon, 4), "k": RANK[kind]})
    out.sort(key=lambda o: (o["k"], o["n"]))
    return out


def zuschnitt(orte: list[dict]) -> list[dict]:
    """Vorhandenes Verzeichnis auf die Region plus 5 km schneiden und Namensformen ergänzen (ohne Netz)."""
    out, seen = [], set()
    for o in orte:
        if not geo.in_region(o["lat"], o["lon"], margin_km=5):
            continue
        for n in namen(o["n"]):
            key = (n, round(o["lat"], 3), round(o["lon"], 3))
            if key not in seen:
                seen.add(key)
                out.append({**o, "n": n})
    out.sort(key=lambda o: (o["k"], o["n"]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path)
    ap.add_argument("--zuschnitt", type=Path, help="vorhandenes orte.json statt Overpass")
    ap.add_argument("--output", type=Path, default=config.BASE_DIR / "app" / "data" / "orte.json")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if a.zuschnitt:
        orte = zuschnitt(json.loads(a.zuschnitt.read_text(encoding="utf-8")))
    else:
        orte = build(json.loads(a.input.read_text(encoding="utf-8")) if a.input else fetch())
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(orte, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    log.info("%d Orte nach %s", len(orte), a.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
