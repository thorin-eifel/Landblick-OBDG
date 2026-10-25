#!/usr/bin/env python3
"""Prüft die Kartenarchive stichprobenartig: zwölf Orte in der Region, drei Zoomstufen, Kachel vorhanden, Gebäudeebene gefüllt.

Zweck:    Nach tools/build_region_tiles.py zeigen, dass die Archive die Fläche tragen (Abnahme O2).
Aufruf:   python tools/check_tiles.py --dir build/tiles/final
Ausgabe:  Tabelle Ort / Zoom / Archiv / Kachel / Gebäude; Exitcode 1 bei Lücke.
Zoom:     z8 und z13 aus region.pmtiles, z14 aus ring.pmtiles (Kerne: core.pmtiles, dort auch z15).
"""
from __future__ import annotations

import argparse
import gzip
import math
import sys
from pathlib import Path

from pmtiles.reader import MmapSource, Reader
from pmtiles.tile import zxy_to_tileid  # noqa: F401  (Reader.get nimmt z, x, y)

# (Ort, Breite, Länge, liegt in einem Zoom-15-Kern laut tools/tile_cores.yaml)
PLACES = [("Eupen", 50.6295, 6.0353, True), ("Kelmis", 50.7167, 6.0000, True), ("Sankt Vith", 50.2833, 6.1269, True),
          ("Burg-Reuland", 50.1972, 6.1389, True), ("Bütgenbach", 50.4256, 6.2050, True), ("Aachen", 50.7753, 6.0839, True),
          ("Verviers", 50.5891, 5.8624, True), ("Malmedy", 50.4256, 6.0277, True), ("Monschau", 50.5550, 6.2400, True),
          ("Clervaux", 50.0547, 6.0314, False), ("Vaals", 50.7706, 6.0186, True), ("Prüm", 50.2098, 6.4194, False)]


def tile_xy(lat: float, lon: float, z: int) -> tuple[int, int]:
    n = 2 ** z
    x = int((lon + 180) / 360 * n)
    y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
    return x, y


def layers(data: bytes) -> set[str]:
    try:
        import mapbox_vector_tile as mvt
    except ImportError:
        return set()
    raw = gzip.decompress(data) if data[:2] == b"\x1f\x8b" else data
    return set(mvt.decode(raw))


VIEWS = [("Region (Ostbelgien)", 50.44, 6.18, 9), ("Eupen", 50.6295, 6.0353, 12), ("Stadt (Aachen)", 50.7753, 6.0839, 13)]


def view_tiles(lat: float, lon: float, z: int, w: int = 1920, h: int = 1080) -> list[tuple[int, int, int]]:
    """Kacheln (512 px, wie MapLibre bei tileSize 512) für ein Fenster w x h, eine Kachel Rand dazu."""
    n = 2 ** z
    cx = (lon + 180) / 360 * n
    cy = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    hw, hh = w / 1024, h / 1024
    return [(z, x, y) for x in range(int(cx - hw) - 1, int(cx + hw) + 2) for y in range(int(cy - hh) - 1, int(cy + hh) + 2) if 0 <= x < n and 0 <= y < n]


def volume(rd) -> None:
    """Übertragungsmenge der Startansicht: Kacheln der Ansicht plus Elternkacheln bis Zoom 0, komprimiert, wie sie über das Netz gingen."""
    print("\nStartansichten, 1920x1080, Vektorkacheln komprimiert:")
    for name, lat, lon, z in VIEWS:
        seen: set[tuple[int, int, int]] = set()
        for t in view_tiles(lat, lon, z):
            seen.add(t)
        total = n = 0
        for (tz, x, y) in seen:
            arch = "core" if tz >= 14 else "region"
            data = rd[arch].get(tz, x, y)
            total += len(data or b"")
            n += bool(data)
        print(f"  {name:24} z{z:<2} {len(seen):3} Kacheln ({n} vorhanden), {total / 1e6:6.2f} MB")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", type=Path, default=Path("build/tiles/final"))
    ap.add_argument("--volume", action="store_true", help="zusätzlich Übertragungsmenge der Startansichten")
    args = ap.parse_args()
    fh = {n: open(args.dir / f"{n}.pmtiles", "rb") for n in ("region", "ring", "core")}
    rd = {n: Reader(MmapSource(f)) for n, f in fh.items()}
    bad = 0
    print(f"{'Ort':16} {'z':>2} {'Archiv':7} {'Kachel':7} Ebenen")
    for name, lat, lon, in_core in PLACES:
        for z, arch in ((8, "region"), (13, "region"), (14, "ring")):
            if z == 14 and in_core:
                arch = "core"
            x, y = tile_xy(lat, lon, z)
            data = rd[arch].get(z, x, y)
            ls = layers(data) if data else set()
            ok = bool(data) and (z < 14 or not ls or "buildings" in ls)
            bad += not ok
            print(f"{name:16} {z:>2} {arch:7} {'ja' if data else 'FEHLT':7} {','.join(sorted(ls)) or '-'}{'' if ok else '  <-- keine Gebäude' if data else ''}")
        if in_core:
            x, y = tile_xy(lat, lon, 15)
            data = rd["core"].get(15, x, y)
            bad += not data
            print(f"{name:16} {15:>2} {'core':7} {'ja' if data else 'FEHLT':7}")
    print("Lücken:", bad)
    if args.volume:
        volume(rd)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
