"""Tests für tools/build_vignette.py: UTM-Rechnung, Abstandsmaske entlang der Landesgrenze, erzeugte Dateien."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("build_vignette", ROOT / "tools" / "build_vignette.py")
bv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bv)
from app import geo  # noqa: E402


def test_utm32_rechnet_wie_die_umkehrung():
    for lon, lat in [(6.456, 49.846), (4.2, 51.0), (8.9, 48.3), (7.5, 50.4)]:
        x, y = bv.utm32(np.array([lon]), np.array([lat]))
        la, lo = geo.utm32_to_wgs84(float(x[0]), float(y[0]))
        assert abs(lo - lon) < 1e-6 and abs(la - lat) < 1e-6


def test_smoothstep_ist_monoton_und_begrenzt():
    t = np.linspace(-1, 2, 50)
    s = bv.smoothstep(t)
    assert s.min() == 0 and s.max() == 1 and np.all(np.diff(s) >= 0)


@pytest.mark.skipif(not (ROOT / "web/geo/vignette.json").exists(), reason="Vignette nicht gebaut (tools/build_vignette.py)")
def test_maske_klar_innen_schwarz_aussen_und_form_folgt_der_grenze():
    meta = json.loads((ROOT / "web/geo/vignette.json").read_text(encoding="utf-8"))
    a = np.array(Image.open(ROOT / "web/geo/vignette.png"))[:, :, 1].astype(float) / 255
    assert a.shape == (meta["hoehe"], meta["breite"])
    assert a[0].min() == 1 and a[-1].min() == 1 and a[:, 0].min() == 1 and a[:, -1].min() == 1   # Rand voll schwarz
    x0, y0, x1, y1 = meta["mercator"]

    def alpha_at(lon: float, lat: float) -> float:
        mx, my = bv.lonlat_to_merc(lon, lat)
        ix = int((mx - x0) / (x1 - x0) * meta["breite"])
        iy = int((y1 - my) / (y1 - y0) * meta["hoehe"])
        return float(a[iy, ix])

    assert alpha_at(6.035, 50.63) == 0.0       # Eupen
    assert alpha_at(6.13, 50.28) == 0.0        # Sankt Vith
    assert alpha_at(6.084, 50.775) == 0.0      # Aachen, gut 10 km jenseits der Grenze: noch klar
    assert alpha_at(5.57, 50.63) > 0.3         # Lüttich, rund 30 km westlich: schon abgedunkelt
    assert alpha_at(5.0, 50.4) > 0.99          # weit im Westen (Namur)
    # Die Form folgt der Grenze: Malmedy liegt zwischen beiden Teilen der DG und bleibt klar, obwohl es selbst nicht zur DG gehört
    assert alpha_at(6.028, 50.426) == 0.0
